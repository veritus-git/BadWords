"""Social clips: Resolve markers, keep-only ops, .ai.json persistence, assembly."""

import json
import os
from datetime import datetime, timezone

AI_JSON_VERSION = 1
BASE_TIMELINE_NAME = "BadWords - Social Clips"


def build_marker_payloads(clips, fps, tl_start_frame):
    """(frame, name, note, duration_frames) per accepted clip; frames absolute."""
    out = []
    for c in clips:
        if not c.get("accepted"):
            continue
        sf = int(round(float(c["start"]) * fps))
        ef = int(round(float(c["end"]) * fps))
        note = c.get("hook", "")
        if c.get("reason"):
            note = f"{note}\n{c['reason']}" if note else c["reason"]
        out.append((tl_start_frame + sf, f"[AI] {c.get('title', 'Clip')}", note, max(1, ef - sf)))
    return out


def add_markers(resolve_handler, payloads, color):
    tl = resolve_handler.timeline
    if tl is None:
        raise RuntimeError("No active timeline in Resolve")
    added = 0
    for frame, name, note, dur in payloads:
        try:
            ok = tl.AddMarker(frame, color, name, note, dur)
        except TypeError:
            ok = tl.AddMarker(frame, color, name, note)  # older Resolve API
        if ok:
            added += 1
    return added


def build_keep_only_ops(clips, fps):
    """Merge accepted clip ranges into non-overlapping keep-only ops."""
    ops = []
    accepted = sorted((c for c in clips if c.get("accepted")), key=lambda c: c["start"])
    for c in accepted:
        s = int(round(float(c["start"]) * fps))
        e = int(round(float(c["end"]) * fps))
        if e - s < 2:
            continue
        if ops and s <= ops[-1]["e"] + 1:
            ops[-1]["e"] = max(ops[-1]["e"], e)
            continue
        ops.append({"s": s, "e": e, "type": "normal"})
    return ops


def unique_timeline_name(resolve_handler, base=BASE_TIMELINE_NAME):
    if not resolve_handler.timeline_exists(base):
        return base
    i = 2
    while resolve_handler.timeline_exists(f"{base} {i}"):
        i += 1
    return f"{base} {i}"


def assemble_clips(resolve_handler, original_tl_name, clips, fps):
    """Assemble a new timeline containing only the accepted clip ranges."""
    import assembler  # flat import, src/ on sys.path
    ops = build_keep_only_ops(clips, fps)
    if not ops:
        raise ValueError("No accepted clips to assemble")
    name = unique_timeline_name(resolve_handler)
    ok, _schedule, actual = assembler.assemble_via_drt(
        resolve_handler, original_tl_name, ops, name)
    if not ok:
        raise RuntimeError("assemble_via_drt failed — see the BadWords log")
    return actual or name


def write_ai_json(path, clips, provider):
    data = {
        "version": AI_JSON_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": {"base_url": provider.get("base_url", ""),
                     "model": provider.get("model", "")},
        "clips": clips,
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def read_ai_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("version") != AI_JSON_VERSION:
        return None
    saved = data.get("clips")
    return saved if isinstance(saved, list) else []
