from __future__ import annotations

import csv
import http.server
import json
import logging
import os
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Any

log = logging.getLogger(__name__)

_HERE = Path(__file__).parent
_HTML = (_HERE / "static" / "index.html").read_text(encoding="utf-8")


def _fmt_iso(s: str) -> str:
    """Normalize ISO-like string (accept partial like 2026-05-07T14:30)."""
    s = s.strip()
    if ":" in s and s.count(":") == 1:
        s += ":00"
    return s


def _parse_timeline_csv(csv_path: Path, data_prefix: str) -> list[dict[str, Any]]:
    """Read timeline.csv, convert paths to URLs."""
    rows: list[dict[str, Any]] = []
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                snap_url = _rel_to_url(data_prefix, row.get("snapshot_path", ""))
                clip_url = _rel_to_url(data_prefix, row.get("clip_path", ""))
                rows.append({
                    "start_time": row.get("start_time", ""),
                    "end_time": row.get("end_time", ""),
                    "event_type": row.get("event_type", ""),
                    "snapshot_url": snap_url,
                    "clip_url": clip_url,
                })
    except (OSError, csv.Error):
        pass
    return rows


def _rel_to_url(data_prefix: str, rel_path: str) -> str | None:
    if not rel_path:
        return None
    return f"/{data_prefix}/{rel_path}"


def _date_range(start_str: str, end_str: str) -> list[str]:
    """Yield YYYY-MM-DD strings from start to end inclusive."""
    days: list[str] = []
    try:
        s = date.fromisoformat(start_str[:10])
        e = date.fromisoformat(end_str[:10])
    except ValueError:
        return days
    d = s
    while d <= e:
        days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def _make_handler(camera_ids: list[str], data_dir: Path):
    """Factory: return a RequestHandler subclass bound to config."""

    class Handler(http.server.BaseHTTPRequestHandler):
        # silence default logging per-request
        def log_message(self, fmt, *args):
            log.debug(fmt, *args)

        def _send_json(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str, status=200):
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_static(self, file_path: Path):
            try:
                if not file_path.is_file():
                    self.send_error(404)
                    return
                ext = file_path.suffix.lower()
                mime = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".mp4": "video/mp4",
                }.get(ext, "application/octet-stream")

                file_size = file_path.stat().st_size
                range_header = self.headers.get("Range")

                if range_header and range_header.startswith("bytes="):
                    range_val = range_header[6:]
                    start: int | None = None
                    end: int | None = None
                    if "-" in range_val:
                        parts = range_val.split("-", 1)
                        start = int(parts[0]) if parts[0] else 0
                        end = int(parts[1]) if parts[1] else file_size - 1
                    if start is None:
                        start = 0
                    if end is None or end >= file_size:
                        end = file_size - 1
                    if start > end or start >= file_size:
                        self.send_error(416)
                        return

                    length = end - start + 1
                    with open(file_path, "rb") as f:
                        f.seek(start)
                        data = f.read(length)

                    self.send_response(206)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(length))
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "max-age=3600")
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    data = file_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "max-age=3600")
                    self.end_headers()
                    self.wfile.write(data)
            except OSError:
                self.send_error(404)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)

            if path == "/":
                return self._send_html(_HTML)

            if path == "/api/cameras":
                return self._send_json(camera_ids)

            if path == "/api/timeline":
                cam = (qs.get("camera") or [None])[0]
                d = (qs.get("date") or [None])[0]
                if not cam or not d:
                    return self._send_json({"error": "missing camera or date"}, 400)
                csv_file = data_dir / cam / d / "timeline.csv"
                prefix = f"data/{cam}/{d}"
                rows = _parse_timeline_csv(csv_file, prefix)
                return self._send_json(rows)

            if path == "/api/timeline/range":
                cam = (qs.get("camera") or [None])[0]
                start = (qs.get("start") or [None])[0]
                end = (qs.get("end") or [None])[0]
                if not cam or not start or not end:
                    return self._send_json({"error": "missing camera, start, or end"}, 400)
                start = _fmt_iso(start)
                end = _fmt_iso(end)
                all_rows: list[dict[str, Any]] = []
                for day in _date_range(start, end):
                    csv_file = data_dir / cam / day / "timeline.csv"
                    prefix = f"data/{cam}/{day}"
                    rows = _parse_timeline_csv(csv_file, prefix)
                    for r in rows:
                        if r["start_time"] >= start and r["start_time"] <= end:
                            all_rows.append(r)
                return self._send_json(all_rows)

            # Static files under /data/
            if path.startswith("/data/"):
                rel = path[len("/data/"):]
                norm = os.path.normpath(rel)
                if norm.startswith("..") or norm.startswith("/"):
                    return self.send_error(403)
                file_path = (data_dir / norm).resolve()
                try:
                    file_path.relative_to(data_dir.resolve())
                except ValueError:
                    return self.send_error(403)
                return self._serve_static(file_path)

            self.send_error(404)

    return Handler


def start_http_server(
    camera_ids: list[str],
    data_base_dir: str = "data",
    addr: str = ":8080",
) -> None:
    """Start HTTP server in a daemon thread.  addr format: ``:8080`` or ``0.0.0.0:8080``."""
    host = "0.0.0.0"
    port = 8080
    if ":" in addr:
        parts = addr.rsplit(":", 1)
        host = parts[0] if parts[0] else "0.0.0.0"
        port = int(parts[1])

    data_dir = Path(data_base_dir).resolve()
    handler = _make_handler(camera_ids, data_dir)
    server = http.server.ThreadingHTTPServer((host, port), handler)

    t = threading.Thread(target=server.serve_forever, name="http-server", daemon=True)
    t.start()
    log.info("HTTP 服务器已启动: http://%s:%s", host, port)
