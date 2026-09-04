import os
import sys

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import pytest


def build_words_data():
    """Synthetic transcript: 3 sentences (seg_start groups), ids sequential.
    Sentence 2 contains filler 'um' (bad) and a duplicated fragment (repeat)."""
    words = []

    def seg(texts, seg_start, statuses=None, dur=0.3):
        seg_end = seg_start + dur * len(texts)
        for i, txt in enumerate(texts):
            st = statuses[i] if statuses else None
            words.append({
                "text": txt, "start": round(seg_start + i * dur, 3),
                "end": round(seg_start + (i + 1) * dur, 3),
                "selected": st in ("bad", "repeat"), "status": st,
                "is_filler": st == "bad", "is_inaudible": False,
                "seg_start": seg_start, "seg_end": seg_end,
                "is_segment_start": i == 0, "type": "word", "id": len(words),
            })

    seg(["hey", "guys", "welcome", "back"], 0.0)
    seg(["um", "today", "we", "are", "recording", "the", "show"], 1.5,
        statuses=["bad", None, None, None, "repeat", "repeat", None])
    seg(["let's", "jump", "into", "it"], 4.0)
    return words


@pytest.fixture
def words_data():
    return build_words_data()


class FakeHTTPResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def fake_urlopen(monkeypatch):
    """Returns (install, calls). install(fn) registers a handler(request) that
    returns FakeHTTPResponse or raises. Every call is recorded in `calls`."""
    calls = []

    def install(handler):
        def _fake_urlopen(request, timeout=None):
            calls.append({"url": getattr(request, "full_url", request), "timeout": timeout,
                          "data": getattr(request, "data", None),
                          "headers": dict(getattr(request, "headers", {}) or {})})
            return handler(request)
        monkeypatch.setattr("ai_advisor.client.urllib.request.urlopen", _fake_urlopen)

    return install, calls


@pytest.fixture
def ai_cfg():
    from ai_advisor.client import AiConfig
    return AiConfig(base_url="http://fake:9999/v1", model="test-model")
