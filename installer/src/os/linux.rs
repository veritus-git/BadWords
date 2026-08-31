//! Linux system integration (.desktop entry, System Python check/install & XDG menus)

use std::path::Path;

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

pub fn create_linux_desktop_entry(install_dir: &Path) -> std::io::Result<()> {
    #[cfg(target_os = "linux")]
    {
        if let Some(home) = dirs::home_dir() {
            let apps_dir = home.join(".local").join("share").join("applications");
            std::fs::create_dir_all(&apps_dir)?;

            let desktop_file = apps_dir.join("badwords.desktop");
            let icon_path = install_dir.join("assets").join("icons").join("icon_default.png");
            let python_bin = install_dir.join("venv").join("bin").join("python");
            let main_script = install_dir.join("main.py");

            let content = format!(
                "[Desktop Entry]\n\
                 Name=BadWords\n\
                 Comment=Text-based Rough Cutting Assistant for DaVinci Resolve\n\
                 Exec=\"{py}\" \"{main}\" %U\n\
                 Path={dir}\n\
                 Icon={icon}\n\
                 Terminal=false\n\
                 Type=Application\n\
                 Categories=AudioVideo;AudioVideoEditing;\n\
                 StartupWMClass=BadWords\n",
                py = python_bin.to_string_lossy(),
                main = main_script.to_string_lossy(),
                dir = install_dir.to_string_lossy(),
                icon = icon_path.to_string_lossy()
            );

            std::fs::write(&desktop_file, content)?;

            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = std::fs::set_permissions(&desktop_file, std::fs::Permissions::from_mode(0o755));
            }
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
            let desktop_file = home.join(".local").join("share").join("applications").join("badwords.desktop");
            if desktop_file.exists() {
                let _ = std::fs::remove_file(desktop_file);
            }
        }
    }

    Ok(())
}
