// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! Windows system integration (Registry HKCU, System Python check/install & Shortcuts)

use std::path::{Path, PathBuf};

#[cfg(target_os = "windows")]
use winreg::enums::*;
#[cfg(target_os = "windows")]
use winreg::RegKey;

/// Fast, non-blocking removal of Windows Mark-of-the-Web (Zone.Identifier NTFS ADS).
/// Never spawns PowerShell so installer startup stays instant (<1ms).
pub fn unblock_file_fast(path: &Path) {
    #[cfg(target_os = "windows")]
    {
        if !path.exists() {
            return;
        }
        let ads_path = format!("{}:Zone.Identifier", path.to_string_lossy());
        let _ = std::fs::remove_file(&ads_path);
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = path;
    }
}

/// Shows a native Win32 MessageBoxW when GUI initialization fails outside the bootstrapper,
/// ensuring the installer never vanishes silently under windows_subsystem = "windows".
pub fn show_fatal_error_box(title: &str, message: &str) {
    #[cfg(target_os = "windows")]
    {
        extern "system" {
            fn MessageBoxW(hwnd: isize, text: *const u16, caption: *const u16, utype: u32) -> i32;
        }
        let title_w: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();
        let msg_w: Vec<u16> = message.encode_utf16().chain(std::iter::once(0)).collect();
        const MB_OK_ICONERROR: u32 = 0x0000_0010;
        unsafe {
            let _ = MessageBoxW(0, msg_w.as_ptr(), title_w.as_ptr(), MB_OK_ICONERROR);
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        eprintln!("[FATAL] {}: {}", title, message);
    }
}

/// Strips the Windows Mark-of-the-Web (Zone.Identifier NTFS stream) from a file or binary
/// directly via NTFS ADS removal in <1ms without spawning slow PowerShell processes.
pub fn unblock_file(path: &Path) {
    unblock_file_fast(path);
}

#[allow(dead_code)]
/// Strips Mark-of-the-Web (Zone.Identifier) directly from top-level app binaries and scripts
/// in pure Rust (<5ms), deliberately skipping venv/models/temp trees with tens of thousands of files.
pub fn unblock_dir(dir: &Path) {
    #[cfg(target_os = "windows")]
    {
        if !dir.is_dir() {
            return;
        }
        fn walk_app_tree(root: &Path, depth: usize) {
            if depth > 4 {
                return;
            }
            if let Ok(entries) = std::fs::read_dir(root) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_dir() {
                        if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                            let lower = name.to_ascii_lowercase();
                            if matches!(
                                lower.as_str(),
                                "venv" | "models" | "temp" | "saves" | "__pycache__" | ".git" | "libs"
                            ) {
                                continue;
                            }
                        }
                        walk_app_tree(&path, depth + 1);
                    } else if path.is_file() {
                        unblock_file_fast(&path);
                    }
                }
            }
        }
        walk_app_tree(dir, 0);
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = dir;
    }
}

