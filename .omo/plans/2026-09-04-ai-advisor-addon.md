# AI Advisor Addon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable LLM "AI Advisor" addon to BadWords that suggests transcript edits (accept/reject panel) and social-media clips (preview, Resolve markers, dedicated clips timeline), touching only `src/gui.py` in existing code.

**Architecture:** New isolated package `src/ai_advisor/` (client → prompts → mapping → clips → panel). The panel reads `main_window.text_canvas.words_data`, applies accepted suggestions through the exact paint path (`algorithms.propagate_status_change` → `_calculate_visual_layer`), adds markers via `ResolveHandler.timeline.AddMarker`, and assembles the clips timeline via `assembler.assemble_via_drt` with keep-only ops `{'s','e','type'}` (timeline-relative frames).

**Tech Stack:** Python 3 (app venv), PySide6 (existing), stdlib `urllib.request`/`json`/`dataclasses` (no new runtime deps), pytest for tests (dev machine only, not the app venv).

**Spec:** `docs/superpowers/specs/2026-09-04-ai-advisor-addon-design.md` (committed at `906783f`)

## Global Constraints

- Only existing file modified: `src/gui.py` (~15-25 lines). Never touch `engine.py`, `algorithms.py`, `api.py`, `assembler.py`, `osdoc.py`, `config.py`, `main.py`, `setupfiles/`.
- Zero new runtime dependencies: HTTP only via `urllib.request` + `json` + `dataclasses`. pytest is a dev-machine tool only, never installed into the app venv.
- Status vocabulary is exactly `"bad" | "repeat" | "typo" | None` (word-level). Never invent new statuses.
- Ops format for assembly: `{"s": int_frame, "e": int_frame, "type": str}` with frames **relative to timeline start**; use `"type": "normal"` for keep-only clip ops.
- Default AI marker color `"Purple"` (key of `config.RESOLVE_COLORS_HEX`; NOT one of the app's op colors Violet/Navy/Olive/Chocolate/Tan).
- All AI-panel UI strings live in `panel.STRINGS` (`"en"` + `"it"`); no changes to `config.get_trans`.
- No AI content ever reaches telemetry; the addon never calls `send_telemetry_ping`.
- Every panel entry point is exception-guarded: an addon failure logs via `osdoc.log_error` and never crashes the app.
- Tests never touch the network: `urllib.request.urlopen` is monkeypatched in every client test.
- Import style inside the addon: `import algorithms`, `import assembler` (flat, like gui.py does at gui.py:3606) work because `src/` is on `sys.path` at app runtime; tests add `src/` to `sys.path` via `tests/ai_advisor/conftest.py`.
- Commit style follows repo convention: `feat:`/`test:`/`docs:` prefixes, lowercase, concise.

## File Structure

| File | Responsibility |
|---|---|
| `src/ai_advisor/__init__.py` | Package marker + `open_panel(main_window)` factory |
| `src/ai_advisor/client.py` | OpenAI-compatible HTTP client, `AiConfig`, typed errors |
| `src/ai_advisor/prompts.py` | System prompts, transcript compaction/chunking, LLM JSON parse + schema validation |
| `src/ai_advisor/mapping.py` | LLM output → word ids (fuzzy), dedup/merge, undo snapshot, accepted-edits application |
| `src/ai_advisor/clips.py` | Marker payloads, keep-only ops, timeline naming, `.ai.json` IO, assemble via `assembler` |
| `src/ai_advisor/panel.py` | `AIPanel` QDialog (Advisor + Settings tabs), `STRINGS` en/it, prefs IO, QThread jobs |
| `tests/ai_advisor/conftest.py` | `sys.path` bootstrap + synthetic `words_data`/sentence fixtures + fake HTTP |
| `tests/ai_advisor/test_client.py` … | One test file per module |
| `src/gui.py` (modify only) | Titlebar "AI" button + `_show_ai_panel` (lazy import, exception-guarded) |

---

### Task 1: Package scaffold + OpenAI-compatible client

**Files:**
- Create: `src/ai_advisor/__init__.py`
- Create: `src/ai_advisor/client.py`
- Create: `tests/ai_advisor/conftest.py`
- Create: `tests/ai_advisor/test_client.py`

**Interfaces (produced):**
- `AiConfig` dataclass: `base_url: str`, `api_key: str`, `model: str`, `temperature: float`, `timeout_s: int`, `max_chars: int`; classmethod `AiConfig.from_prefs(prefs: dict) -> AiConfig`
- `AiClientError(Exception)`, `AiAuthError(AiClientError)`, `AiBadResponse(AiClientError)`
- `chat_json(messages: list[dict], cfg: AiConfig) -> dict` (parsed JSON object; schema validation is NOT its job)
- `list_models(cfg) -> list[str]`
- `test_connection(cfg) -> str` (raises on failure)
- `DEFAULT_BASE_URLS = {"lmstudio": "http://localhost:1234/v1", "ollama": "http://localhost:11434/v1", "custom": ""}`
- Prefs keys: `ai_base_url`, `ai_api_key`, `ai_model`, `ai_temperature`, `ai_timeout_s`, `ai_max_chars`

- [ ] **Step 1: Write conftest + failing client tests**

Create `tests/ai_advisor/conftest.py`:

```python
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
    """Returns (install, calls). install(fn) registers a handler(url, request) that
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
```

Create `tests/ai_advisor/test_client.py`:

```python
import io
import json
import urllib.error

import pytest

from ai_advisor import client
from conftest import FakeHTTPResponse


def _chat_payload(content):
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def test_chat_json_returns_parsed_dict(fake_urlopen, ai_cfg):
    install, calls = fake_urlopen
    install(lambda req: FakeHTTPResponse(json.dumps(_chat_payload('{"a": 1}')).encode()))
    out = client.chat_json([{"role": "user", "content": "hi"}], ai_cfg)
    assert out == {"a": 1}
    req = calls[0]
    assert req["url"].endswith("/chat/completions")
    body = json.loads(req["data"].decode("utf-8"))
    assert body["model"] == "test-model"
    assert body["response_format"] == {"type": "json_object"}


def test_chat_json_retries_without_response_format(fake_urlopen, ai_cfg):
    install, calls = fake_urlopen
    state = {"n": 0}

    def handler(req):
        state["n"] += 1
        if state["n"] == 1:
            raise urllib.error.HTTPError(req.full_url, 400,
                "Bad Request", {}, io.BytesIO(b'{"error": "response_format not supported"}'))
        return FakeHTTPResponse(json.dumps(_chat_payload('{"ok": true}')).encode())

    install(handler)
    out = client.chat_json([{"role": "user", "content": "hi"}], ai_cfg)
    assert out == {"ok": True}
    assert state["n"] == 2
    assert "response_format" not in json.loads(calls[1]["data"].decode("utf-8"))


def test_chat_json_401_raises_auth_error(fake_urlopen, ai_cfg):
    install, _ = fake_urlopen
    install(lambda req: (_ for _ in ()).throw(urllib.error.HTTPError(
        req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"no key"))))
    with pytest.raises(client.AiAuthError):
        client.chat_json([{"role": "user", "content": "hi"}], ai_cfg)


def test_chat_json_connection_error(fake_urlopen, ai_cfg):
    install, _ = fake_urlopen
    install(lambda req: (_ for _ in ()).throw(urllib.error.URLError("connection refused")))
    with pytest.raises(client.AiClientError) as exc:
        client.chat_json([{"role": "user", "content": "hi"}], ai_cfg)
    assert "connection refused" in str(exc.value)


def test_chat_json_invalid_json_raises_bad_response(fake_urlopen, ai_cfg):
    install, _ = fake_urlopen
    install(lambda req: FakeHTTPResponse(
        json.dumps(_chat_payload("not json at all")).encode()))
    with pytest.raises(client.AiBadResponse):
        client.chat_json([{"role": "user", "content": "hi"}], ai_cfg)


def test_chat_json_invalid_json_retries_then_bad_response(fake_urlopen, ai_cfg):
    install, calls = fake_urlopen
    state = {"n": 0}

    def handler(req):
        state["n"] += 1
        return FakeHTTPResponse(json.dumps(_chat_payload("not json at all")).encode())

    install(handler)
    with pytest.raises(client.AiBadResponse):
        client.chat_json([{"role": "user", "content": "hi"}], ai_cfg)
    assert state["n"] == 2  # spec §6: one stricter-JSON retry before failing
    last = json.loads(calls[1]["data"].decode("utf-8"))["messages"][-1]["content"]
    assert "valid JSON" in last


def test_list_models(fake_urlopen, ai_cfg):
    install, calls = fake_urlopen
    install(lambda req: FakeHTTPResponse(
        json.dumps({"data": [{"id": "m1"}, {"id": "m2"}]}).encode()))
    assert client.list_models(ai_cfg) == ["m1", "m2"]
    assert calls[0]["url"].endswith("/models")


def test_test_connection_returns_description(fake_urlopen, ai_cfg):
    install, _ = fake_urlopen
    install(lambda req: FakeHTTPResponse(
        json.dumps({"data": [{"id": "m1"}]}).encode()))
    desc = client.test_connection(ai_cfg)
    assert "m1" in desc


def test_from_prefs_defaults():
    cfg = client.AiConfig.from_prefs({})
    assert cfg.base_url == "http://localhost:1234/v1"
    assert cfg.temperature == 0.2
    cfg2 = client.AiConfig.from_prefs({"ai_base_url": "http://x:1/v1", "ai_model": "z",
                                       "ai_temperature": "0.7", "ai_max_chars": "100"})
    assert cfg2.base_url == "http://x:1/v1" and cfg2.model == "z"
    assert cfg2.temperature == 0.7 and cfg2.max_chars == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/ai_advisor/test_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ai_advisor'` (or ImportError inside).

- [ ] **Step 3: Implement `src/ai_advisor/__init__.py`**

```python
"""AI Advisor addon for BadWords.

LLM-powered edit suggestions and social-clip finder, OpenAI-compatible
providers (LM Studio, Ollama, cloud). See docs/superpowers/specs/
2026-09-04-ai-advisor-addon-design.md.
"""

__version__ = "0.1.0"


def open_panel(main_window):
    """Open the AI Advisor panel. Called from gui.py, exception-guarded there."""
    from .panel import AIPanel
    return AIPanel(main_window)
```

- [ ] **Step 4: Implement `src/ai_advisor/client.py`**

```python
"""OpenAI-compatible LLM client (LM Studio, Ollama, cloud). Stdlib only."""

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_BASE_URLS = {
    "lmstudio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434/v1",
    "custom": "",
}

_PREF_DEFAULTS = {
    "ai_base_url": "http://localhost:1234/v1",
    "ai_api_key": "",
    "ai_model": "",
    "ai_temperature": 0.2,
    "ai_timeout_s": 120,
    "ai_max_chars": 24000,
}


class AiClientError(Exception):
    """Base error for all AI client failures."""


class AiAuthError(AiClientError):
    """HTTP 401/403 — bad or missing API key."""


class AiBadResponse(AiClientError):
    """Server responded but the payload is unusable (empty content, bad JSON)."""


@dataclass
class AiConfig:
    base_url: str = "http://localhost:1234/v1"
    api_key: str = ""
    model: str = ""
    temperature: float = 0.2
    timeout_s: int = 120
    max_chars: int = 24000

    @classmethod
    def from_prefs(cls, prefs):
        def _get(key, cast, default):
            raw = prefs.get(key, default)
            try:
                return cast(raw)
            except (TypeError, ValueError):
                return default
        return cls(
            base_url=str(prefs.get("ai_base_url") or _PREF_DEFAULTS["ai_base_url"]),
            api_key=str(prefs.get("ai_api_key") or ""),
            model=str(prefs.get("ai_model") or ""),
            temperature=_get("ai_temperature", float, _PREF_DEFAULTS["ai_temperature"]),
            timeout_s=_get("ai_timeout_s", int, _PREF_DEFAULTS["ai_timeout_s"]),
            max_chars=_get("ai_max_chars", int, _PREF_DEFAULTS["ai_max_chars"]),
        )


def _headers(cfg):
    h = {"Content-Type": "application/json"}
    if cfg.api_key:
        h["Authorization"] = f"Bearer {cfg.api_key}"
    return h


def _read_error_body(e):
    try:
        return e.read().decode("utf-8", "replace")[:300]
    except Exception:
        return ""


def _post_json(url, payload, cfg):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST", headers=_headers(cfg))
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = _read_error_body(e)
        if e.code in (401, 403):
            raise AiAuthError(f"HTTP {e.code}: {body}")
        err = AiClientError(f"HTTP {e.code}: {body}")
        err.body = body
        raise err
    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        reason = getattr(e, "reason", e)
        raise AiClientError(f"Connection failed: {reason}") from e
    except json.JSONDecodeError as e:
        raise AiBadResponse(f"Server returned invalid JSON envelope: {e}") from e


def _get_json(url, cfg):
    req = urllib.request.Request(url, method="GET", headers=_headers(cfg))
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = _read_error_body(e)
        if e.code in (401, 403):
            raise AiAuthError(f"HTTP {e.code}: {body}")
        raise AiClientError(f"HTTP {e.code}: {body}")
    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        reason = getattr(e, "reason", e)
        raise AiClientError(f"Connection failed: {reason}") from e


def _extract_content(envelope):
    try:
        content = envelope["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise AiBadResponse(f"Unexpected chat response shape: {envelope!r:.200}") from e
    if not content or not str(content).strip():
        raise AiBadResponse("Model returned empty content")
    return str(content)


def chat_json(messages, cfg):
    """POST /chat/completions, return the parsed JSON object the model produced.

    Retries once WITHOUT `response_format` if the server rejects that field, and
    once with a stricter JSON instruction if the model emits unparseable JSON
    (spec §6). Raises AiClientError family; does NOT schema-validate the payload.
    """
    url = cfg.base_url.rstrip("/") + "/chat/completions"
    use_rf = True

    def _call(msgs):
        nonlocal use_rf
        payload = {"model": cfg.model, "messages": msgs, "temperature": cfg.temperature}
        if use_rf:
            payload["response_format"] = {"type": "json_object"}
        try:
            envelope = _post_json(url, payload, cfg)
        except AiClientError as e:
            if use_rf and "response_format" in str(getattr(e, "body", "")):
                use_rf = False
                payload.pop("response_format", None)
                envelope = _post_json(url, payload, cfg)
            else:
                raise
        return _extract_content(envelope)

    from ai_advisor import prompts
    content = _call(messages)
    try:
        return prompts.parse_llm_json(content)
    except ValueError:
        retry_msgs = list(messages) + [{
            "role": "user",
            "content": ("Your previous reply was not valid JSON. Reply again with "
                        "ONLY a valid JSON object and nothing else.")}]
        content2 = _call(retry_msgs)
        try:
            return prompts.parse_llm_json(content2)
        except ValueError as e:
            raise AiBadResponse(f"Model produced unparseable JSON twice: {e}") from e


def list_models(cfg):
    data = _get_json(cfg.base_url.rstrip("/") + "/models", cfg)
    return [m["id"] for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]


def test_connection(cfg):
    models = list_models(cfg)
    return f"OK — {len(models)} model(s) available" + (
        f", first: {models[0]}" if models else "")
```

> Layering note: `client.chat_json` imports `prompts.parse_llm_json` lazily inside the
> function to avoid a module-import cycle (prompts must stay importable standalone in tests).
> `prompts.parse_llm_json` is implemented in Task 2 — for Step 4-6 the client tests exercise
> the parse path through it, so Task 1 and Task 2 are implemented in this order ONLY IF the
> parse function is stubbed; instead implement Task 2's `parse_llm_json` NOW (copy that one
> function from Task 2 into a minimal `prompts.py` with just `parse_llm_json`), and Task 2
> fills in the rest. This is the only forward dependency between tasks.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/ai_advisor/test_client.py -v`
Expected: PASS (all 8 tests).

- [ ] **Step 6: Commit**

```bash
git add src/ai_advisor/__init__.py src/ai_advisor/client.py src/ai_advisor/prompts.py tests/ai_advisor/
git commit -m "feat(ai-advisor): package scaffold + OpenAI-compatible LLM client"
```
(prompts.py at this point contains only `parse_llm_json`; final line of that file:

```python
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
```
)

---

### Task 2: prompts.py — transcript compaction, chunking, validation

**Files:**
- Modify: `src/ai_advisor/prompts.py` (append to the file created in Task 1)
- Test: `tests/ai_advisor/test_prompts.py`

**Interfaces (produced):**
- `EDIT_SYSTEM_PROMPT: str`, `CLIPS_SYSTEM_PROMPT: str`
- `fmt_tc(t: float) -> str` (`"mm:ss.d"`), `parse_tc(s: str) -> float`
- `compact_sentences(words_data: list[dict]) -> list[dict]` — each: `{"start": float, "end": float, "text": str, "word_ids": list[int], "word_texts": list[str], "tagged": "" | "[CUT] "}`
- `build_chunks(sentences: list[dict], max_chars: int, overlap: int = 2) -> list[dict]` — each: `{"header": str, "text": str, "sentences": list[dict]}`
- `validate_edits(obj: dict) -> list[dict]` — normalized: `{"action": "cut"|"recolor", "status": "bad"|"repeat"|"typo", "start": float, "end": float, "quote": str, "reason": str, "category": str}` (invalid entries silently dropped)
- `validate_clips(obj: dict) -> list[dict]` — normalized: `{"start": float, "end": float, "title": str, "hook": str, "reason": str, "score": float, "platform": str}`
- Refines the spec's `index_map`: sentence-level matching replaces per-line maps (sentences carry `word_ids` directly).

- [ ] **Step 1: Write failing tests**

Create `tests/ai_advisor/test_prompts.py`:

```python
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
    assert flat == {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/ai_advisor/test_prompts.py -v`
Expected: FAIL — `AttributeError: module 'ai_advisor.prompts' has no attribute 'fmt_tc'`.

- [ ] **Step 3: Implement — append to `src/ai_advisor/prompts.py`**

```python
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
            "header": f"TRANSCRIPT PART {len(chunks) + 1} ({len(chunks)} done before; "
                      f"timestamps are absolute, not per-part)",
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/ai_advisor/test_prompts.py tests/ai_advisor/test_client.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add src/ai_advisor/prompts.py tests/ai_advisor/test_prompts.py
git commit -m "feat(ai-advisor): transcript compaction, chunking and LLM schema validation"
```

---

### Task 3: mapping.py — LLM output → word ids

**Files:**
- Create: `src/ai_advisor/mapping.py`
- Test: `tests/ai_advisor/test_mapping.py`

**Interfaces (produces):**
- `CONF_MIN = 0.5`
- `map_edit_suggestions(suggestions: list[dict], sentences: list[dict]) -> list[dict]` — each returned item adds: `word_ids: list[int]`, `mapped: bool`, `confidence: float` (0..1), and clamps `start`/`end` to the matched sentence
- `dedup_suggestions(items: list[dict]) -> list[dict]`
- `merge_chunk_results(chunk_lists: list[list[dict]]) -> list[dict]` — concat + dedup + sort by `start`
- `map_clips(clips: list[dict], sentences: list[dict]) -> list[dict]` — clamps `start`/`end` into transcript bounds, sorts by `score` desc
- Consumes: `algorithms.calculate_similarity` (existing, algorithms.py:226)

- [ ] **Step 1: Write failing tests**

Create `tests/ai_advisor/test_mapping.py`:

```python
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
    out = mapping.map_edit_suggestions([_sug(0.0, 1.3, "hey guys welcome back let's jump into it")],
                                       sentences)
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
    assert out[2]["end"] == pytest.approx(sentences[-1]["end"], abs=0.01)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/ai_advisor/test_mapping.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ai_advisor.mapping'`.

- [ ] **Step 3: Implement `src/ai_advisor/mapping.py`**

```python
"""Map LLM suggestions/clips onto real transcript word ids (fuzzy matching)."""

CONF_MIN = 0.5

import algorithms  # flat import, same as gui.py — src/ is on sys.path


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
        c["start"] = max(lo, min(float(c["start"]), hi))
        c["end"] = max(c["start"] + 0.5, min(float(c["end"]), hi))
        out.append(c)
    return sorted(out, key=lambda x: x.get("score", 0.0), reverse=True)
```

> `algorithms.calculate_similarity(s1, s2)` returns a 0..1 float (algorithms.py:226-229).
> Verify during implementation with one manual check in `python3 -c` if it differs; if it
> returns something else (e.g. 0..100), normalize inside `_sentence_score` before use.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/ai_advisor/test_mapping.py -v`
Expected: PASS (all 7).

- [ ] **Step 5: Commit**

```bash
git add src/ai_advisor/mapping.py tests/ai_advisor/test_mapping.py
git commit -m "feat(ai-advisor): fuzzy mapping of LLM suggestions to transcript word ids"
```

---

### Task 4: clips.py — markers, keep-only ops, `.ai.json`, assembly

**Files:**
- Create: `src/ai_advisor/clips.py`
- Test: `tests/ai_advisor/test_clips.py`

**Interfaces (produces):**
- `build_marker_payloads(clips: list[dict], fps: float, tl_start_frame: int) -> list[tuple[int, str, str, int]]` — `(frame, name, note, duration_frames)`
- `add_markers(resolve_handler, payloads, color: str) -> int` — the ONLY Resolve side-effect in the addon besides assembly
- `build_keep_only_ops(clips: list[dict], fps: float) -> list[dict]` — `{"s": int, "e": int, "type": "normal"}` frames relative to timeline start
- `unique_timeline_name(resolve_handler, base: str = "BadWords - Social Clips") -> str`
- `assemble_clips(resolve_handler, original_tl_name: str, clips: list[dict], fps: float) -> str` — returns the new timeline name; consumes `assembler.assemble_via_drt` (assembler.py:482)
- `write_ai_json(path: str, clips: list[dict], provider: dict) -> None`
- `read_ai_json(path: str) -> list[dict] | None`
- Consumes: `ResolveHandler.timeline_exists` (api.py:890), `assembler.assemble_via_drt` returning `(ok, color_schedule, actual_tl_name)`

- [ ] **Step 1: Write failing tests**

Create `tests/ai_advisor/test_clips.py`:

```python
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
    def __init__(self, fail_first=0):
        self.calls = []
        self._fail_first = fail_first

    def AddMarker(self, frame, color, name, note, duration):
        if self._fail_first > 0:
            self._fail_first -= 1
            raise TypeError("AddMarker() takes 4 arguments")
        self.calls.append((frame, color, name, note, duration))
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
    h.timeline._fail_first = 1
    n = clips.add_markers(h, [(100, "[AI] A", "note", 50)], "Purple")
    assert n == 1  # retried without duration on TypeError


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/ai_advisor/test_clips.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/ai_advisor/clips.py`**

```python
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
```

> The keep-only semantics follow from `calculate_timeline_structure` (engine.py:2219-2325):
> ops are the blocks KEPT (those whose color is not in `auto_cut_colors` are filtered OUT of
> cuts, i.e. ops list = keep list); `assemble_via_drt` applies exactly these ops to the
> exported `.drt`. `"normal"` maps to no color (`COLOR_MAP` miss at engine.py:2304-2315) so
> clip ops never collide with auto-cut colors.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/ai_advisor/test_clips.py -v`
Expected: PASS (all 9).

- [ ] **Step 5: Commit**

```bash
git add src/ai_advisor/clips.py tests/ai_advisor/test_clips.py
git commit -m "feat(ai-advisor): clip markers, keep-only ops and .ai.json persistence"
```

---

### Task 5: apply_accepted_edits — pure logic mirroring the paint path

**Files:**
- Modify: `src/ai_advisor/mapping.py` (append)
- Test: `tests/ai_advisor/test_apply_edits.py`

**Interfaces (produces):**
- `build_undo_changes(words_data: list[dict], word_ids: list[int]) -> dict` — `{wid: {status, manual_status, algo_status, is_auto, selected}}` (exact keys UndoManager restores, gui.py:2798-2804)
- `apply_accepted_edits(main_window, items: list[dict]) -> int` — applies all `mapped and accepted` items through the paint path; returns touched word count. Consumes: `main_window.text_canvas.words_data`, `main_window.undo_manager.push(action)`, `main_window._calculate_visual_layer(word_obj)`, `algorithms.propagate_status_change` (algorithms.py:1771 — sets `manual_status` itself, verified).

- [ ] **Step 1: Write failing tests**

Create `tests/ai_advisor/test_apply_edits.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/ai_advisor/test_apply_edits.py -v`
Expected: FAIL — `AttributeError: module 'ai_advisor.mapping' has no attribute 'apply_accepted_edits'`.

- [ ] **Step 3: Implement — append to `src/ai_advisor/mapping.py`**

```python
# ── Applying accepted edits (mirrors the paint path, gui.py:3584-3627) ──────

UNDO_KEYS = ("status", "manual_status", "algo_status", "is_auto", "selected")


def build_undo_changes(words_data, word_ids):
    """Snapshot the UndoManager-restorable keys for the given word ids."""
    id_map = {w["id"]: w for w in words_data}
    changes = {}
    for wid in word_ids:
        w = id_map.get(wid)
        if w is None:
            continue
        changes[wid] = {k: w.get(k) for k in UNDO_KEYS}
    return changes


def apply_accepted_edits(main_window, items):
    """Apply every mapped+accepted suggestion exactly like a manual paint.

    One UndoManager action for the whole batch. Returns touched word count.
    """
    canvas = main_window.text_canvas
    words_data = canvas.words_data
    accepted = [s for s in items if s.get("mapped") and s.get("accepted") and s.get("word_ids")]
    if not accepted:
        return 0

    id_map = {w["id"]: w for w in words_data}
    changes = {}
    for s in accepted:
        for wid, snap in build_undo_changes(words_data, s["word_ids"]).items():
            changes.setdefault(wid, snap)  # first observed state wins
    main_window.undo_manager.push({"type": "paint", "changes": changes})

    import algorithms
    touched = set()
    for s in accepted:
        for wid in s["word_ids"]:
            if wid in touched:
                continue
            updates = algorithms.propagate_status_change(words_data, wid, s["status"])
            for u_wid, _raw in updates:
                w = id_map.get(u_wid)
                if w is None:
                    continue
                w["overlay_suppressed"] = True
                w.pop("is_assembled_cut", None)
                main_window._calculate_visual_layer(w)
                touched.add(u_wid)

    canvas.update()
    return len(touched)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/ai_advisor/test_apply_edits.py tests/ai_advisor/test_mapping.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_advisor/mapping.py tests/ai_advisor/test_apply_edits.py
git commit -m "feat(ai-advisor): batch apply accepted edits through the paint path with undo"
```

---

### Task 6: panel.py — AIPanel dialog, jobs, prefs helpers

**Files:**
- Create: `src/ai_advisor/panel.py`

**Interfaces (produces):**
- `STRINGS: dict` (`"en"`/`"it"`)
- `PREF_DEFAULTS: dict`, `load_ai_prefs(os_doc) -> dict`, `save_ai_prefs(os_doc, values: dict)`
- `ai_json_path(main_window) -> str` — `os_doc.get_saves_folder()/sanitize(_full_title).ai.json`
- `job_suggest_edits(cfg, words_data, progress=None) -> {"kind": "edits", "items": [...]}`
- `job_find_clips(cfg, words_data, platforms: list[str], progress=None) -> {"kind": "clips", "items": [...]}`
- `job_add_markers(resolve_handler, payloads, color, progress=None) -> int`
- `job_assemble_clips(resolve_handler, original_tl_name, clips, fps, progress=None) -> str`
- `_AIWorker(QThread)` with signals `done(object)`, `failed(str)`, `progress(str)`; every `job_*` accepts `progress=None`
- `AIPanel(QDialog)` — Settings tab + Advisor tab, accepts/rejects, Apply/Markers/Assemble buttons
- Verification is `py_compile` + an import smoke test only (PySide6 widget tests need a running display + pytest-qt which we do NOT add; manual e2e is Task 8)

- [ ] **Step 1: Write the pure-helper smoke test**

Create `tests/ai_advisor/test_panel_helpers.py`:

```python
import pytest

from ai_advisor import panel


class FakePrefs(dict):
    def set_pref(self, key, value):
        self[key] = value


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


def test_ai_json_path_sanitizes(tmp_path, monkeypatch):
    fake = type("OS", (), {"get_saves_folder": staticmethod(lambda: str(tmp_path))})()
    mw = type("MW", (), {"_full_title": "My Show: Ep 1!", "engine":
                         type("E", (), {"os_doc": fake})()})()
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/ai_advisor/test_panel_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ai_advisor.panel'`.

- [ ] **Step 3: Implement `src/ai_advisor/panel.py`**

```python
"""AI Advisor panel: Settings tab, Advisor tab, QThread jobs, prefs helpers."""

import os
import re

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from ai_advisor import clips, client, mapping, prompts

# ── UI strings (en/it; no config.get_trans changes) ─────────────────────────

STRINGS = {
    "en": {
        "tab_advisor": "Advisor", "tab_settings": "Settings",
        "btn_edits": "Suggest Edits", "btn_clips": "Find Social Clips",
        "btn_apply": "Apply {n} accepted", "btn_markers": "Add Markers",
        "btn_assemble": "Assemble Clips Timeline", "btn_preview": "Preview",
        "btn_accept": "✓", "btn_reject": "✗", "btn_accept_all": "Accept all",
        "lbl_preset": "Preset", "lbl_base_url": "Base URL", "lbl_api_key": "API key",
        "lbl_model": "Model", "lbl_temperature": "Temperature", "lbl_max_chars": "Max chars per request",
        "lbl_timeout": "Timeout (s)", "lbl_marker_color": "AI marker color",
        "lbl_platforms": "Platforms", "btn_test": "Test Connection", "btn_refresh_models": "⟳",
        "lbl_cloud_warning": "⚠ Cloud endpoint: the transcript will leave this machine.",
        "lbl_idle": "Ready.", "lbl_working": "Working…", "lbl_need_transcript":
        "Run a transcription first (no transcript in this session).",
        "lbl_need_resolve": "DaVinci Resolve is not connected.",
        "lbl_applied": "Applied {n} word change(s).", "lbl_markers": "Added {n} marker(s).",
        "lbl_assembled": "Created timeline: {name}", "lbl_unmapped": "unmapped",
        "lbl_score": "score", "lbl_no_results": "No results yet — run an analysis.",
        "lbl_load_saved": "Loaded {n} saved clip(s) from .ai.json",
        "err_title": "AI Advisor",
    },
    "it": {
        "tab_advisor": "Advisor", "tab_settings": "Impostazioni",
        "btn_edits": "Suggerisci edit", "btn_clips": "Cerca clip social",
        "btn_apply": "Applica {n} accettati", "btn_markers": "Aggiungi marker",
        "btn_assemble": "Assembla timeline clip", "btn_preview": "Anteprima",
        "btn_accept": "✓", "btn_reject": "✗", "btn_accept_all": "Accetta tutti",
        "lbl_preset": "Preset", "lbl_base_url": "Base URL", "lbl_api_key": "API key",
        "lbl_model": "Modello", "lbl_temperature": "Temperatura", "lbl_max_chars": "Caratteri max per richiesta",
        "lbl_timeout": "Timeout (s)", "lbl_marker_color": "Colore marker AI",
        "lbl_platforms": "Piattaforme", "btn_test": "Testa connessione", "btn_refresh_models": "⟳",
        "lbl_cloud_warning": "⚠ Endpoint cloud: il trascritto lascerà questa macchina.",
        "lbl_idle": "Pronto.", "lbl_working": "Elaborazione…", "lbl_need_transcript":
        "Esegui prima una trascrizione (nessun trascritto in questa sessione).",
        "lbl_need_resolve": "DaVinci Resolve non è connesso.",
        "lbl_applied": "Applicate {n} modifiche alle parole.", "lbl_markers": "Aggiunti {n} marker.",
        "lbl_assembled": "Creata timeline: {name}", "lbl_unmapped": "non mappato",
        "lbl_score": "punteggio", "lbl_no_results": "Nessun risultato — avvia un'analisi.",
        "lbl_load_saved": "Caricati {n} clip salvati da .ai.json",
        "err_title": "AI Advisor",
    },
}

STATUS_HEX = {"bad": "#e5484d", "repeat": "#4c7dd0", "typo": "#57a05a"}

PREF_DEFAULTS = {
    "ai_provider_preset": "lmstudio",
    "ai_base_url": client.DEFAULT_BASE_URLS["lmstudio"],
    "ai_api_key": "",
    "ai_model": "",
    "ai_temperature": 0.2,
    "ai_timeout_s": 120,
    "ai_max_chars": 24000,
    "ai_marker_color": "Purple",
    "ai_platforms": ["shorts", "tiktok", "reels"],
}

_PREF_INTS = {"ai_timeout_s", "ai_max_chars"}
_PREF_FLOATS = {"ai_temperature"}


def load_ai_prefs(os_doc):
    raw = os_doc.get_all_prefs() or {}
    out = dict(PREF_DEFAULTS)
    for key, default in PREF_DEFAULTS.items():
        val = raw.get(key, default)
        if key in _PREF_INTS:
            try:
                val = int(val)
            except (TypeError, ValueError):
                val = default
        elif key in _PREF_FLOATS:
            try:
                val = float(val)
            except (TypeError, ValueError):
                val = default
        out[key] = val
    return out


def save_ai_prefs(os_doc, values):
    for key, val in values.items():
        if key in PREF_DEFAULTS:
            os_doc.set_pref(key, val)


def ai_json_path(main_window):
    """<saves_folder>/<sanitized session title>.ai.json"""
    os_doc = main_window.engine.os_doc
    title = getattr(main_window, "_full_title", "") or "session"
    safe = "".join(ch for ch in str(title) if ch.isalnum() or ch in "_- ").replace(" ", "_") or "session"
    return os.path.join(os_doc.get_saves_folder(), safe + ".ai.json")


def _cfg_from(prefs):
    return client.AiConfig(
        base_url=prefs["ai_base_url"], api_key=prefs["ai_api_key"],
        model=prefs["ai_model"], temperature=float(prefs["ai_temperature"]),
        timeout_s=int(prefs["ai_timeout_s"]), max_chars=int(prefs["ai_max_chars"]))


# ── Jobs (pure, run inside _AIWorker; all accept progress=None) ─────────────

def job_suggest_edits(cfg, words_data, progress=None):
    sentences = prompts.compact_sentences(words_data)
    if not sentences:
        raise ValueError("Empty transcript")
    chunks = prompts.build_chunks(sentences, cfg.max_chars)
    raw = []
    for i, ch in enumerate(chunks, 1):
        if progress:
            progress(f"Analyzing part {i}/{len(chunks)}…")
        obj = client.chat_json([{"role": "system", "content": prompts.EDIT_SYSTEM_PROMPT},
                                {"role": "user", "content": ch["text"]}], cfg)
        raw.extend(prompts.validate_edits(obj))
    merged = mapping.merge_chunk_results([mapping.map_edit_suggestions(raw, sentences)])
    return {"kind": "edits", "items": merged}


def job_find_clips(cfg, words_data, platforms, progress=None):
    sentences = prompts.compact_sentences(words_data)
    if not sentences:
        raise ValueError("Empty transcript")
    chunks = prompts.build_chunks(sentences, cfg.max_chars)
    brief = (f"Target platforms: {', '.join(platforms)}. "
             f"Duration: 20-90 seconds per clip.")
    raw = []
    for i, ch in enumerate(chunks, 1):
        if progress:
            progress(f"Scanning part {i}/{len(chunks)}…")
        obj = client.chat_json([{"role": "system", "content": prompts.CLIPS_SYSTEM_PROMPT},
                                {"role": "user", "content": brief + "\n\n" + ch["text"]}], cfg)
        raw.extend(prompts.validate_clips(obj))
    mapped = mapping.map_clips(raw, sentences)
    return {"kind": "clips", "items": mapped}


def job_add_markers(resolve_handler, payloads, color, progress=None):
    return clips.add_markers(resolve_handler, payloads, color)


def job_assemble_clips(resolve_handler, original_tl_name, accepted_clips, fps, progress=None):
    return clips.assemble_clips(resolve_handler, original_tl_name, accepted_clips, fps)


def job_list_models(cfg, progress=None):
    return client.list_models(cfg)


def _job_test_connection(cfg, progress=None):
    """Adapter: test_connection has no progress kwarg (worker always passes one)."""
    return client.test_connection(cfg)


# ── Worker ───────────────────────────────────────────────────────────────────

class _AIWorker(QThread):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self._fn = fn
        self._args = args

    def run(self):
        try:
            result = self._fn(*self._args, progress=lambda m: self.progress.emit(m))
            self.done.emit(result)
        except Exception as e:  # noqa: BLE001 — surfaced to the panel, never crashes the app
            self.failed.emit(f"{type(e).__name__}: {e}")


# ── Panel ────────────────────────────────────────────────────────────────────

_CARD_QSS = ("QFrame {{ background: #222; border: 1px solid #333; border-radius: 6px; }}"
             "QFrame QLabel {{ border: none; }}")


class AIPanel(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.gui = main_window
        self.os_doc = main_window.engine.os_doc
        self.resolve_handler = getattr(main_window, "resolve_handler", None)
        self._prefs = load_ai_prefs(self.os_doc)
        self._worker = None
        self._edits = []   # list of suggestion dicts
        self._clips = []   # list of clip dicts

        self.setWindowTitle("BadWords — AI Advisor")
        self.setMinimumSize(560, 520)
        self._t = lambda key: STRINGS[self._lang()].get(key, key)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.tabs.addTab(self._build_advisor_tab(), self._t("tab_advisor"))
        self.tabs.addTab(self._build_settings_tab(), self._t("tab_settings"))
        self._load_saved_clips()
        self._refresh_action_states()

    # ── helpers ──────────────────────────────────────────────────────────
    def _lang(self):
        try:
            lang = (self.os_doc.get_all_prefs() or {}).get("language", "en")
        except Exception:
            lang = "en"
        return lang if lang in STRINGS else "en"

    def _words_data(self):
        canvas = getattr(self.gui, "text_canvas", None)
        return getattr(canvas, "words_data", None) or []

    def _resolve_ok(self):
        return bool(self.resolve_handler and self.resolve_handler.timeline)

    def _refresh_action_states(self):
        has_words = bool(self._words_data())
        self.btn_edits.setEnabled(has_words and self._worker is None)
        self.btn_clips.setEnabled(has_words and self._worker is None)
        resolve_on = self._resolve_ok()
        self.btn_preview.setEnabled(resolve_on)
        self.btn_markers.setEnabled(resolve_on and self._worker is None)
        self.btn_assemble.setEnabled(resolve_on and self._worker is None)

    def _start_job(self, on_done, fn, *args):
        """Single active worker; `on_done(result)` is invoked with the job result."""
        if self._worker is not None:
            return
        self.lbl_status.setText(self._t("lbl_working"))
        self._worker = _AIWorker(fn, *args, parent=self)
        self._worker.progress.connect(lambda m: self.lbl_status.setText(m))
        self._worker.done.connect(on_done)
        self._worker.failed.connect(self._on_job_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._refresh_action_states()
        self._worker.start()

    def _on_worker_finished(self):
        self._worker = None
        self.lbl_status.setText(self._t("lbl_idle"))
        self._refresh_action_states()

    def _on_job_failed(self, message):
        self.lbl_status.setText(message)
        QMessageBox.warning(self, self._t("err_title"), message)

    # ── Advisor tab ──────────────────────────────────────────────────────
    def _build_advisor_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        self.btn_edits = QPushButton(self._t("btn_edits"))
        self.btn_clips = QPushButton(self._t("btn_clips"))
        self.btn_accept_all = QPushButton(self._t("btn_accept_all"))
        for b, cb in ((self.btn_edits, self._suggest_edits),
                      (self.btn_clips, self._find_clips),
                      (self.btn_accept_all, self._accept_all)):
            row.addWidget(b)
            b.clicked.connect(cb)
        row.addStretch()
        lay.addLayout(row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.results_host = QWidget()
        self.results_lay = QVBoxLayout(self.results_host)
        self.results_lay.addStretch()
        self.scroll.setWidget(self.results_host)
        lay.addWidget(self.scroll, 1)

        self.lbl_status = QLabel(self._t("lbl_no_results"))
        lay.addWidget(self.lbl_status)

        actions = QHBoxLayout()
        self.btn_apply = QPushButton(self._t("btn_apply").format(n=0))
        self.btn_preview = QPushButton(self._t("btn_preview"))
        self.btn_markers = QPushButton(self._t("btn_markers"))
        self.btn_assemble = QPushButton(self._t("btn_assemble"))
        self.btn_apply.clicked.connect(self._apply_edits)
        self.btn_preview.clicked.connect(self._preview_first_clip)
        self.btn_markers.clicked.connect(self._add_markers)
        self.btn_assemble.clicked.connect(self._assemble_clips)
        for b in (self.btn_apply, self.btn_preview, self.btn_markers, self.btn_assemble):
            actions.addWidget(b)
        lay.addLayout(actions)
        return w

    def _clear_results(self):
        while self.results_lay.count() > 1:  # keep trailing stretch
            item = self.results_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_card(self, build_row):
        card = QFrame()
        card.setStyleSheet(_CARD_QSS)
        lay = QVBoxLayout(card)
        build_row(lay)
        self.results_lay.insertWidget(self.results_lay.count() - 1, card)
        return card

    def _show_edits(self):
        self._clear_results()
        for s in self._edits:
            self._add_card(lambda lay, s=s: self._build_edit_card(lay, s))
        self._update_apply_label()

    def _build_edit_card(self, lay, s):
        hexc = STATUS_HEX.get(s.get("status"), "#888")
        quote = QLabel(f"<b style='color:{hexc}'>{s.get('quote', '')}</b>")
        quote.setWordWrap(True)
        lay.addWidget(quote)
        meta = (f"{s['start']:.1f}s → {s['end']:.1f}s · {s.get('category', 'other')} · "
                f"{s.get('action')}:{s.get('status')} · conf {s.get('confidence', 0):.2f}")
        if not s.get("mapped"):
            meta += f" · <i>{self._t('lbl_unmapped')}</i>"
        if s.get("reason"):
            meta += f"<br>{s['reason']}"
        info = QLabel(meta)
        info.setWordWrap(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        row.addStretch()
        s.setdefault("accepted", None)
        btn_ok = QPushButton(self._t("btn_accept"))
        btn_no = QPushButton(self._t("btn_reject"))
        for b, val in ((btn_ok, True), (btn_no, False)):
            b.setCheckable(True)
            b.setChecked(s["accepted"] is val)
            b.clicked.connect(lambda _=False, st=s, v=val, bb=b:
                              self._toggle_accept(st, v, bb))
            row.addWidget(b)
        btn_ok.setEnabled(bool(s.get("mapped")))
        lay.addLayout(row)

    def _toggle_accept(self, suggestion, value, button):
        suggestion["accepted"] = value if button.isChecked() else None
        self._update_apply_label()

    def _update_apply_label(self):
        n = sum(1 for s in self._edits if s.get("mapped") and s.get("accepted"))
        self.btn_apply.setText(self._t("btn_apply").format(n=n))
        self.btn_apply.setEnabled(n > 0 and self._worker is None)

    def _show_clips(self):
        self._clear_results()
        for c in self._clips:
            self._add_card(lambda lay, c=c: self._build_clip_card(lay, c))

    def _build_clip_card(self, lay, c):
        c.setdefault("accepted", False)
        c.setdefault("marker_added", False)
        title = QLabel(f"<b>{c['title']}</b> · {self._t('lbl_score')} "
                       f"{c.get('score', 0):.2f} · {c.get('platform')}")
        title.setWordWrap(True)
        lay.addWidget(title)
        info = QLabel(f"{c['start']:.1f}s → {c['end']:.1f}s ({c['end'] - c['start']:.0f}s)"
                      + (f"<br>{c['hook']}" if c.get("hook") else "")
                      + (f"<br><i>{c['reason']}</i>" if c.get("reason") else ""))
        info.setWordWrap(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        row.addStretch()
        btn_prev = QPushButton(self._t("btn_preview"))
        btn_prev.clicked.connect(lambda _=False, c=c: self._preview_clip(c))
        chk = QCheckBox()
        chk.setChecked(c["accepted"])
        chk.toggled.connect(lambda v, cc=c: cc.__setitem__("accepted", v))
        row.addWidget(btn_prev)
        row.addWidget(chk)
        if c.get("marker_added"):
            row.addWidget(QLabel("●"))
        lay.addLayout(row)

    # ── actions ──────────────────────────────────────────────────────────
    def _suggest_edits(self):
        if not self._words_data():
            QMessageBox.information(self, self._t("err_title"), self._t("lbl_need_transcript"))
            return
        cfg = _cfg_from(self._prefs)
        self._start_job(self._on_job_done, job_suggest_edits, cfg, self._words_data())

    def _find_clips(self):
        if not self._words_data():
            QMessageBox.information(self, self._t("err_title"), self._t("lbl_need_transcript"))
            return
        cfg = _cfg_from(self._prefs)
        self._start_job(self._on_job_done, job_find_clips, cfg, self._words_data(),
                        list(self._prefs.get("ai_platforms") or ["shorts"]))

    def _on_job_done(self, result):
        if result["kind"] == "edits":
            self._edits = result["items"]
            self._show_edits()
            self._update_apply_label()
        else:
            self._clips = result["items"]
            self._show_clips()
            self._write_ai_json()

    def _accept_all(self):
        if not self._edits:
            return
        for s in self._edits:
            if s.get("mapped"):
                s["accepted"] = True
        self._show_edits()

    def _apply_edits(self):
        try:
            n = mapping.apply_accepted_edits(self.gui, self._edits)
        except Exception as e:  # noqa: BLE001 — containment per spec
            self._log_and_warn(f"apply_accepted_edits failed: {e}")
            return
        self.lbl_status.setText(self._t("lbl_applied").format(n=n))

    def _preview_clip(self, clip):
        if not self._resolve_ok():
            QMessageBox.information(self, self._t("err_title"), self._t("lbl_need_resolve"))
            return
        try:
            self.resolve_handler.jump_to_seconds(float(clip["start"]))
        except Exception as e:  # noqa: BLE001
            self._log_and_warn(f"jump_to_seconds failed: {e}")

    def _preview_first_clip(self):
        for c in self._clips:
            if c.get("accepted"):
                self._preview_clip(c)
                return

    def _add_markers(self):
        payloads = clips.build_marker_payloads(
            self._clips, self.resolve_handler.fps,
            self.resolve_handler.get_timeline_start_frame())
        if not payloads:
            return
        color = self._prefs.get("ai_marker_color", "Purple")
        self._start_job(lambda n: self._on_markers_done(n, payloads),
                        job_add_markers, self.resolve_handler, payloads, color)

    def _on_markers_done(self, count, payloads):
        for c in self._clips:
            for frame, name, _note, _dur in payloads:
                if f"[AI] {c.get('title')}" == name:
                    c["marker_added"] = True
        self._show_clips()
        self._write_ai_json()
        self.lbl_status.setText(self._t("lbl_markers").format(n=count))

    def _assemble_clips(self):
        accepted = [c for c in self._clips if c.get("accepted")]
        if not accepted:
            return
        if not self._resolve_ok():
            QMessageBox.information(self, self._t("err_title"), self._t("lbl_need_resolve"))
            return
        self.resolve_handler.refresh_context()
        original_tl_name = self.resolve_handler.timeline.GetName()
        fps = self.resolve_handler.fps
        self._start_job(
            lambda name: self.lbl_status.setText(self._t("lbl_assembled").format(name=name)),
            job_assemble_clips, self.resolve_handler, original_tl_name, accepted, fps)

    def _write_ai_json(self):
        try:
            clips.write_ai_json(ai_json_path(self.gui), self._clips,
                                {"base_url": self._prefs["ai_base_url"],
                                 "model": self._prefs["ai_model"]})
        except Exception as e:  # noqa: BLE001 — persistence is best-effort
            self._log_and_warn(f"write_ai_json failed: {e}")

    def _load_saved_clips(self):
        data = clips.read_ai_json(ai_json_path(self.gui))
        if data:
            self._clips = data
            self._show_clips()
            self.lbl_status.setText(self._t("lbl_load_saved").format(n=len(data)))

    def _log_and_warn(self, message):
        try:
            from osdoc import log_error
            log_error(f"[ai_advisor] {message}")
        except Exception:
            pass
        QMessageBox.warning(self, self._t("err_title"), message)

    # ── Settings tab ─────────────────────────────────────────────────────
    def _build_settings_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        prow = QHBoxLayout()
        prow.addWidget(QLabel(self._t("lbl_preset")))
        self.cb_preset = QComboBox()
        self.cb_preset.addItems(["lmstudio", "ollama", "custom"])
        prow.addWidget(self.cb_preset, 1)
        lay.addLayout(prow)

        self.ed_base_url = QLineEdit(self._prefs["ai_base_url"])
        lay.addWidget(QLabel(self._t("lbl_base_url")))
        lay.addWidget(self.ed_base_url)

        self.ed_api_key = QLineEdit(self._prefs["ai_api_key"])
        self.ed_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addWidget(QLabel(self._t("lbl_api_key")))
        lay.addWidget(self.ed_api_key)

        mrow = QHBoxLayout()
        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.setCurrentText(self._prefs["ai_model"])
        mrow.addWidget(self.cb_model, 1)
        self.btn_refresh_models = QPushButton(self._t("btn_refresh_models"))
        self.btn_refresh_models.clicked.connect(self._refresh_models)
        mrow.addWidget(self.btn_refresh_models)
        lay.addWidget(QLabel(self._t("lbl_model")))
        lay.addLayout(mrow)

        grow = QHBoxLayout()
        self.sp_temperature = QDoubleSpinBox()
        self.sp_temperature.setRange(0.0, 2.0)
        self.sp_temperature.setSingleStep(0.1)
        self.sp_temperature.setValue(float(self._prefs["ai_temperature"]))
        self.sp_max_chars = QSpinBox()
        self.sp_max_chars.setRange(2000, 200000)
        self.sp_max_chars.setValue(int(self._prefs["ai_max_chars"]))
        self.sp_timeout = QSpinBox()
        self.sp_timeout.setRange(10, 900)
        self.sp_timeout.setValue(int(self._prefs["ai_timeout_s"]))
        for label, widget in ((self._t("lbl_temperature"), self.sp_temperature),
                              (self._t("lbl_max_chars"), self.sp_max_chars),
                              (self._t("lbl_timeout"), self.sp_timeout)):
            box = QVBoxLayout()
            box.addWidget(QLabel(label))
            box.addWidget(widget)
            grow.addLayout(box)
        lay.addLayout(grow)

        crow = QHBoxLayout()
        crow.addWidget(QLabel(self._t("lbl_marker_color")))
        self.cb_marker_color = QComboBox()
        try:
            import config
            self.cb_marker_color.addItems(list(config.RESOLVE_COLORS_HEX.keys()))
        except Exception:
            self.cb_marker_color.addItems(["Purple"])
        self.cb_marker_color.setCurrentText(self._prefs["ai_marker_color"])
        crow.addWidget(self.cb_marker_color, 1)
        lay.addLayout(crow)

        self.cb_platforms = QCheckBox("shorts")
        lay.addWidget(QLabel(self._t("lbl_platforms")))
        self._platform_checks = []
        prow2 = QHBoxLayout()
        for name in ("shorts", "tiktok", "reels"):
            chk = QCheckBox(name)
            chk.setChecked(name in (self._prefs.get("ai_platforms") or ["shorts"]))
            self._platform_checks.append(chk)
            prow2.addWidget(chk)
        prow2.addStretch()
        lay.addLayout(prow2)

        self.lbl_cloud_warning = QLabel(self._t("lbl_cloud_warning"))
        self.lbl_cloud_warning.setWordWrap(True)
        self.lbl_cloud_warning.setStyleSheet("color: #e2a91c;")
        lay.addWidget(self.lbl_cloud_warning)

        trow = QHBoxLayout()
        self.btn_test = QPushButton(self._t("btn_test"))
        self.btn_test.clicked.connect(self._test_connection)
        trow.addWidget(self.btn_test)
        trow.addStretch()
        lay.addLayout(trow)
        lay.addStretch()

        for widget, prop in ((self.cb_preset, "currentTextChanged"),
                             (self.ed_base_url, "textChanged"),
                             (self.ed_api_key, "textChanged"),
                             (self.cb_model, "currentTextChanged"),
                             (self.sp_temperature, "valueChanged"),
                             (self.sp_max_chars, "valueChanged"),
                             (self.sp_timeout, "valueChanged"),
                             (self.cb_marker_color, "currentTextChanged")):
            widget.__setattr__("_tag", True)
            getattr(widget, prop).connect(self._save_settings)
        for chk in self._platform_checks:
            chk.toggled.connect(self._save_settings)
        self.cb_preset.currentTextChanged.connect(self._apply_preset)
        self._update_cloud_warning()
        return w

    def _collect_settings(self):
        platforms = [c.text() for c in self._platform_checks if c.isChecked()] or ["shorts"]
        return {
            "ai_provider_preset": self.cb_preset.currentText(),
            "ai_base_url": self.ed_base_url.text().strip(),
            "ai_api_key": self.ed_api_key.text(),
            "ai_model": self.cb_model.currentText().strip(),
            "ai_temperature": self.sp_temperature.value(),
            "ai_max_chars": self.sp_max_chars.value(),
            "ai_timeout_s": self.sp_timeout.value(),
            "ai_marker_color": self.cb_marker_color.currentText(),
            "ai_platforms": platforms,
        }

    def _save_settings(self, *_):
        self._prefs.update(self._collect_settings())
        save_ai_prefs(self.os_doc, self._prefs)
        self._update_cloud_warning()

    def _apply_preset(self, preset):
        base = client.DEFAULT_BASE_URLS.get(preset)
        if base:
            self.ed_base_url.setText(base)

    def _update_cloud_warning(self):
        url = self.ed_base_url.text().lower()
        local = any(h in url for h in ("localhost", "127.0.0.1", "[::1]"))
        self.lbl_cloud_warning.setVisible(not local)

    def _refresh_models(self):
        cfg = _cfg_from(self._collect_settings())
        self._start_job(self._on_models_done, job_list_models, cfg)

    def _on_models_done(self, models):
        current = self.cb_model.currentText()
        self.cb_model.clear()
        self.cb_model.addItems(models)
        if current:
            self.cb_model.setCurrentText(current)

    def _test_connection(self):
        self._save_settings()
        cfg = _cfg_from(self._prefs)
        self._start_job(lambda desc: self.lbl_status.setText(str(desc)),
                        _job_test_connection, cfg)

    # ── lifecycle ────────────────────────────────────────────────────────
    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker.wait(5000)
        event.accept()
```

- [ ] **Step 4: Verify compile + helper tests pass**

Run:
```bash
python3 -m py_compile src/ai_advisor/panel.py && python3 -m pytest tests/ai_advisor/test_panel_helpers.py -v
```
Expected: compile OK, tests PASS (5). (The widget code itself is exercised in Task 8's manual e2e.)

- [ ] **Step 5: Commit**

```bash
git add src/ai_advisor/panel.py tests/ai_advisor/test_panel_helpers.py
git commit -m "feat(ai-advisor): AI panel with settings, accept/reject cards and QThread jobs"
```

---

### Task 7: gui.py hook — titlebar button + guarded opener

**Files:**
- Modify: `src/gui.py` (titlebar build ~line 3902-3920; new method after `_show_edit_menu` ~line 4081)

**Interfaces (consumes):** `ai_advisor.open_panel(main_window)` (Task 1), `osdoc.log_error`, `QMessageBox` (already imported in gui.py).

- [ ] **Step 1: Add the titlebar button**

In `src/gui.py`, find this block (around line 3915-3919):

```python
        self.btn_menu_edit = QPushButton(_t("titlebar_edit"))
        self.btn_menu_edit.setStyleSheet(_btn_qss)
        self.btn_menu_edit.setCursor(Qt.PointingHandCursor)
        self.btn_menu_edit.clicked.connect(self._show_edit_menu)
        menu_lay.addWidget(self.btn_menu_edit)
```

Insert immediately AFTER `menu_lay.addWidget(self.btn_menu_edit)`:

```python
        # AI Advisor addon (lazy import inside _show_ai_panel — startup untouched)
        self.btn_menu_ai = QPushButton("AI")
        self.btn_menu_ai.setStyleSheet(_btn_qss)
        self.btn_menu_ai.setCursor(Qt.PointingHandCursor)
        self.btn_menu_ai.clicked.connect(self._show_ai_panel)
        menu_lay.addWidget(self.btn_menu_ai)
```

(Visibility comes for free: `_menu_container` — which holds `menu_lay` — is shown/hidden by `activate_transcription_mode()` / `deactivate_transcription_mode()` at gui.py:4083-4097.)

- [ ] **Step 2: Add the guarded opener**

Immediately after the end of `_show_edit_menu` (the line `popup.show()` at ~line 4080, before `def activate_transcription_mode`), insert:

```python
    def _show_ai_panel(self):
        """Open the AI Advisor addon panel. Any failure stays contained here."""
        try:
            from ai_advisor import open_panel
            open_panel(self)
        except Exception as e:
            try:
                from osdoc import log_error
                log_error(f"[ai_advisor] panel failed to open: {e}")
            except Exception:
                pass
            QMessageBox.warning(self, "BadWords",
                                "AI Advisor failed to open. See the BadWords log.")
```

- [ ] **Step 3: Verify**

Run:
```bash
python3 -m py_compile src/gui.py && python3 -m pytest tests/ai_advisor -v
```
Expected: compile OK; full addon suite PASS.

Then an import-level smoke check (no display needed):
```bash
python3 - <<'EOF'
import sys, ast
src = open("src/gui.py").read()
tree = ast.parse(src)
names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
assert "_show_ai_panel" in names, "hook method missing"
text = src[src.index("_show_ai_panel"):]
assert "from ai_advisor import open_panel" in text and "QMessageBox.warning" in text
print("gui.py hook OK")
EOF
```
Expected: `gui.py hook OK`.

- [ ] **Step 4: Commit**

```bash
git add src/gui.py
git commit -m "feat(ai-advisor): titlebar AI button opening the addon panel (guarded)"
```

---

### Task 8: Full verification + manual e2e checklist

**Files:** none created; verification only.

- [ ] **Step 1: Run the whole addon suite**

Run: `python3 -m pytest tests/ai_advisor -v`
Expected: all tests PASS (client 8, prompts 9, mapping 7, clips 10, apply 5, panel helpers 6 ≈ 45).

- [ ] **Step 2: Compile every touched source**

Run: `python3 -m py_compile src/ai_advisor/*.py src/gui.py`
Expected: silent success (exit 0).

- [ ] **Step 3: Confirm the untouched-files constraint**

Run: `git diff --name-only 906783f..HEAD -- src/ | sort`
Expected output contains ONLY: `src/ai_advisor/*` (new) and `src/gui.py`. If anything else appears — STOP and fix.

- [ ] **Step 4: Manual e2e (requires Resolve + LM Studio or mock server)**

Mock-server option (no LM Studio needed):
```bash
python3 - <<'EOF' &
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

EDIT = {"suggestions": [{"start": "00:00.0", "end": "00:01.2",
        "quote": "hey guys welcome back", "action": "cut", "status": "bad",
        "reason": "e2e demo", "category": "filler"}]}
CLIPS = {"clips": [{"start": "00:00.0", "end": "00:05.0", "title": "Hook line",
         "hook": "hey guys", "reason": "e2e", "score": 0.9, "platform": "shorts"}]}

class H(BaseHTTPRequestHandler):
    def _send(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        sysmsg = data["messages"][0]["content"]
        self._send({"choices": [{"message": {"content": json.dumps(
            EDIT if "rough-cut" in sysmsg else CLIPS)}}]})
    def do_GET(self):
        self._send({"data": [{"id": "mock-model"}]})
    def log_message(self, *a): pass

HTTPServer(("127.0.0.1", 8765), H).serve_forever()
EOF
```
Checklist (run BadWords inside Resolve, transcribe any short clip):
1. Titlebar shows the "AI" button next to Project/Transcript/Edit after transcription — ✓
2. Settings tab: preset `custom`, base URL `http://127.0.0.1:8765/v1` → "Test Connection" shows a model — ✓
3. "Suggest Edits" → card appears with red quote, unmapped/off-range entries disabled — ✓
4. Accept one card → "Apply 1 accepted" → word painted red in transcript → Ctrl+Z reverts → redo works — ✓
5. Assemble still behaves exactly as before (no changes needed — informational) — ✓
6. "Find Social Clips" → card with score → "Preview" moves Resolve playhead — ✓
7. "Add Markers" → `[AI] Hook line` marker (Purple) appears on the Resolve timeline — ✓
8. "Assemble Clips Timeline" → new timeline contains only the clip range — ✓
9. Save session (.bws) → reopen → accepted statuses persist; `.ai.json` next to saves reloads clip list on panel open — ✓
10. Stop the mock server mid-analysis → panel shows inline error, app alive — ✓

- [ ] **Step 5: Report**

Summarize: tests count, compile results, constraint check output, manual checklist results, and any deviations from this plan.
