# Design — AI Advisor Addon per BadWords

**Data:** 2026-09-04
**Stato:** Design approvato in chat; in attesa di review della spec
**Approccio scelto:** A — addon isolato in `src/ai_advisor/` con agganci minimi a `gui.py`

---

## 1. Contesto e obiettivi

BadWords trascrive audio con faster-whisper, offre editing testuale tipo IDE dove le parole
vengono colorate (status) e assembla una nuova timeline in DaVinci Resolve via `.drt`.
Questo addon aggiunge un **consulente LLM configurabile** che:

1. **Suggerimenti edit** — analizza la trascrizione e propone tagli/ricolorazioni in un
   pannello con **accetta/rifiuta** per ogni proposta; le proposte accettate entrano negli
   status delle parole e riutilizzano senza modifiche heatmap, Assemble e `.bws`.
2. **Clip social** — individua i segmenti con potenziale per social (Shorts/TikTok/Reels)
   con titolo/hook/score, preview jump-to-time, **marker colorati sulla timeline Resolve**
   e generazione di una **timeline dedicata** con i soli clip scelti.

### Obiettivi
- **Invasività minima:** unico file esistente modificato = `gui.py` (~15-25 righe);
  tutto il resto è codice nuovo (`src/ai_advisor/`, `tests/ai_advisor/`).
- **Zero nuove dipendenze:** HTTP via `urllib.request` (già pattern del progetto);
  fuzzy matching riusato da `algorithms.py`.
- **Provider configurabile:** protocollo OpenAI-compatible — LM Studio, Ollama e cloud
  (base URL + API key + modello + temperatura).
- Pipeline esistente (heatmap, Assemble, `.bws`) **intatta**.

### Non-obiettivi (v1)
- Zoom/punch-in automatico sui clip (richiede keyframe transform via `.drt` — complesso e
  fragile; vedi §10 Futuro).