/// Checks whether an official System Python (3.10+) is installed and registered in Windows Registry or PATH
/// Finds a working, compatible System Python (3.10 - 3.12) registered in Windows or PATH
#[allow(dead_code)]
pub fn find_compatible_system_python() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        let mut candidates: Vec<PathBuf> = Vec::new();

        // 1. Direct per-user official Python install directories (Programs\Python\Python31X)
        if let Some(local_appdata) = dirs::data_local_dir() {
            for ver in ["Python312", "Python311", "Python310"] {
                let py = local_appdata.join("Programs").join("Python").join(ver).join("python.exe");
                if py.is_file() {
                    candidates.push(py);
                }
            }
        }

        // 2. Windows Registry: HKCU and HKLM SOFTWARE\Python\PythonCore
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);
        for hive in [hkcu, hklm] {
            if let Ok(core_key) = hive.open_subkey(r"SOFTWARE\Python\PythonCore") {
                for ver in ["3.12", "3.11", "3.10"] {
                    if let Ok(ver_key) = core_key.open_subkey(ver) {
                        if let Ok(ip_key) = ver_key.open_subkey("InstallPath") {
                            if let Ok(path_str) = ip_key.get_value::<String, _>("") {
                                let py = PathBuf::from(path_str.trim()).join("python.exe");
                                if py.is_file() && !candidates.contains(&py) {
                                    candidates.push(py);
                                }
                            }
                        }
                    }
                }
            }
        }

        // 3. System PATH candidates via where.exe (strictly filtering out WindowsApps stubs)
        for cmd in ["python3.12", "python3.11", "python3.10", "python3", "python"] {
            if let Ok(out) = crate::os::create_hidden_command("where.exe").arg(cmd).output() {
                if out.status.success() {
                    let stdout = String::from_utf8_lossy(&out.stdout);
                    for line in stdout.lines() {
                        let trimmed = line.trim();
                        if !trimmed.is_empty() && !trimmed.to_lowercase().contains("windowsapps") {
                            let p = PathBuf::from(trimmed);
                            if p.is_file() && !candidates.contains(&p) {
                                candidates.push(p);
                            }
                        }
                    }
                }
            }
        }

        // Verify candidates by actually executing python code requiring 3.10 <= version < 3.13
        for candidate in candidates {
            if let Ok(out) = crate::os::create_hidden_command(&candidate)
                .arg("-c")
                .arg("import sys; exit(0 if (3, 10) <= sys.version_info < (3, 13) else 1)")
                .output()
            {
                if out.status.success() {
                    return Some(candidate);
                }
            }
        }
    }
    None
}

/// Checks whether a compatible official System Python (3.10 - 3.12) is available
#[allow(dead_code)]
pub fn has_system_python() -> bool {
    find_compatible_system_python().is_some()
}

#[cfg(target_os = "windows")]
/// Broadcasts WM_SETTINGCHANGE ("Environment") directly via user32.dll (<1ms, zero PowerShell).
fn broadcast_environment_change() {
    extern "system" {
        fn SendMessageTimeoutW(
            hwnd: isize,
            msg: u32,
            wparam: usize,
            lparam: *const u16,
            flags: u32,
            timeout: u32,
            result: *mut usize,
        ) -> isize;
    }
    const HWND_BROADCAST: isize = 0xFFFF;
    const WM_SETTINGCHANGE: u32 = 0x001A;
    const SMTO_ABORTIFHUNG: u32 = 0x0002;
    let env_w: Vec<u16> = "Environment\0".encode_utf16().collect();
    let mut res: usize = 0;
    unsafe {
        let _ = SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            env_w.as_ptr(),
            SMTO_ABORTIFHUNG,
            250,
            &mut res,
        );
    }
}

/// Adds specified directories to user-scope PATH in Windows Registry (HKCU\Environment) permanently
#[allow(dead_code, unused_variables)]
pub fn add_to_user_path(paths: &[&Path]) -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let (env_key, _) = hkcu.create_subkey("Environment")?;

        let current_val: String = env_key.get_value("Path").unwrap_or_default();
        let mut parts: Vec<String> = current_val
            .split(';')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect();

        let mut modified = false;
        for &p in paths {
            let p_str = p.to_string_lossy().to_string();
            if !parts.iter().any(|existing| existing.eq_ignore_ascii_case(&p_str)) {
                parts.insert(0, p_str);
                modified = true;
            }
        }

        if modified {
            let new_path = parts.join(";");
            let reg_val = winreg::RegValue {
                bytes: new_path.encode_utf16().chain(std::iter::once(0)).flat_map(|u| u.to_le_bytes()).collect(),
                vtype: winreg::enums::REG_EXPAND_SZ,
            };
            env_key.set_raw_value("Path", &reg_val)?;
            broadcast_environment_change();
        }

        // Update current process PATH immediately
        if let Ok(cur_proc_path) = std::env::var("PATH") {
            let mut prepend_str = String::new();
            for &p in paths {
                let p_str = p.to_string_lossy();
                if !cur_proc_path.to_lowercase().contains(&p_str.to_lowercase()) {
                    prepend_str.push_str(&p_str);
                    prepend_str.push(';');
                }
            }
            if !prepend_str.is_empty() {
                std::env::set_var("PATH", format!("{}{}", prepend_str, cur_proc_path));
            }
        }
    }
    Ok(())
}

