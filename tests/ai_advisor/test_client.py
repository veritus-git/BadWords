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
    install(lambda req: FakeHTTPResponse(json.dumps({"data": [{"id": "m1"}, {"id": "m2"}]}).encode()))
    assert client.list_models(ai_cfg) == ["m1", "m2"]
    assert calls[0]["url"].endswith("/models")


def test_test_connection_returns_description(fake_urlopen, ai_cfg):
    install, _ = fake_urlopen
    install(lambda req: FakeHTTPResponse(json.dumps({"data": [{"id": "m1"}]}).encode()))
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
