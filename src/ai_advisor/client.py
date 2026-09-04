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
