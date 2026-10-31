# About this fork

This repository is a fork of **[BadWords](https://github.com/veritus-git/BadWords)** by Szymon Wolarz ([veritus-git](https://github.com/veritus-git)), a text-based rough-cutting plugin for DaVinci Resolve. It isn't affiliated with or endorsed by the original author. BadWords is released under the [MIT License](LICENSE), and the original copyright notices are kept.

- **Based on:** upstream branch `dev-v4` (the v4 rewrite), commit [`c65926a`](https://github.com/veritus-git/BadWords/commit/c65926a).
- **Default branch here:** `fork`. It contains every change listed below.
- **Original project:** for the official release, installers and support, go to [veritus-git/BadWords](https://github.com/veritus-git/BadWords). The installation commands in the README install the original project, not this fork.

## Differences from the original

Status: **Upstream PR** = offered to the original project, waiting for review. **Fork only** = not offered upstream.

### Fixes
| Change | Status |
|---|---|
| Transcription no longer crashes with PyAV 19 (`metadata_errors`); a failed model download explains why (offline, firewall) instead of "Analysis failed" | Upstream PR [#9](https://github.com/veritus-git/BadWords/pull/9) |
| Esc on the "Cut clips" dialog no longer cuts the current timeline; Cut Now always reports what it did; on a timeline that was never assembled it offers "Assemble without <colour>" | Upstream PR [#10](https://github.com/veritus-git/BadWords/pull/10) |
| macOS: Resolve Studio is no longer detected as Free 21.1 (which removed the launcher and showed "no timelines") | Upstream PR [#11](https://github.com/veritus-git/BadWords/pull/11) |
| AI transcript: sentences no longer end after titles such as "Mr." or "Dr." | Upstream PR [#16](https://github.com/veritus-git/BadWords/pull/16) |

### Features
| Change | Status |
|---|---|
| **Apple Silicon GPU transcription** with mlx-whisper: about 11× faster than the CPU path, same fillers and timings, no PyTorch | Upstream PR [#12](https://github.com/veritus-git/BadWords/pull/12) |
| **Live silence tuning:** remove a share of the pause time (longest first), minimum clip length between cuts, keep part of each pause, live readout | Upstream PR [#13](https://github.com/veritus-git/BadWords/pull/13) |
| **"Colors in this edit" legend:** what each colour means, how much is kept or removed, Remove checkbox per colour | Upstream PR [#14](https://github.com/veritus-git/BadWords/pull/14) |
| **Cuts shown in the transcript text:** removed words struck through, a mark where a pause is cut out | Upstream PR [#15](https://github.com/veritus-git/BadWords/pull/15) |
| **AI story round trip:** copy an AI-ready transcript with sentence IDs, paste the AI's edit back, and Assemble builds the timeline in the AI's order | Upstream PR [#16](https://github.com/veritus-git/BadWords/pull/16) |

### Tools
| Change | Status |
|---|---|
| Speech-to-text benchmark for Mac (faster-whisper vs mlx-whisper vs Apple Speech), on branch [`feat/mac-asr-benchmark`](https://github.com/Boris-Edu/BadWords/tree/feat/mac-asr-benchmark/tools/asr_benchmark) | Fork only |

## Changelog
- **2026-10-31:** fork published with the fixes and features above; PRs #9–#16 offered upstream.
