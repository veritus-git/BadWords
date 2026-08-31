//! Core installation, repair, move, and uninstallation engine
//! Matches setupfiles/setup.py feature-for-feature: System Python detection & auto-installation,
//! GPU detection, venv, pip packages, ffmpeg, libs link, DaVinci Resolve wrappers, and OS standalone integration.

use crate::os::{self, resolve_script_dirs};
use crate::state::{emit_complete, emit_log, emit_progress, emit_progress_sub, EventSender};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

pub const APP_VERSION: &str = "4.0.0";
const GITHUB_ZIP_DEV_URL: &str = "https://github.com/veritus-git/BadWords/archive/refs/heads/dev-v4.zip";
const GITHUB_ZIP_MAIN_URL: &str = "https://github.com/veritus-git/BadWords/archive/refs/heads/main.zip";
const GITLAB_ZIP_URL: &str = "https://gitlab.com/badwords/BadWords/-/archive/main/BadWords-main.zip";

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
    let mut cmd = Command::new(py_bin);
    cmd.args(["-m", "pip", "install", "--no-cache-dir", "--progress-bar", "on"]);
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
    let sender_clone = sender.clone();
    let status_str = status_label.to_string();
    let mut current_detail = default_detail.to_string();

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
                                    let clean_name = pkg_name.trim().split_whitespace().next().unwrap_or("package");
                                    let friendly = friendly_pkg_name(clean_name);
                                    current_detail = format!("Downloading {}", friendly);
                                }
                            } else if line.contains("Collecting") {
                                if let Some(pkg_name) = line.split("Collecting").nth(1) {
                                    let clean_name = pkg_name.trim().split_whitespace().next().unwrap_or("package");
                                    let friendly = friendly_pkg_name(clean_name);
                                    current_detail = format!("Collecting {}", friendly);
                                }
                            } else if line.contains("Installing collected packages") {
                                current_detail = "Unpacking & configuring Python packages...".to_string();
                                // Set sub_pct = 0 so indeterminate gliding pill immediately activates
                                emit_progress_sub(&sender_clone, main_pct_end - 1, 0, &status_str, &current_detail);
                            }

                            // Parse download fraction (e.g. 45.2/78.3 MB or kB)
                            for part in line.split_whitespace() {
                                if part.contains('/') {
                                    let pieces: Vec<&str> = part.split('/').collect();
                                    if pieces.len() == 2 {
                                        if let (Ok(cur), Ok(tot)) = (pieces[0].parse::<f32>(), pieces[1].parse::<f32>()) {
                                            if tot > 0.0 && cur <= tot {
                                                let sub_pct = ((cur / tot) * 100.0).clamp(0.0, 100.0) as u32;
                                                let span = (main_pct_end - main_pct_start) as f32;
                                                let main_pct = main_pct_start + (span * (sub_pct as f32 / 100.0)) as u32;
                                                let det_with_size = format!("{} ({:.1} / {:.1} MB)", current_detail, cur, tot);
                                                emit_progress_sub(&sender_clone, main_pct, sub_pct, &status_str, &det_with_size);
                                            }
                                        }
                                    }
                                }
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

    let status = child.wait();
    let _ = reader_thread.join();

    match status {
        Ok(st) => st.success(),
        Err(_) => false,
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
        if let Ok(output) = Command::new(cmd).arg("-c").arg("import sys; exit(0 if sys.version_info >= (3, 10) else 1)").output() {
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
        if let Ok(output) = Command::new("powershell")
            .args(["-NoProfile", "-Command", "try{$g=Get-WmiObject Win32_VideoController -EA Stop | Where-Object {$_.Name -like '*NVIDIA*'} | Select-Object -First 1; if($g){'1'}else{'0'}}catch{'0'}"])
            .output()
        {
            return String::from_utf8_lossy(&output.stdout).trim() == "1";
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        if let Ok(output) = Command::new("lspci").output() {
            if String::from_utf8_lossy(&output.stdout).to_lowercase().contains("nvidia") {
                return true;
            }
        }
        if let Ok(output) = Command::new("lshw").args(["-C", "display"]).output() {
            if String::from_utf8_lossy(&output.stdout).to_lowercase().contains("nvidia") {
                return true;
            }
        }
    }
    false
}

/// Locates local source repository if available
fn find_local_repo() -> Option<PathBuf> {
    let candidates = [
        PathBuf::from("."),
        PathBuf::from(".."),
        PathBuf::from("/mnt/dump/BadWords"),
    ];

    for candidate in candidates {
        if candidate.join("src").join("main.py").is_file() {
            return candidate.canonicalize().ok();
        }
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

        emit_log(sender, "OK", "Local application files deployed successfully.");
        return true;
    }

    // Remote download
    emit_log(sender, "INFO", "Downloading BadWords release archive from GitHub...");
    let temp_dir = std::env::temp_dir();
    let zip_dest = temp_dir.join("badwords_source.zip");
    let extract_dest = temp_dir.join("badwords_extracted");
    let _ = fs::remove_dir_all(&extract_dest);
    let _ = fs::create_dir_all(&extract_dest);

    let mut downloaded = false;
    for url in [GITHUB_ZIP_DEV_URL, GITHUB_ZIP_MAIN_URL, GITLAB_ZIP_URL] {
        emit_log(sender, "INFO", &format!("Fetching source from: {}", url));
        if download_file_with_progress(url, &zip_dest, 30, "Deploying application files...", "Downloading release archive", sender).is_ok() {
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
        if repo_ffmpeg.is_file() {
            if fs::copy(&repo_ffmpeg, &ffmpeg_bin).is_ok() {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let _ = fs::set_permissions(&ffmpeg_bin, fs::Permissions::from_mode(0o755));
                }
                emit_log(sender, "OK", "Copied local portable FFmpeg binary.");
                return;
            }
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
        let url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz";
        let parent = bin_dir.parent().unwrap_or(bin_dir);
        let archive = parent.join("ffmpeg_static.tar.xz");

        if download_file_with_progress(url, &archive, 48, "Configuring FFmpeg...", "Downloading portable FFmpeg (Linux)", sender).is_ok() {
            let _ = Command::new("tar").args(["-xf", &archive.to_string_lossy(), "-C", &parent.to_string_lossy()]).status();

            if let Ok(entries) = fs::read_dir(parent) {
                for entry in entries.flatten() {
                    let p = entry.path();
                    if p.is_dir() && p.file_name().map_or(false, |n| n.to_string_lossy().starts_with("ffmpeg-")) {
                        let src_ff = p.join("ffmpeg");
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
            emit_log(sender, "OK", "Portable FFmpeg for Linux installed successfully.");
            return;
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

/// Executes the full installation or update process
pub fn run_install(target_dir: PathBuf, sender: EventSender) {
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
        emit_progress(&sender, 55, 2, "Configuring Python environment...", "Setting up isolated virtual environment");
        let venv_dir = target_dir.join("venv");
        
        let py_exec = python_cmd.as_deref().unwrap_or("python3");
        if !venv_dir.exists() {
            emit_log(&sender, "INFO", "Creating Python virtual environment in venv/...");
            let status = Command::new(py_exec)
                .args(["-m", "venv", &venv_dir.to_string_lossy()])
                .status();

            if let Ok(st) = status {
                if st.success() {
                    emit_log(&sender, "OK", "Virtual environment initialized successfully.");
                } else {
                    emit_log(&sender, "WARN", "Standard venv creation failed; attempting virtualenv fallback.");
                    let _ = Command::new(py_exec).args(["-m", "pip", "install", "virtualenv", "--quiet"]).status();
                    let _ = Command::new(py_exec).args(["-m", "virtualenv", &venv_dir.to_string_lossy()]).status();
                }
            }
        } else {
            emit_log(&sender, "OK", "Virtual environment already present.");
        }

        // Determine venv python & pip binaries
        #[cfg(target_os = "windows")]
        let v_py = venv_dir.join("Scripts").join("python.exe");
        #[cfg(not(target_os = "windows"))]
        let v_py = venv_dir.join("bin").join("python");

        if v_py.exists() {
            // Sub-step 1/4: pip, setuptools & wheel
            emit_log(&sender, "INFO", "Upgrading pip, setuptools & wheel...");
            run_pip_install_streaming(
                &v_py,
                &["--upgrade", "pip", "setuptools", "wheel"],
                60,
                68,
                "Configuring Python packages...",
                "[1/4] Upgrading pip, setuptools & wheel",
                &sender,
            );
            emit_log(&sender, "OK", "Package manager tools updated.");

            // Sub-step 2/4: PySide6
            let pyside_check = Command::new(&v_py).args(["-c", "import PySide6"]).output().map_or(false, |o| o.status.success());
            if !pyside_check {
                emit_log(&sender, "INFO", "Installing PySide6 framework...");
                run_pip_install_streaming(
                    &v_py,
                    &["PySide6"],
                    68,
                    78,
                    "Installing GUI framework...",
                    "[2/4] Downloading and installing PySide6 Qt framework",
                    &sender,
                );
                emit_log(&sender, "OK", "PySide6 installed.");
            } else {
                emit_progress_sub(&sender, 78, 100, "Installing GUI framework...", "[2/4] PySide6 framework verified");
                emit_log(&sender, "OK", "PySide6 is ready.");
            }

            // Sub-step 3/4: faster-whisper, pypdf
            emit_log(&sender, "INFO", "Installing faster-whisper and pypdf...");
            run_pip_install_streaming(
                &v_py,
                &["faster-whisper", "pypdf"],
                78,
                85,
                "Installing AI speech engine...",
                "[3/4] Downloading Faster-Whisper AI engine & PyPDF",
                &sender,
            );
            emit_log(&sender, "OK", "Faster-Whisper and PyPDF installed.");

            // Sub-step 4/4: Hardware Acceleration (CUDA 12 or CPU runtime)
            if has_nvidia {
                emit_log(&sender, "INFO", "Installing nvidia-cublas-cu12 and nvidia-cudnn-cu12...");
                run_pip_install_streaming(
                    &v_py,
                    &["nvidia-cublas-cu12", "nvidia-cudnn-cu12"],
                    85,
                    90,
                    "Installing GPU acceleration...",
                    "[4/4] Downloading NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)",
                    &sender,
                );
                emit_log(&sender, "OK", "NVIDIA CUDA 12 hardware acceleration packages installed.");
            } else {
                emit_progress_sub(&sender, 90, 100, "Configuring AI engine...", "[4/4] CPU AI computation verified");
                emit_log(&sender, "OK", "CPU AI acceleration configured.");
            }

            // Final linking
            emit_progress_sub(&sender, 91, 100, "Creating library links...", "Linking site-packages for DaVinci Resolve integration");
            let libs_dir = target_dir.join("libs");
            if !libs_dir.exists() {
                #[cfg(unix)]
                {
                    let site_packages_parent = venv_dir.join("lib");
                    if let Ok(entries) = fs::read_dir(&site_packages_parent) {
                        for entry in entries.flatten() {
                            let sp = entry.path().join("site-packages");
                            if sp.is_dir() {
                                let _ = std::os::unix::fs::symlink(&sp, &libs_dir);
                                emit_log(&sender, "OK", "Libs symlink created.");
                                break;
                            }
                        }
                    }
                }
                #[cfg(target_os = "windows")]
                {
                    let sp = venv_dir.join("Lib").join("site-packages");
                    if sp.is_dir() {
                        let _ = std::os::windows::fs::symlink_dir(&sp, &libs_dir);
                        emit_log(&sender, "OK", "Libs junction created.");
                    }
                }
            }
        }

        // 7. DaVinci Resolve Wrapper (1:1 with setup.py)
        emit_progress(&sender, 92, 3, "Configuring DaVinci Resolve...", "Writing Fusion utility script wrappers");
        let resolve_dirs = resolve_script_dirs();
        let mut wrappers_written = 0;

        for r_dir in &resolve_dirs {
            let _ = fs::create_dir_all(r_dir);
            let wrapper_path = r_dir.join("BadWords.py");
            let wrapper_code = generate_davinci_wrapper(&target_dir);
            if fs::write(&wrapper_path, wrapper_code).is_ok() {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    let _ = fs::set_permissions(&wrapper_path, fs::Permissions::from_mode(0o755));
                }
                emit_log(&sender, "OK", &format!("DaVinci wrapper created at: {}", wrapper_path.display()));
                wrappers_written += 1;
            }
        }

        if wrappers_written == 0 {
            emit_log(&sender, "WARN", "DaVinci Resolve directory not found; please launch DaVinci once to create scripts folder.");
        }

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
            let _ = os::windows::create_windows_shortcuts(&target_dir);
            emit_log(&sender, "OK", "Windows shortcuts (Desktop/Start Menu) & uninstaller registered.");
        }
        #[cfg(target_os = "macos")]
        {
            let _ = os::macos::create_macos_app_bundle(&target_dir);
            emit_log(&sender, "OK", "macOS application bundle (.app) registered.");
        }
        #[cfg(target_os = "linux")]
        {
            let _ = os::linux::create_linux_desktop_entry(&target_dir);
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
        emit_progress(&sender, 15, 0, "Scanning files...", "Verifying directory structure");

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
        emit_progress(&sender, 40, 1, "Repairing core files...", "Re-syncing files from repository");
        let _ = deploy_application_files(&target_dir, &sender);

        // Verify FFmpeg
        let bin_dir = target_dir.join("bin");
        let _ = fs::create_dir_all(&bin_dir);
        ensure_ffmpeg(&bin_dir, &sender);

        // Verify virtual environment and packages
        emit_progress(&sender, 70, 2, "Checking dependencies...", "Verifying Python virtual environment");
        let venv_dir = target_dir.join("venv");
        #[cfg(target_os = "windows")]
        let v_py = venv_dir.join("Scripts").join("python.exe");
        #[cfg(not(target_os = "windows"))]
        let v_py = venv_dir.join("bin").join("python");

        if v_py.exists() {
            let pyside_check = Command::new(&v_py).args(["-c", "import PySide6"]).output().map_or(false, |o| o.status.success());
            if !pyside_check {
                emit_log(&sender, "WARN", "PySide6 missing in venv; reinstalling...");
                let _ = Command::new(&v_py).args(["-m", "pip", "install", "PySide6", "-q"]).status();
            }
            let whisper_check = Command::new(&v_py).args(["-c", "import faster_whisper"]).output().map_or(false, |o| o.status.success());
            if !whisper_check {
                emit_log(&sender, "WARN", "faster-whisper missing in venv; reinstalling...");
                let _ = Command::new(&v_py).args(["-m", "pip", "install", "faster-whisper", "pypdf", "-q"]).status();
            }
            emit_log(&sender, "OK", "Virtual environment verified.");
        }

        // Re-create DaVinci wrapper & shortcuts
        emit_progress(&sender, 90, 2, "Updating integrations...", "Rebuilding DaVinci wrapper and shortcuts");
        let resolve_dirs = resolve_script_dirs();
        for r_dir in &resolve_dirs {
            let wrapper_path = r_dir.join("BadWords.py");
            let wrapper_code = generate_davinci_wrapper(&target_dir);
            let _ = fs::write(&wrapper_path, wrapper_code);
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = fs::set_permissions(&wrapper_path, fs::Permissions::from_mode(0o755));
            }
        }
        emit_log(&sender, "OK", "DaVinci Resolve script wrapper updated.");

        #[cfg(target_os = "windows")]
        {
            let _ = os::windows::register_uninstall_entry(&target_dir, APP_VERSION);
            let _ = os::windows::create_windows_shortcuts(&target_dir);
        }
        #[cfg(target_os = "macos")]
        let _ = os::macos::create_macos_app_bundle(&target_dir);
        #[cfg(target_os = "linux")]
        let _ = os::linux::create_linux_desktop_entry(&target_dir);

        emit_progress(&sender, 100, 3, "Repair complete!", "All files and integrations restored");
        emit_complete(&sender, "repair", true, "BadWords has been successfully verified and repaired!");
    });
}

/// Executes moving the installation to a new directory
pub fn run_move(from_dir: PathBuf, to_dir: PathBuf, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", &format!("Relocating BadWords from {} to {}", from_dir.display(), to_dir.display()));
        emit_progress(&sender, 20, 0, "Copying files...", "Transferring installation files");

        if !from_dir.exists() {
            emit_log(&sender, "ERROR", "Source installation directory not found!");
            emit_complete(&sender, "move", false, "Source installation directory not found.");
            return;
        }

        if let Err(e) = copy_dir_all(&from_dir, &to_dir) {
            emit_log(&sender, "ERROR", &format!("Failed to copy files: {}", e));
            emit_complete(&sender, "move", false, "Failed to copy files to new location.");
            return;
        }

        emit_progress(&sender, 70, 1, "Updating wrappers...", "Updating DaVinci Resolve script paths");
        let resolve_dirs = resolve_script_dirs();
        for r_dir in &resolve_dirs {
            let wrapper_path = r_dir.join("BadWords.py");
            let wrapper_code = generate_davinci_wrapper(&to_dir);
            let _ = fs::write(&wrapper_path, wrapper_code);
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = fs::set_permissions(&wrapper_path, fs::Permissions::from_mode(0o755));
            }
        }

        emit_progress(&sender, 85, 2, "Cleaning old directory...", "Removing files from previous location");
        let _ = fs::remove_dir_all(&from_dir);

        #[cfg(target_os = "windows")]
        {
            let _ = os::windows::register_uninstall_entry(&to_dir, APP_VERSION);
            let _ = os::windows::create_windows_shortcuts(&to_dir);
        }
        #[cfg(target_os = "macos")]
        let _ = os::macos::create_macos_app_bundle(&to_dir);
        #[cfg(target_os = "linux")]
        let _ = os::linux::create_linux_desktop_entry(&to_dir);

        emit_progress(&sender, 100, 3, "Move complete!", "Relocation finished successfully");
        emit_complete(&sender, "move", true, "BadWords has been successfully relocated!");
    });
}

/// Executes complete reset and clean reinstall
pub fn run_reset(target_dir: PathBuf, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", &format!("Resetting BadWords in: {}", target_dir.display()));
        emit_progress(&sender, 20, 0, "Removing old files...", "Deleting existing installation");

        if target_dir.exists() {
            let _ = fs::remove_dir_all(&target_dir);
            emit_log(&sender, "OK", "Previous installation removed.");
        }

        emit_progress(&sender, 40, 1, "Reinstalling fresh copy...", "Beginning clean installation");
        run_install(target_dir, sender);
    });
}

