# BadWords Continuous Learning & Verification Standards

Core always-active PO expectations and workflow gates. Detailed historical notes and UI/OS invariants live in `docs/PO_STANDARDS.md`.

## 1. Continuous Self-Learning Protocol (Mandatory)
Whenever the Product Owner (PO) corrects an output, requests missing proof, or states a product preference:
1. Fix the issue immediately in the active task.
2. Distill a concise generalized rule and update `docs/PO_STANDARDS.md` (and a brief bullet here if always-active) without waiting to be asked.
3. Keep rules deduplicated and concise (keep THIS file **under 4,000 chars**); state briefly in plain Polish what was learned.

## 2. Mandatory Quality Gates Before Reporting
1. **No Long Dashes (`-` Only)**: Never use `\u2014` or `\u2013` anywhere in replies, UI strings, translations, code, comments, or docs; use ASCII `-` only.
2. **Real User-Side Polish Explanations**: Explain findings, bugs, workarounds, and numbered decisions `(C)` to the PO in plain Polish via concrete user scenarios (OS/edition, what user clicks, what breaks or changes on screen) - never dry slogans or raw code unless asked.
3. **Empirical & Live Verification**: Mocks alone are never enough for UI, IPC, Resolve, audio, or updates. Run real Qt widgets (`QT_QPA_PLATFORM=offscreen`), real file/subprocess roundtrips, and verify current Resolve 21.1+ limits (`.agents/skills/davinci-resolve-current/SKILL.md`).
4. **Proactive Visual PNG Inspection**: For any GUI/dialog/progress/scaling change, render PNGs into `tests/artifacts/` and inspect **every PNG** with `read_file` before replying.
5. **Local KVM VMs (`badwords-win11`, `badwords-linux-kde`)**: When changes touch Win11, installers, or clean Linux behavior, verify automatable steps inside VMs first and give the PO a short Polish click-through checklist for manual checks.
6. **State, Roadmap & Release Notes Discipline**:
   - Read `docs/DEV_STATE.md` at start and update it after changes (focus, milestones, exact test counts, next steps).
   - When closing a roadmap point: document in `docs/CEMENTED.md`, check `[x]` + mark `ZAKONCZONO YYYY-MM-DD` with summary and collapsed `<details>` prompt in `ROADMAP_CEMENTING.md`, and add a 3-4 word bullet in `.agents/rules/architecture.md` Sec. 3 (`< 4,000` chars).
   - Update `src/config/release_notes.json` before release tags.

## 3. Active Core Engineering Rules
- **11-Lang i18n & Zero Emojis**: Keep all 11 `src/i18n/*.json` key-identical, fallback to English on missing/empty strings, use vector SVG icons (never emojis like `🛈`, `🔍`, `⏳`, `✔`, `✕`).
- **OS Theme Immunity**: Enforce `Fusion` style + full dark `QPalette` globally so OS Light themes (Windows/KDE/GTK/macOS) never paint black text on dark UI.
- **Windows / Clean-OS Safety**: Static CRT (`+crt-static`) on Rust/C launchers, BOM-free ASCII `setupfiles/*.ps1`, zero `QGraphicsOpacityEffect` inside frameless dialogs, `user.json` privacy keys isolated from `settings.json`, manualSettings `Apply`-deferred scaling.