/// Removes specified directories from user-scope PATH in Windows Registry (HKCU\Environment)
#[allow(dead_code, unused_variables)]
pub fn remove_from_user_path(paths: &[&Path]) -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        if let Ok((env_key, _)) = hkcu.create_subkey("Environment") {
            let current_val: String = env_key.get_value("Path").unwrap_or_default();
            let mut parts: Vec<String> = current_val
                .split(';')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();

            let orig_len = parts.len();
            parts.retain(|part| {
                !paths.iter().any(|&p| p.to_string_lossy().eq_ignore_ascii_case(part))
            });

            if parts.len() != orig_len {
                let new_path = parts.join(";");
                let reg_val = winreg::RegValue {
                    bytes: new_path.encode_utf16().chain(std::iter::once(0)).flat_map(|u| u.to_le_bytes()).collect(),
                    vtype: winreg::enums::REG_EXPAND_SZ,
                };
                let _ = env_key.set_raw_value("Path", &reg_val);
                broadcast_environment_change();
            }
        }
    }
    Ok(())
}

/// Ensures Microsoft Visual C++ 2015-2022 Redistributable (x64) is present on fresh Windows 10/11 PCs
/// so PySide6, ctranslate2, and PyAV native DLLs load cleanly on first launch.
#[allow(dead_code)]
pub fn ensure_vc_redist(sender: &crate::state::EventSender) {
    #[cfg(target_os = "windows")]
    {
        let sys_root = std::env::var("SystemRoot").unwrap_or_else(|_| r"C:\Windows".to_string());
        let sys32 = PathBuf::from(sys_root).join("System32");
        let has_vcruntime = sys32.join("vcruntime140.dll").is_file();
        let has_msvcp = sys32.join("msvcp140.dll").is_file();
        if has_vcruntime && has_msvcp {
            return;
        }

        crate::state::emit_log(
            sender,
            "INFO",
            "Microsoft Visual C++ 2015-2022 Runtime not found in System32; downloading official vc_redist.x64.exe...",
        );
        let temp_dir = std::env::temp_dir();
        let redist_exe = temp_dir.join("bw_vc_redist.x64.exe");
        let url = "https://aka.ms/vs/17/release/vc_redist.x64.exe";

        let agent = ureq::builder()
            .timeout(std::time::Duration::from_secs(60))
            .redirects(10)
            .build();

        let mut ok_dl = false;
        if let Ok(resp) = agent.get(url).set("User-Agent", "BadWords-Installer").call() {
            if let Ok(mut out) = std::fs::File::create(&redist_exe) {
                let mut reader = resp.into_reader();
                if std::io::copy(&mut reader, &mut out).is_ok()
                    && redist_exe.metadata().map(|m| m.len()).unwrap_or(0) > 10_000_000
                {
                    ok_dl = true;
                }
            }
        }

        if ok_dl {
            unblock_file(&redist_exe);
            crate::state::emit_log(
                sender,
                "INFO",
                "Installing Microsoft Visual C++ Runtime (approve UAC prompt if asked)...",
            );
            let status = std::process::Command::new(&redist_exe)
                .args(["/install", "/passive", "/norestart"])
                .status();
            let _ = std::fs::remove_file(&redist_exe);
            if let Ok(st) = status {
                let code = st.code().unwrap_or(-1);
                if code == 0 || code == 1638 || code == 3010 {
                    crate::state::emit_log(sender, "OK", "Microsoft Visual C++ Runtime installed successfully.");
                } else {
                    crate::state::emit_log(
                        sender,
                        "WARN",
                        &format!("VC++ Runtime installer exited with code {} (continuing with bundled runtime).", code),
                    );
                }
            }
        } else {
            let _ = std::fs::remove_file(&redist_exe);
            crate::state::emit_log(
                sender,
                "WARN",
                "Could not download Microsoft Visual C++ Runtime; continuing with bundled DLLs.",
            );
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = sender;
    }
}

/// Downloads and automatically installs official Python 3.12 on Windows (quiet, user scope, no admin required)
#[allow(dead_code)]
pub fn install_system_python(sender: &crate::state::EventSender) -> bool {
    #[cfg(target_os = "windows")]
    {
        crate::state::emit_log(sender, "INFO", "Downloading official Python 3.12.9 for Windows (user-scope)...");
        let temp_dir = std::env::temp_dir();
        let py_installer = temp_dir.join("python-3.12.9-amd64.exe");
        let url = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe";

        if !py_installer.is_file() || py_installer.metadata().map(|m| m.len()).unwrap_or(0) < 15_000_000 {
            if let Ok(resp) = ureq::get(url).call() {
                if let Ok(mut out) = std::fs::File::create(&py_installer) {
                    let mut reader = resp.into_reader();
                    let _ = std::io::copy(&mut reader, &mut out);
                }
            }
        }

        if py_installer.is_file() && py_installer.metadata().map(|m| m.len()).unwrap_or(0) >= 15_000_000 {
            if let Some(local_appdata) = dirs::data_local_dir() {
                let py_dir = local_appdata.join("Programs").join("Python").join("Python312");
                let py_scripts = py_dir.join("Scripts");
                let target_arg = format!("TargetDir={}", py_dir.display());

                crate::state::emit_log(sender, "INFO", "Installing System Python 3.12 into user profile (no admin needed)...");
                let status = crate::os::create_hidden_command(&py_installer)
                    .args([
                        "/quiet",
                        "InstallAllUsers=0",
                        "PrependPath=1",
                        "Include_test=0",
                        "Include_launcher=0",
                        &target_arg,
                    ])
                    .status();

                if let Ok(st) = status {
                    let code = st.code().unwrap_or(-1);
                    if code == 0 || code == 1641 || code == 3010 {
                        crate::state::emit_log(sender, "OK", "System Python 3.12 installed successfully.");
                        // Persistently write to HKCU\Environment\Path and update current process PATH
                        let _ = add_to_user_path(&[&py_dir, &py_scripts]);

                        let test_bin = py_dir.join("python.exe");
                        if test_bin.is_file() {
                            let verify = crate::os::create_hidden_command(&test_bin)
                                .arg("-c")
                                .arg("import sys; exit(0 if (3, 10) <= sys.version_info < (3, 13) else 1)")
                                .output();
                            if verify.is_ok_and(|o| o.status.success()) {
                                crate::state::emit_log(sender, "OK", "System Python 3.12 verified and registered in PATH.");
                                return true;
                            }
                        }
                    } else {
                        crate::state::emit_log(sender, "WARN", &format!("Python installer returned exit code: {}", code));
                    }
                }
            }
        } else {
            crate::state::emit_log(sender, "ERROR", "Failed to download complete Python 3.12 installer.");
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = sender;
    }
    false
}

/// Uninstalls the auto-installed System Python 3.12 and removes its PATH registration
#[allow(dead_code)]
pub fn uninstall_system_python(sender: &crate::state::EventSender) -> bool {
    #[cfg(target_os = "windows")]
    {
        crate::state::emit_log(sender, "INFO", "Uninstalling auto-installed System Python 3.12...");

        let mut py_dirs = Vec::new();
        if let Some(local_appdata) = dirs::data_local_dir() {
            let p12 = local_appdata.join("Programs").join("Python").join("Python312");
            let p10 = local_appdata.join("Programs").join("Python").join("Python310");
            if p12.is_dir() {
                py_dirs.push(p12);
            }
            if p10.is_dir() {
                py_dirs.push(p10);
            }
        }

        // Try uninstalling via cached installer or temp installer
        let temp_dir = std::env::temp_dir();
        for installer_name in ["python-3.12.9-amd64.exe", "python-3.10.11-amd64.exe"] {
            let py_installer = temp_dir.join(installer_name);
            if py_installer.is_file() {
                let _ = crate::os::create_hidden_command(&py_installer)
                    .args(["/uninstall", "/quiet"])
                    .status();
            }
        }

        // Clean up from PATH
        for d in &py_dirs {
            let scripts = d.join("Scripts");
            let _ = remove_from_user_path(&[d, &scripts]);
            if d.exists() {
                let _ = std::fs::remove_dir_all(d);
            }
        }

        crate::state::emit_log(sender, "OK", "System Python runtime uninstalled and PATH cleaned up.");
        return true;
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = sender;
        false
    }
}

#[allow(dead_code)]
/// Registers BadWords in Windows Add/Remove Programs (HKCU - No Admin / UAC Required)
pub fn register_uninstall_entry(install_dir: &Path, version: &str) -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords";
        let (key, _) = hkcu.create_subkey(path)?;

        let install_str = install_dir.to_string_lossy().to_string();
        let icon_path = {
            let asset = install_dir.join("assets").join("icons").join("icon_default.ico");
            if asset.is_file() {
                asset
            } else {
                install_dir.join("icons").join("icon_default.ico")
            }
        };
        let uninstall_exe = install_dir.join("uninstall.exe");
        let uninstall_cmd = format!("\"{}\" --uninstall", uninstall_exe.to_string_lossy());

        key.set_value("DisplayName", &"BadWords")?;
        key.set_value("DisplayVersion", &version)?;
        key.set_value("Publisher", &"Szymon Wolarz")?;
        key.set_value("InstallLocation", &install_str)?;
        key.set_value("DisplayIcon", &icon_path.to_string_lossy().to_string())?;
        key.set_value("UninstallString", &uninstall_cmd)?;
        key.set_value("QuietUninstallString", &format!("{} --quiet", uninstall_cmd))?;
        key.set_value("URLInfoAbout", &"https://github.com/veritus-git/BadWords")?;
        key.set_value("HelpLink", &"https://github.com/veritus-git/BadWords/issues")?;
        key.set_value("NoModify", &1u32)?;
        key.set_value("NoRepair", &0u32)?;
        key.set_value("EstimatedSize", &409600u32)?; // ~400 MB estimated
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = (install_dir, version);
    }

    Ok(())
}

