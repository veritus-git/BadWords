// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

fn main() {
    let mut detected_version = None;

    let ver_files = ["../.version", ".version"];
    for vf in ver_files {
        if let Ok(v) = std::fs::read_to_string(vf) {
            println!("cargo:rerun-if-changed={}", vf);
            let clean = v.trim().trim_matches(|c| c == 'v' || c == 'V').trim();
            if !clean.is_empty() && clean.chars().any(|c| c.is_ascii_digit()) {
                detected_version = Some(clean.to_string());
                break;
            }
        }
    }

    if detected_version.is_none() {
        if let Ok(output) = std::process::Command::new("git")
            .args(["describe", "--tags", "--exact-match"])
            .output()
        {
            if output.status.success() {
                let s = String::from_utf8_lossy(&output.stdout).trim().to_string();
                let clean = s.trim_start_matches(|c| c == 'v' || c == 'V').trim().to_string();
                if !clean.is_empty() && clean.chars().any(|c| c.is_ascii_digit()) {
                    detected_version = Some(clean);
                }
            }
        }
    }

    if detected_version.is_none() {
        let candidates = [
            "../src/config/app_constants.py",
            "../config/app_constants.py",
            "src/config/app_constants.py",
        ];

        for path in candidates {
            let app_constants = std::path::Path::new(path);
            if let Ok(content) = std::fs::read_to_string(app_constants) {
                println!("cargo:rerun-if-changed={}", path);
                for line in content.lines() {
                    let trimmed = line.trim();
                    if trimmed.starts_with("VERSION") || trimmed.starts_with("_DEFAULT_VERSION") {
                        if let Some((_, v)) = trimmed.split_once('=') {
                            let clean = v.trim().trim_matches(|c| c == '"' || c == '\'').trim();
                            if !clean.is_empty() && !clean.contains('(') && !clean.contains(')') && clean.chars().any(|c| c.is_ascii_digit()) {
                                detected_version = Some(clean.to_string());
                                break;
                            }
                        }
                    }
                }
                if detected_version.is_some() {
                    break;
                }
            }
        }
    }

    if let Some(ref ver) = detected_version {
        println!("cargo:rustc-env=CARGO_PKG_VERSION={}", ver);
    }

    #[cfg(windows)]
    {
        let mut res = winres::WindowsResource::new();
        res.set_icon("../assets/icons/icon_default.ico");
        res.set("ProductName", "BadWords");
        res.set("FileDescription", "BadWords Setup");
        res.set("LegalCopyright", "Copyright (c) 2026 Szymon Wolarz");

        if let Some(ref ver) = detected_version {
            res.set("ProductVersion", ver);
            res.set("FileVersion", ver);
        }

        if let Err(e) = res.compile() {
            eprintln!("Warning: failed to compile Windows resources: {}", e);
        }
    }
}
