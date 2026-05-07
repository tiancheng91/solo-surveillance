from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from onvif import ONVIFCamera

log = logging.getLogger(__name__)


@dataclass
class OnvifConfig:
    host: str
    port: int = 80
    username: str = ""
    password: str = ""
    profile: int = 0


def parse_onvif_url(url: str) -> OnvifConfig:
    """Parse ``onvif://username:password@host:port?profile=N``."""
    parsed = urlparse(url)
    if parsed.scheme != "onvif":
        raise ValueError(f"not an onvif url: {url}")

    host = parsed.hostname or ""
    port = parsed.port or 80
    username = parsed.username or ""
    password = parsed.password or ""
    qs = parse_qs(parsed.query)
    profile = int(qs.get("profile", [0])[0])

    return OnvifConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        profile=profile,
    )


def _embed_credentials(raw_uri: str, username: str, password: str) -> str:
    """Embed username:password into an RTSP URL."""
    if not username:
        return raw_uri
    p = urlparse(raw_uri)
    netloc = f"{username}:{password}@{p.hostname}"
    if p.port:
        netloc += f":{p.port}"
    return p._replace(netloc=netloc).geturl()


def _normalize_host(raw_uri: str, expected_host: str) -> str:
    """Replace host in URI with expected_host (some cameras return localhost)."""
    p = urlparse(raw_uri)
    if p.hostname and p.hostname not in (expected_host, "127.0.0.1", "localhost", "0.0.0.0"):
        return raw_uri
    netloc = f"{expected_host}:{p.port}" if p.port else expected_host
    return p._replace(netloc=netloc).geturl()


class OnvifUrlResolver:
    """Connect to an ONVIF device and resolve the RTSP stream URI."""

    def __init__(self, cfg: OnvifConfig) -> None:
        self._cfg = cfg
        self._cam: ONVIFCamera | None = None

    def resolve(self) -> str:
        cfg = self._cfg
        log.info(
            "ONVIF 解析: %s:%s profile=%s",
            cfg.host,
            cfg.port,
            cfg.profile,
        )

        self._cam = ONVIFCamera(
            cfg.host,
            cfg.port,
            cfg.username,
            cfg.password,
        )

        # 验证连接
        try:
            self._cam.create_devicemgmt_service()
        except Exception:
            log.exception("ONVIF 设备连接失败: %s:%s", cfg.host, cfg.port)
            raise

        media = self._cam.create_media_service()
        profiles = media.GetProfiles()
        if not profiles:
            raise RuntimeError(f"ONVIF 设备无可用 media profile: {cfg.host}")

        if cfg.profile >= len(profiles):
            log.warning(
                "profile 索引 %s 越界（共 %s 个），使用 profile 0",
                cfg.profile,
                len(profiles),
            )
            profile = profiles[0]
        else:
            profile = profiles[cfg.profile]

        stream_uri = media.GetStreamUri({
            "StreamSetup": {
                "Stream": "RTP-Unicast",
                "Transport": {"Protocol": "RTSP"},
            },
            "ProfileToken": profile.token,
        })

        raw = str(stream_uri.Uri)
        raw = _normalize_host(raw, cfg.host)
        raw = _embed_credentials(raw, cfg.username, cfg.password)
        log.info("ONVIF 解析完成: %s", re.sub(r"://[^@]+@", "://***@", raw))
        return raw

    def close(self) -> None:
        if self._cam is not None:
            try:
                # ONVIFCamera has no formal close - just drop the ref
                pass
            except Exception:
                pass
            self._cam = None
