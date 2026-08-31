pub mod windows;
pub mod macos;
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

/// Detects DaVinci Resolve Fusion Scripts Utility directories
pub fn resolve_script_dirs() -> Vec<PathBuf> {
    let mut results = Vec::new();

    #[cfg(target_os = "windows")]
    {
        if let Some(appdata) = dirs::config_dir() {
            results.push(appdata.join("Blackmagic Design").join("DaVinci Resolve").join("Support").join("Fusion").join("Scripts").join("Utility"));
            results.push(appdata.join("Blackmagic Design").join("DaVinci Resolve").join("Fusion").join("Scripts").join("Utility"));
        }
        if let Ok(progdata) = std::env::var("PROGRAMDATA") {
            let pd = PathBuf::from(progdata);
            results.push(pd.join("Blackmagic Design").join("DaVinci Resolve").join("Support").join("Fusion").join("Scripts").join("Utility"));
            results.push(pd.join("Blackmagic Design").join("DaVinci Resolve").join("Fusion").join("Scripts").join("Utility"));
        }
    }

    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            results.push(home.join("Library").join("Application Support").join("Blackmagic Design").join("DaVinci Resolve").join("Fusion").join("Scripts").join("Utility"));
        }
        results.push(PathBuf::from("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"));
    }

    #[cfg(target_os = "linux")]
    {
        if let Some(home) = dirs::home_dir() {
            results.push(home.join(".local").join("share").join("DaVinciResolve").join("Fusion").join("Scripts").join("Utility"));
        }
        results.push(PathBuf::from("/opt/resolve/libs/Fusion/Scripts/Utility"));
    }

    results
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
