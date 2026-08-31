#[allow(dead_code)]
pub mod windows;
#[allow(dead_code)]
pub mod macos;
#[allow(dead_code)]
pub mod linux;

use std::path::PathBuf;

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
        }
        raw_paths.push(PathBuf::from("/opt/resolve/libs/Fusion/Scripts/Utility"));
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

/// Searches all known DaVinci Resolve script directories for a BadWords wrapper with a valid INSTALL_DIR
pub fn detect_existing_install() -> Option<PathBuf> {
    let script_dirs = resolve_script_dirs();
    for dir in script_dirs {
        for filename in ["BadWords.py", "BadWords (Linux).py"] {
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
                                if path.exists() {
                                    return Some(path);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    None
}

/// Parses an xrandr output line to extract monitor geometry (w, h, offset_x, offset_y) and returns the centered position
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
        if let Ok(out) = std::process::Command::new("powershell")
            .args(["-NoProfile", "-Command", "Add-Type -AssemblyName System.Windows.Forms; $s = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; \"$($s.X),$($s.Y),$($s.Width),$($s.Height)\""])
            .output()
        {
            let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
            let parts: Vec<f32> = text.split(',').filter_map(|s| s.trim().parse::<f32>().ok()).collect();
            if parts.len() == 4 && parts[2] > 400.0 && parts[3] > 300.0 {
                let cx = parts[0] + (parts[2] - win_w) / 2.0;
                let cy = parts[1] + (parts[3] - win_h) / 2.0;
                return Some((cx.max(0.0), cy.max(0.0)));
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        if let Ok(out) = std::process::Command::new("system_profiler").args(["SPDisplaysDataType"]).output() {
            let text = String::from_utf8_lossy(&out.stdout);
            for line in text.lines() {
                if line.contains("Resolution:") {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if let Some(pos) = parts.iter().position(|&p| p == "Resolution:") {
                        if pos + 3 < parts.len() {
                            if let (Ok(w), Ok(h)) = (parts[pos + 1].parse::<f32>(), parts[pos + 3].parse::<f32>()) {
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

    None
}
