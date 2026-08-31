// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

fn main() {
    #[cfg(windows)]
    {
        let mut res = winres::WindowsResource::new();
        res.set_icon("../assets/icons/icon_default.ico");
        res.set("ProductName", "BadWords Setup");
        res.set("FileDescription", "BadWords Setup Wizard");
        res.set("LegalCopyright", "Copyright (c) 2026 Szymon Wolarz");
        if let Err(e) = res.compile() {
            eprintln!("Warning: failed to compile Windows resources: {}", e);
        }
    }
}
