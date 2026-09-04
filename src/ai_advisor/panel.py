"""AI Advisor panel helpers: STRINGS, prefs IO, job functions. Qt-free (testable)."""

import os

from ai_advisor import client, clips, mapping, prompts

# ── UI strings (en/it; no config.get_trans changes) ─────────────────────────

STRINGS = {
    "en": {
        "tab_advisor": "Advisor", "tab_settings": "Settings",
        "btn_edits": "Suggest Edits", "btn_clips": "Find Social Clips",
        "btn_apply": "Apply {n} accepted", "btn_markers": "Add Markers",
        "btn_assemble": "Assemble Clips Timeline", "btn_preview": "Preview",
        "btn_accept": "✓", "btn_reject": "✗", "btn_accept_all": "Accept all",
        "lbl_preset": "Preset", "lbl_base_url": "Base URL", "lbl_api_key": "API key",
        "lbl_model": "Model", "lbl_temperature": "Temperature",
        "lbl_max_chars": "Max chars per request",
        "lbl_timeout": "Timeout (s)", "lbl_marker_color": "AI marker color",
        "lbl_platforms": "Platforms", "btn_test": "Test Connection",
        "btn_refresh_models": "⟳",
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
        "lbl_model": "Modello", "lbl_temperature": "Temperatura",
        "lbl_max_chars": "Caratteri max per richiesta",
        "lbl_timeout": "Timeout (s)", "lbl_marker_color": "Colore marker AI",
        "lbl_platforms": "Piattaforme", "btn_test": "Testa connessione",
        "btn_refresh_models": "⟳",
        "lbl_cloud_warning": "⚠ Endpoint cloud: il trascritto lascerà questa macchina.",
        "lbl_idle": "Pronto.", "lbl_working": "Elaborazione…", "lbl_need_transcript":
        "Esegui prima una trascrizione (nessun trascritto in questa sessione).",
        "lbl_need_resolve": "DaVinci Resolve non è connesso.",
        "lbl_applied": "Applicate {n} modifiche alle parole.",
        "lbl_markers": "Aggiunti {n} marker.",
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
    safe = "".join(ch for ch in str(title) if ch.isalnum() or ch in "_- ").replace(" ", "_")
    safe = safe or "session"
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
