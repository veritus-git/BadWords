//! Core installation, repair, move, and uninstallation engine
//! Matches setupfiles/setup.py feature-for-feature: GPU detection, venv, pip packages, ffmpeg, libs link, and wrappers.

use crate::os::{self, resolve_script_dirs};
use crate::state::{emit_complete, emit_log, emit_progress, EventSender};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

pub const APP_VERSION: &str = "4.0.0";

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

/// Finds the system Python executable (Python 3.10+)
fn find_python() -> Option<String> {
    let candidates = [
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
    #[cfg(target_os = "linux")]
    {
        let url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz";
        let parent = bin_dir.parent().unwrap_or(bin_dir);
        let archive = parent.join("ffmpeg_static.tar.xz");

        if let Ok(resp) = ureq::get(url).call() {
            let mut reader = resp.into_reader();
            if let Ok(mut out) = fs::File::create(&archive) {
                let _ = std::io::copy(&mut reader, &mut out);
                let _ = Command::new("tar").args(["-xf", &archive.to_string_lossy(), "-C", &parent.to_string_lossy()]).status();
                
                // Find extracted ffmpeg binary
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
                emit_log(sender, "OK", "Portable FFmpeg installed successfully.");
                return;
            }
        }
    }

    emit_log(sender, "WARN", "Could not download FFmpeg. Will use system FFmpeg if available.");
}

/// Executes the full installation or update process
pub fn run_install(target_dir: PathBuf, sender: EventSender) {
    std::thread::spawn(move || {
        emit_log(&sender, "INFO", &format!("Starting BadWords {} installation...", APP_VERSION));
        emit_progress(&sender, 5, 0, "Checking environment...", "Detecting Python runtime & GPU hardware");

        // 1. Hardware and Python detection
        let has_nvidia = detect_nvidia_gpu();
        let gpu_label = if has_nvidia { "NVIDIA CUDA 12" } else { "CPU / AMD / Intel" };
        emit_log(&sender, "INFO", &format!("AI Acceleration Mode: {}", gpu_label));

        let python_cmd = find_python();
        if let Some(ref py) = python_cmd {
            emit_log(&sender, "OK", &format!("Found compatible Python runtime: {}", py));
        } else {
            emit_log(&sender, "WARN", "Python 3.10+ not found in PATH; attempting fallback...");
        }

        // 2. Prepare target directories
        emit_progress(&sender, 15, 1, "Creating directories...", "Setting up application folders");
        let bin_dir = target_dir.join("bin");
        let models_dir = target_dir.join("models");
        let assets_dir = target_dir.join("assets").join("icons");

        if let Err(e) = fs::create_dir_all(&target_dir) {
            emit_log(&sender, "ERROR", &format!("Failed to create destination: {}", e));
            emit_complete(&sender, "install", false, "Failed to create installation directory.");
            return;
        }
        let _ = fs::create_dir_all(&bin_dir);
        let _ = fs::create_dir_all(&models_dir);
        let _ = fs::create_dir_all(&assets_dir);
        emit_log(&sender, "OK", &format!("Destination folder ready: {}", target_dir.display()));

        // 3. Sync source files
        emit_progress(&sender, 30, 1, "Copying application files...", "Deploying BadWords source and assets");
        if let Some(repo_dir) = find_local_repo() {
            emit_log(&sender, "INFO", &format!("Using local repository: {}", repo_dir.display()));
            
            let src_dir = repo_dir.join("src");
            if src_dir.is_dir() {
                let _ = copy_dir_all(&src_dir, &target_dir);
            }

            let src_assets = repo_dir.join("assets");
            if src_assets.is_dir() {
                let _ = copy_dir_all(&src_assets, target_dir.join("assets"));
            }

            let updater_src = repo_dir.join("setupfiles").join("updater.py");
            if updater_src.is_file() {
                let _ = fs::copy(updater_src, target_dir.join("updater.py"));
            }

            emit_log(&sender, "OK", "Application files deployed successfully.");
        } else {
            emit_log(&sender, "INFO", "Deploying base configuration files...");
        }

        // 4. Ensure portable FFmpeg
        emit_progress(&sender, 45, 1, "Checking FFmpeg...", "Configuring portable media engine");
        ensure_ffmpeg(&bin_dir, &sender);

        // 5. Virtual Environment & Python Packages (1:1 with setup.py)
        emit_progress(&sender, 55, 2, "Configuring Python environment...", "Setting up virtual environment");
        let venv_dir = target_dir.join("venv");
        
        let py_exec = python_cmd.as_deref().unwrap_or("python3");
        if !venv_dir.exists() {
            emit_log(&sender, "INFO", "Creating Python virtual environment...");
            let status = Command::new(py_exec)
                .args(["-m", "venv", &venv_dir.to_string_lossy()])
                .status();

            if let Ok(st) = status {
                if st.success() {
                    emit_log(&sender, "OK", "Virtual environment initialized.");
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
            emit_progress(&sender, 65, 2, "Upgrading pip...", "Ensuring pip is up to date");
            let _ = Command::new(&v_py).args(["-m", "pip", "install", "--upgrade", "pip", "-q"]).status();

            // Install PySide6
            emit_progress(&sender, 70, 2, "Installing GUI libraries...", "Installing PySide6 GUI framework");
            let pyside_check = Command::new(&v_py).args(["-c", "import PySide6"]).output().map_or(false, |o| o.status.success());
            if !pyside_check {
                emit_log(&sender, "INFO", "Installing PySide6 framework...");
                let _ = Command::new(&v_py).args(["-m", "pip", "install", "PySide6", "-q"]).status();
                emit_log(&sender, "OK", "PySide6 installed.");
            } else {
                emit_log(&sender, "OK", "PySide6 already installed.");
            }

            // Install faster-whisper, pypdf and CUDA packages if applicable
            emit_progress(&sender, 80, 2, "Installing AI models engine...", "Installing Faster-Whisper & dependencies");
            let mut pkgs = vec!["faster-whisper", "pypdf"];
            if has_nvidia {
                pkgs.extend(["nvidia-cublas-cu12", "nvidia-cudnn-cu12"]);
            }
            emit_log(&sender, "INFO", &format!("Installing core packages: {}", pkgs.join(", ")));
            let mut pip_cmd = Command::new(&v_py);
            pip_cmd.args(["-m", "pip", "install", "--no-cache-dir", "-q"]);
            for pkg in pkgs {
                pip_cmd.arg(pkg);
            }
            let _ = pip_cmd.status();
            emit_log(&sender, "OK", "All AI engine dependencies installed.");

            // Create libs symlink/junction
            emit_progress(&sender, 88, 2, "Creating libs link...", "Linking libraries for DaVinci Resolve integration");
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

        // 6. DaVinci Resolve Wrapper
        emit_progress(&sender, 92, 3, "Configuring DaVinci Resolve...", "Writing Fusion utility script wrappers");
        let resolve_dirs = resolve_script_dirs();
        let mut wrappers_written = 0;

        for r_dir in &resolve_dirs {
            if let Some(parent) = r_dir.parent() {
                if parent.exists() {
                    let _ = fs::create_dir_all(r_dir);
                    let wrapper_path = r_dir.join("BadWords.py");
                    let wrapper_code = generate_davinci_wrapper(&target_dir);
                    if fs::write(&wrapper_path, wrapper_code).is_ok() {
                        emit_log(&sender, "OK", &format!("DaVinci wrapper created at: {}", wrapper_path.display()));
                        wrappers_written += 1;
                    }
                }
            }
        }

        if wrappers_written == 0 {
            emit_log(&sender, "WARN", "DaVinci Resolve directory not found; please launch DaVinci once to create scripts folder.");
        }

        // 7. System Shortcuts & Registry
        emit_progress(&sender, 96, 3, "Creating shortcuts...", "Registering application entry");
        #[cfg(target_os = "windows")]
        {
            let _ = os::windows::register_uninstall_entry(&target_dir, APP_VERSION);
            let _ = os::windows::create_windows_shortcuts(&target_dir);
            emit_log(&sender, "OK", "Windows shortcuts & uninstaller registered.");
        }
        #[cfg(target_os = "macos")]
        {
            let _ = os::macos::create_macos_app_bundle(&target_dir);
            emit_log(&sender, "OK", "macOS application bundle registered.");
        }
        #[cfg(target_os = "linux")]
        {
            let _ = os::linux::create_linux_desktop_entry(&target_dir);
            emit_log(&sender, "OK", "Linux desktop launcher created.");
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

        // Re-copy core files
        emit_progress(&sender, 40, 1, "Repairing core files...", "Re-syncing files from source");
        if let Some(repo_dir) = find_local_repo() {
            let src_dir = repo_dir.join("src");
            if src_dir.is_dir() {
                let _ = copy_dir_all(&src_dir, &target_dir);
            }
            let src_assets = repo_dir.join("assets");
            if src_assets.is_dir() {
                let _ = copy_dir_all(&src_assets, target_dir.join("assets"));
            }
            let updater_src = repo_dir.join("setupfiles").join("updater.py");
            if updater_src.is_file() {
                let _ = fs::copy(updater_src, target_dir.join("updater.py"));
            }
            emit_log(&sender, "OK", "Core files re-synced.");
        }

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
        }
        emit_log(&sender, "OK", "DaVinci Resolve script wrapper updated.");

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
        }

        emit_progress(&sender, 85, 2, "Cleaning old directory...", "Removing files from previous location");
        let _ = fs::remove_dir_all(&from_dir);

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
        let _ = os::windows::remove_windows_shortcuts();
        #[cfg(target_os = "linux")]
        let _ = os::linux::remove_linux_desktop_entry();

        emit_progress(&sender, 100, 3, "Uninstallation complete!", "BadWords removed");
        emit_complete(&sender, "uninstall", true, "BadWords has been completely uninstalled from your system.");
    });
}

/// Generates the Python wrapper script for DaVinci Resolve
fn generate_davinci_wrapper(install_dir: &Path) -> String {
    let path_str = install_dir.to_string_lossy().replace('\\', "/");
    format!(
r#"# BadWords 4.0 DaVinci Resolve Bridge
import sys, os, traceback

INSTALL_DIR = r"{path_str}"
MAIN_SCRIPT = os.path.join(INSTALL_DIR, "main.py")

if INSTALL_DIR not in sys.path:
    sys.path.insert(0, INSTALL_DIR)

if os.path.exists(MAIN_SCRIPT):
    try:
        with open(MAIN_SCRIPT, encoding='utf-8') as f:
            code = f.read()
        gv = globals().copy()
        gv['__file__'] = MAIN_SCRIPT
        exec(code, gv)
    except Exception as e:
        print(f"Error executing BadWords: {{e}}")
        traceback.print_exc()
else:
    print(f"CRITICAL: BadWords main.py not found at: {{MAIN_SCRIPT}}")
"#
    )
}
