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

/// Returns the user-local directory for the standalone portable Python 3.12 runtime (Linux / macOS)
pub fn standalone_python_root() -> Option<PathBuf> {
    #[cfg(target_os = "macos")]
    {
        if let Some(base) = dirs::data_dir() {
            return Some(base.join("BadWords-runtime").join("python312"));
        }
    }
    #[cfg(target_os = "linux")]
    {
        if let Some(base) = dirs::data_local_dir() {
            return Some(base.join("BadWords-runtime").join("python312"));
        }
    }
    #[cfg(not(any(target_os = "linux", target_os = "macos")))]
    {
        return None;
    }
    None
}

/// Checks if a given Python executable is version 3.10 - 3.12 AND has working venv + ensurepip
pub fn is_python_venv_capable<P: AsRef<std::ffi::OsStr>>(cmd: P) -> bool {
    create_hidden_command(cmd)
        .args([
            "-c",
            "import sys, venv, ensurepip; sys.exit(0 if (3, 10) <= sys.version_info < (3, 13) else 1)",
        ])
        .output()
        .is_ok_and(|o| o.status.success())
}

/// Locates an already-downloaded standalone portable Python 3.12 binary on Linux/macOS
#[cfg(unix)]
pub fn find_standalone_python() -> Option<PathBuf> {
    let mut dirs_to_check: Vec<PathBuf> = Vec::new();
    if let Some(root) = standalone_python_root() {
        dirs_to_check.push(root);
    }
    if let Some(cache) = dirs::cache_dir() {
        dirs_to_check.push(cache.join("BadWords-bootstrap").join("python"));
    }
    if let Some(home) = dirs::home_dir() {
        let fallback_cache = home.join(".cache").join("BadWords-bootstrap").join("python");
        if !dirs_to_check.contains(&fallback_cache) {
            dirs_to_check.push(fallback_cache);
        }
    }

    for base in dirs_to_check {
        for rel in ["bin/python3.12", "bin/python3", "python/bin/python3.12", "python/bin/python3"] {
            let cand = base.join(rel);
            if cand.is_file() && is_python_venv_capable(&cand) {
                return Some(cand);
            }
        }
    }
    None
}

