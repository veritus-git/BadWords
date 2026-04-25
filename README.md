# <img src="source files/icon.png" align="right" width="100" style="margin-left: 200px; margin-bottom: 20px;" alt="Logo"> BadWords - Cleaner Timelines, Faster
Automatically **detect, mark and/or remove filler words, silence, and retakes** <br>
in DaVinci Resolve using OpenAI Whisper and FFmpeg.

<br>
![Preview](source%20files/editor_preview.png)

## Quick access shortcuts:
### Installation guides:
**[Linux (any distro)](source%20files/Linux%20GUIDE.md)** <br>
**[Windows](source%20files/Windows%20GUIDE.md)**

### Downloads:

[![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)]() 
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)]() 
[![Download](https://img.shields.io/badge/Download_Latest_BadWords_Release-333333?style=for-the-badge)](https://gitlab.com/badwords/BadWords/-/releases/permalink/latest)



[![macOS](https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white)]() [![Download](https://img.shields.io/badge/Maybe_Someday!-333333?style=for-the-badge)](link)

<a href="https://buymeacoffee.com/badwords" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" align="top" width="30%" style="margin-left: 20px; margin-bottom: 20px;" alt="Logo"></a>

## 🛠️ What's new in 2.0.2?

- Precise cuts: I implemented stable-ts, this is the biggest change. It makes timestamps way more accurate so it finally stops cutting words in half.
- "Lazy assemble": In 2.0.1 and older versions clicking "Assemble" just froze the app until it was done. Now it "thinks" for a sec and smoothly spits out clips onto your timeline. Looks and feels way better.
- Performance/compatibility: The app now automatically picks the best compute type (float16/float32/int8) for your hardware. Should boost speed on new GPUs and fix crashes on older ones (AMD/Intel cards still not supported - use CPU instead).
- Whisper hallucinations: Sometimes Whisper breaks and types "mhm" 100 times in a row. I fixed it by making GUI just show "mhm [x100]" instead of spamming your whole screen.
- UI & Bug fixes: I fixed the annoying appearing white title bar on Windows, cleaned up the interface when you aren't using a "script reviewer mode" and fixed some weird coloring behavior with typos/inaudible fragments (unchecking their visibility now properly ignores them during assembly).
- Better status updates: Added a proper checking/downloading stage on Windows so you actually know what's happening under the hood.
- Optimized Verbatim: Tweaked the transcription logic for slightly better detection of repetitions and slip-ups.
- Better installers: You can now choose to just Update, do a Clean Install (refreshes core files but keeps your settings/models, use it if bugs appear), or do a Full Wipe.
- Official Logo: Added the branding icon! I decided to stick with the color version but improved it a bit. You'll finally see a proper logo on your taskbar.
- Telemetry (Optional): I added an optional stats ping in the installer. If you leave it on it sends a completely anonymous ping when you install/update (just OS, app version, and country). No files, no audio, zero personal data.
- Auto-Sourcing: I completely removed the confusing "Compound Clip Fix Mode" checkbox. BadWords now does "Auto-Sourcing" in the background and automatically figures out how to safely assemble your timeline, even if you have unsynced video or multiple cuts.


## 🚀 Features

- **Smart Detection** - Finds filler words (umm, ahh), silence, and repeated sentences (still in development) using local AI. 
- **DaVinci Integrated** - Runs directly on Davinci Resolve as a Workflow Script, using only local resources
- **Safe & Clean** - Creates isolated environment, keeping your system packages safe and clean.
- **GPU Accelerated** - Utilizes your GPU for fast transcription (NVIDIA Cards Supported Only - for now!)
- **Interactive Review** - Review cuts before applying them to the timeline.
- **Heat map** - Mark timeline with colors instead of invasive rough cutting

![Timeline Heatmap](source%20files/heatmap.png)

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