#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: storycraft_mcp.py
ROLE: MCP Server
DESCRIPTION:
The MCP server AI assistants launch (Claude Desktop, Claude Code...) to build story edits in the
open StoryCraft window. Speaks MCP over stdio (JSON-RPC, one message per line) and forwards each
tool call to the app (handlers/mcp_bridge.py) using the port and key in endpoint.json next to
this file. Standard library only, so any Python 3.8+ can run it.

Claude Code:     claude mcp add storycraft -- <python3> <this file>
Claude Desktop:  "mcpServers": {"storycraft": {"command": "<python3>", "args": ["<this file>"]}}
"""

import json
import os
import sys
import urllib.error
import urllib.request

SERVER = {"name": "storycraft", "version": "1.0.0"}
ENDPOINT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "endpoint.json")

INSTRUCTIONS = (
    "StoryCraft edits interviews in DaVinci Resolve from their transcript. To build a story: call get_transcript "
    "and read all of it; find the through-line; tell the user a short outline (opening, middle, ending); then call "
    "check_edit with your EDIT, one clip per line (M12, M12-M14 or S041-S043), and fix every problem it reports "
    "until it says the edit flows; then call apply_edit, and use review_cuts to judge each cut and refine.  Respect the target length, AVOID tags, clarity and the "
    "rules at the top of the transcript. When the user wants it in Resolve, call send_to_resolve: it creates a new "
    "timeline in the StoryCraft bin and changes no existing timeline."
)

EDIT_DOC = ("The edit: one clip per line in play order. A moment (M12), a run of moments (M12-M14) or a run of "
            "sentences (S041-S043); anything after # on a line is ignored.")

TOOLS = [
    {"name": "storycraft_status",
     "description": "What StoryCraft has open: timeline, whether a transcript is loaded, target length, story board, "
                    "Resolve connection.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_transcript",
     "description": "The open timeline's transcript after the current cuts, grouped into moments (whole thoughts) "
                    "with sentence IDs, time, length, clarity, AVOID and INTERVIEWER tags, plus the editing rules and "
                    "target length. Read it before building an edit; call it again after the user changes cuts.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "set_target_length",
     "description": "Set how long the finished edit should be (also shown on the story board).",
     "inputSchema": {"type": "object", "properties": {
         "length": {"type": "string", "description": "e.g. 2:00, 90s or 2m"}}, "required": ["length"]}},
    {"name": "check_edit",
     "description": "Dry run: measure an edit after cuts and list what breaks the flow (length off target, clips "
                    "under 5 s, clips starting mid-thought, AVOID parts, hard-to-hear parts). Changes nothing.",
     "inputSchema": {"type": "object", "properties": {"edit": {"type": "string", "description": EDIT_DOC}},
                     "required": ["edit"]}},
    {"name": "apply_edit",
     "description": "Put the edit on StoryCraft's story board (the user can still rearrange it). Returns the same "
                    "report as check_edit. Does not touch Resolve.",
     "inputSchema": {"type": "object", "properties": {
         "edit": {"type": "string", "description": EDIT_DOC},
         "outline": {"type": "string", "description": "The outline you followed (optional)."}},
         "required": ["edit"]}},
    {"name": "review_cuts",
     "description": "Cut-by-cut review of the edit on the story board (or of the edit you pass): what is said either "
                    "side of each cut, how far it jumps in the recording, and what may sound wrong (ends or starts "
                    "mid-thought, loudness jump, going back, speaker change), plus clips that repeat each other. Use "
                    "it to improve the order and the cut points, then check_edit and apply_edit the corrected EDIT.",
     "inputSchema": {"type": "object", "properties": {
         "edit": {"type": "string", "description": "Optional. " + EDIT_DOC + " Default: the story board."}}}},
    {"name": "send_to_resolve",
     "description": "Build the edit in DaVinci Resolve, like the Send to Resolve button: a new timeline (\"<timeline> "
                    "StoryCraft Edit N\") in the StoryCraft bin of the open project, with the story's order and all "
                    "cuts, audio crossfades and jump-cut markers. Existing timelines are not changed. Use it when the "
                    "user asks for the edit in Resolve, after apply_edit.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_story_board",
     "description": "The story board as it is now (the user may have moved blocks): blocks in play order with "
                    "sentence IDs, lengths and text, and the total.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def _call_app(tool, args):
    try:
        with open(ENDPOINT) as f:
            ep = json.load(f)
    except (OSError, ValueError):
        return False, "StoryCraft isn't open. Ask the user to start it and open the timeline."
    req = urllib.request.Request(
        f"http://127.0.0.1:{ep['port']}/", data=json.dumps({"tool": tool, "args": args}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-StoryCraft-Key": ep["key"]}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=150) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return bool(out.get("ok")), out.get("text", "")
    except urllib.error.URLError:
        return False, "StoryCraft isn't reachable (it may have been closed). Ask the user to open it."
    except Exception as e:
        return False, f"StoryCraft error: {e}"


def _handle(msg):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None  # notifications (initialized, cancelled...) need no answer
    if method == "initialize":
        version = (msg.get("params") or {}).get("protocolVersion") or "2025-06-18"
        result = {"protocolVersion": version, "capabilities": {"tools": {}}, "serverInfo": SERVER,
                  "instructions": INSTRUCTIONS}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name not in {t["name"] for t in TOOLS}:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        ok, text = _call_app(name, params.get("arguments") or {})
        result = {"content": [{"type": "text", "text": text}], "isError": not ok}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            batch = msg if isinstance(msg, list) else [msg]
            replies = [r for r in (_handle(m) for m in batch) if r is not None]
            reply = replies if isinstance(msg, list) else (replies[0] if replies else None)
        if reply:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