/// Downloads and extracts a relocatable standalone CPython 3.12 build from astral-sh/python-build-standalone.
/// Requires ZERO root/sudo privileges and works on every Linux distro (Fedora 41-44, Arch, Ubuntu, immutable OS) and macOS.
#[cfg(unix)]
pub fn download_standalone_python_unix(sender: &crate::state::EventSender) -> bool {
    if let Some(existing) = find_standalone_python() {
        crate::state::emit_log(
            sender,
            "OK",
            &format!("Using cached standalone Python 3.12 runtime: {}", existing.display()),
        );
        return true;
    }

    let dest_dir = match standalone_python_root() {
        Some(p) => p,
        None => return false,
    };

    let triple = if cfg!(target_os = "linux") {
        if std::env::consts::ARCH == "aarch64" {
            "aarch64-unknown-linux-gnu"
        } else {
            "x86_64-unknown-linux-gnu"
        }
    } else if cfg!(target_os = "macos") {
        if std::env::consts::ARCH == "aarch64" {
            "aarch64-apple-darwin"
        } else {
            "x86_64-apple-darwin"
        }
    } else {
        return false;
    };

    const PBS_FALLBACK_TAG: &str = "20250317";
    const PBS_FALLBACK_VER: &str = "3.12.9";
    let pinned_url = format!(
        "https://github.com/astral-sh/python-build-standalone/releases/download/{tag}/cpython-{ver}+{tag}-{triple}-install_only.tar.gz",
        tag = PBS_FALLBACK_TAG,
        ver = PBS_FALLBACK_VER,
        triple = triple,
    );

    let agent = ureq::builder()
        .timeout(std::time::Duration::from_secs(60))
        .redirects(10)
        .build();

    let mut download_urls: Vec<String> = Vec::new();
    // Try resolving latest CPython 3.12 build from GitHub API first
    if let Ok(resp) = agent
        .get("https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest")
        .set("User-Agent", "BadWords-Installer")
        .call()
    {
        if let Ok(body) = resp.into_string() {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&body) {
                if let Some(assets) = val.get("assets").and_then(|a| a.as_array()) {
                    let needle_suffix = format!("-{}-install_only.tar.gz", triple);
                    for asset in assets {
                        if let (Some(name), Some(url)) = (
                            asset.get("name").and_then(|n| n.as_str()),
                            asset.get("browser_download_url").and_then(|u| u.as_str()),
                        ) {
                            if name.starts_with("cpython-3.12.") && name.ends_with(&needle_suffix) {
                                download_urls.push(url.to_string());
                                break;
                            }
                        }
                    }
                }
            }
        }
    }
    if !download_urls.contains(&pinned_url) {
        download_urls.push(pinned_url);
    }

    let archive_path = std::env::temp_dir().join(format!("bw_pbs_py312_{}.tar.gz", std::process::id()));
    let mut downloaded = false;

    for url in &download_urls {
        crate::state::emit_log(
            sender,
            "INFO",
            &format!("Downloading portable Python 3.12 ({})...", triple),
        );
        let dl_agent = ureq::builder()
            .timeout(std::time::Duration::from_secs(180))
            .redirects(10)
            .build();
        if let Ok(resp) = dl_agent.get(url).set("User-Agent", "BadWords-Installer").call() {
            if let Ok(mut out) = std::fs::File::create(&archive_path) {
                let mut reader = resp.into_reader();
                let mut buf = [0u8; 65536];
                let mut total: u64 = 0;
                let mut last_mb: u64 = 0;
                let mut copy_ok = true;
                loop {
                    match std::io::Read::read(&mut reader, &mut buf) {
                        Ok(0) => break,
                        Ok(n) => {
                            if std::io::Write::write_all(&mut out, &buf[..n]).is_err() {
                                copy_ok = false;
                                break;
                            }
                            total += n as u64;
                            let mb = total / (1024 * 1024);
                            if mb >= last_mb + 5 {
                                last_mb = mb;
                                crate::state::emit_log(
                                    sender,
                                    "INFO",
                                    &format!("Downloading portable Python 3.12... ({} MB)", mb),
                                );
                            }
                        }
                        Err(_) => {
                            copy_ok = false;
                            break;
                        }
                    }
                }
                if copy_ok && total > 10_000_000 {
                    downloaded = true;
                    break;
                }
            }
        }
        let _ = std::fs::remove_file(&archive_path);
    }

    if !downloaded {
        crate::state::emit_log(sender, "ERROR", "Failed to download portable Python 3.12 runtime archive.");
        return false;
    }

    crate::state::emit_log(sender, "INFO", "Extracting portable Python 3.12 runtime...");
    let _ = std::fs::remove_dir_all(&dest_dir);
    if std::fs::create_dir_all(&dest_dir).is_err() {
        let _ = std::fs::remove_file(&archive_path);
        return false;
    }

    let extract_ok = std::process::Command::new("tar")
        .args([
            "-xzf",
            archive_path.to_string_lossy().as_ref(),
            "-C",
            dest_dir.to_string_lossy().as_ref(),
            "--strip-components=1",
        ])
        .status()
        .is_ok_and(|s| s.success());

    let _ = std::fs::remove_file(&archive_path);

    if !extract_ok {
        crate::state::emit_log(sender, "ERROR", "Failed to extract portable Python 3.12 runtime archive.");
        let _ = std::fs::remove_dir_all(&dest_dir);
        return false;
    }

    if let Some(py_bin) = find_standalone_python() {
        crate::state::emit_log(
            sender,
            "OK",
            &format!("Portable Python 3.12 runtime ready (no admin password needed): {}", py_bin.display()),
        );
        return true;
    }

    crate::state::emit_log(sender, "ERROR", "Extracted Python 3.12 runtime failed verification.");
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

