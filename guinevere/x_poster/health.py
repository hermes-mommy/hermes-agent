from __future__ import annotations

"""P13 X Poster — Health check HTTP endpoint."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_HEALTH_BIND_HOST: str = "127.0.0.1"


class XPosterHealthEndpoint:
    """HTTP health endpoint for systemd and monitoring.

    Runs a :class:`ThreadingHTTPServer` in a background daemon thread,
    bound to ``127.0.0.1:<port>`` (default 8097).

    Endpoints:
        ``GET /health``
            Returns JSON ``{"status": "ok" | "degraded" | "unhealthy", ...}``.
        ``GET /api/status``
            Returns queue depth, session health, next slot.
        ``GET /api/posts``
            Returns posts filtered by state (query param).
        ``POST /api/post-action``
            Cancel / hold / resume a post.
        ``POST /api/retry-failed``
            Retry all held/failed posts.
        ``POST /api/dry-run``
            Execute post without publishing.
        ``POST /api/enqueue``
            Enqueue a new post to schedule (multipart form).
        ``POST /api/post-now``
            Post immediately — bypass queue and schedule (multipart form).
    """

    _server: ThreadingHTTPServer | None
    _thread: Thread | None
    _service_ref: Any

    def __init__(self, service_ref: Any, port: int = 8097) -> None:
        self._service_ref = service_ref
        self._port = port
        self._server = None
        self._thread = None

    async def start(self) -> None:
        """Start the health HTTP server in a daemon thread."""
        svc = self._service_ref

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path.startswith("/health"):
                    self._send_health()
                elif self.path.startswith("/api/status"):
                    self._send_status()
                elif self.path.startswith("/api/posts"):
                    self._send_posts()
                elif self.path.startswith("/api/engagement"):
                    self._send_engagement()
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'{"error":"not found"}')

            def do_POST(self) -> None:  # noqa: N802
                if self.path.startswith("/api/post-action"):
                    self._handle_post_action()
                elif self.path.startswith("/api/retry-failed"):
                    self._handle_retry_failed()
                elif self.path.startswith("/api/dry-run"):
                    self._handle_dry_run()
                elif self.path.startswith("/api/enqueue-batch"):
                    self._handle_enqueue_batch()
                elif self.path.startswith("/api/enqueue"):
                    self._handle_enqueue()
                elif self.path.startswith("/api/post-now"):
                    self._handle_post_now()
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'{"error":"not found"}')

            def _send_health(self) -> None:
                try:
                    status = {"status": "ok" if svc._running else "degraded"}
                    body = json.dumps(status).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception:
                    logger.exception("x_poster.health_handler_error")
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b'{"error":"internal"}')

            def _send_status(self) -> None:
                try:
                    data = svc.get_status_summary()
                    body = json.dumps({"ok": True, "status": data}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.status_api_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def _send_posts(self) -> None:
                try:
                    from urllib.parse import urlparse, parse_qs
                    qs = parse_qs(urlparse(self.path).query)
                    state = qs.get("state", ["pending"])[0]
                    limit = int(qs.get("limit", ["10"])[0])
                    posts = svc.list_posts(state=state, limit=limit)
                    body = json.dumps({"ok": True, "posts": posts}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.posts_api_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def _send_engagement(self) -> None:
                try:
                    from urllib.parse import urlparse, parse_qs
                    qs = parse_qs(urlparse(self.path).query)
                    range_param = qs.get("range", ["3mo"])[0]
                    data = svc.get_engagement_summary(range_param)
                    body = json.dumps({"ok": True, **data}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.engagement_api_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def _handle_post_action(self) -> None:
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length)
                    payload = json.loads(raw)
                    action = payload.get("action", "")
                    post_id = payload.get("post_id", "")
                    result = svc.execute_post_action(action, post_id)
                    body = json.dumps({"ok": True, **result}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.post_action_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def _handle_retry_failed(self) -> None:
                try:
                    count = svc.retry_all_failed()
                    body = json.dumps({"ok": True, "retried_count": count}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.retry_failed_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def _handle_dry_run(self) -> None:
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length)
                    payload = json.loads(raw)
                    post_id = payload.get("post_id", "")
                    result = svc.execute_dry_run(post_id)
                    body = json.dumps({"ok": True, "dry_run_result": result}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.dry_run_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def _handle_enqueue(self) -> None:
                try:
                    # Multipart form parsing
                    content_type = self.headers.get("Content-Type", "")
                    if "multipart/form-data" not in content_type:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"error":"expected multipart/form-data"}')
                        return

                    boundary = content_type.split("boundary=")[-1]
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length)
                    parts = raw.split(f"--{boundary}".encode())
                    
                    file_data = b""
                    filename = ""
                    fields: dict[str, str] = {}
                    
                    for part in parts[1:-1]:
                        if b"filename=" in part.split(b"\r\n\r\n")[0]:
                            file_data = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n")
                            header = part.split(b"\r\n\r\n")[0].decode()
                            filename = header.split('filename="')[-1].split('"')[0]
                        else:
                            header = part.split(b"\r\n\r\n")[0].decode()
                            value = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n").decode()
                            if 'name="' in header:
                                key = header.split('name="')[-1].split('"')[0]
                                fields[key] = value

                    result = svc.enqueue_post(
                        filename=filename,
                        file_data=file_data,
                        content_type=fields.get("content_type", ""),
                        author_id=fields.get("author_id", ""),
                        message_id=fields.get("message_id", ""),
                        caption_hint=fields.get("caption_hint", ""),
                    )
                    body = json.dumps({"ok": True, **result}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.enqueue_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def _handle_enqueue_batch(self) -> None:
                """Handle batch enqueue request with multiple media files."""
                try:
                    content_type = self.headers.get("Content-Type", "")
                    if "multipart/form-data" not in content_type:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"error":"expected multipart/form-data"}')
                        return

                    boundary = content_type.split("boundary=")[-1]
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length)
                    parts = raw.split(f"--{boundary}".encode())
                    
                    files_data = []
                    fields: dict[str, str] = {}
                    
                    for part in parts[1:-1]:
                        if b"filename=" in part.split(b"\r\n\r\n")[0]:
                            file_data = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n")
                            header = part.split(b"\r\n\r\n")[0].decode()
                            filename = header.split('filename="')[-1].split('"')[0]
                            # Extract content-type from header if present
                            content_type_file = ""
                            if 'Content-Type:' in header:
                                content_type_file = header.split('Content-Type: ')[-1].split('\r\n')[0].strip()
                            files_data.append({"filename": filename, "data": file_data, "content_type": content_type_file})
                        else:
                            header = part.split(b"\r\n\r\n")[0].decode()
                            value = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n").decode()
                            if 'name="' in header:
                                key = header.split('name="')[-1].split('"')[0]
                                fields[key] = value

                    result = svc.enqueue_post_batch(
                        files_data=files_data,
                        author_id=fields.get("author_id", ""),
                        message_id=fields.get("message_id", ""),
                        caption_hint=fields.get("caption_hint", ""),
                    )
                    body = json.dumps({"ok": True, **result}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.enqueue_batch_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def _handle_post_now(self) -> None:
                """Handle immediate post request (bypasses queue/schedule). Supports batch upload."""
                try:
                    content_type = self.headers.get("Content-Type", "")
                    if "multipart/form-data" not in content_type:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"error":"expected multipart/form-data"}')
                        return

                    boundary = content_type.split("boundary=")[-1]
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length)
                    parts = raw.split(f"--{boundary}".encode())

                    files_data = []
                    fields: dict[str, str] = {}

                    for part in parts[1:-1]:
                        if b"filename=" in part.split(b"\r\n\r\n")[0]:
                            file_data = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n")
                            header = part.split(b"\r\n\r\n")[0].decode()
                            filename = header.split('filename="')[-1].split('"')[0]
                            content_type_file = ""
                            if 'Content-Type:' in header:
                                content_type_file = header.split('Content-Type: ')[-1].split('\r\n')[0].strip()
                            files_data.append({"filename": filename, "data": file_data, "content_type": content_type_file})
                        else:
                            header = part.split(b"\r\n\r\n")[0].decode()
                            value = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n").decode()
                            if 'name="' in header:
                                key = header.split('name="')[-1].split('"')[0]
                                fields[key] = value

                    result = svc.post_now_batch(
                        files_data=files_data,
                        author_id=fields.get("author_id", ""),
                        caption_hint=fields.get("caption_hint", ""),
                    )
                    body = json.dumps(result).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    logger.warning("x_poster.post_now_error", error=str(exc))
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode())

            def log_message(self, format: str, *args: Any) -> None:
                pass  # Suppress default logging

        self._server = ThreadingHTTPServer((_HEALTH_BIND_HOST, self._port), Handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True, name="x-poster-health")
        self._thread.start()
        logger.info("x_poster.health_started", host=_HEALTH_BIND_HOST, port=self._port)

    async def stop(self) -> None:
        """Shutdown the health HTTP server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("x_poster.health_stopped")


__all__ = ["XPosterHealthEndpoint"]
