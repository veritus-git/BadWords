// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! Windows system integration (Registry HKCU, System Python check/install & Shortcuts)

use std::path::{Path, PathBuf};

#[cfg(target_os = "windows")]
use winreg::enums::*;
#[cfg(target_os = "windows")]
use winreg::RegKey;

/// Checks whether an official System Python (3.10+) is installed and registered in Windows Registry or PATH
#[allow(dead_code)]
pub fn has_system_python() -> bool {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);
        for hive in [hkcu, hklm] {
            if let Ok(core_key) = hive.open_subkey(r"SOFTWARE\Python\PythonCore") {
                for subkey in core_key.enum_keys().filter_map(|k| k.ok()) {
                    if subkey.starts_with("3.1") || subkey.starts_with("3.2") {
                        return true;
                    }
                }
            }
        }
        if let Ok(out) = crate::os::create_hidden_command("where.exe").arg("python").output() {
            if out.status.success() {
                return true;
            }
        }
        if let Ok(out) = crate::os::create_hidden_command("py.exe").arg("-0").output() {
            if out.status.success() && String::from_utf8_lossy(&out.stdout).contains("3.") {
                return true;
            }
        }
    }
    false
}

/// Downloads and automatically installs official Python 3.10 on Windows (quiet, PrependPath=1, user scope)
#[allow(dead_code)]
pub fn install_system_python(sender: &crate::state::EventSender) -> bool {
    #[cfg(target_os = "windows")]
    {
        crate::state::emit_log(sender, "INFO", "Downloading official Python 3.10 for Windows...");
        let temp_dir = std::env::temp_dir();
        let py_installer = temp_dir.join("python-3.10.11-amd64.exe");
        let url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe";

        if let Ok(resp) = ureq::get(url).call() {
            if let Ok(mut out) = std::fs::File::create(&py_installer) {
                let mut reader = resp.into_reader();
                let _ = std::io::copy(&mut reader, &mut out);
            }
        }

        if py_installer.exists() {
            crate::state::emit_log(sender, "INFO", "Installing System Python 3.10 (PrependPath=1)...");
            let status = crate::os::create_hidden_command(&py_installer)
                .args(["/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0", "Include_launcher=0"])
                .status();

            if let Ok(st) = status {
                let code = st.code().unwrap_or(-1);
                if code == 0 || code == 1641 || code == 3010 {
                    crate::state::emit_log(sender, "OK", "System Python 3.10 installed successfully.");
                    // Prepend to current process PATH so venv / python commands work immediately
                    if let Some(local_appdata) = dirs::data_local_dir() {
                        let py_dir = local_appdata.join("Programs").join("Python").join("Python310");
                        let py_scripts = py_dir.join("Scripts");
                        if let Ok(current_path) = std::env::var("PATH") {
                            let new_path = format!("{};{};{}", py_dir.display(), py_scripts.display(), current_path);
                            std::env::set_var("PATH", new_path);
                        }
                    }
                    return true;
                } else {
                    crate::state::emit_log(sender, "WARN", &format!("Python installer returned exit code: {}", code));
                }
            }
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = sender;
    }
    false
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
/// Creates Desktop and Start Menu shortcuts on Windows launching pythonw without console
pub fn create_windows_shortcuts(install_dir: &Path, create_desktop: bool, create_menu: bool) -> std::io::Result<()> {
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
            if setup_cand.is_file() {
                let _ = std::fs::copy(&setup_cand, &launcher_exe);
            } else if let Ok(cur_exe) = std::env::current_exe() {
                if let Some(p) = cur_exe.parent() {
                    let cand = p.join("BadWords.exe");
                    if cand.is_file() {
                        let _ = std::fs::copy(&cand, &launcher_exe);
                    }
                }
            }
        }
        let (target_path, arguments, shortcut_icon) = if launcher_exe.is_file() {
            (
                launcher_exe.to_string_lossy().to_string(),
                String::new(),
                launcher_exe.to_string_lossy().to_string()
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
                icon_path.to_string_lossy().to_string()
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
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = (install_dir, create_desktop, create_menu);
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
