---
trigger: always_on
description: Continuous self-learning feedback capture, live mechanism testing, visual proof, Resolve 21.1+ standards, PO scenario communication, and state/roadmap hygiene.
---

# BadWords Continuous Learning & Verification Standards

## 1. Continuous Self-Learning Protocol (Mandatory in Every Conversation)
Whenever the Product Owner (PO) corrects an output, highlights a missing check, requests evidence you did not provide proactively, or states a preference for how BadWords should behave or be explained:
1. **Notice & Fix Immediately**: Address the exact issue in the current session first.
2. **Distill & Persist the Lesson**: Generalize the correction into a concise, actionable rule and add or merge it into **Section 4 (Learned PO Preferences & Corrections)** of this file (or update the relevant skill/doc) **without waiting to be asked**.
3. **Keep Rules Clean**: Deduplicate and merge overlapping bullets instead of appending clutter; keep this file concise and scannable.
4. **Confirm in Polish**: Tell the PO briefly in plain Polish what permanent lesson was recorded for future sessions.

---

## 2. Mandatory Quality Gates Before Reporting Any Change

### A. Live Mechanism & End-to-End Verification (Never Rely on Mocks Alone)
- `python3 run_tests.py` (unit tests with mocks) is the baseline, **not** sufficient proof when a mechanism interacts with external processes, files, OS APIs, network relays, installers, Qt event loops, or DaVinci Resolve.
- Whenever you touch or audit a real mechanism, run a **live/empirical verification** of the actual path (safely isolated from real user data in DEV mode):
  - **UI / Dialogs / Animations**: Instantiate real `QApplication` + real widgets (`QT_QPA_PLATFORM=offscreen`), drive clicks/search/toggles/scaling (75%–150%), verify opacity/geometry/text states, and render PNGs.
  - **IPC / Bridge / Subprocesses / Launchers**: Execute real subprocess invocations, real atomic file roundtrips (`request.lua` -> Lua/Python parser or real `Fusion.prefs` parsing), real `launcher.c` / Rust binary checks.
  - **Audio / FFmpeg / Export / XML / DRT**: Run real FFmpeg commands on sample media, validate generated XML/FCPXML/OTIO/EDL files structurally, verify frame math across drop-frame rates.
  - **Network / Relay / Crash Reports**: Test real payload serialization/validation against the actual endpoint or local test server as permitted and safe.
- Report the exact verification scope honestly (what ran live vs what was mocked).

### B. Proactive Visual Proof & Inspection
- **Never wait to be asked for screenshots.**
- Any change affecting GUI appearance, dialogs, error popups, tooltips, layout, icons, progress bars, dimming, or scaling MUST:
  1. Render PNG screenshots to `tests/artifacts/` (or `raport/screenshots/`) covering all relevant states, tabs, and error states.
  2. Open and visually inspect **every generated PNG** with `read_file` to catch clipped corners, unreadable contrast, raw/default styling, overlapping labels, or system emojis before reporting.

### C. Current DaVinci Resolve State & Documentation Check
- **Never trust stale memory of DaVinci Resolve.** Before analyzing, designing, or modifying any Resolve integration (`src/api/`, `src/osdoc.py`, `src/assembler.py`, `setupfiles/`, `installer/`, or Resolve-related UI):
  1. Load the `davinci-resolve-current` skill (`.agents/skills/davinci-resolve-current/SKILL.md`).
  2. Check local Resolve SDK documentation if present (`/opt/resolve/Developer/Scripting/README.txt` and `/opt/resolve/docs/`) AND search official Blackmagic Design release notes / docs via `search_web` for recent updates (21.1+, 21.2+, 22+).
  3. Explicitly verify Free vs Studio differences (especially Free 21.1+ Python/external-scripting/DRT blocks, Lua 5.1 sandbox constraints, and macOS bundle/App Store quirks).

### D. Real-World User Scenarios Instead of Dry Summaries
- When explaining findings, workarounds, bugs, or numbered decision questions to the PO:
  - **Ban dry, abstract bullet points** (e.g., *"może wystąpić problem z uprawnieniami"* or *"obejście ścieżek"*).
  - Write **concrete, step-by-step user-side scenarios** in plain Polish:
    1. **Who & Where**: Which user, OS, or Resolve edition (e.g., *"Użytkownik na Windowsie z darmowym DaVinci Resolve 21.1+"*).
    2. **Action & Symptom**: What the user clicks and what actually goes wrong on screen (*"Klika Analizuj → pasek postępu stoi na 0% przez minutę i okno się zamyka bez komunikatu"*).
    3. **Why Workaround Exists**: What real failure occurs if a workaround is removed.
    4. **Decision Outcome**: In numbered questions `(C)`, describe the tangible screen behavior difference between Option 1 and Option 2.

---

## 3. State Tracking & Roadmap Hygiene
- **`docs/DEV_STATE.md` (Live Session Memory)**:
  - **Start of Task**: Read `docs/DEV_STATE.md` to see current focus, recent fixes, architectural status, and test baseline.
  - **End of Task**: Update `docs/DEV_STATE.md` whenever code, tests, rules, or roadmap progress change — keep `Last Updated`, `Current Active Focus & Roadmap Position`, `Automated Test Suite` (exact test count), `Completed Milestone Record`, and `Next Steps` accurate.
- **`ROADMAP_CEMENTING.md` (Progress Ledger)**:
  - When a roadmap item is **fully completed and closed** (verified, tests added, documented in `docs/CEMENTED.md`, Sec. 3 bullet added to `architecture.md`):
    1. Check off `[x]` in the top **Postęp cementowania** checklist in `ROADMAP_CEMENTING.md`.
    2. Mark that item's heading with `✅ [ZAKOŃCZONO YYYY-MM-DD]`, add a brief summary of what was completed and where it is documented, and collapse its prompt into `<details>` so it is never re-executed accidentally.

---

## 4. Learned PO Preferences & Corrections (Auto-Updated Ledger)
- **2026-11-23 — Styled Startup & Error Dialogs**: Never ship bare/unstyled OS or Qt dialogs; match BadWords dark theme, localized 11-language fallback, and verify visually via PNGs.
- **2026-11-23 — Unify & Test Real Pipelines**: Shared features (e.g., crash report + Support contact upload) must use one contract/helper and be verified end-to-end, not via mocks alone.
- **2026-11-23 — Current Resolve 21.1+ Reality**: Always verify against up-to-date DaVinci Resolve docs (21.1+ Free removes Python scripting, external socket, and DRT export; relies on sandboxed Lua bridge; keep `BadWords.py` harmlessly).
- **2026-11-23 — Vivid User Cases Over Dry Prompts**: PO needs concrete real-world user stories ("what happens on screen, step by step"), never dry abstract summaries.
- **2026-11-23 — Mark Closed Roadmap Items**: Always check off finished points in `ROADMAP_CEMENTING.md` so the PO never repeats already-completed points.
- **2026-11-23 — Explicit `DEV_STATE.md` Lifecycle**: Always read `docs/DEV_STATE.md` at start and update active focus, milestones, test counts, and next steps at completion.
