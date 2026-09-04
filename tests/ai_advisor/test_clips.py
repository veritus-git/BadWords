import json

import pytest

from ai_advisor import clips


def _clip(start, end, accepted=True, title="Clip"):
    return {"start": start, "end": end, "title": title, "hook": "h", "reason": "r",
            "score": 0.8, "platform": "shorts", "accepted": accepted, "marker_added": False}


def test_build_marker_payloads_frames_and_filter():
    payloads = clips.build_marker_payloads(
        [_clip(1.0, 3.0), _clip(5.0, 6.0, accepted=False), _clip(10.0, 11.5, title="B")],
        fps=30.0, tl_start_frame=86400)
    assert payloads == [
        (86400 + 30, "[AI] Clip", "h\nr", 60),
        (86400 + 300, "[AI] B", "h\nr", 45),
    ]


class FakeTimeline:
    """old_api=True models the legacy Resolve signature: AddMarker(frame, color, name, note)
    raises TypeError when called with a 5th duration argument."""
    def __init__(self, old_api=False):
        self.calls = []
        self._old_api = old_api

    def AddMarker(self, frame, color, name, note, duration=None):
        if self._old_api and duration is not None:
            raise TypeError("AddMarker() takes 4 positional arguments but 5 were given")
        self.calls.append((frame, color, name, note, duration if duration is not None else 0))
        return True


class FakeHandler:
    def __init__(self):
        self.timeline = FakeTimeline()
        self.existing = set()
        self.os_doc = type("OS", (), {"get_temp_folder": staticmethod(lambda: "/tmp")})()

    def timeline_exists(self, name):
        return name in self.existing


def test_add_markers_uses_color_and_counts():
    h = FakeHandler()
    n = clips.add_markers(h, [(100, "[AI] A", "note", 50)], "Purple")
    assert n == 1
    assert h.timeline.calls == [(100, "Purple", "[AI] A", "note", 50)]


def test_add_markers_falls_back_to_4_arg_api():
    h = FakeHandler()
    h.timeline = FakeTimeline(old_api=True)
    n = clips.add_markers(h, [(100, "[AI] A", "note", 50)], "Purple")
    assert n == 1  # retried without duration on TypeError
    assert h.timeline.calls == [(100, "Purple", "[AI] A", "note", 0)]


def test_add_markers_no_timeline_raises():
    h = FakeHandler()
    h.timeline = None
    with pytest.raises(RuntimeError):
        clips.add_markers(h, [(100, "[AI] A", "note", 50)], "Purple")


def test_build_keep_only_ops_merges_and_filters():
    ops = clips.build_keep_only_ops([_clip(1.0, 3.0), _clip(3.0, 4.0),
                                     _clip(0.0, 0.02), _clip(10.0, 11.0, accepted=False)],
                                    fps=30.0)
    assert ops == [{"s": 30, "e": 120, "type": "normal"}]


def test_unique_timeline_name():
    h = FakeHandler()
    assert clips.unique_timeline_name(h) == "BadWords - Social Clips"
    h.existing.add("BadWords - Social Clips")
    assert clips.unique_timeline_name(h) == "BadWords - Social Clips 2"


def test_assemble_clips_calls_assembler(monkeypatch):
    h = FakeHandler()
    recorded = {}

    def fake_assemble(rh, original_tl_name, ops, new_tl_name, **kw):
        recorded.update({"orig": original_tl_name, "ops": ops, "name": new_tl_name})
        return True, {}, new_tl_name

    monkeypatch.setattr("assembler.assemble_via_drt", fake_assemble)
    name = clips.assemble_clips(h, "Episode 1", [_clip(1.0, 3.0)], 30.0)
    assert name == "BadWords - Social Clips"
    assert recorded["orig"] == "Episode 1"
    assert recorded["ops"] == [{"s": 30, "e": 90, "type": "normal"}]


def test_assemble_clips_empty_raises():
    with pytest.raises(ValueError):
        clips.assemble_clips(FakeHandler(), "T", [], 30.0)


def test_ai_json_roundtrip(tmp_path):
    path = str(tmp_path / "show.ai.json")
    clips.write_ai_json(path, [_clip(1.0, 2.0)], {"base_url": "http://x", "model": "m"})
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["version"] == 1 and data["provider"]["model"] == "m"
    assert clips.read_ai_json(path)[0]["title"] == "Clip"


def test_read_ai_json_missing_or_garbage(tmp_path):
    assert clips.read_ai_json(str(tmp_path / "nope.ai.json")) is None
    bad = tmp_path / "bad.ai.json"
    bad.write_text("{ not json", encoding="utf-8")
    assert clips.read_ai_json(str(bad)) is None
