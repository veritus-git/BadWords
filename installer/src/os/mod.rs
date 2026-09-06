// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

#[allow(dead_code)]
pub mod windows;
#[allow(dead_code)]
pub mod macos;
#[allow(dead_code)]
pub mod linux;

use std::path::PathBuf;

/// Creates a standard `Command` configured to never show a console window on Windows
pub fn create_hidden_command<P: AsRef<std::ffi::OsStr>>(program: P) -> std::process::Command {
    #[allow(unused_mut)]
    let mut cmd = std::process::Command::new(program);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    cmd
}

pub const APP_NAME: &str = "BadWords";

/// Returns default installation directory depending on current OS
pub fn default_install_dir() -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        if let Some(mut dir) = dirs::data_local_dir() {
            dir.push(APP_NAME);
            return dir;
        }
    }

    #[cfg(target_os = "macos")]
    {
        if let Some(mut dir) = dirs::data_dir() {
            dir.push(APP_NAME);
            return dir;
        }
    }

    #[cfg(target_os = "linux")]
    {
        if let Some(mut dir) = dirs::data_local_dir() {
            dir.push(APP_NAME);
            return dir;
        }
    }

    PathBuf::from(APP_NAME)
}

/// Checks whether official System Python is installed on current OS
pub fn has_system_python() -> bool {
    #[cfg(target_os = "windows")]
    return windows::has_system_python();

    #[cfg(target_os = "macos")]
    return macos::has_system_python();

    #[cfg(target_os = "linux")]
    return linux::has_system_python();

    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    false
}

/// Strips Mark-of-the-Web (Zone.Identifier) on Windows
pub fn unblock_file(path: &std::path::Path) {
    #[cfg(target_os = "windows")]
    windows::unblock_file(path);
    #[cfg(not(target_os = "windows"))]
    let _ = path;
}

#[allow(dead_code)]
/// Strips Mark-of-the-Web (Zone.Identifier) recursively on Windows
pub fn unblock_dir(path: &std::path::Path) {
    #[cfg(target_os = "windows")]
    windows::unblock_dir(path);
    #[cfg(not(target_os = "windows"))]
    let _ = path;
}

/// Automatically installs official System Python for current OS
pub fn install_system_python(sender: &crate::state::EventSender) -> bool {
    #[cfg(target_os = "windows")]
    return windows::install_system_python(sender);

    #[cfg(target_os = "macos")]
    return macos::install_system_python(sender);

    #[cfg(target_os = "linux")]
    return linux::install_system_python(sender);

    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        let _ = sender;
        false
    }
}

