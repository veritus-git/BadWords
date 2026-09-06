// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

fn main() {
    #[cfg(windows)]
    {
        let mut res = winres::WindowsResource::new();
        res.set_icon("../assets/icons/icon_default.ico");
        res.set("ProductName", "BadWords");
        res.set("FileDescription", "BadWords Setup");
        res.set("LegalCopyright", "Copyright (c) 2026 Szymon Wolarz");

        // Dynamically read version from app_constants.py
        let app_constants = std::path::Path::new("../src/config/app_constants.py");
        if let Ok(content) = std::fs::read_to_string(app_constants) {
            for line in content.lines() {
                let trimmed = line.trim();
                if trimmed.starts_with("VERSION") {
                    if let Some((_, v)) = trimmed.split_once('=') {
                        let clean = v.trim().trim_matches(|c| c == '"' || c == '\'');
                        if !clean.is_empty() {
                            res.set("ProductVersion", clean);
                            res.set("FileVersion", clean);
                            break;
                        }
                    }
                }
            }
        }

        if let Err(e) = res.compile() {
            eprintln!("Warning: failed to compile Windows resources: {}", e);
        }
    }
}
