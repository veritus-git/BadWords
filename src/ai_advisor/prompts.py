"""System prompts, transcript compaction, LLM JSON parsing/validation."""

import json
import re


def parse_llm_json(raw):
    """Extract and parse the first JSON object from an LLM response.

    Tolerates ```json fences and surrounding prose. Raises ValueError.
    """
    if not raw or not str(raw).strip():
        raise ValueError("Empty LLM response")
    txt = str(raw).strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", txt, re.DOTALL)
    if fence:
        txt = fence.group(1)
    else:
        start, end = txt.find("{"), txt.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in LLM response")
        txt = txt[start:end + 1]
    return json.loads(txt)


# ── Timestamp helpers ────────────────────────────────────────────────────────

def fmt_tc(t):
    """Seconds → 'mm:ss.d'."""
    t = max(0.0, float(t))
    m = int(t // 60)
    return f"{m:02d}:{t - m * 60:04.1f}"


def parse_tc(s):
    """'mm:ss.d' → seconds. Raises ValueError on garbage."""
    s = str(s).strip()
    parts = s.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(s)


# ── System prompts ───────────────────────────────────────────────────────────

EDIT_SYSTEM_PROMPT = """You are a video rough-cut editing assistant for BadWords, a tool that
turns transcript edits into timeline cuts. You receive a verbatim transcript, one sentence per
line as "[mm:ss.d-mm:ss.d] text", where fully-cut sentences carry a "[CUT] " prefix.

Suggest edits using ONLY these actions:
- action "cut", status "bad": filler words, stumbles, mistakes that should be removed
- action "cut", status "repeat": retakes or duplicated takes (keep the LAST take)
- action "recolor", status "typo": the word was said correctly but transcribed wrong — no cut

Rules:
- Use ONLY timestamps present in the transcript; "quote" must copy the exact transcript words.
- Never re-suggest a sentence already prefixed "[CUT] ".
- Be conservative: suggest only clear, well-supported edits.
- Respond with ONLY a valid JSON object, no markdown fences.

JSON schema:
{"suggestions": [{"start": "mm:ss.d", "end": "mm:ss.d", "quote": "...",
  "action": "cut", "status": "bad", "reason": "short why", "category": "filler"}]}
"category" is one of: filler, retake, mistake, other."""


CLIPS_SYSTEM_PROMPT = """You are a social media clip finder for dialogue-heavy videos
(podcasts, talking heads). You receive a verbatim transcript, one sentence per line as
"[mm:ss.d-mm:ss.d] text".

Find self-contained moments that work as vertical short-form clips.

Rules:
- "start"/"end" MUST be timestamps present in the transcript; clips must be self-contained.
- Prefer strong hooks, punchlines, hot takes, surprising or emotional moments.
- Respect the requested platforms and duration range given in the user message.
- Respond with ONLY a valid JSON object, no markdown fences.

JSON schema:
{"clips": [{"start": "mm:ss.d", "end": "mm:ss.d", "title": "max 60 chars",
  "hook": "opening line text", "reason": "why it works", "score": 0.0,
  "platform": "shorts"}]}
"platform" is one of: shorts, tiktok, reels. "score" is 0.0-1.0 estimated virality."""


# ── Transcript compaction ────────────────────────────────────────────────────

def _norm_word(t):
    return "".join(ch for ch in t.lower() if ch.isalnum() or ch in "'-")


def compact_sentences(words_data):
    """Group word objects into sentences by seg_start. Keeps word ids + texts."""
    sentences = []
    cur = None
    for w in words_data:
        if w.get("type") != "word":
            continue
        text = (w.get("text") or "").strip()
        if not text:
            continue
        key = round(float(w.get("seg_start", w.get("start", 0.0))), 3)
        if cur is None or cur["key"] != key:
            cur = {"key": key, "start": float(w.get("start", 0.0)),
                   "end": float(w.get("end", 0.0)), "words": []}
            sentences.append(cur)
        cur["end"] = max(cur["end"], float(w.get("end", 0.0)))
        cur["words"].append(w)

    out = []
    for s in sentences:
        ids = [w["id"] for w in s["words"]]
        texts = [(w.get("text") or "").strip() for w in s["words"]]
        statuses = [w.get("status") for w in s["words"]]
        fully_cut = bool(statuses) and all(st in ("bad", "repeat") for st in statuses)
        out.append({
            "start": s["start"], "end": s["end"],
            "text": " ".join(texts), "word_ids": ids, "word_texts": texts,
            "tagged": "[CUT] " if fully_cut else "",
        })
    return out


def build_chunks(sentences, max_chars, overlap=2):
    """Split sentences into prompt chunks of <= max_chars with sentence overlap."""
    lines = []
    for s in sentences:
        lines.append(f"[{fmt_tc(s['start'])}-{fmt_tc(s['end'])}] {s['tagged']}{s['text']}")

    chunks = []
    start = 0
    n = len(sentences)
    while start < n:
        body, length, end = [], 0, start
        while end < n:
            line = lines[end]
            if length + len(line) + 1 > max_chars and body:
                break
            body.append(line)
            length += len(line) + 1
            end += 1
        chunks.append({
            "header": f"TRANSCRIPT PART {len(chunks) + 1} "
                      f"(timestamps are absolute, not per-part)",
            "text": "\n".join(body),
            "sentences": sentences[start:end],
        })
        if end >= n:
            break
        start = max(end - overlap, start + 1)  # never stall
    return chunks


# ── LLM output validation ────────────────────────────────────────────────────

_VALID_STATUS = {"bad", "repeat", "typo"}
_VALID_PLATFORM = {"shorts", "tiktok", "reels"}


def validate_edits(obj):
    """Normalize a {"suggestions": [...]} payload; drop invalid entries."""
    if not isinstance(obj, dict) or not isinstance(obj.get("suggestions"), list):
        raise ValueError('Expected {"suggestions": [...]}')
    out = []
    for s in obj["suggestions"]:
        if not isinstance(s, dict):
            continue
        action = s.get("action", "cut")
        status = s.get("status", "bad")
        if action not in ("cut", "recolor") or status not in _VALID_STATUS:
            continue
        try:
            start, end = parse_tc(s["start"]), parse_tc(s["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if end <= start:
            continue
        out.append({
            "action": action, "status": status, "start": start, "end": end,
            "quote": str(s.get("quote", "")).strip(),
            "reason": str(s.get("reason", "")).strip(),
            "category": str(s.get("category", "other")).strip() or "other",
        })
    return out


def validate_clips(obj):
    """Normalize a {"clips": [...]} payload; drop invalid entries."""
    if not isinstance(obj, dict) or not isinstance(obj.get("clips"), list):
        raise ValueError('Expected {"clips": [...]}')
    out = []
    for c in obj["clips"]:
        if not isinstance(c, dict):
            continue
        try:
            start, end = parse_tc(c["start"]), parse_tc(c["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if end <= start:
            continue
        platform = str(c.get("platform", "shorts")).strip().lower()
        if platform not in _VALID_PLATFORM:
            platform = "shorts"
        try:
            score = min(1.0, max(0.0, float(c.get("score", 0.5))))
        except (TypeError, ValueError):
            score = 0.5
        out.append({
            "start": start, "end": end,
            "title": str(c.get("title", "Untitled clip")).strip()[:80] or "Untitled clip",
            "hook": str(c.get("hook", "")).strip(),
            "reason": str(c.get("reason", "")).strip(),
            "score": score, "platform": platform,
        })
    return out

