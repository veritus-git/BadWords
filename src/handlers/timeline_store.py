#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: timeline_store.py
ROLE: Background Handler
DESCRIPTION:
Keeps the transcript of every timeline (words, marks, chapters, story source) so reopening a
timeline doesn't mean transcribing it again. One small JSON project per Resolve project and
timeline under <StoryCraft saves>/timelines/<project>/<timeline>.json (no audio inside: it is fetched again
from Resolve when needed). Written by the background autosave; opened from the start screen.
"""

import os
import time


def _safe(name):
    s = "".join(c for c in str(name or "") if c.isalnum() or c in " -_.()").strip()
    return s[:120] or "Untitled"


def key_for(packet, resolve_project=""):
    """(project folder, file name) for a data packet, or None when it can't be tied to a timeline."""
    src = (packet or {}).get("transcription_source") or {}
    tl = src.get("timeline_name")
    if tl:
        return _safe(resolve_project or "No project"), _safe(tl)
    f = src.get("source_file")
    if f:
        return "_files", _safe(os.path.basename(f))
    return None


def path_for(saves_dir, project_folder, name):
    return os.path.join(saves_dir, "timelines", project_folder, name + ".json")


KEEP_PREVIOUS = 3


def _keep_previous(path):
    """A new transcription is about to replace this file: keep the old one (with its marks) next to it,
    as "<timeline>.before <date time>.json"; only the last few are kept."""
    import glob
    import shutil
    if not os.path.isfile(path):
        return
    stamp = time.strftime("%Y-%m-%d %H.%M", time.localtime(os.path.getmtime(path)))
    shutil.copy2(path, path[:-len(".json")] + f".before {stamp}.json")
    olds = sorted(glob.glob(glob.escape(path[:-len(".json")]) + ".before *.json"), key=os.path.getmtime)
    for p in olds[:-KEEP_PREVIOUS]:
        try:
            os.remove(p)
        except OSError:
            pass


def save(engine, packet, keep_previous=False):
    """Write the packet for its timeline. Safe to call from a background thread.
    keep_previous: a fresh transcription replaces the saved one; keep the old file as a backup."""
    if not packet or not packet.get("words_data"):
        return None
    try:
        proj = engine._get_resolve_project_name() if hasattr(engine, "_get_resolve_project_name") else ""
    except Exception:
        proj = ""
    key = key_for(packet, proj)
    if key is None:
        return None
    path = path_for(engine.os_doc.get_saves_folder(), *key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if keep_previous:
        _keep_previous(path)
    tmp = path + ".part"
    engine.save_project_state(tmp, packet)
    os.replace(tmp, path)
    return path


def find(saves_dir, resolve_project, timeline_name):
    """(path, saved_at) of the saved transcript for this timeline, or None."""
    if not timeline_name:
        return None
    path = path_for(saves_dir, _safe(resolve_project or "No project"), _safe(timeline_name))
    if os.path.isfile(path):
        return path, os.path.getmtime(path)
    return None


def when_text(ts):
    lt, now = time.localtime(ts), time.localtime()
    if lt.tm_yday == now.tm_yday and lt.tm_year == now.tm_year:
        return time.strftime("%H:%M", lt)
    return time.strftime("%Y-%m-%d %H:%M", lt)