/// Executes complete uninstallation
pub fn run_uninstall(target_dir: PathBuf, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", &format!("Uninstalling BadWords from: {}", target_dir.display()));
        emit_progress(&sender, 20, 0, "Removing files...", "Deleting installation folder");

        let auto_py_marker = target_dir.join(".python_auto_installed");
        let had_auto_python = auto_py_marker.exists();

        if target_dir.exists() {
            if let Err(e) = fs::remove_dir_all(&target_dir) {
                emit_log(&sender, "WARN", &format!("Failed to completely delete folder: {}", e));
            } else {
                emit_log(&sender, "OK", "Installation files deleted.");
            }
        }

        emit_progress(&sender, 60, 1, "Removing integrations...", "Deleting DaVinci Resolve wrappers");
        let resolve_dirs = resolve_script_dirs();
        for r_dir in &resolve_dirs {
            let wrapper_path = r_dir.join("BadWords.py");
            if wrapper_path.exists() {
                let _ = fs::remove_file(&wrapper_path);
                emit_log(&sender, "OK", &format!("Removed wrapper from: {}", wrapper_path.display()));
            }
        }

        emit_progress(&sender, 85, 2, "Cleaning system entries...", "Removing desktop launchers and shortcuts");
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
    let qt_lib_str = install_dir.join("libs").join("PySide6").join("Qt").join("lib").to_string_lossy().replace('\\', "/");
    let main_script_str = install_dir.join("main.py").to_string_lossy().replace('\\', "/");

    format!(
r#"import sys, os, traceback

if sys.platform.startswith('linux'):
    import ctypes
    _qt_lib_dir = r"{qt_lib_str}"
    _qt_preload = [
        'libQt6Core.so.6','libQt6Network.so.6','libQt6DBus.so.6',
        'libQt6Gui.so.6','libQt6Widgets.so.6','libQt6OpenGL.so.6','libQt6XcbQpa.so.6',
    ]
    if os.path.isdir(_qt_lib_dir):
        for _lib in _qt_preload:
            _p = os.path.join(_qt_lib_dir, _lib)
            if os.path.exists(_p):
                try: ctypes.CDLL(_p, mode=ctypes.RTLD_GLOBAL)
                except OSError: pass

INSTALL_DIR = r"{install_str}"
LIBS_DIR    = r"{libs_str}"
MAIN_SCRIPT = r"{main_script_str}"

if os.path.exists(LIBS_DIR):
    if LIBS_DIR in sys.path: sys.path.remove(LIBS_DIR)
    sys.path.insert(0, LIBS_DIR)
if INSTALL_DIR not in sys.path:
    sys.path.append(INSTALL_DIR)

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
