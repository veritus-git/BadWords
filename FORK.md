# About StoryCraft

**StoryCraft** is this fork's name. The repository is a fork of **[BadWords](https://github.com/veritus-git/BadWords)** by Szymon Wolarz ([veritus-git](https://github.com/veritus-git)), a text-based rough-cutting plugin for DaVinci Resolve. It isn't affiliated with or endorsed by the original author. BadWords is released under the [MIT License](LICENSE), and the original copyright notices are kept.

- **Based on:** upstream branch `dev-v4` (the v4 rewrite), commit [`c65926a`](https://github.com/veritus-git/BadWords/commit/c65926a).
- **Default branch here:** `fork`. It contains every change listed below.
- **Original project:** for the official release, installers and support, go to [veritus-git/BadWords](https://github.com/veritus-git/BadWords). The installation commands in the README install StoryCraft, next to an installed BadWords without touching it.
- **Built with Claude:** the fork's changes to BadWords (everything listed below) were built with Claude models (Anthropic) in Claude Code. The original BadWords code is Szymon Wolarz's work.

## Differences from the original

Status: **Merged upstream** = accepted into the original project. **Upstream PR** = offered to the original project, waiting for review. **Fork only** = not offered upstream.

### Fixes
| Change | Status |
|---|---|
| Transcription no longer crashes with PyAV 19 (`metadata_errors`); a failed model download explains why (offline, firewall) instead of "Analysis failed" | Merged upstream [#9](https://github.com/veritus-git/BadWords/pull/9) |
| Esc on the "Cut clips" dialog no longer cuts the current timeline; Cut Now always reports what it did; on a timeline that was never assembled it offers "Assemble without <colour>" | Merged upstream [#10](https://github.com/veritus-git/BadWords/pull/10) |
| macOS: Resolve Studio is no longer detected as Free 21.1 (which removed the launcher and showed "no timelines") | Merged upstream [#11](https://github.com/veritus-git/BadWords/pull/11) |
| AI transcript: sentences no longer end after titles such as "Mr." or "Dr." | Upstream PR [#16](https://github.com/veritus-git/BadWords/pull/16) |

### Features
| Change | Status |
|---|---|
| **Apple Silicon GPU transcription** with mlx-whisper: about 11× faster than the CPU path, same fillers and timings, no PyTorch | Merged upstream [#12](https://github.com/veritus-git/BadWords/pull/12) |
| **Live silence tuning:** remove a share of the pause time (longest first), minimum clip length between cuts, keep part of each pause, live readout | Merged upstream [#13](https://github.com/veritus-git/BadWords/pull/13) |
| **"Colors in this edit" legend:** what each colour means, how much is kept or removed, Remove checkbox per colour | Merged upstream [#14](https://github.com/veritus-git/BadWords/pull/14) |
| **Cuts shown in the transcript text:** removed words struck through, a mark where a pause is cut out | Merged upstream [#15](https://github.com/veritus-git/BadWords/pull/15) |
| **AI story round trip:** copy an AI-ready transcript with sentence IDs, paste the AI's edit back, and Assemble builds the timeline in the AI's order | Upstream PR [#16](https://github.com/veritus-git/BadWords/pull/16) |

### UI revamp (in progress, fork only)
| Change | Status |
|---|---|
| **Pauses: Keep / Mark / Cut** as one choice at the top of the Silence panel, replacing the two switches that turned each other off | Fork only |
| **Play edit** in the player: plays the edit inside BadWords with the video, skipping removed parts and following the story order. Nothing is sent to Resolve | Fork only |
| **Smooth Play edit:** a 360p preview of the edit is rendered in the background (hardware encoder on Mac, cached per piece, about 16× realtime; a changed cut re-renders in about a second) and replaces the jumping playback when ready | Fork only |
| **Story board** panel (right sidebar): the interview as blocks of sentences in two lists, Edit and Not used. Drag to reorder (any order) or move between lists; split into sentences, join, play from a block. AI edits land here; Assemble and Play edit follow the Edit list. Saved per timeline | Fork only |
| **Workflow bar** above the transcript: 1 Clean up → 2 Compose → **Send to Resolve** (always visible), with a live summary (whole recording or story, length after cuts). Assemble is renamed Send to Resolve | Fork only |
| **Colours: Keep / Mark / Cut** on each row of "Colors in this edit" (Keep = stays in without colour, a new option). The per-colour scissors/A list folds into a collapsed "Resolve timeline tools" section | Fork only |
| **Colour themes**, chosen in Settings → General → Theme and applied immediately: Classic (the original look), Graphite (default), Midnight, Studio. Each changes the greys, the accent colour, the corners and the UI font (Inter, Geist, Manrope; bundled under assets/fonts with their SIL Open Font License files); marker colours and Resolve clip colours never change | Fork only |
| **Refreshed layout:** Clean up panels in cards with a title and subtitle; the live pause settings (share removed, minimum clip, kept pause) are sliders; numbered pill steps that show the current step; Send to Resolve joined with its ▾; story-board cards with a drag handle and a "Playing" tag that follows playback | Fork only |
| **Marking in the transcript:** left-click marks with the chosen marker (chips above the text, keys 1–9), right-click clears, Shift-drag selects a passage → play, mark as, clear, restore the AI's marks, detect again. The AI's marks are kept as their own layer, so clearing never loses them; **Restore AI marks** brings them back for everything or a passage | Fork only |
| **"What the AI found" card:** fillers, errors & retakes, script differences and no voice in one place, each with its count, how many you cleared, its switch and Restore; audio and video tracks are one choice each (All / Transcribed or None / Custom) | Fork only |
| **Visual rebuild:** waveform in the theme accent with cut gaps, Play edit pill, highlighted playing line, Resolve connection chip, solid right-click menus | Fork only |
| **Second speaker:** finds what the interviewer says (quieter, different voice) and marks it with your own marker, for you to review; uses the CAM++ voice model from [3D-Speaker](https://github.com/modelscope/3D-Speaker) (Apache-2.0), downloaded on first use, no PyTorch | Fork only |
| **Transcribe again:** select a passage, right-click → transcribe just that part again with the same settings; undo restores the previous words | Fork only |
| **Saved transcripts:** every timeline's transcript (with your marks) is kept automatically; the start screen offers "Open saved transcript" for a timeline transcribed before, so reopening Resolve doesn't mean transcribing again | Fork only |
| **Target length and clarity:** set how long the edit should be (e.g. 2:00 or 90s) on the story board; the AI is asked to aim for it and the board shows the edit against it. Each sentence gets a clarity score (0–100, from the transcription's word confidence and how loud the speech is), shown on the story cards and given to the AI so it favours clearly spoken parts. "Copy for AI" on the board | Fork only |
| **Avoid marker:** tag parts you don't want used (background noise, a voice behind, an awkward hesitation). Nothing is cut or coloured; the AI transcript flags those sentences AVOID and asks the AI to leave them out, and the story board puts them in Not used with an Avoid tag | Fork only |
| Fix: with a story, "Pauses to remove (%)" counts only the pauses inside the story (long pauses in unused parts no longer use up the budget and leave gaps in the edit) | Fork only |
| Fix: clicking the waveform of the assembled timeline puts the playhead where you click | Fork only |
| New timelines go in a **StoryCraft** bin and are named "<timeline> StoryCraft Edit N" (numbering continues after older "BadWords Edit" timelines; an existing BadWords bin is left as it is) | Fork only |
| A timeline transcribed before opens by itself when StoryCraft starts on it; Analyze on it asks "Open saved" or "Transcribe again" instead of transcribing straight away. A new transcription keeps the previous saved one (last 3) as a backup | Fork only |
| **AI edits that flow:** the transcript for the AI is grouped into moments (whole thoughts) with an editing brief (outline first; fewer, longer clips; no clip that starts mid-thought; reorder when it helps; target length, clarity, Avoid, interviewer). On import, StoryCraft checks the edit (length, clips under 5 s, starts mid-thought, Avoid, hard to hear) and copies a fix request to paste back to the AI. Story board cards follow the same moments | Fork only |
| Fix: a timeline made of several clips (e.g. an assembled edit) previews its own audio, so the playhead goes where you click and you hear the edit; the video panel shows that it is audio only. A single source clip as long as the timeline still shows its video | Fork only |
| **Repeated words:** words and short phrases said again straight away ("I think I think", "no no no") are marked as Retake after each transcription, every copy but the last, so one stays; "Repeated words" row in What the AI found (Detect / Restore). The original stutter detector now keeps the last copy too | Fork only |
| **Restarts:** self-corrections (the speaker starts a phrase, hesitates and starts again) are marked as Retake with the repeated words, so only the final version stays; story clips no longer open on "yeah / well / um" or end on "and... / you know" | Fork only |
| Fix: a filler followed by a pause could survive the cut (the cut before it snapped onto the pause after it); cuts now only snap to a silence between the two words they separate | Fork only |
| **MCP server:** Claude Desktop / Claude Code can read the transcript in moments, set the target length, check an edit and put it on the story board of the open StoryCraft window (`mcp_server/storycraft_mcp.py`, local bridge with a per-launch key). Sending to Resolve stays with the user | Fork only |
| **Transcribe with Resolve (speakers):** on Resolve Studio 21.1+, use Resolve's own transcription of the timeline's clips, with speaker detection, instead of Whisper; the other voice is marked Interviewer (kept, flagged for the AI). Falls back to Whisper | Fork only |
| **Better cuts:** "Review cuts" on the story board (and `review_cuts` for Claude): every cut with what is said either side, jumps, mid-thought starts/ends, loudness jumps, speaker changes and repeated points, for the AI to improve order and cut points. Story clip edges land on the quietest moment with a little air, never inside a word. After Send to Resolve: 2-frame audio crossfades on every join and a Yellow "Jump cut" marker where the picture jumps within the same shot | Fork only |
| Fix: a saved transcript is no longer opened by itself when its timeline has changed length since (the start screen says so) | Fork only |
| Transcripts, stories, backups and autosave are kept in the user's own **StoryCraft** folder (macOS: ~/Library/Application Support/StoryCraft/saves), moved there once from the install folder | Fork only |
| `send_to_resolve` for Claude: builds the edit in the open Resolve project as a new timeline (the assistant asks the user to approve each tool use) | Fork only |
| UI: side panels share one design (title, one-line explanation, cards); Script panel rebuilt ("Compare with the script", side by side, find errors without a script); Markers panel titled and carded; Pauses, What the AI found and Fillers scroll instead of squeezing on short windows; story board actions in a 2 x 2 grid so nothing is cut off; the story notice no longer clipped | Fork only |
| Start screen: settings in one card, a soft StoryCraft light behind the logo, larger Analyze / Import buttons. Settings: StoryCraft logo in the sidebar, a title on every page, **About StoryCraft** (credit to the original author, privacy, data folder) instead of Telemetry, **Logs** instead of the report form (it mailed the original author), no update box. Loading: the StoryCraft mark animates (the S is traced, the playhead glides) on the splash and while working | Fork only |
| **Installer and updater for StoryCraft:** `setupfiles/setup.py` (and the macOS / Linux / Windows bootstrap scripts) install StoryCraft from this repo's releases into its own folder (macOS: ~/Library/Application Support/StoryCraft, next to the saves) with `StoryCraft.app` and the Resolve menu entry `StoryCraft.py`; they reuse models an existing BadWords install already downloaded (link, read-only). "Update now" in StoryCraft runs `setupfiles/updater.py` from this repo: it installs the latest release and keeps settings, saves, models and the Python environment. Both never detect, change, repair, move or remove a BadWords install, its `BadWords.py` launcher or `BadWords.app`; uninstall keeps the saves. A development copy (file `.storycraft_dev`) is never updated in place. To publish an update: set `VERSION` in `src/config/app_constants.py` and publish a GitHub release tagged `vX.Y.Z` | Fork only |
| **Repeats:** sentences that only echo the one before ("It changed everything. Changed everything.") and lone "Yeah." / "Mhm." answers are marked as Retake with stammers and restarts (Detect and after each transcription); the edit check (Import AI edit, `check_edit`, `review_cuts`) flags two clips that make the same point and a name repeated in 4+ clips; in a story, every pause with no word in it is cut (a voice in the background goes), and so is a noise between two sentences (a cough) with the pauses around it; pauses over quiet speech follow the pause setting. A story clip that ends just before a 1–2 word tail finishing its sentence (split off by the transcript) keeps the tail | Fork only |
| **Sounds without words** (cough, knock, a voice in the background): their loudness is measured against the voice; one much louder than any word is cut wherever it is. "No voice" in What the AI found counts them and **Listen to sounds** plays each from a second before, with **Keep it / Cut it**; sounds an edit keeps get a Cocoa "Sound" marker in Resolve | Fork only |
| **New interface:** StoryCraft dark and StoryCraft Light themes (Classic, the BadWords look, removed; Graphite / Midnight / Studio kept); editor rebuilt: step bar with gradient Send, transcript as a centred document with times in the margin and soft marks, one tabbed inspector (Found, Story, Pauses, Fillers, Script, Markers) instead of two icon rails, floating player; start screen, Settings and dropdowns restyled; line icons (with a dark set for the light theme, `tools/brand/build_icons.py`) | Fork only |
| **Playhead:** clicking outside the edit while Play edit is on now goes exactly there (Play edit turns off) instead of snapping back into the edit | Fork only |
| **Rebrand to StoryCraft:** own name, mark (S of timeline clips with a playhead), wordmark in Outfit, cyan→violet brand gradient, favicon and app icons ([BRAND.md](BRAND.md), built by `tools/brand/build_brand.py`); drawn splash screen and start-screen header; user-facing text renamed in all 10 languages (only the credit links keep the original name) | Fork only |
| **Fully renamed:** Resolve menu entry `StoryCraft.py` (no longer collides with an installed BadWords' `BadWords.py`), `StoryCraft Bridge.lua`, telemetry texts; the GitHub repository is now Boris-Edu/StoryCraft | Fork only |
| **No telemetry:** the original's one-time anonymous ping went to its author's analytics; the fork sends nothing and never asks (`TELEMETRY_ENABLED = False`) | Fork only |
| **No updates from the original project:** the update check and auto-update are off (`CHECK_ORIGINAL_UPDATES = False`), so a BadWords release can't be installed over the fork | Fork only |
| README "About" section rewritten to credit and support the original author | Fork only |

### Tools
| Change | Status |
|---|---|
| Speech-to-text benchmark for Mac (faster-whisper vs mlx-whisper vs Apple Speech), on branch [`feat/mac-asr-benchmark`](https://github.com/Boris-Edu/StoryCraft/tree/feat/mac-asr-benchmark/tools/asr_benchmark) | Fork only |

## Changelog
- **2026-11-02:** first public release, v4.0.0 (the website is not part of the download). PRs #9–#15 merged into BadWords; #16 open.
- **2026-10-31 (local):** UI revamp started: Keep / Mark / Cut for pauses, Play edit (jumping, then smooth rendered preview), Story board, workflow bar with Send to Resolve, Keep / Mark / Cut for colours, colour themes, refreshed layout and theme fonts; renamed StoryCraft with its own identity.
- **2026-10-31:** fork published with the fixes and features above; PRs #9–#16 offered upstream.
