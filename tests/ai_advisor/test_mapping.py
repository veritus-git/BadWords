import pytest

from ai_advisor import mapping
from conftest import build_words_data


@pytest.fixture
def sentences(words_data):
    from ai_advisor import prompts
    return prompts.compact_sentences(words_data)


def _sug(start, end, quote, status="bad", action="cut", **kw):
    return {"action": action, "status": status, "start": start, "end": end,
            "quote": quote, "reason": "r", "category": "other", **kw}


def test_map_exact_sentence_match(sentences):
    # Sentence 0: 0.0-1.2 "hey guys welcome back"
    out = mapping.map_edit_suggestions([_sug(0.0, 1.2, "hey guys welcome back")], sentences)
    assert out[0]["mapped"] is True
    assert out[0]["word_ids"] == [0, 1, 2, 3]
    assert out[0]["confidence"] >= 0.9


def test_map_narrows_to_quoted_words(sentences):
    # quote only covers "today we" inside sentence 2 (ids 4..10)
    out = mapping.map_edit_suggestions([_sug(1.5, 2.2, "today we")], sentences)
    assert out[0]["mapped"] is True
    assert out[0]["word_ids"] == [5, 6]


def test_map_low_confidence_marks_unmapped(sentences):
    out = mapping.map_edit_suggestions([_sug(300.0, 301.0, "completely absent text")], sentences)
    assert out[0]["mapped"] is False
    assert out[0]["word_ids"] == []


def test_map_clamps_range_to_sentence(sentences):
    out = mapping.map_edit_suggestions(
        [_sug(0.0, 1.3, "hey guys welcome back let's jump into it")], sentences)
    assert out[0]["mapped"] is True
    assert out[0]["start"] == pytest.approx(sentences[0]["start"], abs=0.6)
    assert out[0]["end"] <= sentences[-1]["end"] + 0.01


def test_dedup_merges_overlapping_same_status(sentences):
    items = [
        {"action": "cut", "status": "bad", "start": 1.5, "end": 2.0, "quote": "um",
         "word_ids": [4], "mapped": True, "confidence": 0.9, "reason": "a", "category": "filler"},
        {"action": "cut", "status": "bad", "start": 1.55, "end": 2.05, "quote": "um",
         "word_ids": [4], "mapped": True, "confidence": 0.7, "reason": "b", "category": "filler"},
        {"action": "cut", "status": "repeat", "start": 3.0, "end": 4.0, "quote": "x",
         "word_ids": [8, 9], "mapped": True, "confidence": 0.8, "reason": "c", "category": "retake"},
    ]
    out = mapping.dedup_suggestions(items)
    assert len(out) == 2
    assert out[0]["confidence"] == 0.9  # higher-confidence twin kept


def test_merge_chunk_results_sorts_and_dedups(sentences):
    a = [_sug(1.5, 2.0, "um"), _sug(0.0, 1.2, "hey guys welcome back")]
    b = [_sug(1.52, 2.02, "um")]
    out = mapping.merge_chunk_results([a, b])
    starts = [s["start"] for s in out]
    assert starts == sorted(starts)
    assert len(out) == 2


def test_map_clips_clamps_and_sorts_by_score(sentences):
    clips = [
        {"start": 0.5, "end": 3.5, "title": "B", "score": 0.4, "platform": "shorts"},
        {"start": -5.0, "end": 2.0, "title": "A", "score": 0.9, "platform": "tiktok"},
        {"start": 10.0, "end": 50.0, "title": "C", "score": 0.6, "platform": "reels"},
    ]
    out = mapping.map_clips(clips, sentences)
    assert out[0]["title"] == "A"
    assert out[0]["start"] == pytest.approx(sentences[0]["start"], abs=0.01)
    assert out[1]["title"] == "C"
    assert out[1]["end"] == pytest.approx(sentences[-1]["end"], abs=0.01)
