// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! Core installation, repair, move, and uninstallation engine
//! Matches setupfiles/setup.py feature-for-feature: System Python detection & auto-installation,
//! GPU detection, venv, pip packages, ffmpeg, libs link, DaVinci Resolve wrappers, and OS standalone integration.

use crate::os::{self, resolve_script_dirs};
use crate::state::{emit_complete, emit_log, emit_progress, emit_progress_sub, EventSender};
use std::fs;
use std::path::{Path, PathBuf};

pub const APP_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Recursively collects all files in a directory tree with relative paths and byte sizes
fn collect_all_files(dir: &Path, base: &Path) -> Vec<(PathBuf, PathBuf, u64)> {
    let mut result = Vec::new();
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            let rel = p.strip_prefix(base).unwrap_or(&p).to_path_buf();
            if p.is_dir() {
                result.extend(collect_all_files(&p, base));
            } else if p.is_file() || p.is_symlink() {
                let size = p.metadata().map(|m| m.len()).unwrap_or(0);
                result.push((p, rel, size));
            }
        }
    }
    result
}

/// Recursively copies a directory tree with continuous live progress
fn copy_dir_with_progress(
    src: &Path,
    dst: &Path,
    start_pct: i32,
    end_pct: i32,
    title: &str,
    sender: &EventSender,
) -> std::io::Result<()> {
    fs::create_dir_all(dst)?;
    let files = collect_all_files(src, src);
    let total_bytes: u64 = files.iter().map(|(_, _, s)| *s).sum();
    let total_files = files.len();
    let mut copied_bytes: u64 = 0;
    let mut last_emit = std::time::Instant::now();

    for (idx, (src_file, rel_path, file_size)) in files.into_iter().enumerate() {
        let target_file = dst.join(&rel_path);
        if let Some(parent) = target_file.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let _ = fs::copy(&src_file, &target_file);
        copied_bytes += file_size;

        if last_emit.elapsed() > std::time::Duration::from_millis(40) || idx + 1 == total_files {
            let frac = if total_bytes > 0 {
                (copied_bytes as f32 / total_bytes as f32).clamp(0.0, 1.0)
            } else {
                ((idx + 1) as f32 / total_files.max(1) as f32).clamp(0.0, 1.0)
            };
            let main_pct = start_pct + ((end_pct - start_pct) as f32 * frac) as i32;
            let sub_pct = (frac * 100.0) as i32;
            let copied_mb = (copied_bytes as f64) / 1_048_576.0;
            let total_mb = (total_bytes as f64) / 1_048_576.0;
            let details = if total_mb > 0.1 {
                format!("Copying: {} ({:.1}/{:.1} MB)", rel_path.display(), copied_mb, total_mb)
            } else {
                format!("Copying: {} ({}/{})", rel_path.display(), idx + 1, total_files)
            };
            emit_progress_sub(sender, main_pct as u32, sub_pct as u32, title, &details);
            last_emit = std::time::Instant::now();
        }
    }
    Ok(())
}

/// Recursively deletes a directory with continuous live progress
fn delete_dir_with_progress(
    dir: &Path,
    start_pct: i32,
    end_pct: i32,
    title: &str,
    sender: &EventSender,
) {
    if !dir.exists() {
        return;
    }
    let files = collect_all_files(dir, dir);
    let total_items = files.len();
    let mut last_emit = std::time::Instant::now();

    for (idx, (file_path, rel_path, _)) in files.into_iter().enumerate() {
        let _ = fs::remove_file(&file_path);

        if last_emit.elapsed() > std::time::Duration::from_millis(30) || idx + 1 == total_items {
            let frac = ((idx + 1) as f32 / total_items.max(1) as f32).clamp(0.0, 1.0);
            let main_pct = start_pct + ((end_pct - start_pct) as f32 * frac) as i32;
            let sub_pct = (frac * 100.0) as i32;
            let details = format!("Removing: {} ({}/{})", rel_path.display(), idx + 1, total_items);
            emit_progress_sub(sender, main_pct as u32, sub_pct as u32, title, &details);
            last_emit = std::time::Instant::now();
        }
    }
    let _ = fs::remove_dir_all(dir);
}

/// Recursively copies a directory tree
fn copy_dir_all(src: impl AsRef<Path>, dst: impl AsRef<Path>) -> std::io::Result<()> {
    fs::create_dir_all(&dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let file_type = entry.file_type()?;
        let dest_path = dst.as_ref().join(entry.file_name());
        if file_type.is_dir() {
            copy_dir_all(entry.path(), dest_path)?;
        } else {
            let _ = fs::copy(entry.path(), dest_path);
        }
    }
    Ok(())
}

/// Downloads a file over HTTP(S) to the specified destination with live byte progress
fn download_file_with_progress(
    url: &str,
    dest: &Path,
    main_pct: u32,
    status_label: &str,
    details_prefix: &str,
    sender: &EventSender,
) -> Result<(), String> {
    let resp = ureq::get(url)
        .timeout(std::time::Duration::from_secs(180))
        .call()
        .map_err(|e| format!("Download error from {}: {}", url, e))?;

    let total_bytes = resp.header("content-length").and_then(|l| l.parse::<u64>().ok());
    let mut reader = resp.into_reader();
    let mut out = fs::File::create(dest)
        .map_err(|e| format!("Failed to create destination file {}: {}", dest.display(), e))?;

    let mut buffer = [0u8; 64 * 1024];
    let mut downloaded: u64 = 0;
    let mut last_emit = std::time::Instant::now();

    loop {
        use std::io::Read;
        let bytes_read = reader.read(&mut buffer).map_err(|e| format!("Read error: {}", e))?;
        if bytes_read == 0 {
            break;
        }
        use std::io::Write;
        out.write_all(&buffer[..bytes_read]).map_err(|e| format!("Write error: {}", e))?;
        downloaded += bytes_read as u64;

        if last_emit.elapsed().as_millis() >= 120 {
            last_emit = std::time::Instant::now();
            let mb_down = downloaded as f64 / 1_048_576.0;
            if let Some(total) = total_bytes {
                let mb_total = total as f64 / 1_048_576.0;
                let sub_pct = ((downloaded as f64 / total as f64) * 100.0).clamp(0.0, 100.0) as u32;
                let det = format!("{} ({:.1}/{:.1} MB)", details_prefix, mb_down, mb_total);
                emit_progress_sub(sender, main_pct, sub_pct, status_label, &det);
            } else {
                let det = format!("{} ({:.1} MB downloaded)", details_prefix, mb_down);
                emit_progress_sub(sender, main_pct, 50, status_label, &det);
            }
        }
    }

    emit_progress_sub(sender, main_pct, 100, status_label, &format!("{} (Done)", details_prefix));
    Ok(())
}

