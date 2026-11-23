<!--
Copyright (c) 2026 Szymon Wolarz
Licensed under the MIT License. See LICENSE file in the project root for full license information.
-->

# BadWords Cemented Modules Ledger

> **Purpose:** Authoritative technical reference for all **protected workarounds** and **cemented modules** in BadWords.
> Whenever a roadmap item is audited, fixed, verified, and approved by the Product Owner:
> 1. Add full technical documentation below (exact paths, behavior, `# INVARIANT:` contracts, OS quirks, protecting tests, and "DO NOT CHANGE" rules).
> 2. Add **only a 3–4 word index bullet** pointing to this file in `.agents/rules/architecture.md` Section 3 (to keep `architecture.md` strictly under 4,000 characters).

---

## Documentation Template (Copy for New Entries)

```markdown
### N. <Short Module Title>
- **Status:** Cemented (<YYYY-MM-DD>)
- **Files:** `src/...`, `tests/...`
- **How It Works:** Concise technical summary of the architecture and flow.
- **OS-Specific Behavior:** Windows / Linux / macOS differences and required workarounds.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` ...
- **Regression Tests:** `tests/test_...` (`python3 run_tests.py`)
- **Do Not Change Without Product Owner Approval:** Explicit boundaries.
```

---

## Baseline Protected Workarounds (Pre-Roadmap)

### 1. Python < 3.9 PySide6 Typings Hotfix
- **Status:** Protected Workaround (Pending full Stage 1 audit in Point 1)
- **Files:** `src/main.py` (lines 55–69)
- **How It Works:** On startup when `sys.version_info < (3, 9)`, scans `sys.path` for `PySide6/__init__.py` and patches `def __getattr__(name: str) -> list[str]:` to `def __getattr__(name: str) -> list:`.
- **Why It Exists:** Embedded Python 3.8/3.9 inside older DaVinci Resolve hosts raises `TypeError: unsupported operand type(s) for |` or PEP 585 generic type errors at import time.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Must execute **before** any `from PySide6...` import in `src/main.py`.
- **Regression Tests:** Verified on startup; covered in Stage 1 Point 1 cementing.

### 2. Resolve Headless Console Stream Buffering (`ResolveStreamProxy`)
- **Status:** Protected Workaround (Pending full Stage 1 audit in Point 2)
- **Files:** `src/osdoc.py` (lines 67–104)
- **How It Works:** Wraps `stdout`/`stderr` streams, accumulates partial writes in `self._buffer` until `\n`, strips redundant `[INFO]`/`[ERROR]`/`[STDOUT/ERR]` prefixes, forwards complete lines to the logger, and swallows stream write/flush errors intentionally.
- **Why It Exists:** Prevents crashes or dropped tracebacks when running inside DaVinci Resolve's embedded Python console or headless launchers.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Must implement `write`, `flush`, and `__getattr__` delegation so callers expecting standard file-like stream attributes keep working.
- **Regression Tests:** Covered in Stage 1 Point 2 cementing.

### 3. CUDA / cuDNN Dynamic DLL Injection & CPU Isolation
- **Status:** Protected Workaround & Tested (`tests/test_host_env_fixes.py`; pending full Stage 2 audit in Point 6)
- **Files:** `src/engine/transcription.py` (lines 620–680), `src/osdoc.py` (`has_nvidia_support`, `setup_cuda_dll_paths`, `get_short_path`), `tests/test_host_env_fixes.py`
- **How It Works:** Before initializing Faster-Whisper in GPU mode (`fw_device == "cuda"`), injects venv/libs `nvidia/{cublas,cudnn,cuda_nvrtc,cuda_runtime}/bin`, `torch/lib`, and `bin` paths into `PATH` and `os.add_dll_directory` (Windows) or `LD_LIBRARY_PATH` (Linux). Rejects NVIDIA drivers `< 525` and probes loadability of `cublas64_12.dll`/`cublas64_11.dll` (Windows) or `libcublas.so.12`/`11` (Linux) via `is_cuda_functional()`.
- **OS-Specific Behavior:**
  - Windows: Uses `os.add_dll_directory` + `PATH` + 8.3 short paths (`get_short_path`) for Unicode paths; never runs blind `ctypes.CDLL` preloading loops.
  - Linux: Walks `nvidia/*/lib` and prepends to `LD_LIBRARY_PATH`.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` When `fw_device != "cuda"` (e.g. CPU mode), `_get_cuda_preinit_code()` **must return `""`** so CUDA DLLs are never injected or loaded (prevents Windows `0xC0000005` access violation crashes).
  - `# INVARIANT:` Missing `cublas` or driver `< 525` must gracefully fall back to CPU without crashing.
- **Regression Tests:** `tests/test_host_env_fixes.py`

### 4. Cross-Platform Frameless Window Mixin (`FramelessWindowMixin`)
- **Status:** Protected Workaround (Pending full Stage 1 audit in Point 3)
- **Files:** `src/gui/components/mixins.py`
- **How It Works:** Provides unified frameless window initialization (`frameless_init`), smart corners, and edge resizing across OSes (`_HAS_QFRAMELESS` is currently `False`, using pure Qt + native OS calls).
- **OS-Specific Behavior:**
  - Windows: Root window uses `Qt.Window | Qt.FramelessWindowHint` + Win32 `SetWindowLong` (`WS_THICKFRAME | WS_CAPTION`), DWM attributes (`DwmExtendFrameIntoClientArea`, cloaking, corner/border attributes), and `WM_NCHITTEST` hit-testing; popups use translucent dialogs.
  - macOS: Root window uses native title bar with traffic lights and fullscreen button (`Qt.WindowFullscreenButtonHint`); popups use frameless translucent dialogs.
  - Linux: Root window stays `Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint` with custom `ResizeGrip` edges (never `Qt.Dialog`, preserving WM maximize/fullscreen).
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Linux root window must never use `Qt.Dialog`; Windows root window relies on `WM_NCHITTEST` for Aero Snap and border resize.
- **Regression Tests:** Covered in Stage 1 Point 3 cementing.

### 5. Global Input Focus Clear & Tooltip Debounce (`GlobalAppFilter`)
- **Status:** Protected Workaround (Pending full Stage 3 audit in Point 12A)
- **Files:** `src/gui/dialogs/overlay.py` (lines 21–86)
- **How It Works:** Installed globally on the Qt application to clear focus from active input widgets on outside mouse clicks or `Return`/`Enter`, and replaces native tooltips with a shared debounced custom tooltip (`750ms` single-shot `QTimer` triggered on `Enter`/`Leave`).
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Must ignore transient `RuntimeError` on deleted Qt objects and cancel/hide tooltip timers on `Leave`, `Hide`, `MouseButtonPress`, and `WindowDeactivate`.
- **Regression Tests:** Covered in Stage 3 Point 12A cementing.
