//! macOS system integration (.app bundle & Spotlight)

use std::path::Path;

#[allow(dead_code)]
pub fn create_macos_app_bundle(install_dir: &Path) -> std::io::Result<()> {
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
                "#!/bin/bash\nexec \"{}/runtime/python\" \"{}/main.py\" \"$@\"\n",
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
        }
    }

    #[cfg(not(target_os = "macos"))]
    {
        let _ = install_dir;
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
