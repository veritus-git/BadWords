// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! macOS system integration (.app bundle, System Python check/install & Spotlight)

use std::path::{Path, PathBuf};

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

            // BadWords.cfg in Resources
            let venv_py = install_dir.join("venv").join("bin").join("python3");
            let main_py = install_dir.join("src").join("main.py");
            let cfg_content = format!(
                "INSTALL_DIR={}\nPYTHON_BIN={}\nMAIN_PY={}\n",
                install_dir.to_string_lossy(),
                venv_py.to_string_lossy(),
                main_py.to_string_lossy()
            );
            let _ = std::fs::write(resources.join("BadWords.cfg"), cfg_content);

            // Native Mach-O launcher binary
            let launcher_path = macos.join("BadWords");
            let mut compiled = false;
            let launcher_c_src = include_str!("../../../setupfiles/macos/launcher.c");
            let temp_c = std::env::temp_dir().join("badwords_launcher_tmp.c");

            if std::fs::write(&temp_c, launcher_c_src).is_ok() {
                let st = std::process::Command::new("clang")
                    .args([
                        "-O2",
                        "-fobjc-arc",
                        "-framework", "Foundation",
                        "-framework", "AppKit",
                        "-o", launcher_path.to_string_lossy().as_ref(),
                        temp_c.to_string_lossy().as_ref(),
                    ])
                    .status();
                let _ = std::fs::remove_file(&temp_c);
                if let Ok(s) = st {
                    if s.success() && launcher_path.is_file() {
                        compiled = true;
                    }
                }
            }

            if !compiled {
                // Fallback shell script launcher if clang is unavailable
                let launcher_content = format!(
                    r#"#!/bin/bash
DIR="{}"
if [ -f "$DIR/src/main.py" ]; then
    MAIN_PY="$DIR/src/main.py"
    CWD="$DIR/src"
else
    MAIN_PY="$DIR/main.py"
    CWD="$DIR"
fi

if [ -x "$DIR/venv/bin/python3" ]; then
    PY="$DIR/venv/bin/python3"
elif [ -x "$DIR/venv/bin/python" ]; then
    PY="$DIR/venv/bin/python"
else
    PY="python3"
fi

cd "$CWD"
exec "$PY" "$MAIN_PY" "$@"
"#,
                    install_dir.to_string_lossy()
                );
                let _ = std::fs::write(&launcher_path, launcher_content);
            }

            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let _ = std::fs::set_permissions(&launcher_path, std::fs::Permissions::from_mode(0o755));
            }

            // Copy/embed application icon into Resources
            let icon_dest = resources.join("icon.icns");
            let icon_src = install_dir.join("assets").join("icons").join("icon_default.icns");
            if icon_src.is_file() {
                let _ = std::fs::copy(&icon_src, &icon_dest);
            } else {
                let embedded_icon = include_bytes!("../../../assets/icons/icon_default.icns");
                let _ = std::fs::write(&icon_dest, embedded_icon);
            }

            // Info.plist
            let plist_path = contents.join("Info.plist");
            let plist_content = r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>BadWords</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.veritus.badwords</string>
    <key>CFBundleName</key>
    <string>BadWords</string>
    <key>CFBundleDisplayName</key>
    <string>BadWords</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>4.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>"#;
            std::fs::write(&plist_path, plist_content)?;

            if create_desktop {
                let dt_link = home.join("Desktop").join("BadWords.app");
                if dt_link.exists() || dt_link.is_symlink() {
                    let _ = std::fs::remove_file(&dt_link);
                    let _ = std::fs::remove_dir_all(&dt_link);
                }
                #[cfg(unix)]
                let _ = std::os::unix::fs::symlink(&app_dir, &dt_link);
            }

            // Ad-hoc code sign bundle for Apple Silicon and macOS Gatekeeper
            let _ = std::process::Command::new("codesign")
                .args(["--force", "--deep", "--sign", "-", app_dir.to_string_lossy().as_ref()])
                .status();

            // Touch bundle so LaunchServices immediately updates icon cache
            let _ = std::process::Command::new("touch")
                .arg(app_dir.to_string_lossy().as_ref())
                .status();
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
            // Remove user app bundle
            let user_app = home.join("Applications").join("BadWords.app");
            if user_app.exists() {
                let _ = std::fs::remove_dir_all(&user_app);
            }

            // Remove global app bundle if exists
            let global_app = PathBuf::from("/Applications/BadWords.app");
            if global_app.exists() {
                let _ = std::fs::remove_dir_all(&global_app);
            }

            // Remove desktop shortcut / symlink
            let dt_link = home.join("Desktop").join("BadWords.app");
            if dt_link.exists() || dt_link.is_symlink() {
                let _ = std::fs::remove_file(&dt_link);
                let _ = std::fs::remove_dir_all(&dt_link);
            }
            let dt_file = home.join("Desktop").join("BadWords");
            if dt_file.exists() || dt_file.is_symlink() {
                let _ = std::fs::remove_file(&dt_file);
                let _ = std::fs::remove_dir_all(&dt_file);
            }
        }
    }

    Ok(())
}

/// Detects existing installation path from macOS App Bundle launcher script
pub fn detect_installed_location() -> Option<PathBuf> {
    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            let app_dirs = [
                home.join("Applications").join("BadWords.app"),
                PathBuf::from("/Applications/BadWords.app"),
            ];

            for app_dir in app_dirs {
                let launcher = app_dir.join("Contents").join("MacOS").join("BadWords");
                if launcher.is_file() {
                    if let Ok(content) = std::fs::read_to_string(&launcher) {
                        for line in content.lines() {
                            let line = line.trim();
                            if line.starts_with("cd \"") && line.ends_with("\"") {
                                let dir_str = line.trim_start_matches("cd \"").trim_end_matches('"');
                                let p = PathBuf::from(dir_str);
                                if (p.join("main.py").is_file() || p.join("src").join("main.py").is_file()) && p.exists() {
                                    return Some(p);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    None
}