- Streaming delle risposte LLM.
- Provider con SDK non OpenAI-compatible.
- i18n via `config.get_trans` (le stringhe UI dell'addon vivono in un dict locale en/it, §4.4).
- Qualsiasi modifica a `SettingsDialog`, `engine.py`, `algorithms.py`, `api.py`,
  `assembler.py`, `osdoc.py`, `config.py`, `main.py`, `setupfiles/`.

---

## 2. Architettura

```
src/ai_advisor/
├── __init__.py        # open_panel(gui) — factory + guardie
├── client.py          # client LLM OpenAI-compatible (urllib), tipi errore
├── prompts.py         # prompt di sistema + schema JSON + compact_transcript + chunking
├── mapping.py         # risposta LLM → word id reali (fuzzy match), dedup, validazione
├── panel.py           # AIPanel(QDialog): tab Advisor + tab Settings, worker QThread
└── clips.py           # payload marker, keep-only ops, persistenza .ai.json

tests/ai_advisor/      # pytest, zero rete (urlopen mockato)
```

### 2.1 Punti di aggancio esistenti (uso read-only)

| Simbolo | Dove | Uso |
|---|---|---|
| `BadWordsGUI.words_data` | gui.py:2832 | sorgente di verità: parole + status |
| `BadWordsGUI.engine` / `.resolve_handler` | gui.py:10659-10660 | accesso a prefs, Resolve API |
| `BadWordsGUI._calculate_visual_layer` | gui.py:12683 | Layer Engine: scrive `status`/`selected` finali |
| `algorithms.propagate_status_change` | algorithms.py:1771 | applicazione status coerente (segmenti) |
| `algorithms.check_fuzzy_match` / `calculate_similarity` | algorithms.py:226-266 | mapping quote → word id |
| `ResolveHandler.timeline/project/resolve`, `get_timeline_start_frame`, `jump_to_seconds` | api.py:41-123 | marker, preview |
| `ResolveHandler.generate_timeline_from_ops`, `get_optimal_source_item` | api.py:2186, 1486 | assemble clips timeline |
| `config.RESOLVE_COLORS_HEX` | config.py:334 | colori marker ammessi |
| `OSDoctor.set_pref` / `get_all_prefs` | osdoc.py:361, 259 | configurazione AI |
| Titlebar menu buttons (`menu_lay`, btn_menu_project/transcript/edit) | gui.py:3902-3920 | aggancio bottone AI |

### 2.2 Modifiche ai file esistenti (UNICA — gui.py)

1. **Bottone titlebar** (dopo `btn_menu_edit`, ~gui.py:3915): `self.btn_menu_ai` con
   label `"AI"`, stesso `_btn_qss`, `clicked → self._show_ai_panel`. Visibile come gli
   altri solo in `activate_transcription_mode()`.
2. **Callback**:
   ```python
   def _show_ai_panel(self):
       try:
           from ai_advisor import panel as _ai_panel   # lazy: startup intatto
           _ai_panel.open_panel(self)
       except Exception as e:
           osdoc.log_error(f"AI panel failed: {e}")
           QMessageBox.warning(self, "BadWords", "AI Advisor failed to open. See log.")
   ```

Nessun altro file esistente viene toccato. Le stringhe UI dell'addon stanno in
`panel.py` (dict `STRINGS = {"en": {...}, "it": {...}}`, selezione via pref `language`).

---

## 3. Modello dati

### 3.1 Word object (esistente — l'addon non ne cambia la struttura)

```python
{"text": str, "start": float, "end": float, "selected": bool,
 "status": None|"bad"|"repeat"|"typo", "is_filler": bool,
 "seg_start": float, "seg_end": float, "is_segment_start": bool,
 "type": "word", "id": int,
 "manual_status": ...|None, "algo_status": ...|None,
 "overlay_suppressed": bool, "is_auto": bool, ...}
```

Vocabolario status: `bad` (rosso — filler/errori), `repeat` (blu — retake/duplicati),
`typo` (verde), `None`/normal. `calculate_timeline_structure` (engine.py:2098) converte
gli status in `ops`; `auto_cut_colors` decide cosa viene tagliato all'Assemble.
Il `.bws` persiste gli status → i suggerimenti edit accettati persistono **senza
modifiche al formato di salvataggio**.

### 3.2 Suggerimento edit (interno addon)

```python
{"id": str,                     # uuid4 corto
 "action": "cut"|"recolor",     # recolor = solo colore (tipico: typo), nessun taglio
 "status": "bad"|"repeat"|"typo",
 "word_ids": [int], "start": float, "end": float,
 "quote": str,                  # testo citato dal LLM (per fuzzy match e UI)
 "reason": str, "category": "filler"|"retake"|"mistake"|"other",
 "confidence": float,           # 0..1 dal mapping locale (non dal LLM)
 "mapped": bool,                # False = non agganciato a word id → card disabilitata
 "accepted": bool|None}
```

### 3.3 Clip social (interno addon)

```python
{"id": str, "start": float, "end": float,
 "title": str, "hook": str, "reason": str,
 "score": float,                # 0..1
 "platform": str,               # "shorts"|"tiktok"|"reels"
 "accepted": bool, "marker_added": bool}
```

### 3.4 Persistenza clip

File **`<percorso del .bws senza estensione>.ai.json`** (es. `podcast01.bws` →
`podcast01.ai.json`, stessa cartella; non si tocca `save_bws`):

```json
{"version": 1, "generated_at": "ISO-8601",
 "provider": {"base_url": "...", "model": "..."},
 "clips": [ ...3.3... ]}
```

Scritto ad ogni apply/accept dei clip; ricaricato all'apertura del pannello se presente
per lo stesso progetto. Gli edit non si salvano qui: vivono negli status nel `.bws`.

---

## 4. Componenti

### 4.1 `client.py` — client LLM

```python
@dataclass
class AiConfig:
    base_url: str = "http://localhost:1234/v1"   # LM Studio; Ollama: http://localhost:11434/v1
    api_key: str = ""
    model: str = ""
    temperature: float = 0.2
    timeout_s: int = 120
    max_chars: int = 24000                       # budget per richiesta (chunking)

class AiClientError(Exception): ...
class AiAuthError(AiClientError): ...             # 401/403
class AiBadResponse(AiClientError): ...           # JSON/illeggibile

def chat_json(messages, cfg) -> dict              # POST {base_url}/chat/completions
def list_models(cfg) -> list[str]                 # GET {base_url}/models
def test_connection(cfg) -> str                   # models + chat "ping" → descrizione
```

- Solo `urllib.request` + `json`. Header `Authorization: Bearer` solo se `api_key`.
- Richiesta con `response_format: {"type": "json_object"}`; se il server rifiuta
  (errore "response_format"), **ritenta una volta senza** il campo.
- Risposte passano sempre da `prompts.validate_*` (schema minimo; campi mancanti →
  `AiBadResponse` tipizzato).

### 4.2 `prompts.py` — prompt e compattezza trascritto

- `EDIT_SYSTEM_PROMPT`: ruolo "rough-cut assistant"; regole: usare SOLO i timestamp
  forniti, citare testo esatto, rispondere SOLO JSON conforme allo schema; spiegazione
  dei tre status BadWords (bad/repeat/typo) con significato editoriale; suggerire
  `cut` per filler/retake/errori, `recolor:typo` per refusi senza taglio.
- `CLIPS_SYSTEM_PROMPT`: criteri hook/retention, durata target per piattaforma
  (parametri iniettati dai pref `ai_platforms`), `score` 0-1 con motivazione.
- `compact_transcript(words_data) -> (text, index_map)`:
  raggruppa le parole per `seg_start` in frasi; una riga per frase `"[mm:ss.d] testo"`;
  `index_map[line_no] = [word ids]`; le parole con status già impostato vengono incluse
  con tag `[CUT]`/`[KEEP]` iniziali così il LLM vede le decisioni esistenti.
- **Chunking**: se `len(text) > cfg.max_chars` → split su confini frase con overlap di
  2 frasi; ogni chunk inviato con header `chunk i/n`; i risultati vengono uniti e
  deduplicati in `mapping.py`.
- `parse_llm_json(raw) -> dict`: tollera code fence ```json, estrae il primo oggetto valido.
- `validate_edits(obj, n_expected=None)` / `validate_clips(obj)`: schema minimo, tipi,
  range 0 ≤ start < end.

### 4.3 `mapping.py` — dal LLM alle parole reali

- `map_edit_suggestions(raw_list, words_data, index_map) -> list[dict]`:
  per ogni suggerimento: candidati da `index_map` via timestamp (finestra ±0.5 s),
  conferma con `check_fuzzy_match`/`calculate_similarity` su `quote` vs testo delle
  parole; `confidence < 0.5` → `mapped: False` (mostrata disabilitata con badge);
  risolve `word_ids` contigui; clamp su limiti audio.
- `map_clips(raw_list, words_data) -> list[dict]`: clamp times; (opzionale v1.1)
  snap dei bordi su blocchi `meta_global_silence` adiacenti.
- `dedup(suggestions)`: overlap di range > 80% con stesso status → merge (tieni
  confidence maggiore).
- `merge_chunk_results(results)`: concat + dedup + ordina per start.

### 4.4 `panel.py` — `AIPanel(QDialog)`

Stile coerente con `SettingsDialog` (`FramelessWindowMixin` + `_BaseDialog`).

**Tab "Advisor"**
- Header: provider/modello attivi + dot di stato connessione (verde/rosso).
- Azioni: `[Suggest Edits]` `[Find Social Clips]` (disabilitati senza `words_data`).
- Lista risultati — card:
  - edit: citazione colorata col colore dello status proposto, timecode in/out, reason,
    bottoni ✓/✗; badge `unmapped` se `mapped=False`;
  - clip: score, timecode, titolo, hook, `[Preview]`, checkbox "include in timeline".
- Footer contestuale:
  - edits: `[Apply N accepted]`;
  - clips: `[Add Markers]` `[Assemble Clips Timeline]` (disabilitati se Resolve non connesso).

**Tab "Settings"**
- Preset combo: `LM Studio` / `Ollama` / `Custom / Cloud` (compila base_url default).
- Campi: base_url, api_key (password echo), model (combo editabile popolata da
  `list_models`), temperature, max_chars.
- Marker color combo (chiavi `RESOLVE_COLORS_HEX`, default `Purple`) — l'utente può
  cambiarlo per evitare collisioni con la propria heatmap.
- Cloud preset → label di avviso privacy (il trascritto lascia la macchina).
- `[Test Connection]`; salvataggio immediato via `os_doc.set_pref("ai_*", ...)`.

**Worker**: un solo `_AIWorker(QThread)` attivo; segnali `finished(result)`,
`failed(str)`, `progress(str)` (pattern QThread+Signal esistente, es. gui.py:2566).
Chiusura pannello → `requestInterruption()` + `wait(5000)`; il timeout HTTP è la
guardia principale contro blocchi indefiniti.

**Apply edits** (per ogni accettato, stesso percorso dei pulsanti colore,
riferimento gui.py:3584-3627):
1. snapshot undo (vedi sotto);
2. `updates = algorithms.propagate_status_change(words_data, wid, status)` per ogni word id
   — nel percorso di pittura è `propagate_status_change` a impostare `manual_status`;
   in implementazione si verifica e si garantisce che `manual_status` risulti impostato
   sul valore accettato prima del Layer Engine;
3. per ogni update: `word_obj['overlay_suppressed'] = True`, poi
   `main_window._calculate_visual_layer(word_obj)` (il Layer Engine scrive
   `status`/`selected` finali — accettato = pittura manuale, semanticamente corretto);
4. repaint: `text_canvas._calculate_layout()` + `update()`.
- **Undo**: applicazione batch = singola azione undo; le vecchie stesse chiavi osservate
  in gui.py:3594-3604 (`status`, `manual_status`, `algo_status`, `is_auto`, `selected`).
  L'esatta API undo esistente (`_current_undo_action` / undo stack) viene individuata in
  implementazione e riusata; se l'API undo non è riusabile da fuori senza refactoring,
  l'addon registrerà l'azione tramite lo stesso meccanismo usato dai paint drag.

**Preview clip**: `resolve_handler.jump_to_seconds(clip.start)`.

**Add markers**: per clip accettato:
`frame = get_timeline_start_frame() + int(clip.start * fps)`;
`timeline.AddMarker(frame, ai_marker_color, f"[AI] {title}", note=f"{hook}\n{reason}", duration=int((end-start)*fps))`;
idempotente per prefisso nome `[AI]` + stessa posizione; `marker_added=True`.

**Assemble clips timeline** (riuso della pipeline ops):
- costruisce keep-only ops dai clip accettati (§4.5 `build_keep_only_ops`) nello stesso
  formato prodotto da `calculate_timeline_structure`;
- chiama `get_optimal_source_item(...)` + `generate_timeline_from_ops(ops, source_item,
  "BadWords - Social Clips")`;
- **nota implementativa**: la firma/struttura esatta delle ops attese da
  `generate_timeline_from_ops` (api.py:1685-2070) va confermata leggendo il corpo durante
  la scrittura del piano; fallback dichiarato: se le ops non sono componibili pulitamente,
  v1.0 spedisce markers-only e l'assemble clips passa in v1.1 (la UI già prevede entrambi
  i bottoni separati).

### 4.5 `clips.py` — funzioni pure + side-effect isolati

```python
def build_marker_payloads(clips, fps, tl_start_frame) -> list[tuple]
def build_keep_only_ops(clips, words_data, fps) -> list[dict]
def write_ai_json(path, data) -> None
def read_ai_json(path) -> dict | None
def add_markers(resolve_handler, payloads) -> int   # unico punto con side-effect Resolve
```

---

## 5. Configurazione (prefs via `os_doc.set_pref`)

| Chiave | Default | Note |
|---|---|---|
| `ai_provider_preset` | `lmstudio` | `lmstudio` \| `ollama` \| `custom` |
| `ai_base_url` | `http://localhost:1234/v1` | preset ollama → `http://localhost:11434/v1` |
| `ai_api_key` | `""` | solo preset custom/cloud |
| `ai_model` | `""` | popolato da `list_models` |
| `ai_temperature` | `0.2` | |
| `ai_max_chars` | `24000` | budget chunking per richiesta |
| `ai_marker_color` | `Purple` | chiave di `RESOLVE_COLORS_HEX` |
| `ai_platforms` | `["shorts","tiktok","reels"]` | target clip social |

- API key salvata in chiaro nei prefs: stesso comportamento delle altre prefs
  dell'app; documentato; **mai** inviata in telemetria.
- Le chiamate AI sono standalone: nessun contenuto del transcript tocca la telemetria
  esistente (`send_telemetry_ping` non viene invocato dall'addon).

---

## 6. Error handling

| Caso | Comportamento |
|---|---|
| Connessione rifiutata / timeout | errore inline nel tab + possibilità retry; `timeout_s` da config |
| HTTP 401/403 | `AiAuthError` + hint sulla chiave (preset cloud) |
| JSON malformato dal LLM | 1 retry con istruzione "ONLY valid JSON"; fallback `parse_llm_json`; poi errore tipizzato |
| Match bassa confidenza | card disabilitata con badge `unmapped` (mai applicazione cieca) |
| `words_data` assente/vuota | bottoni analisi disabilitati + hint "run transcription first" |
| Resolve non connesso | Preview/Add Markers/Assemble disabilitati + hint |
| Transcript sopra budget | chunking automatico con overlap + progress "chunk i/n" |
| Eccezione nel pannello | `osdoc.log_error` + chiusura pannello; **mai** crash dell'app |
| Worker attivo + chiusura pannello/app | `requestInterruption` + `wait(5000)`; timeout HTTP come guardia |

---

## 7. Testing

`tests/ai_advisor/` (pytest; progetto attualmente senza test — directory nuova;
nessuna rete: `urllib.request.urlopen` monkeypatchato).

- `test_compact_transcript.py`: frasi/raggruppamento, formato `[mm:ss.d]`, `index_map`,
  tag `[CUT]/[KEEP]`, boundary del chunking (overlap 2 frasi, nessuna perdita parole).
- `test_map_edit_suggestions.py`: match esatto per timestamp, fuzzy su quote,
  `unmapped` sotto soglia, dedup overlap, merge chunk.
- `test_client.py`: 200 ok, JSON in code fence, 401 → `AiAuthError`, body illeggibile →
  `AiBadResponse`, fallback senza `response_format`.
- `test_prompts.py`: `validate_edits`/`validate_clips` ok/ko, `parse_llm_json` con fence/rumore.
- `test_clips.py`: math payload marker (fps, tl_start_frame, duration),
  `build_keep_only_ops` shape, roundtrip `.ai.json`.
- **Checklist e2e manuale** (post-implementazione): LM Studio reale o mock server →
  pannello apre → suggest edits → accetta 2, rifiuta 1 → apply → colori visibili nel
  transcript, undo funziona, Assemble genera timeline attesa; find clips → preview salta
  nel tempo → marker `[AI]` sulla timeline → assemble clips crea la timeline dedicata;
  `.bws` ricaricato mantiene gli status; `.ai.json` ricaricato mostra i clip.

---

## 8. Riepilogo file

| Azione | Percorsi |
|---|---|
| **Creati** | `src/ai_advisor/{__init__,client,prompts,mapping,panel,clips}.py`, `tests/ai_advisor/**` |
| **Modificati** | `src/gui.py` (bottone titlebar + `_show_ai_panel` + lazy import, ~15-25 righe) |
| **Intatti** | `main.py`, `engine.py`, `algorithms.py`, `api.py`, `assembler.py`, `osdoc.py`, `config.py`, `setupfiles/**`, `docs/**` |

---

## 9. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| LLM locali piccoli producono JSON scadente | temperature bassa, schema validato, retry, chunking compatto; `unmapped` gestisce il residuo |
| Formato ops di `generate_timeline_from_ops` non banale | conferma con lettura mirata in fase di piano; fallback markers-only in v1.0 (§4.4) |
| Refresh UI dopo status change | riuso del percorso esistente dei pulsanti colore (propagate → Layer Engine → repaint), §4.4 |
| Worker bloccato su HTTP lento | timeout configurabile + interruption on close |
| Collisione colore marker con heatmap utente | colore configurabile in Settings, default `Purple` |
| Conflitti con update upstream | superficie di modifica = 1 punto di gui.py; addon in package separato |

---

## 10. Futuro (non v1)

- Zoom/punch-in automatico sui clip (keyframe transform via `.drt`).
- i18n completa via `config.get_trans` (10 lingue esistenti).
- Streaming risposte; provider SDK nativi; analisi frame per crop verticale intelligente.
- Regole personali persistenti (stile di montaggio dell'utente) iniettate nel prompt.
