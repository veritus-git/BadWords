// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! Native file & folder dialogs via rfd

pub fn pick_folder(default_dir: Option<&str>) -> Option<String> {
    let mut dialog = rfd::FileDialog::new()
        .set_title("Select BadWords Installation Directory");

    if let Some(dir) = default_dir {
        dialog = dialog.set_directory(dir);
    }

    dialog.pick_folder().map(|p| p.to_string_lossy().into_owned())
}