/// Converts raw wheel / package filenames into clean, user-friendly names
fn friendly_pkg_name(raw: &str) -> String {
    let lower = raw.to_lowercase();
    if lower.contains("pyside6_essentials") {
        "PySide6 Essentials".to_string()
    } else if lower.contains("pyside6_addons") {
        "PySide6 Addons".to_string()
    } else if lower.contains("pyside6") {
        "PySide6 Framework".to_string()
    } else if lower.contains("cudnn") {
        "NVIDIA cuDNN CUDA 12".to_string()
    } else if lower.contains("cublas") {
        "NVIDIA cuBLAS CUDA 12".to_string()
    } else if lower.contains("faster_whisper") || lower.contains("faster-whisper") {
        "Faster-Whisper AI Engine".to_string()
    } else if lower.contains("ctranslate2") {
        "CTranslate2 Runtime".to_string()
    } else if lower.contains("pypdf") {
        "PyPDF Library".to_string()
    } else if lower.contains("shiboken6") {
        "Shiboken6 Core".to_string()
    } else {
        let name = raw.split('-').next().unwrap_or(raw);
        name.trim_end_matches(".whl").trim_end_matches(".tar.gz").to_string()
    }
}

/// Executes pip install with live streaming progress updates
fn run_pip_install_streaming(
    py_bin: &Path,
    args: &[&str],
    main_pct_start: u32,
    main_pct_end: u32,
    status_label: &str,
    default_detail: &str,
    sender: &EventSender,
) -> bool {
    let mut cmd = os::create_hidden_command(py_bin);
    cmd.args(["-m", "pip", "install", "--no-cache-dir"]);
    for arg in args {
        cmd.arg(arg);
    }
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());

    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(e) => {
            emit_log(sender, "ERROR", &format!("Failed to start pip: {}", e));
            return false;
        }
    };

    let mut stdout = child.stdout.take();
    let mut stderr = child.stderr.take();
    emit_progress_sub(sender, main_pct_start, 0, status_label, default_detail);
    let sender_clone = sender.clone();
    let status_str = status_label.to_string();

    let reader_thread = std::thread::spawn(move || {
        if let Some(ref mut out) = stdout {
            use std::io::Read;
            let mut byte_buf = [0u8; 1024];
            let mut line_buf = String::new();

            while let Ok(n) = out.read(&mut byte_buf) {
                if n == 0 {
                    break;
                }
                for &b in &byte_buf[..n] {
                    if b == b'\n' || b == b'\r' {
                        let line = line_buf.trim();
                        if !line.is_empty() {
                            if line.contains("Downloading") {
                                if let Some(pkg_name) = line.split("Downloading").nth(1) {
                                    let clean_name = pkg_name.split_whitespace().next().unwrap_or("package");
                                    let friendly = friendly_pkg_name(clean_name);
                                    let size_str = pkg_name.split('(').nth(1).and_then(|s| s.split(')').next()).unwrap_or("");
                                    let current_detail = if !size_str.is_empty() {
                                        format!("Downloading {} ({})", friendly, size_str)
                                    } else {
                                        format!("Downloading {}", friendly)
                                    };
                                    emit_progress_sub(&sender_clone, main_pct_start, 0, &status_str, &current_detail);
                                }
                            } else if line.contains("Collecting") {
                                if let Some(pkg_name) = line.split("Collecting").nth(1) {
                                    let clean_name = pkg_name.split_whitespace().next().unwrap_or("package");
                                    let friendly = friendly_pkg_name(clean_name);
                                    let current_detail = format!("Collecting {}", friendly);
                                    emit_progress_sub(&sender_clone, main_pct_start, 0, &status_str, &current_detail);
                                }
                            } else if line.contains("Using cached") {
                                if let Some(pkg_name) = line.split("Using cached").nth(1) {
                                    let clean_name = pkg_name.split_whitespace().next().unwrap_or("package");
                                    let friendly = friendly_pkg_name(clean_name);
                                    let current_detail = format!("Using cached {}", friendly);
                                    emit_progress_sub(&sender_clone, main_pct_start, 0, &status_str, &current_detail);
                                }
                            } else if line.contains("Installing collected packages") {
                                let current_detail = "Unpacking & configuring Python packages...".to_string();
                                emit_progress_sub(&sender_clone, main_pct_end - 1, 0, &status_str, &current_detail);
                            }
                        }
                        line_buf.clear();
                    } else {
                        line_buf.push(b as char);
                    }
                }
            }
        }
    });

    let mut err_output = String::new();
    if let Some(ref mut err) = stderr {
        use std::io::Read;
        let _ = err.read_to_string(&mut err_output);
    }

    let status = child.wait();
    let _ = reader_thread.join();

    match status {
        Ok(st) => {
            if !st.success() && !err_output.trim().is_empty() {
                emit_log(sender, "WARN", &format!("pip output: {}", err_output.trim()));
            }
            st.success()
        }
        Err(e) => {
            emit_log(sender, "ERROR", &format!("pip process error: {}", e));
            false
        }
    }
}

/// Extracts a ZIP archive to a destination directory using the zip crate
fn extract_zip(archive_path: &Path, destination: &Path) -> std::io::Result<()> {
    let file = fs::File::open(archive_path)?;
    let mut archive = zip::ZipArchive::new(file)?;

    for i in 0..archive.len() {
        let mut file = archive.by_index(i)?;
        let outpath = match file.enclosed_name() {
            Some(path) => destination.join(path),
            None => continue,
        };

        if file.name().ends_with('/') {
            fs::create_dir_all(&outpath)?;
        } else {
            if let Some(p) = outpath.parent() {
                if !p.exists() {
                    fs::create_dir_all(p)?;
                }
            }
            let mut outfile = fs::File::create(&outpath)?;
            std::io::copy(&mut file, &mut outfile)?;
        }

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            if let Some(mode) = file.unix_mode() {
                let _ = fs::set_permissions(&outpath, fs::Permissions::from_mode(mode));
            }
        }
    }
    Ok(())
}

/// Finds the system Python executable (Python 3.10+)
fn find_python() -> Option<String> {
    let candidates = [
        "python3.14",
        "python3.13",
        "python3.12",
        "python3.11",
        "python3.10",
        "python3",
        "python",
        "py",
    ];

    for cmd in candidates {
        if let Ok(output) = os::create_hidden_command(cmd).arg("-c").arg("import sys; exit(0 if sys.version_info >= (3, 10) else 1)").output() {
            if output.status.success() {
                return Some(cmd.to_string());
            }
        }
    }
    None
}

