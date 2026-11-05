# <img src="repo/banner.svg" alt="BadWords Logo" height="52" valign="middle" />&nbsp;
**Cleaner Timelines, Faster. Simpler Rough-Cutting for DaVinci Resolve.**

<br>

<p align="center">
  <img src="repo/preview.png" alt="BadWords Preview" width="100%">
</p>

<br>

<p align="center">
  <a href="#windows"><img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=data:image/svg%2Bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxwYXRoIGQ9Ik0wIDBoMTEuMzc3djExLjM3Mkgwem0xMi42MjMgMEgyNHYxMS4zNzJIMTIuNjIzek0wIDEyLjYyM2gxMS4zNzdWMjRIMHptMTIuNjIzIDBIMjRWMjRIMTIuNjIzeiIvPjwvc3ZnPg==" alt="Windows"><img src="https://img.shields.io/badge/SUPPORTED_✅-333333?style=for-the-badge" alt="Supported"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="#macos"><img src="https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white" alt="macOS"><img src="https://img.shields.io/badge/SUPPORTED_✅-333333?style=for-the-badge" alt="Supported"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="#linux-any-distro"><img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux"><img src="https://img.shields.io/badge/SUPPORTED_✅-333333?style=for-the-badge" alt="Supported"></a>
</p>

<p align="center">
  <a href="#installation"><img src="https://img.shields.io/badge/INSTALLATION-333333?style=for-the-badge&logo=gnubash&logoColor=white"><img src="https://img.shields.io/badge/QUICK_SETUP-168f4d?style=for-the-badge" alt="Quick Setup"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="docs/USER_GUIDE.md"><img src="https://img.shields.io/badge/DOCUMENTATION-333333?style=for-the-badge&logo=gitbook&logoColor=white"><img src="https://img.shields.io/badge/USER_MANUAL-168f4d?style=for-the-badge" alt="User Manual"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://buymeacoffee.com/badwords" target="_blank"><img src="https://img.shields.io/badge/SUPPORT-333333?style=for-the-badge&logo=buymeacoffee&logoColor=FFFFFF"><img src="https://img.shields.io/badge/BUY_ME_A_COFFEE-168f4d?style=for-the-badge" alt="Buy Me A Coffee"></a>
</p>

<br>