#[allow(dead_code)]
/// Removes BadWords registry entry from HKCU
pub fn unregister_uninstall_entry() -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall";
        if let Ok(key) = hkcu.open_subkey_with_flags(path, KEY_WRITE) {
            let _ = key.delete_subkey_all("BadWords");
        }
    }

    Ok(())
}

#[allow(dead_code)]
/// Detects existing installation path from Windows Registry (HKCU)
pub fn detect_installed_location() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords";
        if let Ok(key) = hkcu.open_subkey(path) {
            if let Ok(loc) = key.get_value::<String, _>("InstallLocation") {
                let p = PathBuf::from(loc.trim());
                if (p.join("main.py").is_file() || p.join("src").join("main.py").is_file()) && p.exists() {
                    return Some(p);
                }
            }
        }
    }
    None
}

#[cfg(target_os = "windows")]
mod win_shortcut_com {
    use std::ffi::c_void;
    use std::path::{Path, PathBuf};

    #[repr(C)]
    #[derive(Clone, Copy)]
    struct Guid {
        data1: u32,
        data2: u16,
        data3: u16,
        data4: [u8; 8],
    }

    const CLSID_SHELL_LINK: Guid = Guid {
        data1: 0x0002_1401,
        data2: 0x0000,
        data3: 0x0000,
        data4: [0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46],
    };
    const IID_ISHELL_LINK_W: Guid = Guid {
        data1: 0x0002_14F9,
        data2: 0x0000,
        data3: 0x0000,
        data4: [0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46],
    };
    const IID_IPERSIST_FILE: Guid = Guid {
        data1: 0x0000_010B,
        data2: 0x0000,
        data3: 0x0000,
        data4: [0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46],
    };