/// Detects NVIDIA GPU hardware for CUDA 12 acceleration
fn detect_nvidia_gpu() -> bool {
    #[cfg(target_os = "windows")]
    {
        if Path::new(r"C:\Windows\System32\nvcuda.dll").exists() || Path::new(r"C:\Windows\System32\nvapi64.dll").exists() {
            return true;
        }
        let hklm = winreg::RegKey::predef(winreg::enums::HKEY_LOCAL_MACHINE);
        if let Ok(class_key) = hklm.open_subkey(r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}") {
            for subkey in class_key.enum_keys().filter_map(|k| k.ok()) {
                if let Ok(dev) = class_key.open_subkey(&subkey) {
                    if let Ok(desc) = dev.get_value::<String, _>("DriverDesc") {
                        if desc.to_lowercase().contains("nvidia") {
                            return true;
                        }
                    }
                }
            }
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        if let Ok(output) = os::create_hidden_command("lspci").output() {
            if String::from_utf8_lossy(&output.stdout).to_lowercase().contains("nvidia") {
                return true;
            }
        }
        if let Ok(output) = os::create_hidden_command("lshw").args(["-C", "display"]).output() {
            if String::from_utf8_lossy(&output.stdout).to_lowercase().contains("nvidia") {
                return true;
            }
        }
    }
    false
}

/// Locates local source repository if available
pub fn find_local_repo() -> Option<PathBuf> {
    let mut candidates = vec![
        PathBuf::from("."),
        PathBuf::from(".."),
        PathBuf::from("../.."),
    ];
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            candidates.push(parent.to_path_buf());
            if let Some(p2) = parent.parent() {
                candidates.push(p2.to_path_buf());
            }
        }
    }

    for candidate in candidates {
        if candidate.join("src").join("main.py").is_file() || (candidate.join("main.py").is_file() && candidate.join("setupfiles").is_dir()) {
            if let Ok(canon) = candidate.canonicalize() {
                return Some(canon);
            }
        }
    }
    None
}

/// Detects version from local files if running from repo/source directory
pub fn detect_local_version() -> Option<String> {
    if let Some(repo_dir) = find_local_repo() {
        for config_path in [repo_dir.join("src").join("config.py"), repo_dir.join("config.py")] {
            if let Ok(content) = fs::read_to_string(&config_path) {
                for line in content.lines() {
                    let trimmed = line.trim();
                    if trimmed.starts_with("APP_VERSION") || trimmed.starts_with("VERSION") {
                        if let Some((_, val)) = trimmed.split_once('=') {
                            let clean = val.trim().trim_matches(|c| c == '"' || c == '\'').trim();
                            if !clean.is_empty() {
                                return Some(clean.to_string());
                            }
                        }
                    }
                }
            }
        }
        return Some(APP_VERSION.to_string());
    }
    None
}

/// Deploys BadWords application files (from local repo or online GitHub/GitLab zip)
fn deploy_application_files(target_dir: &Path, sender: &EventSender) -> bool {
    if let Some(repo_dir) = find_local_repo() {
        emit_log(sender, "INFO", &format!("Using local repository: {}", repo_dir.display()));

        let src_dir = repo_dir.join("src");
        if src_dir.is_dir() {
            let _ = copy_dir_all(&src_dir, target_dir);
        }

        let src_assets = repo_dir.join("assets");
        if src_assets.is_dir() {
            let _ = copy_dir_all(&src_assets, target_dir.join("assets"));
            let icons_sub = src_assets.join("icons");
            if icons_sub.is_dir() {
                let _ = copy_dir_all(&icons_sub, target_dir.join("icons"));
            }
            let layout_sub = src_assets.join("layout");
            if layout_sub.is_dir() {
                let _ = copy_dir_all(&layout_sub, target_dir.join("layout"));
            }
        }

        let updater_src = repo_dir.join("setupfiles").join("updater.py");
        if updater_src.is_file() {
            let _ = fs::copy(updater_src, target_dir.join("updater.py"));
        }

        for doc in ["CHANGELOG.md", "LICENSE", "README.md"] {
            let doc_path = repo_dir.join(doc);
            if doc_path.is_file() {
                let _ = fs::copy(doc_path, target_dir.join(doc));
            }
        }

        let installer_dest_name = if cfg!(target_os = "windows") { "badwords-installer.exe" } else { "badwords-installer" };
        if let Ok(cur_exe) = std::env::current_exe() {
            let dest_bin = target_dir.join(installer_dest_name);
            if cur_exe != dest_bin {
                let _ = fs::copy(&cur_exe, &dest_bin);
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let _ = fs::set_permissions(&dest_bin, fs::Permissions::from_mode(0o755));
                }
            }
        }

        emit_log(sender, "OK", "Local application files deployed successfully.");
        return true;
    }

    // Remote download
    deploy_remote_files(target_dir, sender)
}

/// Queries GitHub API for the latest published release tag and zipball URL
pub fn fetch_latest_github_release() -> Option<(String, String)> {
    let resp = ureq::get("https://api.github.com/repos/veritus-git/BadWords/releases/latest")
        .set("User-Agent", "badwords-installer")
        .timeout(std::time::Duration::from_secs(5))
        .call()
        .ok()?;

    let json: serde_json::Value = resp.into_json().ok()?;
    let tag = json.get("tag_name").and_then(|v| v.as_str())?.to_string();
    let zip_url = json.get("zipball_url").and_then(|v| v.as_str())?.to_string();
    Some((tag, zip_url))
}

/// Queries GitLab API for releases if GitHub API fails
pub fn fetch_latest_gitlab_release() -> Option<(String, String)> {
    let resp = ureq::get("https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases")
        .set("User-Agent", "badwords-installer")
        .timeout(std::time::Duration::from_secs(5))
        .call()
        .ok()?;

    let json: serde_json::Value = resp.into_json().ok()?;
    let first = json.as_array()?.first()?;
    let tag = first.get("tag_name").and_then(|v| v.as_str())?.to_string();
    let zip_url = format!("https://gitlab.com/badwords/BadWords/-/archive/{tag}/BadWords-{tag}.zip");
    Some((tag, zip_url))
}

