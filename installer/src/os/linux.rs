//! Linux system integration (.desktop entry, System Python check/install & XDG menus)

use std::path::{Path, PathBuf};

/// Checks if Python 3.10+ is available in system PATH
pub fn has_system_python() -> bool {
    #[cfg(target_os = "linux")]
    {
        for cmd in ["python3", "python"] {
            if let Ok(out) = std::process::Command::new(cmd)
                .arg("-c")
                .arg("import sys; exit(0 if sys.version_info >= (3, 10) else 1)")
                .output()
            {
                if out.status.success() {
                    return true;
                }
            }
        }
    }
    false
}

/// Attempts to install Python 3 & python3-venv using native package manager
pub fn install_system_python(sender: &crate::state::EventSender) -> bool {
    #[cfg(target_os = "linux")]
    {
        crate::state::emit_log(sender, "INFO", "Attempting to install Python 3 via package manager...");
        let managers: [(&str, Vec<&str>); 4] = [
            ("apt-get", vec!["apt-get", "install", "-y", "python3", "python3-venv"]),
            ("dnf", vec!["dnf", "install", "-y", "python3"]),
            ("yum", vec!["yum", "install", "-y", "python3"]),
            ("pacman", vec!["pacman", "-Sy", "--noconfirm", "python"]),
        ];

        for (cmd, args) in managers {
            if let Ok(which) = std::process::Command::new("which").arg(cmd).output() {
                if which.status.success() {
                    crate::state::emit_log(sender, "INFO", &format!("Detected package manager: {}. Running installation...", cmd));
                    if cmd == "apt-get" {
                        let _ = std::process::Command::new("sudo").args(["apt-get", "update"]).status();
                    }
                    let status = std::process::Command::new("sudo").args(&args).status();
                    if let Ok(st) = status {
                        if st.success() {
                            crate::state::emit_log(sender, "OK", &format!("Python 3 installed successfully via {}.", cmd));
                            return true;
                        }
                    }
                }
            }
        }
    }
    #[cfg(not(target_os = "linux"))]
    {
        let _ = sender;
    }
    false
}

/// Discovers desktop directories dynamically across all Linux distros, languages, and XDG configurations
pub fn find_all_linux_desktop_dirs(home: &Path) -> Vec<PathBuf> {
    let mut dirs_list: Vec<PathBuf> = Vec::new();

    // 1. Rust dirs crate (parses ~/.config/user-dirs.dirs)
    if let Some(xdg_dt) = dirs::desktop_dir() {
        if xdg_dt.is_dir() && !dirs_list.contains(&xdg_dt) {
            dirs_list.push(xdg_dt);
        }
    }

    // 2. Query system xdg-user-dir tool
    if let Ok(out) = std::process::Command::new("xdg-user-dir").arg("DESKTOP").output() {
        if out.status.success() {
            let path_str = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !path_str.is_empty() {
                let p = PathBuf::from(path_str);
                if p.is_dir() && !dirs_list.contains(&p) {
                    dirs_list.push(p);
                }
            }
        }
    }

    // 3. Directly parse ~/.config/user-dirs.dirs as fallback
    let user_dirs_file = home.join(".config").join("user-dirs.dirs");
    if let Ok(content) = std::fs::read_to_string(&user_dirs_file) {
        for line in content.lines() {
            let line = line.trim();
            if line.starts_with("XDG_DESKTOP_DIR=") {
                let val = line.trim_start_matches("XDG_DESKTOP_DIR=").trim_matches('"');
                let resolved = if val.starts_with("$HOME/") {
                    home.join(val.trim_start_matches("$HOME/"))
                } else if val.starts_with('/') {
                    PathBuf::from(val)
                } else {
                    home.join(val)
                };
                if resolved.is_dir() && !dirs_list.contains(&resolved) {
                    dirs_list.push(resolved);
                }
            }
        }
    }

    // 4. Internationalized standard folder names across languages & distros
    let standard_names = [
        "Desktop",          // EN
        "Pulpit",           // PL
        "Schreibtisch",     // DE
        "Bureau",           // FR
        "Escritorio",       // ES / PT
        "Scrivania",        // IT
        "Рабочий стол",     // RU
        "Bureaublad",       // NL
        "Skrivbord",        // SV
        "Skrivebord",       // DA / NO
        "Työpöytä",         // FI
        "Área de Trabalho", // PT-BR
    ];

    for name in standard_names {
        let candidate = home.join(name);
        if candidate.is_dir() && !dirs_list.contains(&candidate) {
            dirs_list.push(candidate);
        }
    }

    // If no existing desktop folder was found at all, fallback to $HOME/Desktop
    if dirs_list.is_empty() {
        let default_dt = home.join("Desktop");
        let _ = std::fs::create_dir_all(&default_dt);
        dirs_list.push(default_dt);
    }

    dirs_list
}

