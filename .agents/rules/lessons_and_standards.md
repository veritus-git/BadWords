---
trigger: always_on
description: Continuous PO learning standards, mandatory quality gates, crash-report inspection, and r/badwordsapp devlogs.
---

# BadWords Continuous Learning & Verification Standards

Core always-active PO expectations and workflow gates. Detailed historical notes and invariants live in `docs/PO_STANDARDS.md`.

## 1. Continuous Self-Learning Protocol (Mandatory)
Whenever the Product Owner (PO) corrects an output, requests missing proof, or states a product preference:
1. Fix the issue immediately in the active task.
2. Distill a concise generalized rule and update `docs/PO_STANDARDS.md` (and a brief bullet here if always-active) without waiting to be asked.
3. Keep THIS file strictly **under 4,000 chars**; state briefly in plain Polish what was learned.

## 2. Mandatory Quality Gates Before Reporting
1. **No Long Dashes (`-` Only)**: Never use `\u2014` or `\u2013` anywhere in replies, UI strings, translations, code, comments, or docs; use ASCII `-` only.
2. **Real User-Side Polish Explanations**: Explain findings, bugs, workarounds, and numbered decisions to the PO in plain Polish via concrete user scenarios - never dry slogans or raw code unless asked.
3. **Mandatory `raport/open/` Check & Polish Error Section**: On every code change/task (unless PO explicitly opts out), inspect `raport/open/` (never edit `resolved/`; alert PO if unmounted). Fix relevant open reports (`report.json` + move to `resolved/`) and ALWAYS include a dedicated Polish section explaining every open error's screen symptoms, root cause, and fix.
4. **Reddit Devlog (`r/badwordsapp`)**: After every change (unless PO opts out), follow `.agents/skills/reddit-devlog/SKILL.md` to create an English post in `devlogs/YYYY-MM-DD_<slug>/post.md`. Casual, genuine tone (NO forced "18yo solo dev" signoffs or corporate buzzwords), natural search keywords, longer bulleted posts for releases, and English UI PNGs ONLY when visuals changed.
5. **Empirical & Live Verification**: Run real Qt widgets (`QT_QPA_PLATFORM=offscreen`), real file/subprocess roundtrips, and verify Resolve 21.1+ limits (`.agents/skills/davinci-resolve-current/SKILL.md`).
6. **Proactive Visual PNG Inspection**: Render GUI changes into `tests/artifacts/` (or `devlogs/...`) and inspect **every PNG** with `read_file` before replying.
7. **Local KVM VMs (`badwords-win11`, `badwords-linux-kde`)**: Verify Win11/installer/clean-Linux changes inside VMs first, then give the PO a short Polish manual checklist.
8. **State, Roadmap & Release Notes Discipline**: Read `docs/DEV_STATE.md` at start and update after changes; follow `ROADMAP_CEMENTING.md` + `docs/CEMENTED.md` + `release_notes.json` on closures/releases.

## 3. Active Core Engineering Rules
- **11-Lang i18n & Zero Emojis**: Keep all 11 `src/i18n/*.json` key-identical, fallback to English on missing/empty strings, vector SVG icons only.
- **OS Theme Immunity**: Enforce `Fusion` style + full dark `QPalette` globally so OS Light themes never paint black text on dark UI.
- **Windows / Clean-OS Safety**: Static CRT (`+crt-static`) on Rust/C launchers, BOM-free ASCII `setupfiles/*.ps1`, zero `QGraphicsOpacityEffect` inside frameless dialogs, `user.json` privacy keys isolated from `settings.json`, `Apply`-deferred scaling.