    #[repr(C)]
    struct IShellLinkW {
        lp_vtbl: *const IShellLinkWVtbl,
    }

    #[repr(C)]
    struct IShellLinkWVtbl {
        query_interface: unsafe extern "system" fn(*mut IShellLinkW, *const Guid, *mut *mut c_void) -> i32,
        add_ref: unsafe extern "system" fn(*mut IShellLinkW) -> u32,
        release: unsafe extern "system" fn(*mut IShellLinkW) -> u32,
        get_path: *const c_void,
        get_id_list: *const c_void,
        set_id_list: *const c_void,
        get_description: *const c_void,
        set_description: unsafe extern "system" fn(*mut IShellLinkW, *const u16) -> i32,
        get_working_directory: *const c_void,
        set_working_directory: unsafe extern "system" fn(*mut IShellLinkW, *const u16) -> i32,
        get_arguments: *const c_void,
        set_arguments: unsafe extern "system" fn(*mut IShellLinkW, *const u16) -> i32,
        get_hotkey: *const c_void,
        set_hotkey: *const c_void,
        get_show_cmd: *const c_void,
        set_show_cmd: *const c_void,
        get_icon_location: *const c_void,
        set_icon_location: unsafe extern "system" fn(*mut IShellLinkW, *const u16, i32) -> i32,
        set_relative_path: *const c_void,
        resolve: *const c_void,
        set_path: unsafe extern "system" fn(*mut IShellLinkW, *const u16) -> i32,
    }

