import pytest

from ai_advisor import mapping
from conftest import build_words_data


class FakeCanvas:
    def __init__(self, words):
        self.words_data = words
        self.updates = 0

    def update(self):
        self.updates += 1


class FakeUndo:
    def __init__(self):
        self.actions = []

    def push(self, action):
        self.actions.append(action)


class FakeMainWindow:
    """Duck-typed main_window with the real two-layer logic simplified."""

    def __init__(self, words):
        self.text_canvas = FakeCanvas(words)
        self.undo_manager = FakeUndo()

    def _calculate_visual_layer(self, word_obj):
        base = word_obj.get("manual_status")
        if base is None:
            if word_obj.get("_is_hallucination") or word_obj.get("is_bad"):
                base = "bad"
            elif word_obj.get("algo_status") == "repeat":
                base = "repeat"
            else:
                base = "normal"
        word_obj["status"] = base
        word_obj["selected"] = base in ("bad", "inaudible", "typo", "repeat")
        return base


def _item(word_ids, status="bad", accepted=True, mapped=True):
    return {"action": "cut", "status": status, "start": 0.0, "end": 1.0,
            "quote": "", "reason": "r", "category": "other",
            "word_ids": word_ids, "mapped": mapped, "accepted": accepted, "confidence": 0.9}


def test_apply_sets_manual_status_via_propagate():
    mw = FakeMainWindow(build_words_data())
    n = mapping.apply_accepted_edits(mw, [_item([4], status="bad")])
    w = mw.text_canvas.words_data[4]
    assert n >= 1
    assert w["status"] == "bad"
    assert w["manual_status"] == "bad"
    assert w["overlay_suppressed"] is True
    assert mw.text_canvas.updates == 1


def test_apply_pushes_single_undo_action():
    mw = FakeMainWindow(build_words_data())
    mapping.apply_accepted_edits(mw, [_item([0, 1]), _item([4])])
    assert len(mw.undo_manager.actions) == 1
    changes = mw.undo_manager.actions[0]["changes"]
    assert set(changes.keys()) == {0, 1, 4}
    for state in changes.values():
        assert set(state.keys()) == {"status", "manual_status", "algo_status",
                                     "is_auto", "selected"}


def test_apply_skips_unmapped_and_rejected():
    mw = FakeMainWindow(build_words_data())
    n = mapping.apply_accepted_edits(mw, [
        _item([0], accepted=False),
        _item([1], mapped=False),
        _item([2, 3]),
    ])
    assert n >= 2
    assert {0, 1} & set(mw.undo_manager.actions[0]["changes"].keys()) == set()
    assert {2, 3} <= set(mw.undo_manager.actions[0]["changes"].keys())


def test_apply_nothing_accepted_returns_zero():
    mw = FakeMainWindow(build_words_data())
    assert mapping.apply_accepted_edits(mw, [_item([0], accepted=False)]) == 0
    assert mw.undo_manager.actions == []


def test_build_undo_changes_snapshot_keys():
    words = build_words_data()
    snap = mapping.build_undo_changes(words, [0, 4])
    assert snap[0] == {k: words[0].get(k) for k in
                       ("status", "manual_status", "algo_status", "is_auto", "selected")}
