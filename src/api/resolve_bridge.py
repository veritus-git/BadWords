#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: resolve_bridge.py
ROLE: IPC Mailbox Client for DaVinci Resolve
DESCRIPTION:
File-mailbox bridge to the BadWords Lua server running inside DaVinci Resolve.
Enables 'External' Scripting for DaVinci Resolve Free (including 21.1+ where Python
and external scripting are blocked).

Protocol:
- BadWords -> Resolve: Atomically writes `request.lua` containing `{ id = "...", body = "..." }`
  into the shared mailbox directory. The Lua loop in Resolve detects it with `bmd.fileexists()`
  and reads it with `loadfile()`.
- Resolve -> BadWords: The Lua script writes `Global.BadWordsBridge.Response = "<id>:<base64>"`
  via `fusion:SetPrefs()` and saves it to disk with `fusion:SavePrefs()`. BadWords polls
  `Fusion.prefs` to retrieve and decode the response.
"""

import os
import sys
import time
import json
import base64
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union

# Logger fallbacks
try:
    from osdoc import log_error, log_info, log_warn
except ImportError:
    def log_error(m): print(f"[ERR] [Bridge] {m}")
    def log_info(m): print(f"[INFO] [Bridge] {m}")
    def log_warn(m): print(f"[WARN] [Bridge] {m}")


class ResolveBridgeClient:
    """Client for file-based IPC mailbox bridge to DaVinci Resolve Lua runner."""

    def __init__(self, install_dir: Optional[Union[str, Path]] = None):
        self._lock = threading.Lock()
        self._counter = 0
        self.install_dir = Path(install_dir) if install_dir else self._discover_install_dir()
        self.mailbox_dir = self._get_mailbox_dir(self.install_dir)
        try:
            self.mailbox_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_warn(f"Failed to create bridge mailbox dir at {self.mailbox_dir}: {e}")
            self.mailbox_dir = self._get_fallback_mailbox_dir()
            self.mailbox_dir.mkdir(parents=True, exist_ok=True)

        self.request_file = self.mailbox_dir / "request.lua"
        self.request_tmp = self.mailbox_dir / "request.tmp"

    @staticmethod
    def _discover_install_dir() -> Optional[Path]:
        """Discovers the BadWords installation root directory."""
        try:
            import config
            if hasattr(config, "INSTALL_DIR") and config.INSTALL_DIR:
                p = Path(config.INSTALL_DIR)
                if p.is_dir():
                    return p
        except Exception:
            pass

        try:
            cur = Path(__file__).resolve()
            for parent in cur.parents:
                if (parent / "main.py").is_file():
                    return parent
        except Exception:
            pass

        try:
            cwd = Path.cwd()
            if (cwd / "main.py").is_file():
                return cwd
        except Exception:
            pass

        return None

    @classmethod
    def _get_mailbox_dir(cls, install_dir: Optional[Path] = None) -> Path:
        """Determines the mailbox directory placed inside the BadWords installation directory."""
        if install_dir and Path(install_dir).is_dir():
            return Path(install_dir) / "bridge"
        return cls._get_fallback_mailbox_dir()

    @staticmethod
    def _get_fallback_mailbox_dir() -> Path:
        """Determines the fallback cross-platform mailbox directory in user data."""
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
            return Path(base) / "BadWords" / "bridge"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "BadWords" / "bridge"
        else:
            xdg = os.environ.get("XDG_DATA_HOME")
            base = Path(xdg) if xdg else Path.home() / ".local" / "share"
            return base / "BadWords" / "bridge"

    @staticmethod
    def get_fusion_support_dir() -> Optional[Path]:
        """Returns per-user Resolve support directory containing Fusion/Profiles and Fusion/Scripts."""
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Blackmagic Design" / "DaVinci Resolve" / "Support"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve"
        else:
            # Linux
            return Path.home() / ".local" / "share" / "DaVinciResolve"
        return None

    def find_fusion_prefs_path(self) -> Optional[Path]:
        """Locates Fusion.prefs (picks the most recently modified profile)."""
        support_dir = self.get_fusion_support_dir()
        if not support_dir or not support_dir.is_dir():
            return None

        profiles_dir = support_dir / "Fusion" / "Profiles"
        if not profiles_dir.is_dir():
            return None

        best_path: Optional[Path] = None
        best_mtime: float = -1.0

        try:
            for entry in profiles_dir.iterdir():
                if entry.is_dir():
                    prefs_file = entry / "Fusion.prefs"
                    if prefs_file.is_file():
                        mtime = prefs_file.stat().st_mtime
                        if mtime > best_mtime:
                            best_mtime = mtime
                            best_path = prefs_file
        except Exception as e:
            log_error(f"Error scanning Fusion profiles: {e}")

        return best_path

    def _next_request_id(self) -> str:
        with self._lock:
            self._counter = (self._counter + 1) % 1000
            now_ms = int(time.time() * 1000)
            return f"{now_ms * 1000 + self._counter}"

    @staticmethod
    def _encode_request(req_id: str, body_json: str) -> str:
        """Encodes request as Lua chunk: return { id = '...', body = [==[...]==] }."""
        level = 1
        while f"]{'=' * level}]" in body_json:
            level += 1
        eq = "=" * level
        return f"return {{ id = \"{req_id}\", body = [{eq}[{body_json}]{eq}] }}\n"

    @staticmethod
    def _extract_pref_value(text: str, key: str) -> Optional[str]:
        """Extracts the value of `key = "..."` assignments from Fusion.prefs text."""
        needle = f'{key} = "'
        result = None
        offset = 0
        text_len = len(text)
        needle_len = len(needle)

        while offset < text_len:
            pos = text.find(needle, offset)
            if pos == -1:
                break
            # Boundary check: preceding character must not be alphanumeric or underscore
            if pos > 0 and (text[pos - 1].isalnum() or text[pos - 1] == '_'):
                offset = pos + needle_len
                continue

            start = pos + needle_len
            end = text.find('"', start)
            if end != -1:
                result = text[start:end]
                offset = end + 1
            else:
                break

        return result

    @staticmethod
    def _decode_response_string(payload_str: str) -> str:
        """
        Decodes response string:
        Maps any \\uE0xx markers back to raw bytes (ANSI/UTF-8 bytes preserved in pure ASCII).
        """
        chars = []
        i = 0
        n = len(payload_str)
        raw_bytes = bytearray()
        has_bytes = False

        while i < n:
            chunk = payload_str[i:i + 6]
            if len(chunk) == 6 and chunk[:4].lower() == "\\ue0":
                try:
                    b = int(chunk[2:6], 16) - 0xE000
                    if 0 <= b <= 255:
                        raw_bytes.append(b)
                        has_bytes = True
                        i += 6
                        continue
                except ValueError:
                    pass
            if has_bytes:
                # Flush collected raw bytes
                try:
                    chars.append(raw_bytes.decode('utf-8'))
                except UnicodeDecodeError:
                    try:
                        chars.append(raw_bytes.decode('cp1250' if sys.platform == 'win32' else 'latin-1', errors='replace'))
                    except Exception:
                        chars.append(raw_bytes.decode('latin-1', errors='replace'))
                raw_bytes.clear()
                has_bytes = False

            chars.append(payload_str[i])
            i += 1

        if has_bytes:
            try:
                chars.append(raw_bytes.decode('utf-8'))
            except UnicodeDecodeError:
                try:
                    chars.append(raw_bytes.decode('cp1250' if sys.platform == 'win32' else 'latin-1', errors='replace'))
                except Exception:
                    chars.append(raw_bytes.decode('latin-1', errors='replace'))

        return "".join(chars)

    def is_bridge_alive(self, timeout_secs: float = 0.25) -> bool:
        """Quick check if DaVinci Resolve BadWords Bridge is alive and responding."""
        try:
            res = self.call("Ping", timeout_secs=timeout_secs)
            return bool(res and (res.get("message") == "Pong" or res.get("ok")))
        except Exception:
            return False

    def call(self, func_name: str, args: Optional[Dict[str, Any]] = None, timeout_secs: float = 30.0) -> Dict[str, Any]:
        """
        Sends a request to the BadWords Lua bridge inside DaVinci Resolve and waits for response.
        
        Args:
            func_name: The API function name in Lua handlers (e.g. 'GetTimelineInfo', 'RenderAudio').
            args: Dictionary of arguments for the function.
            timeout_secs: Maximum wait time in seconds before raising TimeoutError.
            
        Returns:
            Decoded dictionary response.
        """
        prefs_path = self.find_fusion_prefs_path()
        if not prefs_path:
            raise RuntimeError("Could not find DaVinci Resolve Fusion.prefs profile.")

        req_id = self._next_request_id()
        payload = {"func": func_name}
        if args:
            payload.update(args)
        body_json = json.dumps(payload, ensure_ascii=False)
        lua_content = self._encode_request(req_id, body_json)

        with self._lock:
            try:
                # 1. Atomically write request.lua
                try:
                    with open(self.request_tmp, "w", encoding="utf-8") as f:
                        f.write(lua_content)
                    self.request_tmp.replace(self.request_file)
                except Exception as e:
                    raise IOError(f"Failed to write mailbox request: {e}")

                # 2. Poll Fusion.prefs for Ack and Response
                deadline = time.time() + timeout_secs
                poll_interval = 0.01
                acked = False

                while time.time() < deadline:
                    time.sleep(poll_interval)
                    try:
                        if not prefs_path.is_file():
                            continue
                        with open(prefs_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                    except Exception:
                        continue

                    # Check for Ack
                    if not acked:
                        ack_val = self._extract_pref_value(content, "Ack")
                        if ack_val == req_id:
                            acked = True

                    # Check for Response
                    resp_val = self._extract_pref_value(content, "Response")
                    if resp_val and resp_val.startswith(f"{req_id}:"):
                        b64_part = resp_val[len(req_id) + 1:]
                        try:
                            decoded_bytes = base64.b64decode(b64_part)
                            json_str = decoded_bytes.decode("utf-8", errors="replace")
                            json_str = self._decode_response_string(json_str)
                            return json.loads(json_str)
                        except Exception as e:
                            raise ValueError(f"Failed to parse bridge response: {e}")

                # Timeout expired
                if acked:
                    raise TimeoutError(f"Request '{func_name}' (id: {req_id}) was acknowledged by Resolve, but timed out after {timeout_secs}s.")
                else:
                    raise TimeoutError(
                        f"DaVinci Resolve did not acknowledge request '{func_name}'. "
                        f"Ensure DaVinci Resolve is running and 'Workspace -> Scripts -> BadWords Bridge' has been launched."
                    )
            finally:
                # Always remove request.lua so Resolve idle loop does not keep parsing it
                try:
                    if self.request_file.exists():
                        self.request_file.unlink()
                except Exception:
                    pass
                try:
                    if self.request_tmp.exists():
                        self.request_tmp.unlink()
                except Exception:
                    pass
