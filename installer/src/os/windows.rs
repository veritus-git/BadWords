//! Windows system integration (Registry HKCU & Shortcuts)

use std::path::Path;

#[cfg(target_os = "windows")]
use winreg::enums::*;
#[cfg(target_os = "windows")]
use winreg::RegKey;

#[allow(dead_code)]
/// Registers BadWords in Windows Add/Remove Programs (HKCU - No Admin / UAC Required)
pub fn register_uninstall_entry(install_dir: &Path, version: &str) -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords";
        let (key, _) = hkcu.create_subkey(path)?;

        let install_str = install_dir.to_string_lossy().to_string();
        let icon_path = install_dir.join("assets").join("icons").join("icon_default.ico");
        let uninstall_cmd = format!("powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -Command \"& '{}' --uninstall\"", install_dir.join("uninstall.exe").to_string_lossy());

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
/// Creates Desktop and Start Menu shortcuts on Windows via PowerShell COM helper
pub fn create_windows_shortcuts(install_dir: &Path) -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        let exe_path = install_dir.join("BadWords.exe");
        let icon_path = install_dir.join("assets").join("icons").join("icon_default.ico");
        let script = format!(
            "$ws = New-Object -ComObject WScript.Shell; \
             $desktop = [Environment]::GetFolderPath('Desktop'); \
             $programs = [Environment]::GetFolderPath('Programs'); \
             $s1 = $ws.CreateShortcut(\"$desktop\\BadWords.lnk\"); \
             $s1.TargetPath = '{exe}'; \
             $s1.WorkingDirectory = '{dir}'; \
             $s1.IconLocation = '{ico},0'; \
             $s1.Save(); \
             $s2 = $ws.CreateShortcut(\"$programs\\BadWords.lnk\"); \
             $s2.TargetPath = '{exe}'; \
             $s2.WorkingDirectory = '{dir}'; \
             $s2.IconLocation = '{ico},0'; \
             $s2.Save();",
            exe = exe_path.to_string_lossy(),
            dir = install_dir.to_string_lossy(),
            ico = icon_path.to_string_lossy()
        );

        let _ = std::process::Command::new("powershell")
            .args(&["-NoProfile", "-NonInteractive", "-Command", &script])
            .output();
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = install_dir;
    }

    Ok(())
}

#[allow(dead_code)]
/// Removes Desktop and Start Menu shortcuts on Windows
pub fn remove_windows_shortcuts() -> std::io::Result<()> {
    #[cfg(target_os = "windows")]
    {
        let script = 
            "$desktop = [Environment]::GetFolderPath('Desktop'); \
             $programs = [Environment]::GetFolderPath('Programs'); \
             Remove-Item \"$desktop\\BadWords.lnk\" -Force -ErrorAction SilentlyContinue; \
             Remove-Item \"$programs\\BadWords.lnk\" -Force -ErrorAction SilentlyContinue;";

        let _ = std::process::Command::new("powershell")
            .args(&["-NoProfile", "-NonInteractive", "-Command", script])
            .output();
    }

    Ok(())
}