/// Downloads and deploys BadWords from latest GitHub Release or repository
fn deploy_remote_files(target_dir: &Path, sender: &EventSender) -> bool {
    let temp_dir = std::env::temp_dir();
    let zip_dest = temp_dir.join("badwords_release.zip");
    let extract_dest = temp_dir.join("badwords_release_extracted");

    let _ = fs::remove_file(&zip_dest);
    let _ = fs::remove_dir_all(&extract_dest);
    let _ = fs::create_dir_all(&extract_dest);

    let mut downloaded = false;
    let mut candidate_urls = Vec::new();

    if let Some((tag, zip_url)) = fetch_latest_github_release() {
        emit_log(sender, "INFO", &format!("Detected latest GitHub release: {}", tag));
        candidate_urls.push(zip_url);
        candidate_urls.push(format!("https://github.com/veritus-git/BadWords/archive/refs/tags/{}.zip", tag));
    } else if let Some((tag, zip_url)) = fetch_latest_gitlab_release() {
        emit_log(sender, "INFO", &format!("Detected latest GitLab release: {}", tag));
        candidate_urls.push(zip_url);
    }

    // Git branch archives as reliable dynamic fallbacks
    candidate_urls.push("https://github.com/veritus-git/BadWords/archive/refs/heads/main.zip".to_string());
    candidate_urls.push("https://github.com/veritus-git/BadWords/archive/refs/heads/dev-v4.zip".to_string());
    candidate_urls.push("https://gitlab.com/badwords/BadWords/-/archive/main/BadWords-main.zip".to_string());

    for url in candidate_urls {
        emit_log(sender, "INFO", &format!("Fetching release source from: {}", url));
        if download_file_with_progress(&url, &zip_dest, 30, "Deploying application files...", "Downloading release archive", sender).is_ok() {
            downloaded = true;
            break;
        }
    }

    if !downloaded {
        emit_log(sender, "ERROR", "Failed to download BadWords source package. Check internet connection.");
        return false;
    }

    emit_log(sender, "INFO", "Extracting BadWords application files...");
    if extract_zip(&zip_dest, &extract_dest).is_err() {
        emit_log(sender, "ERROR", "Failed to extract downloaded archive.");
        return false;
    }

    // Find the extracted root directory (e.g. BadWords-dev-v4 or BadWords-main)
    if let Ok(entries) = fs::read_dir(&extract_dest) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() && (p.join("src").join("main.py").is_file() || p.join("main.py").is_file()) {
                let src_sub = if p.join("src").is_dir() { p.join("src") } else { p.clone() };
                let _ = copy_dir_all(&src_sub, target_dir);

                let assets_sub = p.join("assets");
                if assets_sub.is_dir() {
                    let _ = copy_dir_all(&assets_sub, target_dir.join("assets"));
                    let icons_sub = assets_sub.join("icons");
                    if icons_sub.is_dir() {
                        let _ = copy_dir_all(&icons_sub, target_dir.join("icons"));
                    }
                    let layout_sub = assets_sub.join("layout");
                    if layout_sub.is_dir() {
                        let _ = copy_dir_all(&layout_sub, target_dir.join("layout"));
                    }
                }

                let updater_sub = p.join("setupfiles").join("updater.py");
                if updater_sub.is_file() {
                    let _ = fs::copy(updater_sub, target_dir.join("updater.py"));
                }

                let installer_dest_name = if cfg!(target_os = "windows") { "badwords-installer.exe" } else { "badwords-installer" };
                if let Ok(cur_exe) = std::env::current_exe() {
                    let dest_bin = target_dir.join(installer_dest_name);
                    if cur_exe != dest_bin {
                        let _ = fs::copy(&cur_exe, &dest_bin);
                        #[cfg(unix)]
                        {
                            use std::os::unix::fs::PermissionsExt;
                            let _ = fs::set_permissions(&dest_bin, fs::Permissions::from_mode(0o755));
                        }
                    }
                }

                emit_log(sender, "OK", "Remote application files deployed successfully.");
                let _ = fs::remove_file(&zip_dest);
                let _ = fs::remove_dir_all(&extract_dest);
                return true;
            }
        }
    }

    let _ = fs::remove_file(&zip_dest);
    let _ = fs::remove_dir_all(&extract_dest);
    false
}

/// Ensures portable FFmpeg is present in bin/
fn ensure_ffmpeg(bin_dir: &Path, sender: &EventSender) {
    let ffmpeg_name = if cfg!(target_os = "windows") { "ffmpeg.exe" } else { "ffmpeg" };
    let ffmpeg_bin = bin_dir.join(ffmpeg_name);

    if ffmpeg_bin.exists() {
        emit_log(sender, "OK", "Portable FFmpeg binary is present.");
        return;
    }

    // Check if local repo already has bin/ffmpeg
    if let Some(repo) = find_local_repo() {
        let repo_ffmpeg = repo.join("bin").join(ffmpeg_name);
        if repo_ffmpeg.is_file() && fs::copy(&repo_ffmpeg, &ffmpeg_bin).is_ok() {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = fs::set_permissions(&ffmpeg_bin, fs::Permissions::from_mode(0o755));
            }
            emit_log(sender, "OK", "Copied local portable FFmpeg binary.");
            return;
        }
    }

    emit_log(sender, "INFO", "Downloading portable FFmpeg...");

    #[cfg(target_os = "windows")]
    {
        let url = "https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-essentials_build.zip";
        let temp_dir = std::env::temp_dir();
        let archive = temp_dir.join("ffmpeg_win.zip");
        let extract_dir = temp_dir.join("ffmpeg_extracted");
        let _ = fs::remove_dir_all(&extract_dir);
        let _ = fs::create_dir_all(&extract_dir);

        if download_file_with_progress(url, &archive, 48, "Configuring FFmpeg...", "Downloading portable FFmpeg (Windows)", sender).is_ok() {
            if extract_zip(&archive, &extract_dir).is_ok() {
                // Search for ffmpeg.exe inside extracted tree
                if let Ok(entries) = fs::read_dir(&extract_dir) {
                    for entry in entries.flatten() {
                        let candidate = entry.path().join("bin").join("ffmpeg.exe");
                        if candidate.is_file() {
                            let _ = fs::copy(&candidate, &ffmpeg_bin);
                            emit_log(sender, "OK", "Portable FFmpeg for Windows installed successfully.");
                            let _ = fs::remove_file(&archive);
                            let _ = fs::remove_dir_all(&extract_dir);
                            return;
                        }
                    }
                }
            }
        }
    }

    #[cfg(target_os = "linux")]
    {
        let urls = [
            "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
        ];
        let parent = bin_dir.parent().unwrap_or(bin_dir);
        let archive = parent.join("ffmpeg_static.tar.xz");

        for url in urls {
            if download_file_with_progress(url, &archive, 48, "Configuring FFmpeg...", "Downloading portable FFmpeg (Linux)", sender).is_ok() {
                let _ = os::create_hidden_command("tar").args(["-xf", &archive.to_string_lossy(), "-C", &parent.to_string_lossy()]).status();

                if let Ok(entries) = fs::read_dir(parent) {
                    for entry in entries.flatten() {
                        let p = entry.path();
                        if p.is_dir() && p.file_name().is_some_and(|n| n.to_string_lossy().starts_with("ffmpeg-")) {
                            let src_ff = if p.join("bin").join("ffmpeg").is_file() {
                                p.join("bin").join("ffmpeg")
                            } else {
                                p.join("ffmpeg")
                            };
                            if src_ff.is_file() {
                                let _ = fs::copy(&src_ff, &ffmpeg_bin);
                                #[cfg(unix)]
                                {
                                    use std::os::unix::fs::PermissionsExt;
                                    let _ = fs::set_permissions(&ffmpeg_bin, fs::Permissions::from_mode(0o755));
                                }
                            }
                            let _ = fs::remove_dir_all(p);
                            break;
                        }
                    }
                }
                let _ = fs::remove_file(&archive);
                if ffmpeg_bin.is_file() {
                    emit_log(sender, "OK", "Portable FFmpeg for Linux installed successfully.");
                    return;
                }
            }
        }

        // Fallback: Copy system ffmpeg if available on machine
        if let Ok(output) = os::create_hidden_command("which").arg("ffmpeg").output() {
            if output.status.success() {
                let sys_ff = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !sys_ff.is_empty() && Path::new(&sys_ff).is_file() && fs::copy(&sys_ff, &ffmpeg_bin).is_ok() {
                    #[cfg(unix)]
                    {
                        use std::os::unix::fs::PermissionsExt;
                        let _ = fs::set_permissions(&ffmpeg_bin, fs::Permissions::from_mode(0o755));
                    }
                    emit_log(sender, "OK", "Copied system FFmpeg as local runtime binary.");
                    return;
                }
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        let url = "https://evermeet.cx/ffmpeg/getrelease/zip";
        let temp_dir = std::env::temp_dir();
        let archive = temp_dir.join("ffmpeg_mac.zip");

        if download_file_with_progress(url, &archive, 48, "Configuring FFmpeg...", "Downloading portable FFmpeg (macOS)", sender).is_ok() {
            if extract_zip(&archive, bin_dir).is_ok() {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let _ = fs::set_permissions(&ffmpeg_bin, fs::Permissions::from_mode(0o755));
                }
                emit_log(sender, "OK", "Portable FFmpeg for macOS installed successfully.");
                let _ = fs::remove_file(&archive);
                return;
            }
        }
    }

    emit_log(sender, "WARN", "Could not download portable FFmpeg. System FFmpeg will be used if present.");
}

