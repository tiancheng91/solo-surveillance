from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

import cv2
import numpy as np

from surveillance.detectors.base import VisionContext, VisionDetector, VisionResult

log = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """你是一个监控摄像头画面分析助手。
请分析当前画面中是否存在以下场景，对每个场景输出 0~1 的置信度分数。
只返回 JSON 格式（不要包含其他文字）：

{json_marker}
{scenes_text}
{json_marker}

注意：
- 0.0 = 完全不符合，1.0 = 完全符合
- 如果没有足够依据判断某个场景，输出 0.0
- 多个场景可以同时存在"""


class LLMVisionDetector(VisionDetector):
    """Vision detector that calls an LLM API (Anthropic / OpenAI) for scene understanding.

    Reads from two config sections merged together::

        # ── 全局 LLM 连接配置 ──
        llm:
          provider: "anthropic"
          model: "claude-sonnet-4-20250514"
          api_key: "${ANTHROPIC_API_KEY}"
          base_url: ""
          cooldown_sec: 60
          resize_width: 640

        # ── detectors 下的场景定义（可 per-camera 覆盖）──
        detectors:
          llm_vision:
            enabled: true
            conf: 0.6
            scenes:
              feeding: "婴儿正在吃奶"

    ``analyze_batch()`` sends all frames in a single API call (multi-image).
    """

    name = "llm_vision"

    def __init__(self, llm_cfg: dict, vision_cfg: dict) -> None:
        self.enabled = bool(vision_cfg.get("enabled", False))
        self.provider = str(llm_cfg.get("provider", "anthropic")).lower()
        self.model = str(llm_cfg.get("model", "claude-sonnet-4-20250514"))
        self.api_key = str(llm_cfg.get("api_key", ""))
        self.base_url = str(llm_cfg.get("base_url", "")).strip() or None
        self.conf_threshold = float(vision_cfg.get("conf", 0.6))
        self.cooldown_sec = float(llm_cfg.get("cooldown_sec", 60.0))
        self.resize_width = int(llm_cfg.get("resize_width", 640))
        self.system_prompt = str(vision_cfg.get("system_prompt", ""))
        self.scenes: dict[str, str] = vision_cfg.get("scenes", {}) or {}
        self._last_call = 0.0
        self._client = None

    @classmethod
    def from_config(cls, llm_cfg: dict | None, vision_cfg: dict | None) -> LLMVisionDetector | None:
        """Factory: returns None when not enabled or misconfigured."""
        vc = vision_cfg or {}
        if not vc.get("enabled"):
            return None
        lc = llm_cfg or {}
        if not lc.get("api_key"):
            return None
        return cls(lc, vc)

    # ── public API ──────────────────────────────────────────────

    def analyze(self, frame_bgr: np.ndarray, ctx=None) -> VisionResult:
        return self.analyze_batch([frame_bgr], ctx)

    def analyze_batch(
        self,
        frames: list[np.ndarray],
        ctx: VisionContext | None = None,
    ) -> VisionResult:
        if not self.enabled or not self.scenes or not self.api_key:
            return VisionResult(labels={})

        now = time.time()
        if now - self._last_call < self.cooldown_sec:
            log.debug("[llm_vision] cooldown 中，跳过 (%.1fs / %.1fs)",
                      now - self._last_call, self.cooldown_sec)
            return VisionResult(labels={})
        self._last_call = now

        try:
            b64_frames = [self._encode_frame(f) for f in frames]
        except Exception:
            log.exception("[llm_vision] 帧编码失败")
            return VisionResult(labels={})

        scenes_text = "\n".join(f"  {k}: {v}" for k, v in self.scenes.items())
        marker = "---SCENES---"
        prompt = _PROMPT_TEMPLATE.format(json_marker=marker, scenes_text=scenes_text)

        try:
            if self.provider == "openai":
                raw = self._call_openai(b64_frames, prompt)
            else:
                raw = self._call_anthropic(b64_frames, prompt)
        except Exception:
            log.exception("[llm_vision] API 调用失败")
            return VisionResult(labels={})

        labels = self._parse_response(raw)
        if not labels:
            log.debug("[llm_vision] LLM 原始响应: %s", raw[:300])
        log.info("[llm_vision] 场景识别结果 (frames=%d): %s", len(frames), labels)
        return VisionResult(labels=labels)

    def close(self) -> None:
        self._client = None

    # ── internals ───────────────────────────────────────────────

    def _encode_frame(self, frame_bgr: np.ndarray) -> str:
        """BGR numpy array → base64 JPEG string (optionally resized)."""
        if self.resize_width > 0:
            h, w = frame_bgr.shape[:2]
            if w > self.resize_width:
                scale = self.resize_width / w
                new_w = self.resize_width
                new_h = int(h * scale)
                frame_bgr = cv2.resize(frame_bgr, (new_w, new_h),
                                       interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        ok, buf = cv2.imencode(".jpg", rgb, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            raise RuntimeError("imencode failed")
        return base64.b64encode(buf).decode("utf-8")

    def _call_anthropic(self, b64_frames: list[str], prompt: str) -> str:
        try:
            import anthropic
        except ImportError:
            log.warning("[llm_vision] anthropic 未安装，请执行: uv add anthropic")
            return ""

        client: anthropic.Anthropic = self._get_client(anthropic.Anthropic)
        content: list[dict] = []
        for b64 in b64_frames:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            })
        content.append({"type": "text", "text": prompt})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 512,
            "messages": [{"role": "user", "content": content}],
        }
        if self.system_prompt:
            kwargs["system"] = self.system_prompt

        resp = client.messages.create(**kwargs)
        return resp.content[0].text if resp.content else ""

    def _call_openai(self, b64_frames: list[str], prompt: str) -> str:
        try:
            import openai
        except ImportError:
            log.warning("[llm_vision] openai 未安装，请执行: uv add openai")
            return ""

        client: openai.OpenAI = self._get_client(openai.OpenAI)
        content: list[dict] = []
        for b64 in b64_frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        content.append({"type": "text", "text": prompt})

        msgs: list[dict] = [{"role": "user", "content": content}]
        if self.system_prompt:
            msgs.insert(0, {"role": "system", "content": self.system_prompt})

        resp = client.chat.completions.create(
            model=self.model,
            max_tokens=512,
            messages=msgs,
        )
        return resp.choices[0].message.content or ""

    def _parse_response(self, raw: str) -> dict[str, float]:
        """Extract ``{scene: confidence}`` from LLM JSON response."""
        if not raw:
            return {}
        # Strip markdown code fences
        text = raw.strip()
        for fence in ("```json", "```"):
            if text.startswith(fence):
                text = text[len(fence):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log.warning("[llm_vision] LLM 返回非 JSON: %s", raw[:200])
            return {}

        if not isinstance(data, dict):
            return {}

        labels: dict[str, float] = {}
        for key in self.scenes:
            val = data.get(key, data.get(key.replace("_", " "), 0.0))
            try:
                score = float(val)
            except (TypeError, ValueError):
                score = 0.0
            score = max(0.0, min(1.0, score))
            if score >= self.conf_threshold:
                labels[f"llm_{key}"] = round(score, 4)
        return labels

    def _get_client(self, cls: type):
        if self._client is None:
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = cls(**kwargs)
        return self._client
