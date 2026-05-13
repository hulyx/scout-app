"""
ExtensionBridge — Local HTTP server (port 8765) that mediates between
Python workers and the Scout Companion browser extension.

Requests from workers → queued as commands → polled by extension →
results posted back → delivered to waiting workers.
"""

import http.server
import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BRIDGE_PORT = 8765
COMMAND_POLL_TIMEOUT = 2.0  # extension polls every ~2s
WORKER_TIMEOUT = 60.0


_bridge_instance: Optional["ExtensionBridge"] = None


def set_bridge(bridge: Optional["ExtensionBridge"]):
    global _bridge_instance
    _bridge_instance = bridge


def get_bridge() -> Optional["ExtensionBridge"]:
    return _bridge_instance


class TimeoutError(Exception):
    """Raised when an extension command does not complete in time."""


class _BridgeHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler that dispatches to the shared bridge state."""

    # Shared state set by ExtensionBridge when creating the server.
    bridge: "ExtensionBridge" = None  # type: ignore

    # ------------------------------------------------------------------
    # Suppress default stderr logging
    def log_message(self, fmt, *args):
        logger.debug("bridge: " + fmt, *args)

    # ------------------------------------------------------------------
    # Routing
    def do_GET(self):
        parsed = self._parse_path()
        if parsed == ("api", "ping"):
            return self._json({"status": "ok"})
        elif parsed == ("api", "commands"):
            return self._get_commands()
        self._send(404, {"error": "not found"})

    def do_POST(self):
        parsed = self._parse_path()
        if parsed[0] == "api" and parsed[1] == "execute":
            return self._post_execute()
        if len(parsed) == 3 and parsed[0] == "api" and parsed[1] == "result":
            return self._post_result(parsed[2])
        self._send(404, {"error": "not found"})

    # ------------------------------------------------------------------
    # Helpers
    def _parse_path(self):
        parts = self.path.strip("/").split("/")
        return tuple(parts)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def _send(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: dict):
        self._send(200, data)

    # ------------------------------------------------------------------
    # Endpoints
    def _get_commands(self):
        bridge = self.bridge
        bridge._last_extension_poll = time.monotonic()
        with bridge._lock:
            pending = []
            for cid, cmd in bridge._pending.items():
                # Only return to extension if not already claimed by another poll
                if not cmd.get("claimed"):
                    cmd["claimed"] = True
                    pending.append({
                        "id": cid,
                        "action": cmd["action"],
                        "params": cmd["params"],
                    })
                    if len(pending) >= 5:
                        break
        self._json(pending)

    def _post_execute(self):
        body = self._read_body()
        action = body.get("action", "")
        params = body.get("params", {})
        cid = str(uuid.uuid4())
        bridge = self.bridge
        with bridge._lock:
            bridge._pending[cid] = {
                "action": action,
                "params": params,
                "claimed": False,
            }
        self._json({"id": cid})

    def _post_result(self, command_id: str):
        body = self._read_body()
        bridge = self.bridge
        with bridge._lock:
            bridge._results[command_id] = body
            # Remove from pending so it won't be polled again
            bridge._pending.pop(command_id, None)
            # Notify any waiting worker
            bridge._cond.notify_all()
        self._json({"status": "ack"})


class ExtensionBridge:
    """Thread-safe bridge that queues commands for the browser extension
    and delivers results back to waiting Python workers.

    Usage::

        bridge = ExtensionBridge()
        bridge.start()
        result = bridge.execute("search_etsy", {"query": "cat mug"})
        bridge.stop()
    """

    def __init__(self, port: int = BRIDGE_PORT):
        self.port = port
        self._server: Optional[http.server.HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._pending: Dict[str, dict] = {}
        self._results: Dict[str, dict] = {}
        self._last_extension_poll: float = 0.0

    @property
    def extension_connected(self) -> bool:
        """True if the extension has polled for commands in the last 30 seconds."""
        return (time.monotonic() - self._last_extension_poll) < 30.0

    # ------------------------------------------------------------------
    # Lifecycle
    def start(self):
        """Start the bridge HTTP server on a background thread."""
        if self._server is not None:
            logger.warning("Bridge already running")
            return

        _BridgeHandler.bridge = self
        set_bridge(self)
        self._server = http.server.HTTPServer(
            ("127.0.0.1", self.port), _BridgeHandler
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True, name="bridge-http"
        )
        self._thread.start()
        logger.info("ExtensionBridge listening on 127.0.0.1:%d", self.port)

    def stop(self):
        """Shut down the bridge HTTP server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            self._thread = None
            set_bridge(None)
            logger.info("ExtensionBridge stopped")

    @property
    def running(self) -> bool:
        return self._server is not None

    # ------------------------------------------------------------------
    # Command API
    def execute(self, action: str, params: dict = None,
                timeout: float = WORKER_TIMEOUT) -> dict:
        """Queue a command and block until the extension returns a result.

        Returns the result dict (with at least a ``"status"`` key).

        Raises:
            TimeoutError: if the extension does not respond in time.
        """
        if params is None:
            params = {}
        cid = str(uuid.uuid4())
        with self._lock:
            self._pending[cid] = {
                "action": action,
                "params": params,
                "claimed": False,
            }

        deadline = time.monotonic() + timeout
        try:
            while True:
                with self._lock:
                    if cid in self._results:
                        return self._results.pop(cid)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._pending.pop(cid, None)
                        raise TimeoutError(
                            f"Command {action} (id={cid}) timed out after "
                            f"{timeout}s"
                        )
                    self._cond.wait(timeout=min(remaining, 1.0))
        finally:
            # Cleanup regardless
            with self._lock:
                self._pending.pop(cid, None)
                self._results.pop(cid, None)


# ------------------------------------------------------------------
# Convenience utilities
def is_extension_available(port: int = BRIDGE_PORT) -> bool:
    """Return True if the bridge is reachable on localhost."""
    import urllib.request
    try:
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/ping", timeout=2
        )
        return resp.status == 200
    except Exception:
        return False


def is_extension_connected() -> bool:
    """Return True if the browser extension has polled recently (<30s).

    Unlike is_extension_available() which only checks the bridge server,
    this checks if the extension itself is active and polling.
    """
    bridge = get_bridge()
    if bridge is None:
        return False
    return bridge.extension_connected


def get_bridge_status(port: int = BRIDGE_PORT) -> dict:
    """Return status dict from the bridge."""
    import urllib.request
    try:
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/ping", timeout=2
        )
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"status": "error", "error": str(e)}
