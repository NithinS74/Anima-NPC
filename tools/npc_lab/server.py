"""Bounded loopback-only HTTP bridge for a single-user development console."""

import asyncio
import concurrent.futures
import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tools.npc_lab.service import CancelRequest, LabService, LabTurn

STATIC = Path(__file__).parent / "web"
ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/style.css": ("style.css", "text/css")}
for character in ("mira", "elin", "daren", "iona"):
    ASSETS[f"/portraits/{character}.svg"] = (f"portraits/{character}.svg", "image/svg+xml")


class LabServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, service: LabService, port=8765):
        self.service = service
        self.token = secrets.token_urlsafe(32)
        self.workers = threading.BoundedSemaphore(8)
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.loop.run_forever, daemon=True, name="npc-lab-loop")
        try:
            super().__init__(("127.0.0.1", port), LabHandler)
        except BaseException:
            self.loop.close()
            raise
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.loop_thread.start()

    def process_request(self, request, client_address):
        if not self.workers.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.workers.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.workers.release()

    def call(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        try:
            return future.result(timeout=12)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError from None

    def server_close(self):
        super().server_close()
        if self.loop.is_running():
            async def stop_tasks():
                tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                for task in tasks:
                    task.cancel()
                if tasks:
                    await asyncio.wait(tasks, timeout=1)
            try:
                asyncio.run_coroutine_threadsafe(stop_tasks(), self.loop).result(timeout=2)
            finally:
                self.loop.call_soon_threadsafe(self.loop.stop)
                self.loop_thread.join(timeout=2)
                if not self.loop_thread.is_alive():
                    self.loop.close()


class LabHandler(BaseHTTPRequestHandler):
    server: LabServer

    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *args):
        pass  # no user text, tokens or provider errors in access logs

    def send(self, status, body, content_type="application/json"):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get("Host") == self.server.origin.removeprefix("http://")

    def do_GET(self):
        if not self.valid_host():
            self.send(403, {"error": "invalid_host"})
        elif self.path == "/api/info":
            self.send(200, self.server.service.info())
        elif self.path in ASSETS:
            name, mime = ASSETS[self.path]
            body = (STATIC / name).read_bytes()
            if name == "index.html":
                body = body.replace(b"__LAB_TOKEN__", self.server.token.encode("ascii"))
            self.send(200, body, mime)
        else:
            self.send(404, {"error": "not_found"})

    def do_POST(self):
        if not self.valid_host() or self.headers.get("Origin") != self.server.origin or not hmac.compare_digest(
            self.headers.get("X-Lab-Token", ""), self.server.token
        ):
            self.send(403, {"error": "invalid_origin_or_token"})
            return
        if self.path not in {"/api/turn", "/api/cancel"}:
            self.send(404, {"error": "not_found"})
            return
        try:
            if self.headers.get("Transfer-Encoding") or self.headers.get_content_type() != "application/json":
                self.send(415, {"error": "json_required"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 16384:
                self.send(413, {"error": "body_limit"})
                return
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("incomplete body")
            if self.path == "/api/turn":
                turn = LabTurn.model_validate_json(body)
                result = self.server.call(self.server.service.turn(turn))
            else:
                request = CancelRequest.model_validate_json(body)
                result = self.server.call(self.server.service.cancel(request))
            self.send(409 if result.get("error") == "lab_busy" else 200, result)
        except ValueError:
            self.send(400, {"error": "invalid_test_input"})
        except TimeoutError:
            self.send(504, {"error": "lab_timeout"})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self.send(500, {"error": "lab_failure"})  # never raw validation/provider details
