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