/// Automatically uninstalls auto-installed System Python for current OS
pub fn uninstall_system_python(sender: &crate::state::EventSender) -> bool {
    #[cfg(target_os = "windows")]
    return windows::uninstall_system_python(sender);

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    {
        if let Some(root) = standalone_python_root() {
            if let Some(parent) = root.parent() {
                if parent.exists() {
                    let _ = std::fs::remove_dir_all(parent);
                    crate::state::emit_log(sender, "OK", "Removed standalone Python 3.12 runtime.");
                    return true;
                }
            }
        }
        false
    }

    #[cfg(not(any(target_os = "windows", target_os = "linux", target_os = "macos")))]
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

/// Returns the persistent marker file path storing the active BadWords installation path
pub fn install_path_marker_file() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("BADWORDS_TEST_MARKER_PATH") {
        return Some(PathBuf::from(p));
    }
    if let Some(cfg) = dirs::config_dir() {
        return Some(cfg.join(APP_NAME).join("install_path"));
    }
    if let Some(home) = dirs::home_dir() {
        return Some(home.join(".config").join(APP_NAME).join("install_path"));
    }
    None
}

/// Saves the installed path to the persistent system marker
pub fn record_installed_location(path: &std::path::Path) {
    if let Some(marker) = install_path_marker_file() {
        if let Some(parent) = marker.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let _ = std::fs::write(&marker, path.to_string_lossy().as_bytes());
    }
    if std::env::var("BADWORDS_TEST_MARKER_PATH").is_err() {
        if let Some(data) = dirs::data_local_dir() {
            let p = data.join(APP_NAME).join("install_path");
            if let Some(parent) = p.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            let _ = std::fs::write(&p, path.to_string_lossy().as_bytes());
        }
    }
}

/// Removes persistent installation markers during uninstallation
pub fn remove_installed_location() {
    if let Some(marker) = install_path_marker_file() {
        let _ = std::fs::remove_file(&marker);
    }
    if std::env::var("BADWORDS_TEST_MARKER_PATH").is_err() {
        if let Some(data) = dirs::data_local_dir() {
            let p = data.join(APP_NAME).join("install_path");
            let _ = std::fs::remove_file(&p);
        }
    }
}

