# BadWords - Complete User Guide & Manual

> [!WARNING]  
> **Disclaimer:** I've never written full documentation before, and I used AI to help put this entire guide together. Because of that, some mistakes, weird phrasing, or inaccuracies might still be present. If you stumble upon anything confusing or hard to understand, feel free to contact me directly or open an Issue on GitHub - Pull Requests are also welcome!

## Table of Contents


**[0. Quickstart Guide (How to start using BadWords)](#0-quickstart-guide-how-to-start-using-badwords)**<br>
&nbsp;&nbsp;&nbsp;&nbsp;[0.1 Launching from DaVinci Resolve](#01-launching-from-davinci-resolve)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[0.2 Choosing Source Audio & Model](#02-choosing-source-audio-model)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[0.3 Reviewing, Color-Coding & Cut Settings](#03-reviewing-color-coding-cut-settings)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[0.4 Assembling the Cut Timeline](#04-assembling-the-cut-timeline)<br>

**[1. Welcome Screen & Source Selection](#1-welcome-screen-source-selection)**<br>
&nbsp;&nbsp;&nbsp;&nbsp;[1.1 Transcription Workspace](#11-transcription-workspace)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[1.2 Fast Silence Workspace (Standalone Silence Removal)](#12-fast-silence-workspace-standalone-silence-removal)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[1.3 First-Run Model Download & Setup](#13-first-run-model-download-setup)<br>

**[2. Top Titlebar & Project Management](#2-top-titlebar-project-management)**<br>
&nbsp;&nbsp;&nbsp;&nbsp;[2.1 Project Menu](#21-project-menu)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[2.2 Transcript Menu (Export .txt & Clipboard)](#22-transcript-menu-export-txt-clipboard)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[2.3 Versions Dropdown](#23-versions-dropdown)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[2.4 Source Timeline & Audio Tracks Info](#24-source-timeline-audio-tracks-info)<br>

**[3. Transcript Editor & Sidebar Tools](#3-transcript-editor-sidebar-tools)**<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.1 Words Painting](#31-words-painting)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.2 Inaudible Fragments](#32-inaudible-fragments)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.3 Transcript Search Overlay](#33-transcript-search-overlay)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.4 Main Sidebar Panel](#34-main-sidebar-panel)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.5 Script Analysis Sidebar Panel](#35-script-analysis-sidebar-panel)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.6 Silence Detection Sidebar Panel](#36-silence-detection-sidebar-panel)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.7 Filler Words Sidebar Panel](#37-filler-words-sidebar-panel)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.8 Assembly Sidebar Panel](#38-assembly-sidebar-panel)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[3.9 Sidebar Drag & Drop Customization](#39-sidebar-drag-drop-customization)<br>

**[4. Audio Preview & Navigation Bar](#4-audio-preview-navigation-bar)**<br>
&nbsp;&nbsp;&nbsp;&nbsp;[4.1 Jump to Word (Instant Resolve Timeline Scrubbing)](#41-jump-to-word-instant-resolve-timeline-scrubbing)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[4.2 Integrated Audio Player Controls](#42-integrated-audio-player-controls)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[4.3 Speed Adjustment & Playhead Synchronization](#43-speed-adjustment-playhead-synchronization)<br>

**[5. Timeline Assembly & DaVinci Integration](#5-timeline-assembly-davinci-integration)**<br>
&nbsp;&nbsp;&nbsp;&nbsp;[5.1 The Assembly Split Button & Track Options Drawer](#51-the-assembly-split-button-track-options-drawer)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[5.2 Native `.drt` Pipeline (Non-Destructive Protection)](#52-native-drt-pipeline-non-destructive-protection)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[5.3 Timeline Heatmap Overview](#53-timeline-heatmap-overview)<br>

**[6. Settings & Preferences](#6-settings-preferences)**<br>
&nbsp;&nbsp;&nbsp;&nbsp;[6.1 General Settings](#61-general-settings)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[6.2 Interface & Transcript Formatting](#62-interface-transcript-formatting)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[6.3 Audio Sync Calibration (Offset, Padding, Snap Max)](#63-audio-sync-calibration-offset-padding-snap-max)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[6.4 Keyboard & Mouse Shortcut Bindings](#64-keyboard-mouse-shortcut-bindings)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[6.5 Custom Markers Configuration](#65-custom-markers-configuration)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[6.6 AI Engine Configuration (Advanced Mode)](#66-ai-engine-configuration-advanced-mode)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[6.7 Telemetry, Contact & Issue Reporting](#67-telemetry-contact-issue-reporting)<br>

**[7. Step-by-Step Practical Recipes ("How do I...?")](#7-step-by-step-practical-recipes-how-do-i)**<br>
&nbsp;&nbsp;&nbsp;&nbsp;[Recipe A: Cutting Video Based on a Written Script](#recipe-a-cutting-video-based-on-a-written-script)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[Recipe B: Removing Retakes & False Starts without a Script](#recipe-b-removing-retakes-false-starts-without-a-script)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[Recipe C: Fast Silence Cut without Transcribing](#recipe-c-fast-silence-cut-without-transcribing)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[Recipe D: One-Click Filler Word Purge](#recipe-d-one-click-filler-word-purge)<br>
&nbsp;&nbsp;&nbsp;&nbsp;[Recipe E: Working with Difficult Words, Names & Jargon](#recipe-e-working-with-difficult-words-names-jargon)<br>

**[8. Shortcuts Cheat Sheet & FAQ](#8-shortcuts-cheat-sheet-faq)**<br>

## 0. Quickstart Guide (How to start using BadWords)
If you want to just start using BadWords and go from raw footage to a cut timeline in a few minutes, follow this guide. 

```mermaid
flowchart LR
    A["Launch in Resolve"] --> B["Pick Track & Model"]
    B --> C["Click Analyze"]
    C --> D["Paint Mistakes"]
    D --> E["Assemble"]
    E --> F["New Cut Timeline"]
```

<br>

---

<br>

### 0.1 Launching from DaVinci Resolve
1. Open your project in **DaVinci Resolve**.
2. In DaVinci Resolve's top application menu bar, navigate to:
   $$\text{\textbf{Workspace}} \longrightarrow \text{\textbf{Scripts}} \longrightarrow \text{\textbf{BadWords}}$$
3. The BadWords window will appear on top of DaVinci Resolve.

<br>

---

<br>

### 0.2 Choosing Source Audio & Model
1. **Timeline Selection:** Confirm your active timeline is selected in the dropdown. (Click `Refresh` if you just created a new timeline).
2. **Track/s Selection:** Select the audio track(s) where dialogue is recorded (e.g., `A1` for your primary microphone).
3. **Language:** Select the spoken language of the recording.
4. **Model:** Leave default (**Large Turbo**) or change to **Large** on high-end hardware or **Medium** on lower-end hardware.

> [!IMPORTANT]  
> **Model Quality Warning:** While smaller models (*Tiny*, *Base*, *Small*) are available in the dropdown, their transcription precision is significantly degraded. Because BadWords relies entirely on verbatim word accuracy to calculate frame-exact cuts, using models below *Medium* can cause the AI to hallucinate or miss words, making the tool practically unusable.
5. Click the green **`Analyze`** button.

<p align="center">
  <img src="images/01a_quickstart_source_selection.png" alt="Choosing Source Audio and Model" width="80%">
</p>

<br>

---

<br>

### 0.3 Reviewing, Color-Coding & Cut Settings
1. Once processing finishes, your audio appears formatted as interactive text.
2. Filler words (*"um", "uh", "yyy", "mhm"* etc.) are automatically highlighted in **Red**.
3. Use your mouse to click or drag across mistakes, false starts, or repeated takes:
   - **Press `1` or select Red** for errors and filler words.
   - **Press `2` or select Blue** for retakes and repeated sentences.
   - **Press `4` or select Eraser** to clear any accidental highlight.

<p align="center">
  <img src="images/01b_quickstart_reviewing.png" alt="Reviewing and Painting Mistakes" width="80%">
</p>

4. **Silence & Auto-Cut Options in Sidebar:**
   - **Silence Detection Panel:** Choose whether dead air is removed directly (`Cut silence directly`) or highlighted in a light **Tan** color (`Mark silence with color`) so you can adjust cuts manually in Resolve.
   - **Auto-Cut vs Clip Coloring (Assembly Panel):** By default, marked words stay on the timeline as **color-coded clips**. However, if you click the circular **"A" (Auto-cut)** icon next to any color in the *Assembly* panel (it turns green), everything painted with that color will be **ripple-cut (deleted)** during assembly!

<p align="center">
  <img src="images/01c_quickstart_autocut.png" alt="Auto Cut and Clip Coloring in Assembly Panel" width="80%">
</p>

5. Hold **`Ctrl + Left Click`** on any word to instantly jump both BadWords audio and DaVinci Resolve's playhead to that exact timestamp.

<br>

---

<br>

### 0.4 Assembling the Cut Timeline
1. When you have finished marking your transcript, click the green **`Assemble`** button in the corner of the main panel on the right.
2. BadWords automatically builds and imports a **brand new timeline** into DaVinci Resolve named `<Timeline_Name>_Edit 1`.
> [!NOTE]
> **100% Non-Destructive:** Your original timeline remains completely untouched. On the new timeline, cuts are applied frame-accurately and every remaining clip is **color-coded directly in DaVinci Resolve (Clip Color)** according to your text markings for instant visual verification.

<br>

---

<br>

## 1. Welcome Screen & Source Selection

When BadWords opens, you are greeted by the **Welcome Screen**. This view allows you to configure your transcription pipeline or switch to the ultra-fast standalone silence removal tool.

<p align="center">
  <img src="images/02_welcome_screen.png" alt="Welcome Screen Layout" width="80%">
</p>

<!-- 
IMAGE PLACEHOLDER: docs/images/02_welcome_screen.png
Capture the initial BadWords Welcome Screen with annotations:
[1] Timeline Selector & Refresh Button
[2] Track/s Selector Dropdown
[3] Language Searchable Dropdown
[4] Model Dropdown & Info Tooltip
[5] More Accurate Transcription Toggle & Script Drawer
[6] Import Project (.bws) & Analyze Buttons
[7] Fast Silence Detection Link
-->

<br>

---

<br>

### 1.1 Transcription Workspace

| UI Element | Type | Purpose & Description |
| :--- | :--- | :--- |
| **Timeline Selection** | *Dropdown* | Lists all timelines present in your currently open DaVinci Resolve project. Select the timeline you wish to transcribe. |
| **Refresh Timelines `Refresh`** | *Button* | Re-queries DaVinci Resolve's API to update the list of timelines and audio tracks if you created or renamed one while BadWords was open. |
| **Track/s Selection** | *Multi-Select* | Allows you to select one, multiple, or all audio tracks (`A1`, `A2`, etc.). <br>**Important:** When multiple tracks are selected, BadWords mixes them into a **single combined audio stream** for Whisper. It does *not* transcribe each track separately. If multiple speakers talk over each other on separate tracks, the AI will "hear" mixed overlapping speech. |
| **Language** | *Searchable Dropdown* | Specifies the spoken language of the recording. Selecting a language automatically configures language-specific verbatim acoustic prompts (from a library of 60+ languages) and backend parameters to prevent the AI from translating or smoothing out native hesitation sounds. |
| **Model** | *Dropdown* | Selects the local Faster-Whisper neural network model. *(See the detailed Model Selection Guide below).* |
| **More Accurate Transcription** | *Toggle Switch* | Opens a collapsible slide-out drawer where you can paste or import a reference script (`.txt`, `.pdf`, `.docx`). Keywords from the script are extracted and fed directly into the model's initial prompt, dramatically increasing accuracy on technical jargon, names, and numbers. |
| **Import Project** | *Button* | Opens an existing BadWords `.bws` project file to resume previous editing sessions. |
| **Analyze** | *Action Button* | Extracts audio from Resolve, executes VAD & Whisper acoustic transcription, runs initial silence detection, and opens the main editor. |

#### Model Selection Guide & Hardware Requirements

> [!CAUTION]  
> BadWords relies strictly on **verbatim speech-to-text accuracy** to find acoustic cuts. Models below **Medium** are not recommended for production work as high word error rates degrade the entire cutting workflow.

| Model | Memory (VRAM / RAM) | Disk Space | Speed | Recommended Use Case |
| :--- | :---: | :---: | :---: | :--- |
| **Large Turbo** *(Default)* | ~2.5 GB | ~1.6 GB | Fast & Highly Accurate | **Strongly Recommended.** Best balance of verbatim precision and rendering speed on modern NVIDIA GPUs. |
| **Large (v3)** | ~3.5 GB | ~3.1 GB | Maximum Precision | **Recommended.** Best for heavy accents, technical jargon, or noisy backgrounds. |
| **Medium** | ~2.5 GB | ~1.5 GB | Moderate | Minimum recommended model for lower-spec GPUs or CPU-only setups. |
| **Small** | ~1.0 GB | ~480 MB | Fast | *Legacy / Testing only.* Low verbatim precision on stutters and filler words. |
| **Base** | ~0.5 GB | ~140 MB | Very Fast | *Not recommended.* Prone to hallucinating words and skipping pauses. |
| **Tiny** | ~0.3 GB | ~75 MB | Ultra Fast | *Not recommended.* Only for quick code testing. |

<br>

---

<br>

### 1.2 Fast Silence Workspace (Standalone Silence Removal)

Clicking the link **`Simple Silence Detection`** at the bottom of the Welcome Screen flips the interface into **Fast Silence Mode**. This mode bypasses speech-to-text entirely, using light-weight audio normalization and silence analysis to cut dead air across an entire timeline in seconds.

> [!NOTE]  
> **Built-in Audio Normalization:** Unlike DaVinci Resolve's native silence cutter (which requires manually tweaking dB levels for every different audio clip), BadWords **automatically normalizes audio levels in the background** before scanning. This makes the default threshold (`-42.0 dB`) universally accurate across all microphone setups out of the box.

<p align="center">
  <img src="images/03_fast_silence_screen.png" alt="Fast Silence Screen" width="70%">
</p>

<!-- 
IMAGE PLACEHOLDER: docs/images/03_fast_silence_screen.png
Capture Fast Silence mode with annotations:
[1] Silence Threshold (dB)
[2] Padding (s)
[3] Min Silence Duration (s)
[4] Cut Silence Directly vs Mark Silence with Color Toggles
[5] Run Detection Button
-->

#### Fast Silence Controls:
1. **Silence Threshold (dB):** Volume level below which normalized audio is classified as silence.  
   *Default: `-42.0 dB` (Pre-normalized audio ensures this threshold works universally).*
2. **Padding (s):** Safety margin preserved before and after speech to ensure word beginnings and trailing consonants are never clipped.  
   *Default: `0.10s`.*
3. **Min Silence Duration (s):** Minimum pause length required before a cut is triggered.  
   *Default: `0.20s`.*
4. **Mode Toggles (Mutually Exclusive):**
   - **`Cut silence directly`:** Automatically removes silence gaps and ripples the timeline together upon execution.
   - **`Mark silence with color`:** Leaves clips intact but color-codes silent regions with **Tan** clip colors in DaVinci Resolve for manual review.
5. **`Run Detection`:** Executes the pass and instantly builds a **brand new timeline** in DaVinci Resolve (e.g. `<Timeline_Name>_Edit 1`), leaving your source timeline **100% untouched**.

<br>

---

<br>

### 1.3 First-Run Model Download & Setup
When you analyze footage with a specific AI model for the first time:
- BadWords automatically downloads the neural network weights from HuggingFace directly into your local installation directory (`models/`).

> [!NOTE]  
> **Initial Download & Animated Progress Bar:**  
> During this one-time download, **the animated progress bar will run in an infinite loop without a percentage counter**, which might make it feel like the process is taking long or stuck. Do not close or force-quit the application! BadWords is actively fetching large neural network files in the background. Depending on your internet connection speed, this process typically takes a few minutes. If a genuine network issue occurs, BadWords will immediately stop and show an error dialog.

- Once downloaded, the model files are saved permanently on your local drive. All subsequent transcriptions with that model run completely offline and start instantly with zero download delay.

<br>

---

<br>

## 2. Top Titlebar & Project Management

The top bar of BadWords provides access to file management, transcript exports, and timeline synchronization. Note that these project menus and source details appear only **after the analysis is complete** and the transcript is loaded into the editor.

<br>

---

<br>

### 2.1 Project Menu
- **Export Project:** Saves the complete state of your current session into a portable `.bws` (BadWords Save) file. This includes the full word-level timestamps, your manual color markings, script comparison data, audio file for audio preview and timeline metadata.
- **Import Project:** Restores an existing session from a `.bws` file.

<p align="center">
  <img src="images/04a_titlebar_overview.png" alt="Titlebar Overview 1" width="50%">
</p>

> [!TIP]  
> **Crash Recovery & AutoSave:** BadWords runs a silent background AutoSave engine. If DaVinci Resolve or your system crashes unexpectedly, BadWords detects the cached session on the next launch and prompts you to restore your work with a single click.

<br>

---

<br>

### 2.2 Transcript Menu (Export .txt & Clipboard)
- **Export as .txt:** Exports the entire transcript as a clean, formatted plain `.txt` document.
- **Copy to clipboard:** Copies the transcript directly to your system clipboard

<p align="center">
  <img src="images/04b_titlebar_overview.png" alt="Titlebar Overview 2" width="50%">
</p>

<br>

---

<br>

### 2.3 Versions Dropdown
- **Version Dropdown:** Displays the currently active timeline and all previous versions. Also allowing to switch between them and come back to any previous version. 

> [!TIP]  
> A ***version*** is a save of state of the text and color markings, created every time after clicking **Assemble**

<p align="center">
  <img src="images/04c_titlebar_overview.png" alt="Titlebar Overview 3" width="50%">
</p>

<br>

---

<br>

### 2.4 Source Timeline & Audio Tracks Info
Located directly in the center of the titlebar, this indicator shows exactly what audio was fed into the AI model during analysis:
- **`Source Timeline:`** The name of the original timeline in DaVinci Resolve that was extracted.
- **`Tracks:`** The specific audio track(s) (e.g. `A1` or `A1, A2`) that Whisper processed.
- **Why it matters:** It serves as a constant reference of truth. If you selected multiple microphone tracks, it reminds you that Whisper analyzed a mixed audio stream of those tracks together. It also identifies which timeline in DaVinci Resolve BadWords will duplicate and cut when you assemble.

<p align="center">
  <img src="images/04d_titlebar_overview.png" alt="Titlebar Overview 4" width="50%">
</p>

<br>

---

<br>

## 3. Transcript Editor & Sidebar Tools

BadWords operates within an IDE-inspired interface designed for high-efficiency dialogue editing. 

The **central workspace** displays your verbatim speech transcription, where every single word is bound to frame-accurate audio timestamps. Because each word directly represents its corresponding audio slice, selecting, painting, or cutting text performs exact timeline operations on those audio and video segments.

Surrounding the central transcript are modular **Sidebar Panels** containing tools for script alignment, silence trimming, filler word detection, and timeline assembly. These sidebars are fully customizable:
- **Resizable:** Drag sidebar borders to adjust width according to your preference.
- **Draggable:** Freely reorder tabs or drag entire panels between the left and right sides of the window.
- **Collapsible:** Fold and collapse any panel to let the transcript fill more screen space.

> [!NOTE]  
> Switching between open tabs retains your custom resized width. However, completely collapsing and reopening a sidebar panel resets its width back to the default size.

<p align="center">
  <img src="images/05_transcript_canvas.png" alt="Transcript Canvas and Word Painting" width="80%">
</p>

<!-- 
IMAGE PLACEHOLDER: docs/images/05_transcript_canvas.png
Capture Transcript Canvas with annotations:
[1] Timestamp Header [00:14]
[2] Sentence Block
[3] Red Highlighted Filler Word
[4] Blue Highlighted Retake Block
[5] Green Highlighted Typo
[6] Inaudible (...) Token
[7] Search Overlay Active
-->

<br>

---

<br>

### 3.1 Words Painting
BadWords uses a ***Color-coded heatmap*** for editing. Selecting a color tool (from the sidebar palette or keys `1`–`4`) and clicking or dragging across words applies that color tag to the corresponding acoustic segment.

For manual editing without a script, you can use these colors however you prefer (for instance, marking all errors in Red and retakes in Blue). However, when using automated tools like **Script Comparison** (see [Section 3.5](#35-script-analysis-compare-vs-standalone-side-by-side-view)), BadWords assigns precise semantic meaning to each color:

| Painting Color | DaVinci Clip Color | Meaning in Script Comparison / Recommended Usage |
| :---: | :---: | :--- |
| **Red** | **Violet** | Filler words (*"uh"*, *"um"*, *"yyy"*), obvious stumbles, coughs, and speech errors. |
| **Blue** | **Navy** | Retakes, repeated sentences, false starts, and alternate takes. |
| **Green** | **Olive** | Minor phrasing deviations, typos, or improvisations compared to the script. |
| **Brown** | **Chocolate** | Inaudible speech, mumbled phrases, or microphone clicks. |
| **Eraser** | *Default* | Strips color tags from selected words, restoring standard clip status. |
| **Custom** | *User Assigned* | User-defined custom categories (e.g. "B-Roll", "Zoom In", "Sound Effect"). |

By default, **all marked words remain on your assembled timeline as color-coded clips (DaVinci Clip Color)** so you can inspect them visually before making cuts. To configure automatic ripple cutting or post-review mass removal for specific colors, see [Section 3.8: Assembly & Color Cutting Matrix](#38-assembly-color-cutting-matrix-auto-cut-vs-cut-now).

> [!NOTE]  
> **Color Rules & Reserved Presets:**  
> - **Silence Representation:** Silence is not shown as text tokens in the BadWords editor canvas. The **Tan** clip color is applied exclusively on silent cuts inside DaVinci Resolve when you enable `Mark silence with color` in the [Silence Detection Panel](#36-silence-detection-panel-post-transcript-trimming).
> - **Reserved Colors:** Custom markers cannot use **Green**, **Blue**, **Tan**, or **Chocolate** to prevent visual collisions with native DaVinci clip colors and system states (silence and inaudible audio).

<br>

---

<br>

### 3.2 Inaudible Fragments
When audio is completely unintelligible, muffled, or masked by loud background noise, Whisper cannot transcribe speech. BadWords flags these moments as inaudible fragments, represented in the transcript canvas as `(...)` tokens.

<p align="center">
  <img src="images/06_inaudible_fragments.png" alt="Inaudible Fragments" width="90%">
</p>

> [!TIP]  
> **Why it matters:** Instead of guessing why a jump or silent gap occurred, this gives you full transparency to see exactly what the AI couldn't parse, allowing you to review those moments manually in Resolve.

You can customize how inaudible tokens are displayed in the editor (hidden, uncolored, or marked with Chocolate color) and how they are handled on the timeline in the [Assembly & Color Cutting Matrix (#3.8)](#38-assembly-color-cutting-matrix-auto-cut-vs-cut-now).

<br>

---

<br>

### 3.3 Transcript Search Overlay
Pressing **Ctrl + F** (or Cmd + F on macOS) toggles the floating search bar:
- Type any word or phrase to highlight matches across the entire transcript.
- Match counter displays live results (e.g. 4/18).
- Use the **Up / Down Arrow keys** on your keyboard (or click the arrow buttons in the search bar) to cycle through matches.
- Press **Ctrl + F** again (or click the close button) to hide the search bar.

<br>

---

<br>

### 3.4 Main Sidebar Panel <img src="../assets/layout/main.png" width="24" height="24" valign="middle">

The **Main Panel** serves as the primary control center for manual word painting and quick assembly actions. It is organized into two sections:

<img align="right" src="images/07a_sidebar_tools.png" alt="Sidebar Main Upper" width="240">

#### Upper Section: Marking Palette & Custom Colors
- **Active Marker Selector:** Radio buttons to switch between **Red**, **Blue**, **Green**, **Eraser**, and custom markers. Shortcut keys `1`, `2`, `3`, `4` select these tools instantly.
- **Clear Transcript (Brush Icon):** Erases all color markings across the entire project with a confirmation dialog.
- **`+ add custom marker...`:** Opens the Settings dialog directly to create, configure, and assign shortcuts to custom color markers (see [Section 6.5: Custom Markers Configuration](#65-custom-markers-configuration)).

<br clear="all">

<img align="right" src="images/07b_sidebar_tools.png" alt="Sidebar Main Lower" width="240">

#### Lower Section: Favorites & Timeline Export
- **Analysis Duration Indicator:** Displays exact stats on transcription processing time (e.g. *Analyzed in: 0.18min*).
- **Pinned Favorites:** Dynamically reveals any tools or toggles you have starred with the Star `★` button on *Assembly* Sidebar Panel (such as one-click auto-cut toggles), letting you control them without leaving the Main tab.
- **`Assemble` Split Button:** Triggers timeline assembly and includes an expandable dropdown drawer to choose which tracks are cut. For complete details on track modes, see [Section 5.1: The Assembly Split Button & Track Options Drawer](#51-the-assembly-split-button-track-options-drawer).

<br clear="all">

<br>

---

<br>

### 3.5 Script Analysis Sidebar Panel <img src="../assets/layout/script.png" width="24" height="24" valign="middle">

The **Script Analysis Panel** houses intelligent alignment tools that automatically detect speech errors and retakes, either by comparing the recording against an imported script or by finding acoustic repetitions in unscripted takes.

<p align="center">
  <img src="images/08a_script_analysis_sbs.png" alt="Script Analysis" width="100%">
</p>

<img align="right" src="images/08b_script_analysis_sbs.png" alt="Script Analysis Sidebar" width="240">

#### Available Tools & Modes:
- **Script Input Area & `Import Script`:** Paste your text or load `.txt`, `.docx`, or `.pdf` files. BadWords automatically strips formatting and normalizes whitespace.
- **`Analyze (Standalone)`:** Scans the raw transcript *without* a script using a lightweight repetition detection algorithm to spot repeated phrases and false starts, marking earlier discarded takes in **Blue**. *(Note: This feature is under active development and currently serves as a quick helper to highlight potential retake zones in long transcripts for manual inspection).*
- **`Analyze (Compare)`:** A proprietary, custom-built sequence alignment algorithm developed specifically for BadWords. Powered by advanced dynamic programming techniques inspired by bioinformatic DNA sequence alignment, it provides rock-solid, dependable script matching. It compares your recording against the imported text and color-codes deviations:
  - Words matching the script remain unpainted.
  - Repeated attempts and retakes are painted **Blue**.
  - Filler words, stumbles, and speech errors are painted **Red**.
  - Minor phrasing variations and slight mishearings compared to the script are painted **Green** (these green typo tags can be toggled on/off anytime using `Show detected typos` in the [Assembly Panel](#38-assembly-sidebar-panel-)).
- **`Side-by-Side View (BETA)`:** Opens the two-column comparative view (shown in the screenshot above) with the reference script on the left and the live transcript on the right, highlighting unspoken lines, skipped phrases, and improvisations.
- **`Return to Normal View`:** To exit the Side-by-Side view at any time, open the Script Analysis sidebar tab and click this button to restore the standard transcript editor canvas.

> [!TIP]  
> For complete step-by-step editing workflows, see [Recipe A: Cutting Based on a Script](#recipe-a-cutting-video-based-on-a-written-script) and [Recipe B: Removing Retakes without a Script](#recipe-b-removing-retakes-false-starts-without-a-script).

<br clear="all">

<br>

---

<br>

### 3.6 Silence Detection Sidebar Panel <img src="../assets/layout/silence.png" width="24" height="24" valign="middle">

The **Silence Detection Panel** allows you to fine-tune acoustic silence trimming applied after full speech transcription, removing awkward pauses and dead air.

#### Detection Parameters:
- **Threshold (dB):** Volume floor in decibels (default `-42.0 dB`). Audio below this level is classified as silence. Click `↺` to reset.
- **Padding (s):** Preserves safety margins around speech (default `0.05s`) so the start and end of spoken words are never clipped. Click `↺` to reset.
- **Min Silence Duration (s):** Minimum pause length required to trigger a cut (default `0.20s`). Click `↺` to reset.

#### Silence Actions:
- **`Detect and cut silence` Toggle:** Automatically ripple-deletes silent gaps during timeline assembly.
- **`Detect and mark silence` Toggle:** Retains silent gaps on the timeline but tags them with the **Tan** clip color in DaVinci Resolve for manual inspection.

> [!TIP]  
> If you want to remove silence from an entire timeline instantly without transcribing speech, use the **Fast Silence Workspace** on the Welcome Screen (see [Section 1.2](#12-fast-silence-workspace-standalone-silence-removal) and [Recipe C](#recipe-c-fast-silence-cut-without-transcribing)).

<br>

---

<br>

### 3.7 Filler Words Sidebar Panel <img src="../assets/layout/fillers.png" width="24" height="24" valign="middle">

The **Filler Words Panel** manages BadWords' built-in dictionary for identifying hesitation sounds (*"uh"*, *"um"*, *"yyy"*, *"mhm"*, *"like"*).

#### Dictionary & Automation Controls:
- **Inline Words Editor:** Edit the list of comma-separated filler words directly.
- **Live Word Counter:** Displays the total count of recognized filler words.
- **`Save` & `↺` (Reset):** Save custom dictionary edits or revert to the factory default list.
- **`Mark filler words automatically` Toggle:** When enabled, any word in your transcript matching the dictionary is automatically painted **Red** right as transcription finishes.

> [!TIP]  
> To learn how to purge all filler words from your timeline in one click, see [Recipe D: One-Click Filler Word Purge](#recipe-d-one-click-filler-word-purge).

<br>

---

<br>

### 3.8 Assembly Sidebar Panel <img src="../assets/layout/assembly.png" width="24" height="24" valign="middle">

The **Assembly Panel** is the control matrix that defines exactly how each marker color and system state translates into timeline edits in DaVinci Resolve.

<p align="center">
  <img src="images/09_assembly_matrix.png" alt="Assembly Panel" width="80%">
</p>

<!-- 
IMAGE PLACEHOLDER: docs/images/09_assembly_matrix.png
Capture the Assembly Matrix showing:
[1] Show/Mark Inaudible Toggles
[2] Show Detected Typos Toggle
[3] Color Row: Color Name & Hex Badge
[4] Cut Now (Scissors) Button
[5] Auto-Cut Checkbox Icon
[6] Star (Pin to Favorites) Button
-->

#### Global Inaudible & Typos Toggles:
- **`Show inaudible fragments`:** Controls how inaudible `(...)` tokens behave in the transcript canvas (see [Section 3.2](#32-inaudible-fragments)):
  1. **Hidden:** When toggled OFF, inaudible tokens are completely hidden and their duration is smoothly absorbed by surrounding words and color blocks.
  2. **Visible (Uncolored):** When toggled ON (without color marking), tokens appear as plain text `(...)` and assemble as standard uncolored clips in DaVinci Resolve.
  3. **Marked with Chocolate Color:** When `Mark inaudible with color` is also toggled ON, inaudible tokens turn brown in the editor and are color-coded as **Chocolate** clips in DaVinci Resolve upon assembly for visual review.
- **`Show detected typos`:** Toggles whether minor phrasing deviations detected by Script Comparison are highlighted in **Green** or left unpainted.

#### Controls per Color Row:
1. **Scissors Icon (`Cut Now`):** Prompts you to immediately cut and remove all clips of this color from either the **Currently Selected Timeline** or a **New Timeline** in DaVinci Resolve.
2. **Auto-Cut Icon (Checkmark / "A"):** When active (green), any text painted with this color is **automatically ripple-deleted** during the standard `Assemble` process.
3. **Star Icon (`★`):** Pins this color's Auto-Cut toggle directly onto the Main Panel under *Pinned Favorites*.

<br>

---

<br>

### 3.9 Sidebar Drag & Drop Customization
You can reorder sidebar activity icons or drag panels between the left and right sides of the window by simply clicking and dragging the sidebar button handles.

<br>

---

<br>

## 4. Audio Preview & Navigation Bar

The bottom panel of the editor houses the **Audio Preview Bar**, eliminating guesswork by allowing you to listen to words and navigate Resolve directly from the text.

<p align="center">
  <img src="images/06_audio_preview_bar.png" alt="Audio Preview Bar" width="100%">
</p>

<!-- 
IMAGE PLACEHOLDER: docs/images/06_audio_preview_bar.png
Capture the bottom Audio Preview Bar showing:
[1] Floating Audio Preview Toggle Island
[2] Play/Pause Button
[3] Waveform / Seeker JumpSlider
[4] Timestamp Display (Current / Total)
[5] Speed Dropdown (1.0x)
-->

<br>

---

<br>

### 4.1 Jump to Word (Instant Resolve Timeline Scrubbing)
- **Shortcut:** **`Ctrl` + Left Click** (Configurable in Settings to `Alt` or `Shift` + Left/Right click).
- Clicking any word in the transcript instantly moves **both**:
  1. The internal BadWords audio playback head.
  2. The **DaVinci Resolve timeline playhead** to the exact frame where the word was spoken!

<br>

---

<br>

### 4.2 Integrated Audio Player Controls
- **Play / Pause:** Click the animated play button or press **`Space`**.
- **Seeker Bar (JumpSlider):** Click anywhere on the progress bar to scrub through the audio.
- **Skip Backward / Forward:** Press **`Left Arrow`** / **`Right Arrow`** to jump in 2-second increments.
- **Toggle Floating Tab:** Click the floating island tab at the bottom of the editor to hide or show the audio bar.

<br>

---

<br>

### 4.3 Speed Adjustment & Playhead Synchronization
Click the speed dropdown to select playback rates: `0.5x`, `0.75x`, `1.0x`, `1.25x`, `1.5x`, or `2.0x`. Pitch correction is applied automatically to maintain vocal clarity at high speeds.

<br>

---

<br>

## 5. Timeline Assembly & DaVinci Integration

When editing is complete, clicking the **Assemble** button converts your text modifications into timeline operations in DaVinci Resolve.

<p align="center">
  <img src="images/10_assembly_drawer.png" alt="Assembly Track Selection Drawer" width="90%">
</p>

<!-- 
IMAGE PLACEHOLDER: docs/images/10_assembly_drawer.png
Capture the Assemble Split Button expanded with the Track Options Drawer:
[1] Assemble Button Main Click Area
[2] Drawer Expand Arrow (Expand / Collapse)
[3] Track Mode Selector (All / Transcription Only / Custom)
[4] Video Tracks Checkboxes (V1, V2...)
[5] Audio Tracks Checkboxes (A1, A2...)
-->

<br>

---

<br>

### 5.1 The Assembly Split Button & Track Options Drawer
- **Main Button Area:** Clicking **`Assemble`** immediately triggers the build process using current track settings.
- **Drawer Arrow (`Expand / Collapse`):** Expands the **Track Options Drawer** directly above the button:
  - **All tracks:** Includes every video and audio track present on the source timeline in the final ripple edit.
  - **Only transcription tracks:** Cuts only the audio track(s) selected during transcription.
  - **Custom selection:** Allows you to check/uncheck specific video tracks (`V1`, `V2`, `V3`) and audio tracks (`A1`, `A2`, `A3`).

<br>

---

<br>

### 5.2 Native `.drt` Pipeline (Non-Destructive Protection)

Unlike tools relying on legacy Final Cut Pro 7 XML exports (which break adjustment clips, Fusion titles, and generators), BadWords uses a **Native DaVinci Resolve Timeline (`.drt`) Engine**:

```mermaid
flowchart TD
    A["Source Timeline in Resolve"] -->|1. Export .drt| B["ZIP Archive Extraction"]
    B -->|2. Parse SeqContainer XML| C["Calculate Frame-Accurate Cuts"]
    C -->|3. Modify Start / Duration / In| D["Repack .drt Archive"]
    D -->|4. Import into Resolve| E["Brand New Assembled Timeline"]
    E -->|5. Apply Markers & Colors| F["Finished Output"]
```

#### What this guarantees:
- **100% Non-Destructive:** Your source timeline is NEVER modified or overwritten.
- **Preserves All Effects:** Video transitions, color grades, Fusion compositions, adjustment clips, and subtitles remain intact.
- **Sub-50ms Timing Accuracy:** Incorporates a global calibrated temporal offset (`0.133s`) to align acoustic phonemes with video frames.

<br>

---

<br>

### 5.3 Timeline Heatmap Overview
Upon import into DaVinci Resolve, BadWords attaches native timeline markers to every edited region. This creates a color-coded "heatmap" directly inside Resolve’s Edit Page, allowing you to instantly spot where edits took place and inspect cuts visually.

<br>

---

<br>

## 6. Settings & Preferences

Clicking the Gear Icon Settings opens the **Settings Dialog**. You can switch between **Basic View** and **Advanced View** at the top.

<p align="center">
  <img src="images/11_settings_dialog.png" alt="Settings Dialog Overview" width="90%">
</p>

<!-- 
IMAGE PLACEHOLDER: docs/images/11_settings_dialog.png
Capture Settings dialog showing:
[1] Basic / Advanced View Switcher
[2] Left Category Navigation List
[3] Setting Row with Input & Reset (Refresh) Button
[4] Footer Bar: Reset All Settings, Close, Apply
-->

<br>

---

<br>

### 6.1 General Settings
- **Interface Language (`Language`):** Switches UI language (English, Polish, German, French, Spanish, Russian, Italian, Japanese, Chinese, etc.).
- **Accent Color:** Selects the theme accent color (Green, Blue, Purple, Orange, Red, Teal, Pink, Amber).
- **App Icon:** Chooses the application window icon style.
- **Always on top:** Keeps BadWords floating above DaVinci Resolve.
- **Notify me about new versions:** Checks GitHub/GitLab releases on startup.
- **Auto-update on startup:** Silently downloads and installs patches automatically before opening.

<br>

---

<br>

### 6.2 Interface & Transcript Formatting
- **Transcript Layout Mode:** Choose between **Segmented Blocks** (breaks text into clean sentence chunks with `[00:14]` timestamp headers) and **Continuous Flow** (unbroken paragraph prose).
- **Transcript Font & Font Size:** Changes typography and font scaling (pt).
- **Line Spacing (px):** Adjusts vertical padding between lines.
- **Precise Timestamps (ms):** Displays full millisecond timestamps (e.g. `[01:08.432]`) instead of rounded seconds (`[01:08]`).
- **Punctuation marks per block (`chunk_punct_count`):** Number of sentences grouped into a single transcript block.
- **Max chunk words / Lookahead words:** Controls maximum line length and punctuation-aware word wrapping.

<br>

---

<br>

### 6.3 Audio Sync Calibration (Offset, Padding, Snap Max)

Fine-tune these parameters if you need razor-sharp acoustic synchronization:

| Parameter | Default Value | Description |
| :--- | :---: | :--- |
| **Offset (s)** | `0.133s` | Shifts all transcript timestamps backward or forward. Negative values start cuts slightly earlier; positive values delay them. |
| **Padding (s)** | `0.000s` | Adds extra duration to the tail of each spoken word, ensuring trailing consonants are never clipped. |
| **Snap Max (s)** | `0.250s` | Maximum silence gap between two adjacent words to merge them into a single uninterrupted audio clip. |

<br>

---

<br>

### 6.4 Keyboard & Mouse Shortcut Bindings
Configure custom keys for every action:
- Switch to Red / Blue / Green Marker
- Switch to Eraser
- Jump to Word (`Ctrl` / `Alt` / `Shift` + Left / Right Mouse Button)
- Play / Pause (`Space`)
- Skip Backward / Forward (`Left` / `Right`)
- Search (`Ctrl + F`)
- Open Settings (`Escape`)

<br>

---

<br>

### 6.5 Custom Markers Configuration
Create bespoke markers for your personal workflow:
1. Click **`+ Add Marker`**.
2. Enter a marker name (e.g., *"B-Roll Insert"* or *"Sound Effect"*).
3. Assign any unused DaVinci Resolve color.
4. Assign a keyboard shortcut key.
5. Export or import your marker configurations across different editing workstations.

<br>

---

<br>

### 6.6 AI Engine Configuration (Advanced Mode)

For power users who wish to customize the Faster-Whisper transcription engine:

| Setting | Default | Description |
| :--- | :---: | :--- |
| **Device** | `Auto` | Selects processing device (`Auto`, `CUDA` for NVIDIA GPUs, or `CPU`). |
| **Compute Type** | `int8` / `Auto` | Quantization precision (`int8`, `float16`, `bfloat16`, `float32`). |
| **VAD Filter** | `False` | Silero Voice Activity Detection pre-filter. |
| **Beam Size** | `1` | Greedy decoding (`1`) forces raw acoustic capture without grammatical smoothing. |
| **Temperature** | `0.0` | Sampling temperature. `0.0` ensures deterministic, hallucination-free output. |
| **Condition on Previous Text** | `False` | Disables previous context chaining to eliminate infinite repetition loops. |
| **Initial Prompt** | *Golden Verbatim* | Custom acoustic prompt guiding the AI to capture stutters and filler phonemes. |

<br>

---

<br>

### 6.7 Telemetry, Contact & Issue Reporting
- **Anonymous Telemetry:** 100% anonymous ping containing OS type and version number only (no audio or personal data is ever collected).
- **Direct Support Form:** Enter an issue title and description, attach screenshots, and send a diagnostic ticket with log files directly to the developer with one click.

<br>

---

<br>

## 7. Step-by-Step Practical Recipes ("How do I...?")

<br>

---

<br>

### Recipe A: Cutting Video Based on a Written Script
**Goal:** You recorded a video reading from a script and made several mistakes or repeated sentences. You want to keep only the good takes that match your script.

```mermaid
sequenceDiagram
    autonumber
    actor User as Video Editor
    participant BW as BadWords
    participant DR as DaVinci Resolve
    
    User->>BW: Paste original script into "Script Analysis" panel
    User->>BW: Click "Analyze (Compare)"
    BW->>BW: Fuzzy Anchor Match & Deviation Detection
    Note over BW: Retakes marked Blue, Errors marked Red
    User->>BW: Review text & hit "Assemble"
    BW->>DR: Create clean timeline with only successful takes!
```

1. Launch BadWords on your raw recording timeline.
2. In the left sidebar, open the **Script Analysis** tab.
3. Paste your script into the box or click **`Import Script`** to load your `.docx` or `.pdf`.
4. Click **`Analyze (Compare)`**.
5. BadWords automatically aligns the transcript with the script:
   - Repeated attempts are painted **Blue**.
   - Bloopers and misspoken words are painted **Red**.
6. Skim the text. If you prefer a take the AI marked blue, use the **Eraser (`4`)** on that take and paint the other one **Blue (`2`)**.
7. Click **`Assemble`** to create your clean cut.

<br>

---

<br>

### Recipe B: Removing Retakes & False Starts without a Script
**Goal:** You recorded a casual podcast or gameplay video without any script and want to remove false starts and stumbles automatically.

1. Launch BadWords and click **`Analyze`**.
2. Open the **Script Analysis** tab in the sidebar.
3. Click **`Analyze (Standalone)`**.
4. BadWords will scan the transcript for acoustic repetitions (e.g. *"In today's video we... In today's video we will explore..."*).
5. The earlier, discarded attempts will turn **Blue**.
6. Click **`Assemble`**.

<br>

---

<br>

### Recipe C: Fast Silence Cut without Transcribing
**Goal:** You have a 2-hour podcast and just want to remove all silent pauses instantly without waiting for speech-to-text.

1. Open BadWords from DaVinci Resolve.
2. At the bottom of the Welcome Screen, click **`Simple Silence Detection`**.
3. Set your threshold (Default `-42.0 dB` works for most microphones).
4. Ensure **`Cut silence directly`** is toggled ON.
5. Click **`Run Detection`**.
6. Within seconds, a newly rippled, tightened timeline appears in Resolve!

<br>

---

<br>

### Recipe D: One-Click Filler Word Purge
**Goal:** Remove all hesitation sounds (*"uh"*, *"um"*, *"like"*) from an interview.

1. Open BadWords and transcribe your timeline.
2. Filler words are automatically highlighted in **Red**.
3. Open the **Filler Words** tab in the sidebar if you want to add custom words (e.g. slang or recurring filler phrases).
4. In the **Assembly** panel, ensure **Auto-Cut** is enabled for **Red (Errors)**.
5. Click **`Assemble`**. All filler words are cleanly removed from the timeline.

<br>

---

<br>

### Recipe E: Working with Difficult Words, Names & Jargon
**Goal:** You are editing a technical tutorial containing code snippets, system paths, or brand names that standard AI models mishear.

1. On the Welcome Screen, turn ON **`More accurate transcription`**.
2. Paste your reference text or documentation into the slide-out script box.
3. Click **`Analyze`**.
4. BadWords extracts the technical terms, feeds them directly into Whisper's prompt layer, and delivers a perfect verbatim transcription on the first pass!

<br>

---

<br>

## 8. Shortcuts Cheat Sheet & FAQ

<br>

---

<br>

### Default Keyboard & Mouse Shortcuts

| Shortcut | Action | Scope |
| :--- | :--- | :--- |
| **`1`** | Select Red Marker (Errors / Fillers) | Transcript Editor |
| **`2`** | Select Blue Marker (Retakes) | Transcript Editor |
| **`3`** | Select Green Marker (Typos) | Transcript Editor |
| **`4`** | Select Eraser (Clear Marks) | Transcript Editor |
| **`Ctrl` + Left Click** | Jump to Word (Scrub Resolve & Audio Player) | Transcript Editor |
| **`Space`** | Play / Pause Audio Preview | Global |
| **`Left Arrow`** | Skip 2 seconds backward | Audio Player |
| **`Right Arrow`** | Skip 2 seconds forward | Audio Player |
| **`Ctrl + F`** | Open Transcript Search Overlay | Transcript Editor |
| **`Enter` / `Shift + Enter`** | Next / Previous Search Result | Search Overlay |
| **`Escape`** | Close Search / Open Settings Dialog | Global |

<br>

---

<br>

### Frequently Asked Questions (FAQ)

#### Q: Does BadWords overwrite or modify my original timeline?
**A:** **No, never.** BadWords is 100% non-destructive. Every time you click *Assemble* or *Cut Now*, BadWords generates a brand new timeline copy (e.g. `Timeline_Edit 1`, `Timeline_Edit 2`). Your original timeline remains completely untouched.

#### Q: Why did the first transcription take longer than usual?
**A:** On the first run with a new AI model, BadWords downloads the model weights and optimizes them for your GPU/CPU architecture. All subsequent transcriptions run locally from cache at maximum hardware speed.

#### Q: Are my audio files or transcripts uploaded to any cloud server?
**A:** **No.** All speech recognition, silence processing, and timeline manipulation execute 100% locally on your computer.

#### Q: What if a cut is slightly too tight or cuts a breath?
**A:** In Settings -> **Audio Sync**, slightly increase **Padding (s)** (e.g. to `0.05s` or `0.10s`) or adjust **Offset (s)**.

<p align="center">
  <b>BadWords - Cleaner Timelines, Faster.</b><br>
  <i>Developed by Szymon Wolarz • Licensed under the MIT License</i>
</p>