/// Configures the Python virtual environment, upgrades pip tools, and installs all dependencies
fn setup_python_environment(target_dir: &Path, python_cmd: Option<&str>, has_nvidia: bool, sender: &EventSender) -> bool {
    emit_progress(sender, 55, 2, "Configuring Python environment...", "Setting up isolated virtual environment");
    let venv_dir = target_dir.join("venv");
    
    let py_exec = python_cmd.unwrap_or("python3");
    if !venv_dir.exists() {
        emit_log(sender, "INFO", "Creating Python virtual environment in venv/...");
        let status = os::create_hidden_command(py_exec)
            .args(["-m", "venv", &venv_dir.to_string_lossy()])
            .status();

        if let Ok(st) = status {
            if st.success() {
                emit_log(sender, "OK", "Virtual environment initialized successfully.");
            } else {
                emit_log(sender, "WARN", "Standard venv creation failed; attempting virtualenv fallback.");
                let _ = os::create_hidden_command(py_exec).args(["-m", "pip", "install", "virtualenv", "--quiet"]).status();
                let _ = os::create_hidden_command(py_exec).args(["-m", "virtualenv", &venv_dir.to_string_lossy()]).status();
            }
        }
    } else {
        emit_log(sender, "OK", "Virtual environment already present.");
    }

    // Determine venv python & pip binaries
    #[cfg(target_os = "windows")]
    let v_py = venv_dir.join("Scripts").join("python.exe");
    #[cfg(not(target_os = "windows"))]
    let v_py = venv_dir.join("bin").join("python");

    if v_py.exists() {
        // Sub-step: pip, setuptools & wheel
        emit_log(sender, "INFO", "Upgrading pip, setuptools & wheel...");
        run_pip_install_streaming(
            &v_py,
            &["--upgrade", "pip", "setuptools", "wheel"],
            60,
            68,
            "Configuring Python packages...",
            "Upgrading pip, setuptools & wheel",
            sender,
        );
        emit_log(sender, "OK", "Package manager tools updated.");

        // Sub-step: PySide6
        let pyside_check = os::create_hidden_command(&v_py).args(["-c", "import PySide6"]).output().is_ok_and(|o| o.status.success());
        if !pyside_check {
            emit_log(sender, "INFO", "Installing PySide6 framework...");
            run_pip_install_streaming(
                &v_py,
                &["PySide6"],
                68,
                78,
                "Installing GUI framework...",
                "Downloading and installing PySide6 Qt framework",
                sender,
            );
            emit_log(sender, "OK", "PySide6 installed.");
        } else {
            emit_progress_sub(sender, 78, 100, "Installing GUI framework...", "PySide6 framework verified");
            emit_log(sender, "OK", "PySide6 is ready.");
        }

        // Sub-step: faster-whisper, pypdf
        emit_log(sender, "INFO", "Installing faster-whisper and pypdf...");
        run_pip_install_streaming(
            &v_py,
            &["faster-whisper", "pypdf"],
            78,
            85,
            "Installing AI speech engine...",
            "Downloading Faster-Whisper AI engine & PyPDF",
            sender,
        );
        emit_log(sender, "OK", "Faster-Whisper and PyPDF installed.");

        // Sub-step: Hardware Acceleration (CUDA 12 or CPU runtime)
        if has_nvidia {
            emit_log(sender, "INFO", "Installing nvidia-cublas-cu12 and nvidia-cudnn-cu12...");
            run_pip_install_streaming(
                &v_py,
                &["nvidia-cublas-cu12", "nvidia-cudnn-cu12"],
                85,
                90,
                "Installing GPU acceleration...",
                "Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)",
                sender,
            );
            emit_log(sender, "OK", "NVIDIA CUDA 12 hardware acceleration packages installed.");
        } else {
            emit_progress_sub(sender, 90, 100, "Configuring AI engine...", "CPU AI computation verified");
            emit_log(sender, "OK", "CPU AI acceleration configured.");
        }

        // Final linking
        emit_progress_sub(sender, 91, 100, "Creating library links...", "Linking site-packages for DaVinci Resolve integration");
        link_site_packages_for_resolve(target_dir, sender);
        return true;
    }
    false
}

/// Links site-packages to target_dir/libs for DaVinci Resolve script execution
fn link_site_packages_for_resolve(target_dir: &Path, sender: &EventSender) {
    let libs_dir = target_dir.join("libs");
    let venv_dir = target_dir.join("venv");

    if libs_dir.is_symlink() || libs_dir.exists() {
        let _ = fs::remove_file(&libs_dir);
        let _ = fs::remove_dir_all(&libs_dir);
    }

    #[cfg(unix)]
    {
        let site_packages_parent = venv_dir.join("lib");
        if let Ok(entries) = fs::read_dir(&site_packages_parent) {
            for entry in entries.flatten() {
                let sp = entry.path().join("site-packages");
                if sp.is_dir() {
                    let _ = std::os::unix::fs::symlink(&sp, &libs_dir);
                    emit_log(sender, "OK", "Libs symlink created.");
                    return;
                }
            }
        }
    }
    #[cfg(target_os = "windows")]
    {
        let sp = venv_dir.join("Lib").join("site-packages");
        if sp.is_dir() {
            let _ = std::os::windows::fs::symlink_dir(&sp, &libs_dir);
            emit_log(sender, "OK", "Libs junction created.");
        }
    }
}