pub fn create_linux_desktop_entry(install_dir: &Path) -> std::io::Result<()> {
    #[cfg(target_os = "linux")]
    {
        if let Some(home) = dirs::home_dir() {
            let apps_dir = home.join(".local").join("share").join("applications");
            let icons_dir = home.join(".local").join("share").join("icons").join("hicolor").join("256x256").join("apps");
            let icons_root = home.join(".local").join("share").join("icons");

            let _ = std::fs::create_dir_all(&apps_dir);
            let _ = std::fs::create_dir_all(&icons_dir);
            let _ = std::fs::create_dir_all(&icons_root);

            let desktop_file = apps_dir.join("badwords.desktop");
            let uninstall_desktop_file = apps_dir.join("badwords-uninstall.desktop");
            let src_icon = install_dir.join("assets").join("icons").join("icon_default.png");
            
            // Deploy icons to standard XDG search paths
            if src_icon.is_file() {
                let _ = std::fs::copy(&src_icon, icons_dir.join("badwords.png"));
                let _ = std::fs::copy(&src_icon, icons_root.join("badwords.png"));
            }

            let python_bin = install_dir.join("venv").join("bin").join("python");
            let main_script = install_dir.join("main.py");
            let installer_bin = install_dir.join("badwords-installer");

            let content = format!(
                "[Desktop Entry]\n\
                 Version=1.0\n\
                 Type=Application\n\
                 Name=BadWords\n\
                 GenericName=Text-based Rough Cutting Assistant\n\
                 Comment=AI-powered video editing and rough cutting assistant for DaVinci Resolve\n\
                 Exec=\"{py}\" \"{main}\" %U\n\
                 Path={dir}\n\
                 Icon={icon}\n\
                 Terminal=false\n\
                 Categories=AudioVideo;AudioVideoEditing;Video;\n\
                 Keywords=BadWords;badwords;davinci;resolve;video;editor;cut;whisper;\n\
                 StartupWMClass=BadWords\n",
                py = python_bin.to_string_lossy(),
                main = main_script.to_string_lossy(),
                dir = install_dir.to_string_lossy(),
                icon = src_icon.to_string_lossy()
            );

            std::fs::write(&desktop_file, &content)?;

            // Uninstaller entry in application menu
            let uninstaller_exec = if installer_bin.is_file() {
                format!("\"{}\" --uninstall", installer_bin.to_string_lossy())
            } else if let Ok(cur_exe) = std::env::current_exe() {
                format!("\"{}\" --uninstall", cur_exe.to_string_lossy())
            } else {
                format!("\"{}/badwords-installer\" --uninstall", install_dir.to_string_lossy())
            };

            let uninstall_content = format!(
                "[Desktop Entry]\n\
                 Version=1.0\n\
                 Type=Application\n\
                 Name=Uninstall BadWords\n\
                 GenericName=BadWords Uninstaller\n\
                 Comment=Uninstall BadWords and remove all configured components\n\
                 Exec={exec}\n\
                 Path={dir}\n\
                 Icon={icon}\n\
                 Terminal=false\n\
                 Categories=Utility;\n\
                 Keywords=BadWords;uninstall;remove;clean;\n",
                exec = uninstaller_exec,
                dir = install_dir.to_string_lossy(),
                icon = src_icon.to_string_lossy()
            );

            let _ = std::fs::write(&uninstall_desktop_file, &uninstall_content);

            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = std::fs::set_permissions(&desktop_file, std::fs::Permissions::from_mode(0o755));
                let _ = std::fs::set_permissions(&uninstall_desktop_file, std::fs::Permissions::from_mode(0o755));
            }

            // Desktop shortcut on all detected desktop directories across distros and locales
            let desktop_dirs = find_all_linux_desktop_dirs(&home);
            for dt_dir in desktop_dirs {
                if dt_dir.is_dir() {
                    let dt_shortcut = dt_dir.join("BadWords.desktop");
                    let _ = std::fs::write(&dt_shortcut, &content);
                    #[cfg(unix)]
                    {
                        use std::os::unix::fs::PermissionsExt;
                        let _ = std::fs::set_permissions(&dt_shortcut, std::fs::Permissions::from_mode(0o755));
                    }
                    // Mark as trusted for GNOME desktop environment
                    let _ = std::process::Command::new("gio")
                        .args(["set", &dt_shortcut.to_string_lossy().to_string(), "metadata::trusted", "true"])
                        .status();
                }
            }

            // Force update desktop database and icon caches so GNOME/KDE index it immediately
            let _ = std::process::Command::new("update-desktop-database")
                .arg(apps_dir.to_string_lossy().to_string())
                .status();
            let _ = std::process::Command::new("gtk-update-icon-cache")
                .args(["-f", "-t", &home.join(".local").join("share").join("icons").join("hicolor").to_string_lossy().to_string()])
                .status();
        }
    }

    #[cfg(not(target_os = "linux"))]
    {
        let _ = install_dir;
    }

    Ok(())
}

pub fn remove_linux_desktop_entry() -> std::io::Result<()> {
    #[cfg(target_os = "linux")]
    {
        if let Some(home) = dirs::home_dir() {
            let apps_dir = home.join(".local").join("share").join("applications");
            let desktop_file = apps_dir.join("badwords.desktop");
            let uninstall_desktop_file = apps_dir.join("badwords-uninstall.desktop");
            if desktop_file.exists() {
                let _ = std::fs::remove_file(desktop_file);
            }
            if uninstall_desktop_file.exists() {
                let _ = std::fs::remove_file(uninstall_desktop_file);
            }

            let desktop_dirs = find_all_linux_desktop_dirs(&home);
            for dt_dir in desktop_dirs {
                let dt_shortcut = dt_dir.join("BadWords.desktop");
                if dt_shortcut.exists() {
                    let _ = std::fs::remove_file(dt_shortcut);
                }
            }

            let _ = std::process::Command::new("update-desktop-database")
                .arg(apps_dir.to_string_lossy().to_string())
                .status();
        }
    }

    Ok(())
}