    #[repr(C)]
    struct IPersistFile {
        lp_vtbl: *const IPersistFileVtbl,
    }

    #[repr(C)]
    struct IPersistFileVtbl {
        query_interface: *const c_void,
        add_ref: *const c_void,
        release: unsafe extern "system" fn(*mut IPersistFile) -> u32,
        get_class_id: *const c_void,
        is_dirty: *const c_void,
        load: *const c_void,
        save: unsafe extern "system" fn(*mut IPersistFile, *const u16, i32) -> i32,
    }

    #[link(name = "ole32")]
    extern "system" {
        fn CoInitializeEx(pv_reserved: *mut c_void, dw_co_init: u32) -> i32;
        fn CoCreateInstance(
            rclsid: *const Guid,
            p_unk_outer: *mut c_void,
            dw_cls_context: u32,
            riid: *const Guid,
            ppv: *mut *mut c_void,
        ) -> i32;
        fn CoUninitialize();
    }

    #[link(name = "shell32")]
    extern "system" {
        fn SHGetFolderPathW(hwnd: isize, csidl: i32, h_token: isize, dw_flags: u32, psz_path: *mut u16) -> i32;
    }

    fn to_wide(s: &str) -> Vec<u16> {
        s.encode_utf16().chain(std::iter::once(0)).collect()
    }

    pub fn known_folder_path(csidl: i32) -> Option<PathBuf> {
        let mut buf = [0u16; 260];
        let hr = unsafe { SHGetFolderPathW(0, csidl, 0, 0, buf.as_mut_ptr()) };
        if hr == 0 {
            let len = buf.iter().position(|&c| c == 0).unwrap_or(buf.len());
            if len > 0 {
                return Some(PathBuf::from(String::from_utf16_lossy(&buf[..len])));
            }
        }
        None
    }

    /// Creates a Windows .lnk shortcut in pure Win32 COM (<1ms, zero PowerShell spawn).
    pub fn create_lnk(
        lnk_path: &Path,
        target: &str,
        arguments: &str,
        working_dir: &str,
        icon_path: &str,
        description: &str,
    ) -> bool {
        const COINIT_APARTMENTTHREADED: u32 = 0x2;
        const CLSCTX_INPROC_SERVER: u32 = 0x1;
        const RPC_E_CHANGED_MODE: i32 = 0x8001_0106u32 as i32;

        if let Some(parent) = lnk_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }

        let target_w = to_wide(target);
        let args_w = to_wide(arguments);
        let dir_w = to_wide(working_dir);
        let icon_w = to_wide(icon_path);
        let desc_w = to_wide(description);
        let lnk_w = to_wide(&lnk_path.to_string_lossy());