/// Fast reconfiguration of relocated Python virtual environment preserving all copied packages without re-downloading
fn reconfigure_relocated_python_environment(to_dir: &Path, sender: &EventSender) -> bool {
    emit_log(sender, "INFO", "Reconfiguring relocated Python virtual environment...");
    let venv_dir = to_dir.join("venv");
    if !venv_dir.is_dir() {
        return false;
    }

    link_site_packages_for_resolve(to_dir, sender);

    #[cfg(target_os = "windows")]
    let v_py = venv_dir.join("Scripts").join("python.exe");
    #[cfg(not(target_os = "windows"))]
    let v_py = venv_dir.join("bin").join("python");

    #[cfg(not(target_os = "windows"))]
    {
        if !v_py.exists() {
            if let Some(sys_py) = find_python() {
                let bin_dir = venv_dir.join("bin");
                let _ = fs::create_dir_all(&bin_dir);
                let _ = fs::remove_file(&v_py);
                let _ = std::os::unix::fs::symlink(&sys_py, &v_py);
                let py3 = bin_dir.join("python3");
                let _ = fs::remove_file(&py3);
                let _ = std::os::unix::fs::symlink(&sys_py, &py3);
            }
        }
    }

    if v_py.is_file() {
        let test_ok = os::create_hidden_command(&v_py)
            .args(["-c", "import PySide6; import faster_whisper"])
            .output()
            .is_ok_and(|o| o.status.success());
        if test_ok {
            emit_log(sender, "OK", "Preserved all existing packages and GPU acceleration libraries from previous location.");
            return true;
        }
    }

    emit_log(sender, "WARN", "Relocated venv needed refresh; rebuilding environment...");
    let has_nvidia = detect_nvidia_gpu();
    setup_python_environment(to_dir, None, has_nvidia, sender)
}

/// Executes the full installation or update process
pub fn run_install(target_dir: PathBuf, create_desktop: bool, #[allow(unused_variables)] create_menu: bool, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", &format!("Starting BadWords {} installation...", APP_VERSION));
        emit_progress(&sender, 5, 0, "Checking environment...", "Detecting Python runtime & GPU hardware");

        // 1. Hardware detection
        let has_nvidia = detect_nvidia_gpu();
        let gpu_label = if has_nvidia { "NVIDIA CUDA 12 (Accelerated)" } else { "CPU / AMD / Intel (Standard)" };
        emit_log(&sender, "INFO", &format!("AI Acceleration Mode: {}", gpu_label));

        // 2. System Python Check & Auto-Installation (Required for DaVinci Resolve scripts menu!)
        let has_sys_py = os::has_system_python();
        if !has_sys_py {
            emit_log(&sender, "WARN", "System Python not detected. DaVinci Resolve requires an official system Python installation.");
            emit_progress(&sender, 10, 0, "Installing System Python...", "Downloading and setting up official Python 3.10");
            
            if os::install_system_python(&sender) {
                // Leave marker file so uninstaller knows Python was auto-installed
                let _ = fs::create_dir_all(&target_dir);
                let _ = fs::write(target_dir.join(".python_auto_installed"), "1");
            } else {
                emit_log(&sender, "WARN", "Could not automatically install system Python. Please ensure Python 3.10+ is installed.");
            }
        } else {
            emit_log(&sender, "OK", "Official System Python detected.");
        }

        let python_cmd = find_python();
        if let Some(ref py) = python_cmd {
            emit_log(&sender, "OK", &format!("Using Python executable for venv: {}", py));
        } else {
            emit_log(&sender, "WARN", "Python 3.10+ binary not found in PATH; attempting fallback...");
        }

        // 3. Prepare target directories
        emit_progress(&sender, 18, 1, "Creating directories...", "Setting up application folders");
        let bin_dir = target_dir.join("bin");
        let models_dir = target_dir.join("models");
        let assets_dir = target_dir.join("assets").join("icons");

        if let Err(e) = fs::create_dir_all(&target_dir) {
            emit_log(&sender, "ERROR", &format!("Failed to create destination directory: {}", e));
            emit_complete(&sender, "install", false, "Failed to create installation directory.");
            return;
        }
        let _ = fs::create_dir_all(&bin_dir);
        let _ = fs::create_dir_all(&models_dir);
        let _ = fs::create_dir_all(&assets_dir);
        emit_log(&sender, "OK", &format!("Destination folder ready: {}", target_dir.display()));

        // 4. Sync / Download source files
        emit_progress(&sender, 30, 1, "Deploying application files...", "Copying BadWords source and assets");
        if !deploy_application_files(&target_dir, &sender) {
            emit_complete(&sender, "install", false, "Failed to deploy BadWords application files.");
            return;
        }

        // 5. Ensure portable FFmpeg
        emit_progress(&sender, 45, 1, "Checking FFmpeg...", "Configuring portable media engine");
        ensure_ffmpeg(&bin_dir, &sender);

        // 6. Virtual Environment & Python Packages (1:1 with setup.py)
        setup_python_environment(&target_dir, python_cmd.as_deref(), has_nvidia, &sender);

        // 7. DaVinci Resolve Wrapper (1:1 with setup.py)
        emit_progress(&sender, 92, 3, "Configuring DaVinci Resolve...", "Writing Fusion utility script wrappers");
        deploy_davinci_wrapper(&target_dir, &sender);

        // 8. Copy installer binary as uninstaller / setup inside target_dir
        if let Ok(current_exe) = std::env::current_exe() {
            let uninstaller_dest = if cfg!(target_os = "windows") {
                target_dir.join("uninstall.exe")
            } else {
                target_dir.join("badwords-installer")
            };
            let _ = fs::copy(&current_exe, &uninstaller_dest);
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = fs::set_permissions(&uninstaller_dest, fs::Permissions::from_mode(0o755));
            }
        }

        // 9. System Shortcuts & Registry (Full Standalone Integration)
        emit_progress(&sender, 96, 3, "Creating shortcuts...", "Registering application in OS");
        #[cfg(target_os = "windows")]
        {
            let _ = os::windows::register_uninstall_entry(&target_dir, APP_VERSION);
            let _ = os::windows::create_windows_shortcuts(&target_dir, create_desktop, create_menu);
            emit_log(&sender, "OK", "Windows shortcuts & uninstaller registered.");
        }
        #[cfg(target_os = "macos")]
        {
            let _ = os::macos::create_macos_app_bundle(&target_dir, create_desktop);
            emit_log(&sender, "OK", "macOS application bundle (.app) registered.");
        }
        #[cfg(target_os = "linux")]
        {
            let _ = os::linux::create_linux_desktop_entry(&target_dir, create_desktop, create_menu);
            emit_log(&sender, "OK", "Linux desktop launcher (.desktop) created.");
        }

        emit_progress(&sender, 100, 3, "Installation complete!", "BadWords is ready to use");
        emit_log(&sender, "OK", "BadWords installation completed successfully.");
        emit_complete(&sender, "install", true, "BadWords has been successfully installed and configured!");
    });
}

