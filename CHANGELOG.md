# Changelog

All notable changes to the **BadWords** project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.0.2] - 2026-02-25
### Added
- [cite_start]**Compute Type Selection**: Added automatic/manual selection for optimal compute types (`float16`, `float32`, `int8`) to improve performance on new GPUs and compatibility on older hardware[cite: 4].
- [cite_start]**Lazy-Assemble**: Implemented a non-blocking assembly process so the application no longer appears to be "crashed" or frozen during timeline creation[cite: 4].
- [cite_start]**Windows Status Updates**: Added a dedicated "checking/downloading" stage for better feedback during the initial setup on Windows[cite: 4].
- [cite_start]**Branding**: Official project icon added for better visibility in the taskbar and system[cite: 4].
- [cite_start]**Telemetry**: Added optional, anonymous statistics ping in the installer (OS, version, and country only)[cite: 4].
- **Easter Egg**: Secret code added. [cite_start]Try typing `$RGB` in the script window and click "Analyze"[cite: 4].

### Changed
- [cite_start]**Precise Timestamps**: Integrated `stable-ts` for word-level precision, significantly reducing instances of words being cut in half[cite: 4].
- [cite_start]**Auto-Sourcing**: Replaced the manual "Compound Clip Fix Mode" with an intelligent background "Auto-Sourcing" algorithm for smarter timeline assembly[cite: 4].
- [cite_start]**Installer Improvements**: Updated installers to support "Update", "Clean Install", and "Full Wipe" modes[cite: 4].
- [cite_start]**Verbatim Optimization**: Tweaked the transcription logic for better repetition detection[cite: 4].

### Fixed
- [cite_start]**Whisper Hallucinations**: Repetitive AI output (e.g., "mhm mhm...") is now detected and compressed in the GUI (e.g., `[x100]`)[cite: 4].
- [cite_start]**UI Scaling**: Fixed the "non-script-reviewer" window behavior and improved text display[cite: 4].
- [cite_start]**Windows UI**: Fixed the issue where a white title bar would appear on Windows systems[cite: 4].
- [cite_start]**Logic Fixes**: Corrected the behavior of "typos" and "inaudible" fragments when visibility is toggled off[cite: 4].

## [2.0.1] - 2026-02-8
### Added
- [cite_start]**Multi-language Support**: Added all supported Whisper languages, including RTL (Right-to-Left) language support[cite: 3].
- [cite_start]**Editor Features**: Added "Show detected typos", "Clear transcript", and "Import project" options to the editor page[cite: 3].
- [cite_start]**User Preferences**: The app now saves user settings between sessions[cite: 3].

### Changed
- [cite_start]**Silence Detection**: Updated the silence detection algorithm for better accuracy[cite: 3].
- [cite_start]**Window Flexibility**: Changed the fixed editor window resolution to be resizable[cite: 3].

### Fixed
- [cite_start]Fixed the yellow marking of missing parts in the script comparison mode[cite: 3].

## [2.0.0] - 2026-02-07
### Added
- [cite_start]**Windows Support**: First official Windows Installer release[cite: 2].
- [cite_start]**Cross-Platform**: Achieved full cross-platform compatibility[cite: 2].

### Changed
- [cite_start]**Engine Rewrite**: Migrated from `openai-whisper` to `faster-whisper` for significantly faster transcription and lower RAM usage[cite: 2].
- [cite_start]**Architecture**: App is now fully "compact," with all necessary files contained within a single directory[cite: 2].
- [cite_start]**Linux Update**: Rewrote the Linux installer to support the new `faster-whisper` engine[cite: 2].

### Removed
- [cite_start]Removed the manual option for downloading Whisper models on Linux (now handled automatically)[cite: 2].

## [1.0.3] - 2026-01-30
### Added
- [cite_start]Added Russian language support.
- [cite_start]Added a "Marquee Progress Bar" to indicate activity during transcription.

### Changed
- [cite_start]**Refactoring**: Decoupled logical functions from `gui.py` into `algorithms.py` and `engine.py`.
- [cite_start]**Terminology**: Renamed the "Generate" function to "Assemble".
- [cite_start]**UI Design**: Implemented dynamic window heights for a cleaner look.
- [cite_start]**Installer Safety**: Updated Linux installer to work without the `--break-system-packages` flag.
- [cite_start]**Compound Clips**: Completely remade the "Compound Clip Fix" option.

### Fixed
- [cite_start]Fixed timeline assembly crashes when working on audio-only timelines.
- [cite_start]Corrected issues with the "Compare" option (reduced excessive blue/yellow marking).
- [cite_start]Fixed script importing from PDF and DOCX files.
- [cite_start]Whisper enhancement for better verbatim transcript precision.

## [1.0.0] - [1.0.2] - Start of 2026
- [cite_start]Early local development and proof-of-concept.