        unsafe {
            let hr_init = CoInitializeEx(std::ptr::null_mut(), COINIT_APARTMENTTHREADED);
            if hr_init < 0 && hr_init != RPC_E_CHANGED_MODE {
                return false;
            }
            let should_uninit = hr_init == 0 || hr_init == 1;

            let mut psl_raw: *mut c_void = std::ptr::null_mut();
            let hr_create = CoCreateInstance(
                &CLSID_SHELL_LINK,
                std::ptr::null_mut(),
                CLSCTX_INPROC_SERVER,
                &IID_ISHELL_LINK_W,
                &mut psl_raw,
            );
            let mut ok = false;
            if hr_create >= 0 && !psl_raw.is_null() {
                let psl = psl_raw as *mut IShellLinkW;
                let vtbl = &*(*psl).lp_vtbl;
                let _ = (vtbl.set_path)(psl, target_w.as_ptr());
                if !arguments.is_empty() {
                    let _ = (vtbl.set_arguments)(psl, args_w.as_ptr());
                }
                let _ = (vtbl.set_working_directory)(psl, dir_w.as_ptr());
                let _ = (vtbl.set_icon_location)(psl, icon_w.as_ptr(), 0);
                let _ = (vtbl.set_description)(psl, desc_w.as_ptr());

                let mut ppf_raw: *mut c_void = std::ptr::null_mut();
                let hr_qi = (vtbl.query_interface)(psl, &IID_IPERSIST_FILE, &mut ppf_raw);
                if hr_qi >= 0 && !ppf_raw.is_null() {
                    let ppf = ppf_raw as *mut IPersistFile;
                    let p_vtbl = &*(*ppf).lp_vtbl;
                    if (p_vtbl.save)(ppf, lnk_w.as_ptr(), 1) >= 0 {
                        ok = true;
                    }
                    (p_vtbl.release)(ppf);
                }
                (vtbl.release)(psl);
            }

            if should_uninit {
                CoUninitialize();
            }
            ok
        }
    }
}

