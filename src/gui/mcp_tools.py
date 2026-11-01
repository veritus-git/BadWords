#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: mcp_tools.py
ROLE: GUI Logic
DESCRIPTION:
What an AI assistant can do with the open window (through handlers/mcp_bridge.py): read the
transcript in moments, set the target length, check an edit, put it on the story board, read
the board back. The same functions as Copy for AI and Import AI edit, so the assistant sees and
gets checked exactly like a pasted answer. Sending to Resolve stays with the user.
"""

import re

import algorithms


def _mmss(s):
    s = int(round(max(0.0, s or 0.0)))
    return f"{s // 60}:{s % 60:02d}"


def _parse_length(value):
    """'2:00', '2m', '1.5 min', '90s', '90' or a number -> seconds; None when it isn't a length."""
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    txt = str(value or "").strip().lower().replace(",", ".")
    m = re.fullmatch(r"(\d+):(\d{1,2})", txt)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(m|min|mins|minutes?)", txt)
    if m:
        return float(m.group(1)) * 60
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(s|sec|secs|seconds?)?", txt)
    if m:
        return float(m.group(1))
    return None


def build_tools(win):
    def _need_transcript():
        canvas = getattr(win, 'text_canvas', None)
        if canvas is None or not canvas.words_data:
            raise RuntimeError("No transcript is open in StoryCraft. Ask the user to open or transcribe the timeline first.")
        return canvas

    def _target():
        return (win.engine.load_preferences() or {}).get('story_target_s') or None

    def _sentences():
        sentences = win._load_ai_sentences()
        if not sentences or not sentences[0].get("moment"):
            _, sentences = win._build_ai_transcript()
            win._remember_ai_sentences(sentences)
        return sentences

    def _evaluate(edit):
        _need_transcript()
        if isinstance(edit, list):
            edit = "\n".join(str(x) for x in edit)
        sentences = _sentences()
        picks, unknown = algorithms.parse_story_answer(str(edit or ""), len(sentences), algorithms.moment_ranges(sentences))
        clips = algorithms.story_clips(picks, sentences)
        prefs = win._live_cut_prefs()
        # measure as Send to Resolve will: the pause budget counts this edit's clips
        prefs['story_clips'] = [{"cut_start": c["cut_start"], "cut_end": c["cut_end"]} for c in clips] or None
        rh = getattr(win.engine, 'resolve_handler', None)
        fps = getattr(rh, 'fps', None) or 24.0
        ops, _ = win.engine.calculate_timeline_structure_with_cuts([dict(w) for w in win.text_canvas.words_data], fps, prefs)
        duration = sum(o['e'] - o['s'] for o in algorithms.apply_story_order(ops, clips, fps, float(prefs.get('offset', 0.133)))) / fps
        issues = algorithms.check_story(clips, sentences, duration, _target())
        return sentences, clips, duration, issues, unknown

    def _report(sentences, clips, duration, issues, unknown):
        t = _target()
        head = f"{len(clips)} clips, {_mmss(duration)} after cuts"
        if t:
            head += f" (target {_mmss(t)}, between {_mmss(t * 0.9)} and {_mmss(t * 1.1)})"
        lines = [head]
        for k, c in enumerate(clips, 1):
            run = sentences[c["first"]:c["last"] + 1]
            ids = c["start_id"] if c["start_id"] == c["end_id"] else f'{c["start_id"]}-{c["end_id"]}'
            cl = [s["clarity"] for s in run if s.get("clarity") is not None]
            tags = (f", clarity {round(sum(cl) / len(cl))}" if cl else "") + (", AVOID" if any(s.get("avoid") for s in run) else "") \
                + (", INTERVIEWER" if all(s.get("speaker2") for s in run) else "")
            text = c["text"] if len(c["text"]) <= 90 else c["text"][:89] + "…"
            lines.append(f"{k}. {ids} ({run[0].get('moment', '')}, {c['cut_end'] - c['cut_start']:.1f}s{tags}): {text}")
        if unknown:
            lines.append("Unknown IDs, ignored: " + ", ".join(dict.fromkeys(unknown)))
        if issues:
            lines.append("Problems to fix before applying:")
            lines += [f"- {algorithms._FIX_LINES[code].format(**detail)}" for code, detail in issues]
        elif clips:
            lines.append("No problems found: the edit flows.")
        return "\n".join(lines)

    def status(args):
        canvas = getattr(win, 'text_canvas', None)
        snap = getattr(win, '_transcription_source', None) or {}
        story = getattr(win, '_story', None) or {}
        rh = getattr(win.engine, 'resolve_handler', None)
        try:
            connected = bool(rh and rh.is_connected())
        except Exception:
            connected = False
        words = len(canvas.words_data) if canvas is not None and canvas.words_data else 0
        t = _target()
        return "\n".join([
            f"Timeline: {snap.get('timeline_name') or snap.get('source_file') or 'none'}",
            f"Transcript open: {'yes, ' + str(words) + ' items' if words else 'no'}",
            f"Target length: {_mmss(t) if t else 'not set'}",
            f"Story board: {len(story.get('clips') or [])} clips, {_mmss(story.get('duration', 0.0))}" if story else "Story board: empty",
            f"DaVinci Resolve connected: {'yes' if connected else 'no'}",
        ])

    def get_transcript(args):
        _need_transcript()
        text, sentences = win._build_ai_transcript()
        win._remember_ai_sentences(sentences)
        return text

    def set_target_length(args):
        secs = _parse_length(args.get("length"))
        if not secs:
            raise ValueError("Give a length like 2:00, 90s or 2m.")
        board = getattr(win, 'story_board', None)
        if board is not None and hasattr(board, 'edit_target'):
            board.edit_target.setText(_mmss(secs))
            board._on_target_changed()
        else:
            prefs = win.engine.load_preferences() or {}
            prefs['story_target_s'] = int(round(secs))
            win.engine.save_preferences(prefs)
        return f"Target length set to {_mmss(secs)}."

    def check_edit(args):
        return _report(*_evaluate(args.get("edit")))

    def apply_edit(args):
        sentences, clips, duration, issues, unknown = _evaluate(args.get("edit"))
        if not clips:
            raise ValueError("No clip IDs found in the edit. Use one clip per line: M12, M12-M14 or S041-S043.")
        story = {"clips": [{"cut_start": c["cut_start"], "cut_end": c["cut_end"], "start_id": c["start_id"],
                            "end_id": c["end_id"]} for c in clips],
                 "keep_source_order": False, "duration": duration}
        win._story = story
        board = getattr(win, 'story_board', None)
        if board is not None:
            board.load_ai_story(sentences, story)
            if hasattr(win, '_toggle_activity') and not getattr(win.btn_nav_story, 'is_active', False):
                win._toggle_activity("story")
        else:
            win._update_story_banner()
            win._refresh_cut_preview()
        outline = (args.get("outline") or "").strip()
        win._show_temporary_status(win.txt("msg_story_loaded").format(clips=len(clips), assemble=win.txt("btn_assemble")))
        return (_report(sentences, clips, duration, issues, unknown)
                + ("\nOutline received." if outline else "")
                + "\nApplied to the story board. The user reviews it (Play edit) and presses Send to Resolve.")

    def get_story_board(args):
        board = getattr(win, 'story_board', None)
        if board is None or not board.sentences:
            return "The story board is empty."
        from gui.panels.story_panel import BLOCK_ROLE, _decode
        lines = []
        total = 0.0
        for i in range(board.list_edit.count()):
            f, l = _decode(board.list_edit.item(i).data(BLOCK_ROLE))
            d = board.block_duration((f, l))
            total += d
            text = " ".join(s["text"] for s in board.sentences[f:l + 1])
            lines.append(f"{i + 1}. {board.block_label((f, l))} ({d:.1f}s): {text[:90] + ('…' if len(text) > 90 else '')}")
        story = getattr(win, '_story', None) or {}
        head = f"Edit: {board.list_edit.count()} blocks, {_mmss(story.get('duration', total))} after cuts"
        t = _target()
        if t:
            head += f" (target {_mmss(t)})"
        return "\n".join([head] + lines + [f"Not used: {board.list_unused.count()} blocks."])

    def review_cuts(args):
        _need_transcript()
        text = win._cut_review(args.get("edit") or None)
        if not text:
            raise ValueError("There is no edit to review: the story board is empty. Apply an edit first, or pass one.")
        return text

    def send_to_resolve(args):
        """Same as the Send to Resolve button: a new timeline in the StoryCraft bin, cuts and story applied."""
        _need_transcript()
        if getattr(win, '_is_live_transcribing', False):
            raise RuntimeError("StoryCraft is still transcribing. Try again when it's done.")
        rh = getattr(win.engine, 'resolve_handler', None)
        if not (rh and rh.is_connected()):
            raise RuntimeError("DaVinci Resolve isn't connected to StoryCraft.")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, win._on_assemble)  # after this call returns: the assembly runs in its own thread
        story = getattr(win, '_story', None) or {}
        what = f"the story ({len(story.get('clips') or [])} clips, {_mmss(story.get('duration', 0.0))})" if story else "the whole transcript with the current cuts"
        return (f"Sending {what} to DaVinci Resolve: a new timeline appears in the StoryCraft bin in a few seconds, "
                "with audio crossfades and Yellow 'Jump cut' markers where the picture jumps.")

    return {
        "send_to_resolve": send_to_resolve,
        "review_cuts": review_cuts,
        "storycraft_status": status,
        "get_transcript": get_transcript,
        "set_target_length": set_target_length,
        "check_edit": check_edit,
        "apply_edit": apply_edit,
        "get_story_board": get_story_board,
    }
