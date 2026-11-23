---
name: davinci-resolve-current
description: >-
  Up-to-date DaVinci Resolve (21.1+, 21.2+, 22+) Scripting API and Free vs Studio
  reference and verification checklist. Load whenever analyzing, debugging, or
  modifying DaVinci Resolve integration, wrappers, Lua bridge, DRT/XML assembly,
  or Resolve-related settings and installer scripts.
---

# DaVinci Resolve Current State & API Verification

## Mandatory Freshness Check (Do This First)
Never rely purely on memory for DaVinci Resolve capabilities, API methods, or edition restrictions:
1. **Check Local SDK Docs (when Resolve is installed on the machine)**:
   - Linux: `/opt/resolve/Developer/Scripting/README.txt` and `/opt/resolve/docs/ReadMe.html`
   - Windows: `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\README.txt`
   - macOS: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/README.txt`
2. **Check Latest Official Updates Online (`search_web`)**:
   - Search Blackmagic Design release notes and Scripting API changes for versions `21.1`, `21.2`, `22+` whenever evaluating new limitations, page names, render/import methods, or Free vs Studio boundaries.

---

## Verified DaVinci Resolve 21.1+ / 22+ Facts (As of 2026-11)

### 1. Free vs Studio Scripting Boundary (Changed in v21.1)
- **DaVinci Resolve Free 21.1+**:
  - **Python scripting REMOVED**: Both internal (`Workspace -> Scripts -> *.py`) and external Python API (`DaVinciResolveScript` / `fusionscript` socket) are restricted to **DaVinci Resolve Studio**.
  - **External scripting connections BLOCKED**: External tools cannot connect via `bmd.scriptapp("Resolve")` on Free 21.1+ (`NoneType` / blocked socket).
  - **Lua 5.1 Embedded Scripts STILL WORK (with tighter sandbox)**:
    - Menu scripts (`Workspace -> Scripts -> Utility -> BadWords Bridge.lua`) run inside Resolve's Lua 5.1 sandbox.
    - **Sandbox limits**: No `io`, no `ffi`, no `require`, no UI Manager popups in Free 21.1+.
    - **How BadWords communicates (`src/api/resolve_bridge.py` + `setupfiles/BadWords Bridge.lua`)**:
      - BadWords -> Resolve: atomic write of `request.lua` in shared mailbox dir; Lua reads via `bmd.fileexists()` + `loadfile()`.
      - Resolve -> BadWords: Lua writes `Global.BadWordsBridge.Response = "<id>:<base64>"` via `fusion:SetPrefs()` + `fusion:SavePrefs()`; BadWords reads `Fusion.prefs` using shared file-read permissions on Windows (`FILE_SHARE_READ | WRITE | DELETE`) to avoid `ERROR_SHARING_VIOLATION`.
  - **DRT Export/Import BLOCKED in Free 21.1+**:
    - Native `.drt` container export/import fails or hangs in Free 21.1+.
    - BadWords must disable DRT mode in UI (`SettingsDialog`), bypass `.drt` paths (`is_free_21_1_or_newer()`), and use **FCP7 XML** (`TIER 2` XML assembly).
  - **Deployment Invariant**: Keep deploying `BadWords.py` harmlessly in primary `Utility` script dir even on Free 21.1+ (never delete `BadWords.py` based on edition - protects macOS shared-bundle installs and users upgrading to Studio or downgrading to `< 21.1`). Install `BadWords Bridge.lua` on Free/Unknown, never on verified Studio.

### 2. DaVinci Resolve Free `< 21.1` vs Studio
- **Free `< 21.1`**: Internal `Workspace -> Scripts -> BadWords` Python execution can still pass `resolve`/`fusion`/`bmd` in-process when host Python matches venv Python. External scripting still requires Studio or the Lua bridge.
- **Studio (all versions)**: Full internal & external Python scripting (`Local` / `Network` in Resolve Preferences -> System -> General), native DRT timeline import/export, and AI/Studio scripting APIs.

### 3. OS-Specific Quirks to Always Verify
- **macOS**:
  - Free and Studio share the **same app bundle path** (`/Applications/DaVinci Resolve/DaVinci Resolve.app`), so edition detection must NOT blindly guess `"Free"` when uncertain on macOS (otherwise `_connect()` skips native Studio connections).
  - **Mac App Store** version runs inside an Apple App Sandbox container - check container paths and file access permissions for mailbox/scripts/media.
  - External launcher fallback inside Resolve uses `open -n ... --args --embedded` for `BadWords.app`.
- **Windows**:
  - Simultaneous read/write on `Fusion.prefs` requires `CreateFileW` with `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE`.
  - Paths with spaces/Unicode (e.g., Polish usernames) can break external tools unless UTF-8 / 8.3 short paths are handled safely.
- **Linux**:
  - Resolve typically lives in `/opt/resolve` (or `/home/resolve` on Rocky/ISO installs).
  - Studio vs Free clues: `/opt/resolve/docs/`, `.desktop` entries, `rpm`/`pacman`/`dpkg`, `resolve -v`, `/opt/resolve/.license/`.
  - `Utility` script dirs include `~/.local/share/DaVinciResolve/Fusion/Scripts/Utility` and `/opt/resolve/Fusion/Scripts/Utility` (plus `/opt/resolve/libs/Fusion/Scripts/Utility`).

### 4. API Changes & Deprecations (From Resolve 21+ SDK Docs)
- **`OpenPage(pageName)`** now includes `"photo"` (`"media"`, `"photo"`, `"cut"`, `"edit"`, `"fusion"`, `"color"`, `"fairlight"`, `"deliver"`).
- **Use Job IDs, not render indices**: `StartRendering(jobId)`, `DeleteRenderJob(jobId)`, `GetRenderJobStatus(jobId)` replace deprecated index-based calls.
- **Use modern non-dict-legacy getters/setters** (`GetProjectListInCurrentFolder` instead of `GetProjectsInCurrentFolder`, `GetItemListInTrack` instead of `GetItemsInTrack`, etc.).
- **`ImportTimelineFromFile` options for DRT**: `"timelineName"`, `"importSourceClips"`, and `"sourceClipsFolders"` are **NOT valid for DRT import** (valid for XML/AAF/EDL/FCPXML/OTIO).
- **Deprecated `GetSetting`/`SetSetting` keys**: `perfProxyMediaOn` -> `perfProxyMediaMode` (`0`/`1`/`2`), `videoMonitorUseRec601For422SDI` -> `videoMonitorUseMatrixOverrideFor422SDI`.
- **Studio/AI APIs** (`AnalyzeForIntellisearch`, `AnalyzeForSlate`, `GenerateSpeech`) return `False` on Free or if Extras are not downloaded.

---

## Verification Checklist Before Completing Resolve-Related Changes
1. Did you check whether behavior differs across **Resolve Free 21.1+**, **Free < 21.1**, **Studio**, and **Standalone (no Resolve installed)**?
2. Did you verify no Python-only Resolve API call is relied upon unconditionally in Free 21.1+ without a Lua bridge or XML fallback?
3. Did you test the actual bridge / XML / settings / detection path safely in DEV mode (`tests/test_host_env_fixes.py`, `tests/test_startup_guard.py`, `tests/test_settings_and_version.py`, plus live roundtrip checks where possible)?
4. Did you confirm `sync_resolve_scripts` never writes into real system Resolve directories during `DEV` mode?