#[allow(dead_code)]
/// Creates Desktop and Start Menu shortcuts on Windows cleanly via pure Win32 COM (<2ms, zero PowerShell).
pub fn create_windows_shortcuts(
    install_dir: &Path,
    create_desktop: bool,
    create_menu: bool,
    version: Option<&str>,
) -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        let icon_path = {
            let asset = install_dir.join("assets").join("icons").join("icon_default.ico");
            if asset.is_file() {
                asset
            } else {
                install_dir.join("icons").join("icon_default.ico")
            }
        };
        let launcher_exe = install_dir.join("BadWords.exe");
        let setup_cand = install_dir.join("setupfiles").join("windows").join("BadWords.exe");
        let bootstrap_cand = std::env::var("LOCALAPPDATA")
            .map(|l| PathBuf::from(l).join("BadWords-bootstrap").join("BadWords.exe"))
            .unwrap_or_default();
        let exe_dir_cand = std::env::current_exe()
            .ok()
            .and_then(|cur| cur.parent().map(|p| p.join("BadWords.exe")))
            .unwrap_or_default();

        let local_cand = [setup_cand, bootstrap_cand, exe_dir_cand]
            .into_iter()
            .find(|c| c.is_file());

        if let Some(cand) = local_cand {
            unblock_file(&cand);
            let mut should_copy = !launcher_exe.is_file();
            if !should_copy {
                if let (Ok(cm), Ok(tm)) = (cand.metadata(), launcher_exe.metadata()) {
                    if cm.len() != tm.len() {
                        should_copy = true;
                    } else if let (Ok(ct), Ok(tt)) = (cm.modified(), tm.modified()) {
                        if ct > tt {
                            should_copy = true;
                        }
                    }
                }
            }
            if should_copy {
                let _ = std::fs::copy(&cand, &launcher_exe);
            }
        }
        if !launcher_exe.is_file() {
            // Single fast download attempt for pre-built BadWords.exe launcher
            let mut candidate_urls = vec![
                "https://github.com/veritus-git/BadWords/releases/latest/download/BadWords.exe".to_string(),
            ];
            if let Some(ver) = version {
                if ver.starts_with('v') || ver.chars().next().is_some_and(|c| c.is_ascii_digit()) {
                    let clean = ver.trim_start_matches('v');
                    candidate_urls.insert(
                        0,
                        format!("https://github.com/veritus-git/BadWords/releases/download/v{}/BadWords.exe", clean),
                    );
                }
            }
            let agent = ureq::builder()
                .timeout(std::time::Duration::from_secs(4))
                .redirects(10)
                .build();
            for dl_url in candidate_urls {
                if let Ok(resp) = agent.get(&dl_url).call() {
                    let mut reader = resp.into_reader();
                    if let Ok(mut out) = std::fs::File::create(&launcher_exe) {
                        if std::io::copy(&mut reader, &mut out).is_ok() {
                            if launcher_exe.metadata().map(|m| m.len()).unwrap_or(0) > 10000 {
                                break;
                            } else {
                                let _ = std::fs::remove_file(&launcher_exe);
                            }
                        }
                    }
                }
            }
        }

        if launcher_exe.is_file() {
            unblock_file(&launcher_exe);
        }
        let (target_path, arguments, shortcut_icon) = if launcher_exe.is_file() {
            (
                launcher_exe.to_string_lossy().to_string(),
                String::new(),
                launcher_exe.to_string_lossy().to_string(),
            )
        } else {
            let pythonw_path = install_dir.join("venv").join("Scripts").join("pythonw.exe");
            let main_py = if install_dir.join("src").join("main.py").is_file() {
                install_dir.join("src").join("main.py")
            } else {
                install_dir.join("main.py")
            };
            (
                pythonw_path.to_string_lossy().to_string(),
                format!("\"{}\"", main_py.to_string_lossy()),
                icon_path.to_string_lossy().to_string(),
            )
        };
        let work_dir = install_dir.to_string_lossy().to_string();

        const CSIDL_PROGRAMS: i32 = 0x0002;
        const CSIDL_DESKTOPDIRECTORY: i32 = 0x0010;

        if create_desktop {
            let desktop_dir = win_shortcut_com::known_folder_path(CSIDL_DESKTOPDIRECTORY)
                .or_else(|| dirs::home_dir().map(|h| h.join("Desktop")));
            if let Some(d) = desktop_dir {
                let lnk = d.join("BadWords.lnk");
                if win_shortcut_com::create_lnk(
                    &lnk,
                    &target_path,
                    &arguments,
                    &work_dir,
                    &shortcut_icon,
                    "BadWords",
                ) {
                    unblock_file(&lnk);
                }
            }
        }
        if create_menu {
            let programs_dir = win_shortcut_com::known_folder_path(CSIDL_PROGRAMS).or_else(|| {
                std::env::var("APPDATA").ok().map(|a| {
                    PathBuf::from(a)
                        .join("Microsoft")
                        .join("Windows")
                        .join("Start Menu")
                        .join("Programs")
                })
            });
            if let Some(p) = programs_dir {
                let lnk = p.join("BadWords.lnk");
                if win_shortcut_com::create_lnk(
                    &lnk,
                    &target_path,
                    &arguments,
                    &work_dir,
                    &shortcut_icon,
                    "BadWords",
                ) {
                    unblock_file(&lnk);
                }
            }
        }
        unblock_dir(install_dir);
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = (install_dir, create_desktop, create_menu, version);
    }

    Ok(())
}

#[allow(dead_code)]
/// Removes Desktop and Start Menu shortcuts on Windows in pure Rust without launching PowerShell
pub fn remove_windows_shortcuts() -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        if let Some(user_home) = dirs::home_dir() {
            let desktop_lnk = user_home.join("Desktop").join("BadWords.lnk");
            let _ = std::fs::remove_file(desktop_lnk);
        }
        if let Ok(appdata) = std::env::var("APPDATA") {
            let menu_lnk = Path::new(&appdata)
                .join("Microsoft")
                .join("Windows")
                .join("Start Menu")
                .join("Programs")
                .join("BadWords.lnk");
            let _ = std::fs::remove_file(menu_lnk);
        }
    }

    Ok(())
}