> [!IMPORTANT]
> ### ⚠️ BadWords v4 — Active Development & Early Access Notice
>
> **BadWords v4 is still actively in development** and does not yet have every single feature I originally envisioned. 
> 
> **Why release it now?**  
> The previous release (v3.2.4) came out quite a while ago, and more critically, it became completely unusable on fresh installations due to a breaking upstream change in PyAV (which removed an internal argument used by Faster-Whisper). At the same time, an immense number of upgrades, optimizations, and new tools had already accumulated in my local development tree. Rather than holding everything back, I worked hard to bring this version into a solid, functional state so that everyone can actually use BadWords again.
> 
> **Because v4 is in active development, encountering bugs, quirks, or rough edges IS possible.**  
> If you run into **ANY bug, crash, or unexpected behavior**, or if something feels **unintuitive, confusing, or awkward and uncomfortable to use** — **I warmly encourage and genuinely ASK you to reach out!** Please open an [Issue on GitHub](https://github.com/veritus-git/BadWords/issues) or email me directly at **[badwords.git@gmail.com](mailto:badwords.git@gmail.com)**.
> 
> As an 18-year-old solo developer, it is impossible for me to test every conceivable hardware setup, operating system configuration, audio format, and DaVinci Resolve project edge-case on my own. Your bug reports, feedback, and suggestions are what allow me to fix issues quickly, add new features, and keep pushing BadWords forward. If anything at all is unclear about how to use the app, please don't hesitate to reach out!

<br>

## <img src="repo/icons/info.svg" alt="Info" width="30" height="30" valign="text-bottom"> What is it?

**BadWords** is a plugin-app for DaVinci Resolve built for anyone dealing with dialogue-heavy footage (podcasts, talking heads, gameplays). Instead of scrubbing through hours of audio on a timeline to find silences, retakes, and filler words, BadWords transforms your workflow into an easy text-editing experience.

It uses local AI (Faster-Whisper) to give you a full transcript of your audio. You can then color-code mistakes, compare it against your original script, and with one click, send the processed timeline back to Resolve — complete with markers and cuts. 

BadWords does **80% of the tedious work for you** (cutting tight silences, marking obvious bloopers), leaving only the final polishing to you.

## <img src="repo/icons/sparkles.svg" alt="Key Features" width="30" height="30" valign="text-bottom"> Key Features

Here is what makes BadWords stand out from other editing tools:

* **True Verbatim Transcription:** BadWords uses heavily customized prompt engineering, parameters, and chunking with Faster-Whisper to force the AI into true "verbatim" mode. It catches every tiny stutter, 'um', and false start with a precision unmatched in the open-source space. What you hear is exactly what you see in the text, making it incredibly easy to spot deviations visually. And if the audio is completely garbled, it conveniently marks it as `(...)` (Inaudible) for you to check manually.

* **Smart Script Comparison:** If you record based on a script, this feature is a massive time saver. Paste your original script into BadWords, and the advanced algorithm will instantly compare it against your recorded audio. The magic here is that it visually highlights *only* the noteworthy fragments that differ from your script - like spontaneous deviations or repeated retakes. By instantly seeing what went wrong, you don't have to listen to the entire audio track anymore. You can completely skip the perfect 1:1 matches and focus your attention *only* on the parts that actually need editing! (Plus, it automatically scrapes technical terms from your script to feed to the AI, dramatically improving transcription accuracy on technical terms).

* **IDE-Like Text-Based Editing:** Say goodbye to endlessly scrubbing through DaVinci Resolve timelines. BadWords shifts the entire editing paradigm by letting you edit your video exactly like a text document in an IDE. You simply read the transcript, visually highlight the mistakes with different colors, and hit "Assemble". The app instantly translates your text-based changes into perfect, frame-accurate cuts directly on your timeline.

* **Convenient Silence Detection:** Yes, DaVinci Resolve now has its own silence cutter, but BadWords does it differently. Before scanning for silence, BadWords automatically normalizes the audio in the background. This means speech volume is leveled out, making the default silence threshold (-42dB) incredibly precise without you having to tweak it for every single project - just flip a switch. It even features "island absorption": random short noises like a desk bump or a quick cough get swallowed up and cut out as silence anyway.

## <img src="repo/icons/workflow.svg" alt="How it works" width="30" height="30" valign="text-bottom"> How it works

1. **Select & Transcribe:** Launch BadWords directly from Resolve (or run in Standalone Mode by picking media files from disk), select your audio tracks, and hit Analyze. The AI transcribes everything.
2. **Edit like a Document:** Your audio opens as text in an IDE-inspired editor. You (or the algorithm) can paint words with different colors:
   * **Red** — Filler words / obvious mistakes to remove
   * **Blue** — Retakes / duplicates
   * **Green** — Typos / close matches
3. **Compare to Script or Analyze Standalone:** If you have an original script, BadWords can automatically compare it against your transcript to highlight deviations. No script? No problem! Use the Standalone Analysis to automatically detect stutters, false starts, and retakes from the raw audio.
4. **Assemble or Export Timeline:** Once you're done playing with the text, hit Assemble (or Export). BadWords automatically generates a **brand new, clean timeline** inside Resolve with all your cuts and color markers applied perfectly, or exports a universal XML/EDL timeline for your NLE of choice.

<p align="center">
  <img src="repo/heatmap_preview.png" alt="BadWords Heatmap" width="85%">
</p>

## <img src="repo/icons/circle-check.svg" alt="Why BadWords" width="30" height="30" valign="text-bottom"> Why use BadWords?

- **Massive Time Saver:** Turns hours of manual clicking and scrubbing into a quick visual review. The silence detection alone is highly precise and will save you tons of time.
- **100% Local & Private:** No cloud processing, no subscriptions, no data harvesting. All processing happens entirely on your own hardware (except for optional, anonymous telemetry).
- **Non-Destructive Versioning:** BadWords never edits your original timeline. Every time you click "Assemble", it creates a new timeline copy.
- **Timeline Heatmap Approach:** AI isn't perfect; it might miss tiny stutters. That's why BadWords is designed to give you an overview (a "heatmap") of your clip qualities using Resolve's native colorful markers, letting you finalize the cuts manually exactly where needed.

---

## <img src="repo/icons/flame.svg" alt="What's New" width="30" height="30" valign="text-bottom"> What's New in 4.0?

Version 4.0 is a monumental leap forward for BadWords. What started as an urgent update to fix breaking upstream dependencies and improve timeline assembly turned into the largest overhaul in the project's history. Here is a breakdown of the most important new features, workflows, and performance enhancements designed for you:

* **Fully Functional Standalone Mode (No DaVinci Resolve Required!):**
  You no longer need DaVinci Resolve running to use BadWords! You can now load media files (video or audio) directly from your disk or drag and drop multiple files into the standalone file queue.
  * **Multi-Format Timeline Export:** Export your cut project directly into 4 industry-standard timeline formats:
    * **Final Cut Pro 7 XML (`.xml`)** — Universal format for DaVinci Resolve, Adobe Premiere Pro, and more.
    * **Final Cut Pro XML (`.fcpxml`)** — For modern Final Cut Pro workflows.
    * **OpenTimelineIO (`.otio`)** — The modern open-source standard for timeline interchange.
    * **CMX 3600 EDL (`.edl`)** — Classic linear edit decision list.
  * **Lightweight Background Proxies:** Automatically generates fast 360p video preview proxies so you can scrub and preview massive 4K/8K camera footage with zero lag.
  * **Conforming & Timecode Support:** Automatic sequence framerate conformity, Broadcast Wave (BWF) timecode conforming, multi-track audio preservation, and stereo downmix/pan routing.

* **Revolutionized Text Marking: Marquee Box Selection & Brush Painting:**
  * **Desktop-Style Marquee Box Selection:** Selecting and marking dialogue is now faster and more intuitive than ever. Just click and drag your cursor over words (just like drawing a selection rectangle on your computer desktop!) to highlight and color-code chunks of words in bulk.
  * **Configurable Mouse Modes:** The classic word-by-word painting mode hasn't gone anywhere! You can seamlessly switch between **Marquee Selection** and **Brush Painting**, and freely configure which action is bound to the Left vs. Right Mouse Button in Settings.
  * **Live Strikethrough Cut Preview:** Words marked for deletion are now visually struck through with a continuous line directly in the transcript editor, giving you an immediate preview of what Assemble will remove.

* **Advanced Silence Detection with Real-Time In-RAM Tuning (<5ms):**
  The Silence Detection sidebar panel has been thoroughly redesigned to give you complete creative control over your pacing:
  * **Independent Controls:** Separate switches for **Detect and cut silence** vs **Detect and mark silence**.
  * **Decibel Threshold & Duration Sliders:** Dedicated sliders for Silence Threshold (-60 dB to 0 dB), Min Silence Duration, and Min Clip Duration.
  * **Pauses to Remove (%):** Choose to eliminate 100% of dead air or retain a custom percentage of pauses for a natural conversational flow.
  * **Keep Pause Padding (s):** Adds a customizable safety buffer (default: 0.10s) before and after speech to guarantee you never clip the start or trailing end of a word.
  * **Instant In-RAM Recalculation:** Adjusting any slider recalculates silence cuts directly from RAM waveform peaks in **under 5ms** without re-running FFmpeg or freezing the interface. You get live pause counters and duration stats (`226 pauses marked - 3:37 (26%)`) updated in real time!

* **Interactive Timeline Preview with Real-Time Cut Skipping:**
  The bottom audio/video player has been upgraded into a comprehensive Timeline Preview:
  * **Waveform & Progressive Cut Hatching:** Visualizes your entire timeline waveform with progressive cut hatching (dynamic diagonal stripes scaling with zoom level) and rounded clip boundary notches.
  * **Real-Time Cut Skipping:** Hit Play, and the player will dynamically skip over all cut and silence zones in real time! You can now listen to exactly how your rough-cut will sound before assembling or exporting.
  * **Integrated Video Preview:** Scrub and preview video clips seamlessly alongside the waveform, with playhead clamping, click-to-seek navigation, and persistent preview retention across assembly passes.

* **Apple Silicon Hardware Acceleration: ~11x Faster via `mlx-whisper` (macOS):**
  Mac users rejoice! On Apple Silicon (M1, M2, M3, M4, M5), BadWords now utilizes native Apple Metal GPU acceleration through `mlx-whisper`.
  * **Up to ~11x faster** than CPU faster-whisper (transcribing multi-minute audio in seconds rather than minutes).
  * Fully preserves verbatim prompt engineering, sound-island clustering, and filler word detection.
  * Automatically falls back to CPU faster-whisper if MLX is unavailable.
  * Includes CPU topology optimizations for Intel and Apple Silicon to avoid E-core stalls and thread contention.

* **Timeline Assembly Paradigm Shift: FCP7 XML Default + Native DRT Option:**
  * **FCP7 XML by Default:** BadWords now defaults to Final Cut Pro 7 XML assembly. This eliminates DaVinci Resolve's long-standing `.drt` limitation where cut audio and video tracks became unlinked. In XML, clips remain linked and synchronized out of the box!
  * **Full DaVinci Free 21.1+ Parity:** Completely circumvents Blackmagic's decision to block `.drt` script imports in DaVinci Resolve Free 21.1+.
  * **Native `.drt` Still Supported:** DaVinci Resolve Studio users (and Free < 21.1) who want 100% preservation of Color grades, Fusion comps, Fairlight plugins, and OFX can re-enable native `.drt` assembly in Settings at any time.

* **Chunked Live-Streaming Transcription & Zero-Lag UI:**
  * Watch your transcript materialize in real-time chunks with an animated TopStatusIsland indicator and token reveal.
  * Powered by an O(1) incremental layout rendering engine with dirty-rect painting, keeping the app buttery-smooth even with multi-hour timelines.
  * GPU yield micro-pauses prevent GPU starvation and keep your desktop responsive while transcribing.

* **Fix for Upstream PyAV 19 Crash:**
  * Fixed the critical upstream breaking change where PyAV 19.0.0 removed the `metadata_errors` argument from `av.open()`, which caused fresh installs of BadWords 3.2.4 and `faster-whisper` to crash with a `TypeError`.
  * Injected runtime compatibility shims and pinned `av<19` across all installers and updaters.

* **Dedicated "Colors in this edit" Panel & UI Overhaul:**
  * A dedicated Colors panel in the sidebar with an active color legend, color counters, and one-click bulk removal.
  * Dynamic header spacing and customizable UI panel visibility.
  * High-DPI and resolution-independent UI scaling across small and ultra-wide monitors.
  * Added Simplified Chinese (`zh`) UI translation, bringing official localization to 11 languages.

* **Modern Cross-Platform Rust GUI Installer & Standalone Launchers:**
  * Brand-new graphical setup wizard built in Rust (egui) featuring dual animated progress bars, live pip output streaming, system registry integration, and automatic fallback to terminal setup.
  * Native single-binary standalone desktop launchers for Windows (`.exe`), Linux (ELF), and macOS (Mach-O).

---

<a id="installation"></a>
## <img src="repo/icons/wrench.svg" alt="Installation & Setup" width="30" height="30" valign="text-bottom"> Installation & Setup

I know that installing plugins can sometimes be a headache. That's why I made BadWords use a **unified, one-click installation process** that looks and works exactly the same on every operating system. You don't need to manually download zip files, configure Python paths, or install dependencies - the setup handles everything automatically.

In version 4.0, BadWords features a **brand new Graphical User Interface** for easier and more accessible instalation process - **it's as easy as it gets!**

### <img src="repo/icons/download.svg" alt="Installation Process" width="24" height="24" valign="text-bottom"> The Installation Process

1. **Copy the command** for your specific operating system from the [section below](#-option-1-automated-setup-commands-recommended).
2. **Paste the command** into your terminal (PowerShell on Windows, Terminal on macOS/Linux) and press **Enter**.
3. The **BadWords Setup** window will appear
4. Skip Welcome Screen with `Enter`, then **select `1`** (you can click with your mouse or simply press **`1`** on your keyboard).

<p align="center">
  <img src="repo/gui_setup_preview.png" alt="BadWords GUI Setup Preview" width="70%">
</p>

5. **Confirm the install path** (~4GB for core files + AI models), or browse/type in a custom destination path.
6. Wait for the setup to finish. When it's done you can simply Launch BadWords as normal desktop app or open it from DaVinci Resolve: **Workspace** → **Scripts** → **BadWords**

<br>

> As you can see on the screenshot above, the installer menu gives you **5** other options besides standard installation. In the future, you can use the exact same command to *Update* your app (if automatic update fails), *Repair* broken files, *Move* the installation to another drive, *Reinstall* or completely *Uninstall* BadWords!

> [!NOTE]
> ### 🛡️ Security Notice (Windows SAC & macOS Gatekeeper)
> BadWords is a **100% free and open-source project created by an independent solo developer**. Since I don't have an expensive $400/yr commercial code-signing certificate, security filters like **Windows 11 Smart App Control** or **macOS Gatekeeper** may flag the newly compiled graphical binary.
> 
> If that happens, the setup script **automatically detects the block and gives you an option to run the Terminal Setup (option 1)**:
>
> <p align="center">
>   <img src="repo/sac_notice.png" alt="Security Fallback Notice" width="70%">
> </p>
>

### <img src="repo/icons/terminal.svg" alt="Terminal Setup" width="24" height="24" valign="text-bottom"> Fallback: Terminal Setup

If your system blocks the graphical window, the terminal setup offers **100% of the exact same features and tools**:

<p align="center">
  <img src="repo/cli_setup_preview.png" alt="Terminal Setup Preview" width="65%">
</p>

1. **Press `1`** for standard installation.
2. Choose whether to create **Desktop and Start Menu shortcuts** (`Y/n`).
3. Provide a path where you want BadWords (~4GB) and your chosen AI models to be installed, or simply **press Enter** to use the default location.
4. Wait for the download and setup to complete.
5. Press **Enter** to launch BadWords (or **n** to skip it).

<br>

---

<a id="automated-setup-commands"></a>
### <img src="repo/icons/terminal.svg" alt="Option 1" width="24" height="24" valign="text-bottom"> Option 1: Automated Setup Commands (Recommended)
The absolute easiest way to start the setup. It securely downloads and runs the lightweight setup wizard directly from this repository.

<br>

#### <img src="repo/icons/windows.svg" alt="Windows" width="20" height="20" valign="text-bottom"> Windows
Open the Start Menu, search for **PowerShell**, open it, paste the following command, and press **Enter**:

```powershell
irm "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/windows-setup.ps1" | iex
```

<br>

#### <img src="repo/icons/apple.svg" alt="macOS" width="20" height="20" valign="text-bottom"> macOS
Open the **Terminal** app (search with Spotlight `Cmd + Space`), paste the following command, and press **Enter**:

```bash
curl -fsSL "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/mac-setup.sh" | bash
```

<br>

#### <img src="repo/icons/linux.svg" alt="Linux" width="20" height="20" valign="text-bottom"> Linux (Any Distro)
Open your terminal, paste the following command, and press **Enter**:

```bash
curl -fsSL "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/linux-setup.sh" | bash
```

<br>

---

### <img src="repo/icons/package.svg" alt="Option 2" width="24" height="24" valign="text-bottom"> Option 2: Manual Locall Setup
Don't like running online terminal commands? You can download the pre-compiled standalone installer directly from the [Releases page](https://github.com/veritus-git/BadWords/releases/latest):

**Windows:**
  1. Download `badwords-setup-windows.exe`.
  2. Double-click to run. *(If blocked by SmartScreen: right-click the file → **Properties** → check **Unblock** at the bottom → click **Apply**).*

**macOS:**
  1. Download `badwords-setup-macos`.
  2. Open Terminal in your download folder, remove the macOS quarantine attribute, and launch the installer:
     ```bash
     xattr -d com.apple.quarantine badwords-setup-macos && chmod +x badwords-setup-macos && ./badwords-setup-macos
     ```

**Linux:**
  1. Download `badwords-setup-linux`.
  2. Double click to run or (if it fails) open terminal in the download folder, make it executable, and run:
     ```bash
     chmod +x badwords-setup-linux && ./badwords-setup-linux
     ```

---

### <img src="repo/icons/shield-check.svg" alt="Safe" width="24" height="24" valign="text-bottom"> Wait, are these terminal commands actually safe?
Pasting `curl` or `iex` commands can trigger red flags for cautious users. Here is why BadWords uses them and why you don't need to worry:

* **Zero System Interference:** These commands **do not require Administrator / root privileges** (no `sudo` or "Run as Administrator" needed). Everything is downloaded into a safe, isolated directory in your local user folder.
* **Always Up-to-Date:** Fetching the script directly from GitHub ensures you are always running the latest version of the installer, so you don't have to deal with broken links or outdated dependencies.
* **100% Transparent:** The commands point directly to plain-text files hosted right here on GitHub. You can click the *View script* links above to read every single line of code before pressing Enter!

---

## <img src="repo/icons/launch.svg" alt="Launching" width="30" height="30" valign="text-bottom"> Launching & Compatibility by DaVinci Version

Depending on whether you use **Standalone Mode**, **DaVinci Resolve Studio**, or **DaVinci Resolve Free**, and which version you have installed, here is how you can launch and connect BadWords:

* **Standalone Mode (No DaVinci Resolve Needed):**  
  *BadWords can now run completely independently from DaVinci Resolve!*
  * **How to use:** Launch BadWords directly from your Desktop, Start Menu, or terminal. Drag and drop audio or video files directly into the file queue.
  * **Export:** Cut your dialogue, tune silence, and export ready-to-import timelines to **Final Cut Pro 7 XML (`.xml`)**, **Final Cut Pro XML (`.fcpxml`)**, **OpenTimelineIO (`.otio`)**, or **CMX 3600 EDL (`.edl`)** for DaVinci Resolve, Adobe Premiere Pro, Final Cut Pro, or any other NLE!

* **DaVinci Resolve Studio (Any version):**  
  *Full functionality with zero limitations.*
  * **Option A (Desktop App):** Launch BadWords directly from your Desktop / Start Menu or terminal. Ensure that in DaVinci Resolve *Preferences → System → General*, **External scripting using** is set to **Local**. BadWords connects automatically via native IPC.
  * **Option B (Embedded Mode):** Inside DaVinci Resolve, click **Workspace** → **Scripts** → **BadWords** to launch it directly within Resolve.
  * **Timeline Assembly:** Defaults to the **FCP7 XML pipeline** because it natively preserves audio-to-video clip linking. If you need to preserve Resolve-specific Color Page grades, Fusion comps, Fairlight FX, or plugins, you can switch to the native `.drt` pipeline in Settings with a single click.

* **DaVinci Resolve Free (v21.0 and older):**  
  *External scripting is locked by Blackmagic in the free edition, but embedded execution works.*
  * **Option A (Embedded Mode):** Inside DaVinci Resolve, click **Workspace** → **Scripts** → **BadWords**.
  * **Option B (Bridge Mode):** In Resolve, click **Workspace** → **Scripts** → **BadWords Bridge**, then launch BadWords from your Desktop / Start Menu.
  * **Timeline Assembly:** Defaults to **FCP7 XML** with preserved clip linking; native `.drt` assembly is available as an option in Settings.

* **DaVinci Resolve Free (v21.1+):**  
  *In v21.1+, Blackmagic blocked both external scripting AND direct embedded Python scripts in the free edition.*
  * **Bridge Mode (The only way to connect):**
    1. Open DaVinci Resolve and load your project.
    2. Click **Workspace** → **Scripts** → **BadWords Bridge** (runs once per Resolve session).
    3. Launch BadWords from your Desktop or Start Menu - it connects automatically using the Lua bridge!
  * **Timeline Assembly:** Powered by the robust **FCP7 XML assembly pipeline** (because Blackmagic disabled `.drt` script exports in Free 21.1+).

---

### <img src="repo/icons/workflow.svg" alt="Assembly Pipeline" width="24" height="24" valign="text-bottom"> Timeline Assembly: FCP7 XML (Default) vs. Native DRT (Optional)

> [!NOTE]
> **Evolution of Timeline Assembly in v4.0:**  
> Previously, BadWords relied almost entirely on manipulating DaVinci's native `.drt` (DaVinci Resolve Timeline) file for assembly.  
> Starting in **v4.0**, BadWords has transitioned to **Final Cut Pro 7 XML (`.xml`) as the default and recommended assembly pipeline**.
> 
> **Why switch to XML as the default?**
> 1. **Native Clip Linking Preservation:** When importing a `.drt` timeline assembled via script, DaVinci Resolve has an internal limitation where cut audio and video clips lose their link on the timeline, unlinking them and causing massive editing friction. The XML pipeline natively preserves clip linking — your video and audio tracks remain linked and locked together!
> 2. **Resolve Free 21.1+ Compatibility:** Blackmagic completely blocked `.drt` script exports and imports in DaVinci Resolve Free 21.1+. The XML pipeline ensures seamless rough-cutting for all users regardless of Resolve version or license.
> 
> **Do you still want Native `.drt`?**  
> **Yes, it is still here!** Users of **DaVinci Resolve Studio** (and Free versions older than 21.1) can easily switch back to the `.drt` pipeline at any time directly in Settings (*Settings → Assembly → uncheck "Force FCP7 XML Assembly"*). If your workflow relies on preserving complex DaVinci-specific elements already applied to your clips before cutting (such as Color Page node trees & grades, Fusion compositions, Fairlight audio FX / VST plugins, or Resolve OFX), `.drt` remains fully supported.

| Timeline Element / Feature | FCP7 XML Pipeline<br>*(Default in v4.0)* | Native .drt Pipeline<br>*(Studio & Free <21.1 Option)* |
| :--- | :---: | :---: |
| **Audio-Video Clip Linking** | ✅ **100% Linked & Preserved** *(Audio stays locked to video)* | ⚠️ **Unlinked** *(Resolve API limitation: cut audio & video clips become unlinked)* |
| **Cuts, Ripple-Cut & In/Out Points** | ✅ 100% frame-accurate | ✅ 100% frame-accurate |
| **Multi-Track Video & Audio** *(V1, V2..., A1, A2...)* | ✅ Fully Preserved | ✅ Fully Preserved |
| **Media Files & Audio Waveforms** | ✅ Fully Preserved | ✅ Fully Preserved |
| **Proxy Media & Playback** | ✅ Fully Supported *(Seamless relink to existing Media Pool proxies)* | ✅ Fully Supported *(Playback → Prefer Proxies)* |
| **Clip Marker Colors on Timeline** | ✅ Preserved & Re-applied | ✅ Preserved & Re-applied |
| **Basic Transforms** *(Position, Zoom, Crop, Opacity)* | ✅ Fully Preserved | ✅ Fully Preserved |
| **Fractional Frame Rates** *(23.976, 29.97, 59.94 fps)* | ✅ 100% Frame-Accurate (Zero Drift) | ✅ 100% Frame-Accurate |
| **Track Filtering & Selection** | ✅ Fully Supported | ✅ Fully Supported |
| **Color Page Grading & Node Trees** | ⚠️ **Not Carried Over** *(Clips point to raw source files; grade after cutting or use Remote Grades)* | ✅ **100% Preserved** *(Nodes, LUTs, Qualifiers)* |
| **Fusion Page Compositions on Clips** | ⚠️ **Not Carried Over** *(XML specification does not support Fusion nodes)* | ✅ **100% Preserved** |
| **Fairlight Audio FX & VST Plugins** | ⚠️ **Not Carried Over** | ✅ **100% Preserved** *(EQ, Dynamics, VST)* |
| **Resolve OFX & Neural Engine** *(Magic Mask, Blur)* | ⚠️ **Not Carried Over** | ✅ **100% Preserved** |
| **Compound Clips & Nested Timelines** | ⚠️ May be flattened or imported as blank generators | ✅ **100% Preserved** |

> [!TIP]
> **Summary & Workflow Recommendation:**  
> If you run BadWords on **raw footage (A-roll, talking-head videos, raw podcasts, interviews, gameplays)** before color grading and applying VFX — **the FCP7 XML pipeline is strictly superior and recommended**, because your cuts will keep audio and video clips linked together.  
> If you have already created complex Color node trees or Fusion animations on your clips prior to rough-cutting, those Resolve-specific nodes are preserved in Studio (via `.drt`), which can be activated with a single click in Settings!

> **Important:** Your *first launch*, *first transcription*, and *first analysis* will take considerably longer than usual as the AI model completes its initial setup for your hardware. **All subsequent transcriptions are typically much faster.** <br>
> **Note:** Whisper models perform best with English and major European languages. Other languages are supported but might yield lower precision.

---

## <img src="repo/icons/list-checks.svg" alt="Requirements" width="30" height="30" valign="text-bottom"> Requirements
- **App:** DaVinci Resolve (Free or Studio, including Mac App Store edition)
- **Hardware:** NVIDIA GPU highly recommended for acceleration (CPU-only mode is available).
- **Disk Space:** ~4GB free space for the app, plus 1–5GB depending on your chosen AI models.

---

## <img src="repo/icons/user.svg" alt="About Me" width="30" height="30" valign="text-bottom"> A little about me & the project

Hi! I am Simon - the 18 year old solo-developer of BadWords. This project started totally randomly. It wasn't planned, it wasn't supposed to become a full-on program. Heck! It wasn't supposed to even leave my computer... but somehow it became the biggest and most advanced project I've made.
It's probably not the best, the fastest, the cleanest, or the most useful thing you'll see... but while making it, I realized that it could actually be useful not only to me - but for many others.
So... I made it for everyone.
It is still in development, it probably has a lot of bugs, "holes", crashes on edge-cases and unoptimized functions. So if you ever stumble upon any problems - feel free to open an Issue or contact me directly.
Just by using BadWords and sending feedback, you are contributing to this project's community :)

**Support the Project!**  
If BadWords saved you even a bit of time, consider buying me a coffee. It helps me maintain the project between school and life!

<a href="https://www.buymeacoffee.com/BadWords" target="_blank"><img src="https://img.buymeacoffee.com/button-api/?text=Bribe%20me%20with%20coffee&emoji=%E2%98%95&slug=BadWords&button_colour=0b8e46&font_colour=ffffff&font_family=Inter&outline_colour=ffffff&coffee_colour=FFFFFF" alt="Bribe Me With Coffee" height="50px"/></a>

---

## <img src="repo/icons/users.svg" alt="Contribute & Contact" width="30" height="30" valign="text-bottom"> Contribute & Contact

This is an open-source project. Feel free to open issues or pull requests to improve the tool!

[![Reddit](https://img.shields.io/badge/Reddit-FF4500?style=for-the-badge&logo=reddit&logoColor=white)](https://www.reddit.com/message/compose/?to=KoxSwYT)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:badwords.git@gmail.com)

[License (MIT)](LICENSE)  
*Note: This tool is not affiliated with Blackmagic Design. Use at your own risk.*