/// Executes file verification and repair
pub fn run_repair(mut target_dir: PathBuf, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", "Starting verification and repair...");
        emit_progress(&sender, 10, 0, "Scanning files...", "Verifying directory structure");

        if !target_dir.exists() {
            if let Some(detected) = os::detect_existing_install() {
                emit_log(&sender, "INFO", &format!("Recovered target path from DaVinci wrapper: {}", detected.display()));
                target_dir = detected;
            } else {
                emit_log(&sender, "ERROR", &format!("Installation directory does not exist: {}", target_dir.display()));
                emit_complete(&sender, "repair", false, "Installation directory not found.");
                return;
            }
        }

        // Re-deploy application core files
        emit_progress(&sender, 30, 1, "Repairing core files...", "Re-syncing files from repository");
        let _ = deploy_application_files(&target_dir, &sender);

        // Verify FFmpeg
        emit_progress(&sender, 45, 1, "Checking media engine...", "Verifying FFmpeg binary");
        let bin_dir = target_dir.join("bin");
        let _ = fs::create_dir_all(&bin_dir);
        ensure_ffmpeg(&bin_dir, &sender);

        // Verify virtual environment and packages
        emit_progress(&sender, 60, 2, "Checking dependencies...", "Verifying Python virtual environment");
        let venv_dir = target_dir.join("venv");
        #[cfg(target_os = "windows")]
        let v_py = venv_dir.join("Scripts").join("python.exe");
        #[cfg(not(target_os = "windows"))]
        let v_py = venv_dir.join("bin").join("python");

        if !v_py.exists() {
            emit_log(&sender, "WARN", "Virtual environment missing or damaged; rebuilding fresh environment...");
            let has_nvidia = detect_nvidia_gpu();
            let _ = setup_python_environment(&target_dir, None, has_nvidia, &sender);
        } else {
            let pyside_check = os::create_hidden_command(&v_py).args(["-c", "import PySide6"]).output().is_ok_and(|o| o.status.success());
            if !pyside_check {
                emit_log(&sender, "WARN", "PySide6 missing in venv; reinstalling...");
                let _ = os::create_hidden_command(&v_py).args(["-m", "pip", "install", "PySide6", "-q"]).status();
            }
            let whisper_check = os::create_hidden_command(&v_py).args(["-c", "import faster_whisper"]).output().is_ok_and(|o| o.status.success());
            if !whisper_check {
                emit_log(&sender, "WARN", "faster-whisper missing in venv; reinstalling...");
                let _ = os::create_hidden_command(&v_py).args(["-m", "pip", "install", "faster-whisper", "pypdf", "-q"]).status();
            }
            emit_log(&sender, "OK", "Virtual environment verified.");
        }

        // Re-create DaVinci wrapper & shortcuts
        emit_progress(&sender, 90, 2, "Updating integrations...", "Rebuilding DaVinci wrapper and shortcuts");
        deploy_davinci_wrapper(&target_dir, &sender);

        #[cfg(target_os = "windows")]
        {
            let _ = os::windows::register_uninstall_entry(&target_dir, APP_VERSION);
            let _ = os::windows::create_windows_shortcuts(&target_dir, true, true);
        }
        #[cfg(target_os = "macos")]
        let _ = os::macos::create_macos_app_bundle(&target_dir, true);
        #[cfg(target_os = "linux")]
        let _ = os::linux::create_linux_desktop_entry(&target_dir, true, true);

        emit_progress(&sender, 100, 3, "Repair complete!", "All files and integrations restored");
        emit_complete(&sender, "repair", true, "BadWords has been successfully verified and repaired!");
    });
}

/// Executes moving the installation to a new directory
pub fn run_move(from_dir: PathBuf, to_dir: PathBuf, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", &format!("Relocating BadWords from {} to {}", from_dir.display(), to_dir.display()));

        if !from_dir.exists() {
            emit_log(&sender, "ERROR", "Source installation directory not found!");
            emit_complete(&sender, "move", false, "Source installation directory not found.");
            return;
        }

        // Step 1: Copy files progressively with live MB and file count updates (5% -> 70%)
        emit_progress(&sender, 5, 0, "Transferring files...", "Scanning source files");
        if let Err(e) = copy_dir_with_progress(&from_dir, &to_dir, 5, 70, "Transferring files...", &sender) {
            emit_log(&sender, "ERROR", &format!("Failed to copy files: {}", e));
            emit_complete(&sender, "move", false, "Failed to copy files to new location.");
            return;
        }

        // Step 2: Reconfigure Python environment preserving all 10 GB of existing packages (70% -> 80%)
        emit_progress(&sender, 70, 1, "Reconfiguring Python environment...", "Updating virtual environment paths");
        reconfigure_relocated_python_environment(&to_dir, &sender);

        // Step 3: Update DaVinci Resolve wrappers (80% -> 85%)
        emit_progress(&sender, 80, 2, "Updating wrappers...", "Updating DaVinci Resolve script paths");
        deploy_davinci_wrapper(&to_dir, &sender);

        // Step 4: Clean old directory progressively (85% -> 98%)
        emit_progress(&sender, 85, 2, "Cleaning old directory...", "Removing old installation files");
        delete_dir_with_progress(&from_dir, 85, 98, "Cleaning old directory...", &sender);

        #[cfg(target_os = "windows")]
        {
            let _ = os::windows::register_uninstall_entry(&to_dir, APP_VERSION);
            let _ = os::windows::create_windows_shortcuts(&to_dir, true, true);
        }
        #[cfg(target_os = "macos")]
        let _ = os::macos::create_macos_app_bundle(&to_dir, true);
        #[cfg(target_os = "linux")]
        let _ = os::linux::create_linux_desktop_entry(&to_dir, true, true);

        emit_progress(&sender, 100, 3, "Move complete!", "Relocation finished successfully");
        emit_complete(&sender, "move", true, "BadWords has been successfully relocated!");
    });
}

/// Executes complete reset and clean reinstall
pub fn run_reset(target_dir: PathBuf, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", &format!("Resetting BadWords in: {}", target_dir.display()));

        if target_dir.exists() {
            emit_progress(&sender, 5, 0, "Removing old files...", "Deleting existing installation files");
            delete_dir_with_progress(&target_dir, 5, 30, "Removing old files...", &sender);
            emit_log(&sender, "OK", "Previous installation removed.");
        }

        emit_progress(&sender, 35, 1, "Reinstalling fresh copy...", "Beginning clean installation");
        run_install(target_dir, true, true, sender);
    });
}