/// Detects existing BadWords installation path via running binary location, persistent marker, DaVinci Resolve wrappers, OS registration, or standard directories.
pub fn detect_existing_install() -> Option<PathBuf> {
    // 1. High priority: Check if current running installer is placed inside an installed BadWords folder
    if let Ok(cur_exe) = std::env::current_exe() {
        if let Some(parent) = cur_exe.parent() {
            let has_main = parent.join("main.py").is_file() || parent.join("src").join("main.py").is_file();
            let is_not_installer_repo = !parent.join("installer").join("Cargo.toml").is_file();
            let has_install_markers = parent.join("venv").is_dir()
                || parent.join(".version").is_file()
                || parent.join("settings.json").is_file()
                || parent.join("BadWords").is_file()
                || parent.join("BadWords.exe").is_file()
                || parent.join("updater.py").is_file()
                || parent.join("algorithms.py").is_file();
            if has_main && is_not_installer_repo && has_install_markers {
                return Some(parent.to_path_buf());
            }
        }
    }

    // 2. High priority: Check if current working directory is an installed BadWords folder
    if let Ok(cur_dir) = std::env::current_dir() {
        let has_main = cur_dir.join("main.py").is_file() || cur_dir.join("src").join("main.py").is_file();
        let is_not_installer_repo = !cur_dir.join("installer").join("Cargo.toml").is_file();
        let has_install_markers = cur_dir.join("venv").is_dir()
            || cur_dir.join(".version").is_file()
            || cur_dir.join("settings.json").is_file()
            || cur_dir.join("BadWords").is_file()
            || cur_dir.join("BadWords.exe").is_file()
            || cur_dir.join("updater.py").is_file()
            || cur_dir.join("algorithms.py").is_file();
        if has_main && is_not_installer_repo && has_install_markers {
            return Some(cur_dir);
        }
    }

    // 3. Check persistent configuration marker file
    if let Some(marker) = install_path_marker_file() {
        if marker.is_file() {
            if let Ok(content) = std::fs::read_to_string(&marker) {
                let p = PathBuf::from(content.trim());
                if p.is_dir() && (p.join("main.py").is_file() || p.join("src").join("main.py").is_file() || p.join(".version").is_file()) {
                    return Some(p);
                }
            }
        }
    }
    if std::env::var("BADWORDS_TEST_MARKER_PATH").is_err() {
        if let Some(data) = dirs::data_local_dir() {
            let marker = data.join(APP_NAME).join("install_path");
            if marker.is_file() {
                if let Ok(content) = std::fs::read_to_string(&marker) {
                    let p = PathBuf::from(content.trim());
                    if p.is_dir() && (p.join("main.py").is_file() || p.join("src").join("main.py").is_file() || p.join(".version").is_file()) {
                        return Some(p);
                    }
                }
            }
        }
    }

    // 4. Check DaVinci Resolve script wrappers (Lua Bridge & Python wrappers)
    let script_dirs = resolve_script_dirs();
    let wrapper_names = [
        "BadWords Bridge.lua",
        "BadWords.lua",
        "BadWords.py",
        "BadWords (Linux).py",
        "BadWords (Mac).py",
        "BadWords (Windows).py",
        "Badwords.py",
        "BadWords_Launcher.py",
    ];
    for dir in script_dirs {
        for filename in wrapper_names {
            let wrapper = dir.join(filename);
            if wrapper.is_file() {
                if let Ok(content) = std::fs::read_to_string(&wrapper) {
                    for line in content.lines() {
                        let trimmed = line.trim();
                        let target_candidate = if trimmed.contains("INSTALL_DIR") {
                            if let Some(start) = trimmed.find("[[") {
                                if let Some(end) = trimmed.rfind("]]") {
                                    if end > start + 2 {
                                        trimmed[start + 2..end].trim()
                                    } else {
                                        ""
                                    }
                                } else {
                                    ""
                                }
                            } else if let Some((_, val)) = trimmed.split_once('=') {
                                let mut raw = val.trim();
                                if raw.starts_with('r') || raw.starts_with('R') {
                                    raw = &raw[1..];
                                }
                                raw.trim().trim_matches(|c| c == '"' || c == '\'' || c == ';').trim()
                            } else {
                                ""
                            }
                        } else if trimmed.contains("MAIN_SCRIPT") {
                            if let Some((_, val)) = trimmed.split_once('=') {
                                let mut raw = val.trim();
                                if raw.starts_with('r') || raw.starts_with('R') {
                                    raw = &raw[1..];
                                }
                                let cleaned = raw.trim().trim_matches(|c| c == '"' || c == '\'' || c == ';').trim();
                                let p = PathBuf::from(cleaned);
                                if p.is_file() {
                                    if let Some(parent) = p.parent() {
                                        if parent.is_dir() {
                                            return Some(parent.to_path_buf());
                                        }
                                    }
                                }
                                ""
                            } else {
                                ""
                            }
                        } else {
                            ""
                        };

                        if !target_candidate.is_empty() {
                            let mut path = PathBuf::from(target_candidate);
                            if path.is_file() {
                                if let Some(parent) = path.parent() {
                                    path = parent.to_path_buf();
                                }
                            }
                            if path.exists() && (path.join("main.py").is_file() || path.join("src").join("main.py").is_file() || path.join("updater.py").is_file() || path.join("algorithms.py").is_file()) {
                                return Some(path);
                            }
                        }
                    }
                }
            }
        }
    }

    // 5. Check OS native registration (Windows Registry, Linux .desktop entry, macOS App Bundle)
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
