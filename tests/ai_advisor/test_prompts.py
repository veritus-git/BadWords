import pytest

from ai_advisor import prompts
from conftest import build_words_data


def test_fmt_tc_and_parse_tc_roundtrip():
    assert prompts.fmt_tc(75.24) == "01:15.2"
    assert prompts.parse_tc("01:15.2") == pytest.approx(75.2, abs=0.05)
    assert prompts.fmt_tc(9.9) == "00:09.9"


def test_compact_sentences_groups_by_segment(words_data):
    sentences = prompts.compact_sentences(words_data)
    assert len(sentences) == 3
    first = sentences[0]
    assert first["text"] == "hey guys welcome back"
    assert first["word_ids"] == [0, 1, 2, 3]
    assert first["start"] == pytest.approx(0.0) and first["end"] == pytest.approx(1.2)


def test_compact_sentences_tags_fully_cut_sentence(words_data):
    sentences = prompts.compact_sentences(words_data)
    # Sentence 2 has statuses [bad, None, None, None, repeat, repeat, None] — NOT fully cut
    assert sentences[1]["tagged"] == ""
    # Force a fully-cut sentence and check tagging
    for w in words_data:
        if w["seg_start"] == 4.0:
            w["status"] = "bad"
    sentences = prompts.compact_sentences(words_data)
    assert sentences[2]["tagged"] == "[CUT] "


def test_build_chunks_respects_max_chars(words_data):
    sentences = prompts.compact_sentences(words_data)
    chunks = prompts.build_chunks(sentences, max_chars=60)
    assert len(chunks) >= 2
    for ch in chunks:
        assert len(ch["text"]) <= 60 + 200  # hard cap sanity (one long line allowed)
    joined_ids = [s["word_ids"] for ch in chunks for s in ch["sentences"]]
    flat = {wid for ids in joined_ids for wid in ids}
    assert flat == set(range(15))


def test_build_chunks_overlap_keeps_boundary_sentences():
    sentences = [{"start": i * 10.0, "end": i * 10.0 + 5, "text": f"s{i}",
                  "word_ids": [i], "word_texts": [f"s{i}"], "tagged": ""}
                 for i in range(10)]
    chunks = prompts.build_chunks(sentences, max_chars=45, overlap=2)
    # consecutive chunks share at most `overlap` sentences
    for a, b in zip(chunks, chunks[1:]):
        shared = {s["text"] for s in a["sentences"]} & {s["text"] for s in b["sentences"]}
        assert len(shared) <= 2


def test_parse_llm_json_tolerates_fences_and_prose():
    assert prompts.parse_llm_json('{"a": 1}') == {"a": 1}
    assert prompts.parse_llm_json('Sure!\n```json\n{"a": [1, 2]}\n```\ndone') == {"a": [1, 2]}
    assert prompts.parse_llm_json('blah {"a": {"b": 2}} blah') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        prompts.parse_llm_json("no json here")
    with pytest.raises(ValueError):
        prompts.parse_llm_json("")


def test_validate_edits_normalizes_and_drops_invalid():
    obj = {"suggestions": [
        {"start": "00:01.0", "end": "00:02.0", "quote": "um", "action": "cut",
         "status": "bad", "reason": "filler", "category": "filler"},
        {"start": "bogus", "end": "00:02.0", "quote": "x", "action": "cut", "status": "bad"},
        {"start": "00:05.0", "end": "00:04.0", "quote": "x", "action": "cut", "status": "bad"},
        {"start": "00:06.0", "end": "00:07.0", "quote": "x", "action": "cut", "status": "nonsense"},
        {"start": "00:08.0", "end": "00:09.0", "quote": "code", "action": "recolor",
         "status": "typo", "reason": "wrong word"},
    ]}
    out = prompts.validate_edits(obj)
    assert len(out) == 2
    assert out[0]["start"] == pytest.approx(1.0) and out[0]["status"] == "bad"
    assert out[1]["action"] == "recolor" and out[1]["status"] == "typo"


def test_validate_edits_rejects_wrong_shape():
    with pytest.raises(ValueError):
        prompts.validate_edits({"nope": []})
    with pytest.raises(ValueError):
        prompts.validate_edits("string")


def test_validate_clips_clamps_score_and_defaults():
    obj = {"clips": [
        {"start": "00:10.0", "end": "01:25.0", "title": "Hot take", "hook": "line",
         "reason": "r", "score": 2.5, "platform": "youtube"},
        {"start": "00:01.0", "end": "00:00.5"},
    ]}
    out = prompts.validate_clips(obj)
    assert len(out) == 1
    assert out[0]["score"] == 1.0
    assert out[0]["platform"] == "shorts"  # unknown → default