/// Detects all possible DaVinci Resolve Fusion Scripts Utility directories
pub fn resolve_script_dirs() -> Vec<PathBuf> {
    let mut raw_paths = Vec::new();

    #[cfg(target_os = "windows")]
    {
        if let Some(appdata) = dirs::config_dir() {
            raw_paths.push(appdata.join("Blackmagic Design").join("DaVinci Resolve").join("Support").join("Fusion").join("Scripts").join("Utility"));
            raw_paths.push(appdata.join("Blackmagic Design").join("DaVinci Resolve").join("Fusion").join("Scripts").join("Utility"));
        }
        if let Ok(progdata) = std::env::var("PROGRAMDATA") {
            let pd = PathBuf::from(progdata);
            raw_paths.push(pd.join("Blackmagic Design").join("DaVinci Resolve").join("Support").join("Fusion").join("Scripts").join("Utility"));
            raw_paths.push(pd.join("Blackmagic Design").join("DaVinci Resolve").join("Fusion").join("Scripts").join("Utility"));
        }
        if let Some(local_appdata) = dirs::data_local_dir() {
            let pkg_root = local_appdata.join("Packages");
            if pkg_root.is_dir() {
                if let Ok(entries) = std::fs::read_dir(pkg_root) {
                    for entry in entries.flatten() {
                        let name = entry.file_name().to_string_lossy().to_lowercase();
                        if name.starts_with("blackmagicdesign.davinciresolve") {
                            let base = entry.path().join("LocalState").join("AppDataRoaming").join("Blackmagic Design").join("DaVinci Resolve");
                            raw_paths.push(base.join("Support").join("Fusion").join("Scripts").join("Utility"));
                            raw_paths.push(base.join("Fusion").join("Scripts").join("Utility"));
                        }
                    }
                }
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            raw_paths.push(home.join("Library").join("Application Support").join("Blackmagic Design").join("DaVinci Resolve").join("Fusion").join("Scripts").join("Utility"));
        }
        raw_paths.push(PathBuf::from("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"));
    }

    #[cfg(target_os = "linux")]
    {
        if let Some(home) = dirs::home_dir() {
            raw_paths.push(home.join(".local").join("share").join("DaVinciResolve").join("Fusion").join("Scripts").join("Utility"));
            raw_paths.push(home.join(".var").join("app").join("com.blackmagicdesign.resolve").join("data").join("DaVinciResolve").join("Fusion").join("Scripts").join("Utility"));
        }
        raw_paths.push(PathBuf::from("/opt/resolve/libs/Fusion/Scripts/Utility"));
        raw_paths.push(PathBuf::from("/opt/resolve/Fusion/Scripts/Utility"));
    }

    // Deduplicate while preserving order
    let mut unique = Vec::new();
    for p in raw_paths {
        if !unique.contains(&p) {
            unique.push(p);
        }
    }
    unique
}

/// Detects existing BadWords installation path via OS registration, DaVinci Resolve wrappers, or standard directories.
pub fn detect_existing_install() -> Option<PathBuf> {
    // 1. Check OS native registration (Windows Registry, Linux .desktop entry, macOS App Bundle)
    #[cfg(target_os = "windows")]
    if let Some(p) = windows::detect_installed_location() {
        return Some(p);
    }

    #[cfg(target_os = "linux")]
    if let Some(p) = linux::detect_installed_location() {
        return Some(p);
    }

    #[cfg(target_os = "macos")]
    if let Some(p) = macos::detect_installed_location() {
        return Some(p);
    }

    // 2. Check DaVinci Resolve script wrappers (legacy versions e.g. 3.2.4)
    let script_dirs = resolve_script_dirs();
    for dir in script_dirs {
        for filename in ["BadWords.py", "BadWords (Linux).py", "BadWords (Mac).py", "BadWords (Windows).py", "Badwords.py"] {
            let wrapper = dir.join(filename);
            if wrapper.is_file() {
                if let Ok(content) = std::fs::read_to_string(&wrapper) {
                    for line in content.lines() {
                        let trimmed = line.trim();
                        if trimmed.starts_with("INSTALL_DIR") {
                            if let Some((_, val)) = trimmed.split_once('=') {
                                let mut raw = val.trim();
                                if raw.starts_with('r') || raw.starts_with('R') {
                                    raw = &raw[1..];
                                }
                                let clean_path = raw.trim().trim_matches(|c| c == '"' || c == '\'');
                                let path = PathBuf::from(clean_path);
                                if path.exists() && (path.join("main.py").is_file() || path.join("src").join("main.py").is_file()) {
                                    return Some(path);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Fallback 1: Default installation directory
    let def = default_install_dir();
    if def.join("main.py").is_file() || def.join("src").join("main.py").is_file() {
        return Some(def);
    }

    // Fallback 2: Common OS standard paths
    if let Some(home) = dirs::home_dir() {
        let candidates = [
            home.join(".local").join("share").join(APP_NAME),
            home.join(".local").join(APP_NAME),
            home.join(APP_NAME),
            home.join("AppData").join("Local").join(APP_NAME),
            home.join("Library").join("Application Support").join(APP_NAME),
        ];
        for c in candidates {
            if (c.join("main.py").is_file() || c.join("src").join("main.py").is_file()) && c.exists() {
                return Some(c);
            }
        }
    }

    None
}

/// Parses an xrandr output line to extract monitor geometry (w, h, offset_x, offset_y) and returns the centered position
#[cfg(target_os = "linux")]
fn parse_xrandr_geometry(line: &str, win_w: f32, win_h: f32) -> Option<(f32, f32)> {
    for part in line.split_whitespace() {
        if part.contains('x') && part.contains('+') {
            let subparts: Vec<&str> = part.split('+').collect();
            if subparts.len() >= 3 {
                if let Some((w_str, h_str)) = subparts[0].split_once('x') {
                    if let (Ok(w), Ok(h), Ok(ox), Ok(oy)) = (
                        w_str.parse::<f32>(),
                        h_str.parse::<f32>(),
                        subparts[1].parse::<f32>(),
                        subparts[2].parse::<f32>(),
                    ) {
                        if w > 400.0 && h > 300.0 {
                            let cx = ox + (w - win_w) / 2.0;
                            let cy = oy + (h - win_h) / 2.0;
                            return Some((cx, cy));
                        }
                    }
                }
            }
        }
    }
    None
}

/// Detects the exact primary monitor bounds and returns the top-left (x, y) coordinates to center a window
pub fn get_primary_monitor_center(win_w: f32, win_h: f32) -> Option<(f32, f32)> {
    #[cfg(target_os = "linux")]
    {
        // 1. Try xrandr with connected primary
        if let Ok(out) = std::process::Command::new("xrandr").arg("--current").output() {
            let text = String::from_utf8_lossy(&out.stdout);
            for line in text.lines() {
                if line.contains(" connected") && line.contains("primary") {
                    if let Some(pos) = parse_xrandr_geometry(line, win_w, win_h) {
                        return Some(pos);
                    }
                }
            }
            // 2. Fallback to first connected monitor
            for line in text.lines() {
                if line.contains(" connected") {
                    if let Some(pos) = parse_xrandr_geometry(line, win_w, win_h) {
                        return Some(pos);
                    }
                }
            }
        }

        // 3. Try xdpyinfo
        if let Ok(out) = std::process::Command::new("xdpyinfo").output() {
            let text = String::from_utf8_lossy(&out.stdout);
            for line in text.lines() {
                if line.contains("dimensions:") {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.len() >= 2 {
                        if let Some((w_str, h_str)) = parts[1].split_once('x') {
                            if let (Ok(w), Ok(h)) = (w_str.parse::<f32>(), h_str.parse::<f32>()) {
                                if w > 400.0 && h > 300.0 {
                                    return Some(((w - win_w) / 2.0, (h - win_h) / 2.0));
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        #[link(name = "user32")]
        extern "system" {
            fn GetSystemMetrics(n_index: i32) -> i32;
        }
        unsafe {
            let sw = GetSystemMetrics(0) as f32; // SM_CXSCREEN
            let sh = GetSystemMetrics(1) as f32; // SM_CYSCREEN
            if sw > 400.0 && sh > 300.0 {
                let cx = ((sw - win_w) / 2.0).max(0.0);
                let cy = ((sh - win_h) / 2.0).max(0.0);
                return Some((cx, cy));
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        #[repr(C)]
        struct CGPoint { x: f64, y: f64 }
        #[repr(C)]
        struct CGSize { width: f64, height: f64 }
        #[repr(C)]
        struct CGRect { origin: CGPoint, size: CGSize }

        #[link(name = "CoreGraphics", kind = "framework")]
        extern "C" {
            fn CGMainDisplayID() -> u32;
            fn CGDisplayBounds(display: u32) -> CGRect;
        }

        unsafe {
            let bounds = CGDisplayBounds(CGMainDisplayID());
            let sw = bounds.size.width as f32;
            let sh = bounds.size.height as f32;
            if sw > 400.0 && sh > 300.0 {
                let cx = ((sw - win_w) / 2.0).max(0.0);
                let cy = ((sh - win_h) / 2.0).max(0.0);
                return Some((cx, cy));
            }
        }
    }

    None
}
