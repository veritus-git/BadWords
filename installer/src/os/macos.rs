// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! macOS system integration (.app bundle, System Python check/install & Spotlight)

use std::path::Path;

#[allow(dead_code)]
/// Checks if an official macOS Python framework (3.8+) exists in /Library/Frameworks/Python.framework
pub fn has_system_python() -> bool {
    #[cfg(target_os = "macos")]
    {
        let framework_base = Path::new("/Library/Frameworks/Python.framework/Versions");
        if framework_base.is_dir() {
            for ver in ["3.13", "3.12", "3.11", "3.10", "3.9", "3.8"] {
                if framework_base.join(ver).is_dir() {
                    return true;
                }
            }
        }
    }
    false
}

#[allow(dead_code)]
/// Downloads and installs official Python 3.10 macOS framework package
pub fn install_system_python(sender: &crate::state::EventSender) -> bool {
    #[cfg(target_os = "macos")]
    {
        crate::state::emit_log(sender, "INFO", "Downloading official Python 3.10 for macOS...");
        let temp_dir = std::env::temp_dir();
        let py_pkg = temp_dir.join("python-3.10.11-macos11.pkg");
        let url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-macos11.pkg";

        if let Ok(resp) = ureq::get(url).call() {
            if let Ok(mut out) = std::fs::File::create(&py_pkg) {
                let mut reader = resp.into_reader();
                let _ = std::io::copy(&mut reader, &mut out);
            }
        }

        if py_pkg.exists() {
            crate::state::emit_log(sender, "INFO", "Installing Python 3.10 framework...");
            let status = std::process::Command::new("sudo")
                .args(["installer", "-pkg", &py_pkg.to_string_lossy(), "-target", "/"])
                .status();

            if let Ok(st) = status {
                if st.success() {
                    crate::state::emit_log(sender, "OK", "System Python framework installed successfully.");
                    return true;
                }
            }
        }
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = sender;
    }
    false
}

#[allow(dead_code)]
pub fn create_macos_app_bundle(install_dir: &Path, create_desktop: bool) -> std::io::Result<()> {
    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            let app_dir = home.join("Applications").join("BadWords.app");
            let contents = app_dir.join("Contents");
            let macos = contents.join("MacOS");
            let resources = contents.join("Resources");

            std::fs::create_dir_all(&macos)?;
            std::fs::create_dir_all(&resources)?;

            // Launcher script
            let launcher_path = macos.join("BadWords");
            let launcher_content = format!(
                "#!/bin/bash\nexec \"{}/venv/bin/python\" \"{}/main.py\" \"$@\"\n",
                install_dir.to_string_lossy(),
                install_dir.to_string_lossy()
            );
            std::fs::write(&launcher_path, launcher_content)?;

            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = std::fs::set_permissions(&launcher_path, std::fs::Permissions::from_mode(0o755));
            }

            // Info.plist
            let plist_path = contents.join("Info.plist");
            let plist_content = r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>BadWords</string>
    <key>CFBundleIdentifier</key>
    <string>com.veritus.badwords</string>
    <key>CFBundleName</key>
    <string>BadWords</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>4.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>"#;
            std::fs::write(&plist_path, plist_content)?;

            if create_desktop {
                let dt_link = home.join("Desktop").join("BadWords.app");
                if !dt_link.exists() {
                    #[cfg(unix)]
                    let _ = std::os::unix::fs::symlink(&app_dir, &dt_link);
                }
            }
        }
    }

    #[cfg(not(target_os = "macos"))]
    {
        let _ = (install_dir, create_desktop);
    }

    Ok(())
}

#[allow(dead_code)]
pub fn remove_macos_app_bundle() -> std::io::Result<()> {
    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            let app_dir = home.join("Applications").join("BadWords.app");
            if app_dir.exists() {
                let _ = std::fs::remove_dir_all(app_dir);
            }
        }
    }

    Ok(())
}
