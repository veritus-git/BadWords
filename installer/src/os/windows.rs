// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! Windows system integration (Registry HKCU, System Python check/install & Shortcuts)

use std::path::{Path, PathBuf};

#[cfg(target_os = "windows")]
use winreg::enums::*;
#[cfg(target_os = "windows")]
use winreg::RegKey;

/// Strips the Windows Mark-of-the-Web (Zone.Identifier NTFS stream) from a file or binary
pub fn unblock_file(path: &Path) {
    #[cfg(target_os = "windows")]
    {
        if !path.exists() {
            return;
        }
        // 1. Direct deletion of NTFS Alternate Data Stream Zone.Identifier
        let ads_path = format!("{}:Zone.Identifier", path.to_string_lossy());
        let _ = std::fs::remove_file(&ads_path);

        // 2. PowerShell Unblock-File invocation
        let path_str = path.to_string_lossy();
        let _ = crate::os::create_hidden_command("powershell")
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                &format!("Unblock-File -LiteralPath '{}' -ErrorAction SilentlyContinue; Remove-Item -LiteralPath '{}:Zone.Identifier' -Force -ErrorAction SilentlyContinue", path_str, path_str),
            ])
            .status();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = path;
    }
}

#[allow(dead_code)]
/// Strips Mark-of-the-Web (Zone.Identifier) recursively from an entire directory tree
pub fn unblock_dir(dir: &Path) {
    #[cfg(target_os = "windows")]
    {
        if !dir.exists() {
            return;
        }
        let dir_str = dir.to_string_lossy();
        let _ = crate::os::create_hidden_command("powershell")
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                &format!("Get-ChildItem -LiteralPath '{}' -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {{ Unblock-File -LiteralPath $_.FullName -ErrorAction SilentlyContinue; Remove-Item -LiteralPath \"$($_.FullName):Zone.Identifier\" -Force -ErrorAction SilentlyContinue }}", dir_str),
            ])
            .status();
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

            // Broadcast environment variable changes to system without restarting
            let _ = crate::os::create_hidden_command("powershell")
                .args([
                    "-NoProfile",
                    "-NonInteractive",
                    "-WindowStyle",
                    "Hidden",
                    "-Command",
                    "[Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH', 'User'), 'User')",
                ])
                .status();
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

                let _ = crate::os::create_hidden_command("powershell")
                    .args([
                        "-NoProfile",
                        "-NonInteractive",
                        "-WindowStyle",
                        "Hidden",
                        "-Command",
                        "[Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH', 'User'), 'User')",
                    ])
                    .status();
            }
        }
    }
    Ok(())
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

#[allow(dead_code)]
/// Creates Desktop and Start Menu shortcuts on Windows launching BadWords.exe without console
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
        if !launcher_exe.is_file() {
            let setup_cand = install_dir.join("setupfiles").join("windows").join("BadWords.exe");
            let bootstrap_cand = std::env::var("LOCALAPPDATA")
                .map(|l| PathBuf::from(l).join("BadWords-bootstrap").join("BadWords.exe"))
                .unwrap_or_default();

            if setup_cand.is_file() {
                unblock_file(&setup_cand);
                let _ = std::fs::copy(&setup_cand, &launcher_exe);
            } else if bootstrap_cand.is_file() {
                unblock_file(&bootstrap_cand);
                let _ = std::fs::copy(&bootstrap_cand, &launcher_exe);
            } else if let Ok(cur_exe) = std::env::current_exe() {
                if let Some(p) = cur_exe.parent() {
                    let cand = p.join("BadWords.exe");
                    if cand.is_file() {
                        unblock_file(&cand);
                        let _ = std::fs::copy(&cand, &launcher_exe);
                    }
                }
            }
        }
        if !launcher_exe.is_file() {
            // Attempt to download pre-built BadWords.exe launcher from GitHub releases
            let mut candidate_urls = vec![
                "https://github.com/veritus-git/BadWords/releases/latest/download/BadWords.exe".to_string(),
            ];
            if let Some(ver) = version {
                candidate_urls.push(format!("https://github.com/veritus-git/BadWords/releases/download/v{}/BadWords.exe", ver));
                candidate_urls.push(format!("https://github.com/veritus-git/BadWords/releases/download/{}/BadWords.exe", ver));
            }
            let agent = ureq::builder()
                .timeout(std::time::Duration::from_secs(15))
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

        let mut script_parts = vec![
            "$ws = New-Object -ComObject WScript.Shell;".to_string(),
        ];

        if create_desktop {
            script_parts.push(format!(
                "$desktop = [Environment]::GetFolderPath('Desktop'); \
                 $s1 = $ws.CreateShortcut(\"$desktop\\BadWords.lnk\"); \
                 $s1.TargetPath = '{target}'; \
                 $s1.Arguments = '{args}'; \
                 $s1.WorkingDirectory = '{dir}'; \
                 $s1.IconLocation = '{ico},0'; \
                 $s1.Description = 'BadWords'; \
                 $s1.Save();",
                target = target_path,
                args = arguments,
                dir = install_dir.to_string_lossy(),
                ico = shortcut_icon
            ));
        }

        if create_menu {
            script_parts.push(format!(
                "$programs = [Environment]::GetFolderPath('Programs'); \
                 $s2 = $ws.CreateShortcut(\"$programs\\BadWords.lnk\"); \
                 $s2.TargetPath = '{target}'; \
                 $s2.Arguments = '{args}'; \
                 $s2.WorkingDirectory = '{dir}'; \
                 $s2.IconLocation = '{ico},0'; \
                 $s2.Description = 'BadWords'; \
                 $s2.Save();",
                target = target_path,
                args = arguments,
                dir = install_dir.to_string_lossy(),
                ico = shortcut_icon
            ));
        }

        let full_script = script_parts.join(" ");
        let _ = crate::os::create_hidden_command("powershell")
            .args(&["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", &full_script])
            .output();

        // Proactively unblock shortcuts and installation directory
        if create_desktop {
            if let Some(user_home) = dirs::home_dir() {
                unblock_file(&user_home.join("Desktop").join("BadWords.lnk"));
            }
        }
        if create_menu {
            if let Ok(appdata) = std::env::var("APPDATA") {
                unblock_file(
                    &Path::new(&appdata)
                        .join("Microsoft")
                        .join("Windows")
                        .join("Start Menu")
                        .join("Programs")
                        .join("BadWords.lnk"),
                );
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
