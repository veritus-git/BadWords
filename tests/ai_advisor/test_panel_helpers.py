import pytest

from ai_advisor import panel


class FakePrefs(dict):
    def set_pref(self, key, value):
        self[key] = value

    def get_all_prefs(self):
        return dict(self)


def test_load_ai_prefs_merges_defaults():
    prefs = FakePrefs({"ai_base_url": "http://custom:1/v1"})
    cfg = panel.load_ai_prefs(prefs)
    assert cfg["ai_base_url"] == "http://custom:1/v1"
    assert cfg["ai_temperature"] == panel.PREF_DEFAULTS["ai_temperature"]
    assert cfg["ai_marker_color"] == "Purple"


def test_save_ai_prefs_roundtrip():
    prefs = FakePrefs()
    panel.save_ai_prefs(prefs, {"ai_base_url": "http://y:2/v1", "ai_temperature": 0.5})
    assert prefs["ai_base_url"] == "http://y:2/v1"
    assert panel.load_ai_prefs(prefs)["ai_temperature"] == 0.5


def test_ai_json_path_sanitizes(tmp_path):
    fake = type("OS", (), {"get_saves_folder": staticmethod(lambda: str(tmp_path))})()
    mw = type("MW", (), {"_full_title": "My Show: Ep 1!",
                         "engine": type("E", (), {"os_doc": fake})()})()
    path = panel.ai_json_path(mw)
    assert path.startswith(str(tmp_path))
    assert path.endswith("My_Show_Ep_1.ai.json")


def test_job_suggest_edits_shape(monkeypatch, words_data, ai_cfg):
    from ai_advisor import client
    monkeypatch.setattr(client, "chat_json",
                        lambda msgs, cfg: {"suggestions": [
                            {"start": "00:00.0", "end": "00:01.2",
                             "quote": "hey guys welcome back", "action": "cut",
                             "status": "bad", "reason": "demo", "category": "other"}]})
    out = panel.job_suggest_edits(ai_cfg, words_data)
    assert out["kind"] == "edits"
    assert out["items"] and out["items"][0]["mapped"] is True
    assert out["items"][0]["word_ids"] == [0, 1, 2, 3]


def test_job_find_clips_shape(monkeypatch, words_data, ai_cfg):
    from ai_advisor import client
    monkeypatch.setattr(client, "chat_json",
                        lambda msgs, cfg: {"clips": [
                            {"start": "00:00.0", "end": "00:01.2", "title": "T",
                             "hook": "h", "reason": "r", "score": 0.9,
                             "platform": "shorts"}]})
    out = panel.job_find_clips(ai_cfg, words_data, ["shorts"])
    assert out["kind"] == "clips"
    assert out["items"][0]["end"] <= 1.3


def test_job_test_connection(monkeypatch, ai_cfg):
    from ai_advisor import client
    monkeypatch.setattr(client, "test_connection", lambda cfg: "OK — 1 model(s)")
    assert panel._job_test_connection(ai_cfg) == "OK — 1 model(s)"
