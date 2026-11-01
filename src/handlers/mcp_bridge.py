#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: mcp_bridge.py
ROLE: Background Handler
DESCRIPTION:
Lets AI assistants (Claude Desktop, Claude Code...) work with the open StoryCraft window through
mcp_server/storycraft_mcp.py, the MCP server they launch. This side is a small HTTP server on
127.0.0.1 only, with a random key; each request runs on the Qt main thread, so tools can touch
the story board safely. Port and key go to mcp_server/endpoint.json (readable by this user only).
"""

import json
import os
import queue
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import QTimer

from osdoc import log_info, log_error


class McpBridge:
    def __init__(self, tools, install_dir, parent):
        """tools: {name: callable(args dict) -> str}; an exception becomes an error result."""
        self._tools = tools
        self._queue = queue.Queue()
        self._token = secrets.token_hex(16)
        self._endpoint = os.path.join(install_dir, "mcp_server", "endpoint.json")
        bridge = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                if self.headers.get("X-StoryCraft-Key") != bridge._token:
                    self.send_response(403)
                    self.end_headers()
                    return
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                    req = json.loads(self.rfile.read(length) or b"{}")
                    result = bridge._call(req.get("tool"), req.get("args") or {})
                except Exception as e:
                    result = {"ok": False, "text": f"Bad request: {e}"}
                body = json.dumps(result).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

        self._timer = QTimer(parent)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._drain)
        self._timer.start()

        os.makedirs(os.path.dirname(self._endpoint), exist_ok=True)
        fd = os.open(self._endpoint, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"port": self._server.server_address[1], "key": self._token, "pid": os.getpid()}, f)
        log_info(f"AI assistant bridge listening on 127.0.0.1:{self._server.server_address[1]}")

    def _call(self, name, args):
        """Called on a server thread: hand the call to the main thread and wait for it."""
        if name not in self._tools:
            return {"ok": False, "text": f"Unknown tool: {name}"}
        done, box = threading.Event(), {}
        self._queue.put((self._tools[name], args, done, box))
        if not done.wait(120):
            return {"ok": False, "text": "StoryCraft is busy (a dialog may be open). Try again in a moment."}
        return box["result"]

    def _drain(self):
        while True:
            try:
                fn, args, done, box = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                box["result"] = {"ok": True, "text": fn(args)}
            except Exception as e:
                log_error(f"AI assistant tool failed: {e}")
                box["result"] = {"ok": False, "text": str(e)}
            done.set()

    def stop(self):
        try:
            self._timer.stop()
            self._server.shutdown()
            self._server.server_close()
        except Exception:
            pass
        try:
            with open(self._endpoint) as f:
                if json.load(f).get("pid") == os.getpid():
                    os.remove(self._endpoint)
        except Exception:
            pass
