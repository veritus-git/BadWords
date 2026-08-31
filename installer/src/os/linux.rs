//! Linux system integration (.desktop entry & XDG menus)

use std::path::Path;

pub fn create_linux_desktop_entry(install_dir: &Path) -> std::io::Result<()> {
    #[cfg(target_os = "linux")]
    {
        if let Some(home) = dirs::home_dir() {
            let apps_dir = home.join(".local").join("share").join("applications");
            std::fs::create_dir_all(&apps_dir)?;

            let desktop_file = apps_dir.join("badwords.desktop");
            let icon_path = install_dir.join("assets").join("icons").join("icon_default.png");
            let content = format!(
                "[Desktop Entry]\n\
                 Name=BadWords\n\
                 Comment=Text-based Rough Cutting Assistant for DaVinci Resolve\n\
                 Exec=\"{dir}/main.py\" %U\n\
                 Icon={icon}\n\
                 Terminal=false\n\
                 Type=Application\n\
                 Categories=AudioVideo;AudioVideoEditing;\n\
                 StartupWMClass=BadWords\n",
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
