"""Map LLM suggestions/clips onto real transcript word ids (fuzzy matching)."""

import algorithms

CONF_MIN = 0.5


def _norm(s):
    return " ".join("".join(ch for ch in c.lower() if ch.isalnum() or ch in "'-")
                    for c in str(s or "").split())


def _time_overlap(a0, a1, b0, b1):
    """Overlap of [a0,a1] with [b0,b1], normalized by the LLM range length."""
    span = max(a1 - a0, 1e-6)
    inter = min(a1, b1) - max(a0, b0)
    return max(0.0, min(1.0, inter / span))


def _sentence_score(sug, sent):
    t = _time_overlap(sug["start"], sug["end"], sent["start"], sent["end"])
    q = algorithms.calculate_similarity(_norm(sug.get("quote", "")), _norm(sent["text"]))
    return 0.6 * t + 0.4 * q


def _narrow_word_ids(sug, sent):
    """Narrow a sentence's word ids to the sub-range covered by the quote."""
    qwords = [_norm(w) for w in sug.get("quote", "").split() if _norm(w)]
    ids, texts = sent["word_ids"], sent["word_texts"]
    n = len(qwords)
    if n == 0 or n >= len(ids):
        return list(ids)
    best_i, best_sc = 0, -1
    for i in range(len(ids) - n + 1):
        sc = sum(1 for j in range(n) if qwords[j] == _norm(texts[i + j]))
        if sc > best_sc:
            best_sc, best_i = sc, i
    if best_sc <= 0:
        return list(ids)
    return list(ids[best_i:best_i + n])


def map_edit_suggestions(suggestions, sentences):
    out = []
    for sug in suggestions:
        best, best_score = None, 0.0
        for sent in sentences:
            sc = _sentence_score(sug, sent)
            if sc > best_score:
                best, best_score = sent, sc
        sug = dict(sug)
        if best is None or best_score < CONF_MIN:
            sug.update({"mapped": False, "word_ids": [], "confidence": round(best_score, 2)})
            out.append(sug)
            continue
        sug.update({
            "mapped": True,
            "word_ids": _narrow_word_ids(sug, best),
            "confidence": round(best_score, 2),
            "start": best["start"], "end": best["end"],
        })
        out.append(sug)
    return out


def _overlap_ratio(a0, a1, b0, b1):
    inter = min(a1, b1) - max(a0, b0)
    if inter <= 0:
        return 0.0
    return inter / min(a1 - a0, b1 - b0)


def dedup_suggestions(items):
    """Keep the higher-confidence item of overlapping twins (same action+status)."""
    out = []
    for s in sorted(items, key=lambda x: x.get("confidence", 0.0), reverse=True):
        dup = any(
            k.get("action") == s.get("action") and k.get("status") == s.get("status")
            and _overlap_ratio(k["start"], k["end"], s["start"], s["end"]) > 0.8
            for k in out)
        if not dup:
            out.append(s)
    return out


def merge_chunk_results(chunk_lists):
    return sorted(dedup_suggestions([s for lst in chunk_lists for s in lst]),
                  key=lambda x: x["start"])


def map_clips(clips, sentences):
    if not sentences:
        return []
    lo, hi = sentences[0]["start"], sentences[-1]["end"]
    out = []
    for c in clips:
        c = dict(c)
        s = max(lo, min(float(c["start"]), hi))
        e = max(lo, min(float(c["end"]), hi))
        if e <= s:
            e = min(hi, s + 0.5)
        c["start"], c["end"] = s, e
        out.append(c)
    return sorted(out, key=lambda x: x.get("score", 0.0), reverse=True)