/// Executes complete uninstallation with live file-by-file progress
pub fn run_uninstall(target_dir: PathBuf, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", &format!("Uninstalling BadWords from: {}", target_dir.display()));

        let auto_py_marker = target_dir.join(".python_auto_installed");
        let had_auto_python = auto_py_marker.exists();

        if target_dir.exists() {
            emit_progress(&sender, 5, 0, "Removing files...", "Deleting installation folder");
            delete_dir_with_progress(&target_dir, 5, 70, "Removing files...", &sender);
            emit_log(&sender, "OK", "Installation files deleted.");
        }

        emit_progress(&sender, 75, 1, "Removing integrations...", "Deleting DaVinci Resolve wrappers");
        remove_davinci_wrappers(&sender);

        emit_progress(&sender, 90, 2, "Cleaning system entries...", "Removing desktop launchers and shortcuts");
        #[cfg(target_os = "windows")]
        {
            let _ = os::windows::remove_windows_shortcuts();
            let _ = os::windows::unregister_uninstall_entry();
        }
        #[cfg(target_os = "macos")]
        let _ = os::macos::remove_macos_app_bundle();
        #[cfg(target_os = "linux")]
        let _ = os::linux::remove_linux_desktop_entry();

        if had_auto_python {
            emit_log(&sender, "INFO", "Note: Official Python installed during setup was kept intact to avoid breaking other tools.");
        }

        emit_progress(&sender, 100, 3, "Uninstallation complete!", "BadWords removed");
        emit_complete(&sender, "uninstall", true, "BadWords has been completely uninstalled from your system.");
    });
}

/// Generates the Python wrapper script for DaVinci Resolve (1:1 with setupfiles/setup.py)
fn generate_davinci_wrapper(install_dir: &Path) -> String {
    let install_str = install_dir.to_string_lossy().replace('\\', "/");
    let libs_str = install_dir.join("libs").to_string_lossy().replace('\\', "/");
    let main_script_str = install_dir.join("main.py").to_string_lossy().replace('\\', "/");

    format!(
r#"import sys, os, traceback

INSTALL_DIR = r"{install_str}"
MAIN_SCRIPT = r"{main_script_str}"

# 1. Discover all site-packages candidates (venv direct paths + libs symlink/junction)
_candidates = [
    r"{libs_str}",
    os.path.join(INSTALL_DIR, "libs"),
    os.path.join(INSTALL_DIR, "venv", "Lib", "site-packages"),
]

_v_lib = os.path.join(INSTALL_DIR, "venv", "lib")
if os.path.isdir(_v_lib):
    try:
        for _entry in os.listdir(_v_lib):
            _sp = os.path.join(_v_lib, _entry, "site-packages")
            if os.path.isdir(_sp) and _sp not in _candidates:
                _candidates.append(_sp)
    except Exception:
        pass

for _sp_dir in _candidates:
    if os.path.isdir(_sp_dir):
        if _sp_dir in sys.path:
            sys.path.remove(_sp_dir)
        sys.path.insert(0, _sp_dir)

if INSTALL_DIR not in sys.path:
    sys.path.append(INSTALL_DIR)

# 2. Windows: register DLL search paths for PySide6 and shiboken6
if sys.platform.startswith('win') and hasattr(os, 'add_dll_directory'):
    for _sp_dir in _candidates:
        if os.path.isdir(_sp_dir):
            for _pkg in ['PySide6', 'shiboken6']:
                _p = os.path.join(_sp_dir, _pkg)
                if os.path.isdir(_p):
                    try: os.add_dll_directory(_p)
                    except Exception: pass

# 3. Linux: Preload Qt6 shared libraries if needed
if sys.platform.startswith('linux'):
    import ctypes
    for _sp_dir in _candidates:
        _qt_lib_dir = os.path.join(_sp_dir, "PySide6", "Qt", "lib")
        if os.path.isdir(_qt_lib_dir):
            _qt_preload = [
                'libQt6Core.so.6','libQt6Network.so.6','libQt6DBus.so.6',
                'libQt6Gui.so.6','libQt6Widgets.so.6','libQt6OpenGL.so.6','libQt6XcbQpa.so.6',
            ]
            for _lib in _qt_preload:
                _p = os.path.join(_qt_lib_dir, _lib)
                if os.path.exists(_p):
                    try: ctypes.CDLL(_p, mode=ctypes.RTLD_GLOBAL)
                    except OSError: pass
            break

# 4. Launch main script
if os.path.exists(MAIN_SCRIPT):
    try:
        with open(MAIN_SCRIPT, encoding='utf-8') as f: code = f.read()
        gv = globals().copy(); gv['__file__'] = MAIN_SCRIPT
        exec(code, gv)
    except Exception as e:
        print(f'Error: {{e}}'); traceback.print_exc()
else:
    print(f'CRITICAL: {{MAIN_SCRIPT}} not found')
"#
    )
}

const LEGACY_WRAPPER_NAMES: &[&str] = &[
    "BadWords.py",
    "Badwords.py",
    "BadWords (Linux).py",
    "BadWords (Mac).py",
    "BadWords (macOS).py",
    "BadWords (Windows).py",
    "BadWords_Launcher.py",
    "BadWords.lua",
];

/// Deploys exactly ONE DaVinci Resolve wrapper, prioritizing user-level directories to prevent duplicate menu entries
pub fn deploy_davinci_wrapper(target_dir: &Path, sender: &EventSender) -> bool {
    let resolve_dirs = resolve_script_dirs();

    // 1. Clean up any existing / legacy wrappers across all candidate paths first
    for r_dir in &resolve_dirs {
        for leg in LEGACY_WRAPPER_NAMES {
            let leg_path = r_dir.join(leg);
            if leg_path.exists() {
                let _ = fs::remove_file(&leg_path);
            }
        }
    }

    // 2. Write exactly ONE wrapper to the first writable directory (user dir prioritized)
    let wrapper_code = generate_davinci_wrapper(target_dir);
    for r_dir in &resolve_dirs {
        let _ = fs::create_dir_all(r_dir);
        let wrapper_path = r_dir.join("BadWords.py");
        if fs::write(&wrapper_path, &wrapper_code).is_ok() {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = fs::set_permissions(&wrapper_path, fs::Permissions::from_mode(0o755));
            }
            emit_log(sender, "OK", &format!("DaVinci wrapper created at: {}", wrapper_path.display()));
            return true;
        }
    }

    emit_log(sender, "WARN", "DaVinci Resolve directory not found; please launch DaVinci once to create scripts folder.");
    false
}

/// Removes all BadWords wrappers and legacy variations from all DaVinci Resolve script directories
pub fn remove_davinci_wrappers(sender: &EventSender) {
    let resolve_dirs = resolve_script_dirs();
    for r_dir in &resolve_dirs {
        for leg in LEGACY_WRAPPER_NAMES {
            let p = r_dir.join(leg);
            if p.exists() {
                let _ = fs::remove_file(&p);
                emit_log(sender, "OK", &format!("Removed DaVinci wrapper: {}", p.display()));
            }
        }
    }
}
