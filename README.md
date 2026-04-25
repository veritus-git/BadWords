# BadWords - Cleaner Timelines, Faster
Automatically **detect, mark and/or remove filler words, silence, and retakes** <br>
in DaVinci Resolve using OpenAI Whisper, FFmpeg and Python.

<br>
![Preview](assets/editor_preview.png)

## Quick access shortcuts:
### Installation & Uninstalation guides: <br> [Linux (any distro)](assets/Linux%20GUIDE.md) <br> [Windows](assets/Windows%20GUIDE.md)
# [Download Latest BadWords Release](https://gitlab.com/badwords/BadWords/-/releases/permalink/latest)<br>

[![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)]()
[![Download](https://img.shields.io/badge/Supported_✅-333333?style=for-the-badge)](link)

[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)]() 
[![Download](https://img.shields.io/badge/Supported_✅-333333?style=for-the-badge)](link)

[![macOS](https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white)]() [![Download](https://img.shields.io/badge/Soon!-333333?style=for-the-badge)](link)






<a href="https://buymeacoffee.com/badwords" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" align="top" width="30%" style="margin-left: 20px; margin-bottom: 20px;" alt="Logo"></a>

## 🛠️ What's new in 2.0.3?

- Percentage Progress Bar: Transcription now shows a precise, real-time percentage progress bar so you always know exactly how far along Whisper is.
- Full Uninstallers: Both Windows and Linux now ship with complete, scorched-earth uninstallers that cleanly remove all associated files, hidden folders, and registry entries — no leftovers.
- Linux Install Path Selection: The Linux installer now lets you choose a custom installation path instead of forcing a single fixed location.
- Geolocation opt-out in Telemetry: You can now disable geolocation in the optional telemetry ping. Opting out strips all location data from the anonymous install/update signal.
- Subprocess stability fixes: Resolved edge-case crashes and race conditions in background subprocess handling for more reliable transcription runs.
- Installer optimisations: Both installers are smarter — the Linux script skips redundant PyTorch downloads when updating, and the GPU acceleration mode is auto-detected on updates so you don't have to pick it again.


## 🚀 Features

- **Smart Detection** - Finds filler words (umm, ahh), silence, and repeated sentences (still in development) using local AI. 
- **DaVinci Integrated** - Runs directly on Davinci Resolve as a Workflow Script, using only local resources
- **Safe & Clean** - Creates isolated environment, keeping your system packages safe and clean.
- **GPU Accelerated** - Utilizes your GPU for fast transcription (NVIDIA Cards Supported Only - for now!)
- **Interactive Review** - Review cuts before applying them to the timeline.
- **Heat map** - Mark timeline with colors instead of invasive rough cutting

![Timeline Heatmap](assets/heatmap.png)

## ⭐️ Core Capabilities

- **Script Comparison:** Paste your script to find deviations or missing lines (algorithm in development).
- **Filler Word Removal:** Auto-cut "yyy", "eee", "umm" and custom words.  
- **Silence Removal:** Detects silence based on dB threshold.  
- **Non-Destructive:** Creates a new timeline with cuts and colors preserving your original edit.

## 🛠 Requirements

* App: DaVinci Resolve (Free or Studio)  
* Internet: Required for initial setup to download AI models and required packages.  
* GPU: NVIDIA Cards acceleration - CPU only mode available 

## 🎬 A little about me & the project  

Hi! I am Simon - the 17 year old solo-developer of BadWords. This project started totally randomly. It wasn't planned, it wasn't supposed to become a full-on program. Heck! It wasn't supposed to even leave my computer... but somehow it became the biggest and most advanced project I've made.

It's probably not the best, the fastest, the cleanest, or the most useful thing you'll see... but while making it, I realized that it could actually be useful not only to me - but for many others. 

So... I made it for everyone.

It is still in development, it probably has a lot of bugs, "holes", crashes on edge-cases and unoptimized functions. So if you ever stumble upon any problems - feel free to open an Issue or contact me directly. 

Just by using BadWords and sending feedback, you are contributing to this project's community :)

## 🤝 Contribute

This is an open-source project. Feel free to open issues or pull requests to improve the tool\!

[![Download](https://img.shields.io/badge/Contact_me_here_👉️-333333?style=for-the-badge)]()
[![Reddit](https://img.shields.io/badge/Reddit-FF4500?style=for-the-badge&logo=reddit&logoColor=white)](https://www.reddit.com/message/compose/?to=KoxSwYT)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/users/786624853364572211)

[License (MIT)](LICENSE) Note: This tool is not affiliated with Blackmagic Design. Use at your own risk.
