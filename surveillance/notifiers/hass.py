from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from surveillance.notifiers import Notifier

log = logging.getLogger(__name__)


class HassNotifier(Notifier):
    """Push events to Home Assistant event bus via REST API (stdlib only).

    Config section ``hass``::

        hass:
          enabled: true
          url: "http://homeassistant:8123"
          token: "${HASS_TOKEN}"

    Events are prefixed with ``camera.`` (e.g. ``camera.person``).
    """

    def __init__(self, url: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._token = token
        log.info("HA notifier 已启用: %s", self._url)

    @classmethod
    def from_config(cls, raw: dict) -> HassNotifier | None:
        cfg = raw.get("hass")
        if not cfg or not cfg.get("enabled"):
            return None
        url = str(cfg.get("url", "")).rstrip("/")
        token = str(cfg.get("token", ""))
        if not url or not token:
            log.warning("hass 配置不完整（缺少 url 或 token），跳过")
            return None
        return cls(url, token)

    def fire(self, event_type: str, data: dict) -> None:
        event = f"camera.{event_type}"
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")

        import threading

        t = threading.Thread(
            target=self._post,
            args=(event, payload),
            name=f"ha-{event}",
            daemon=True,
        )
        t.start()

    def _post(self, event: str, payload: bytes) -> None:
        try:
            req = Request(
                f"{self._url}/api/events/{event}",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
            with urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    log.warning("HA 返回非 200: %s", resp.status)
        except HTTPError as e:
            log.warning("HA HTTP 错误 %s: %s", e.code, e.reason)
        except URLError:
            log.warning("HA 连接失败: %s", self._url)
        except Exception:
            log.exception("HA 推送异常")
