// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.

//! Shared state and IPC event messaging for the installer

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::mpsc::Sender;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[allow(dead_code)]
pub struct IpcMessage {
    pub action: String,
    pub path: Option<String>,
    pub mode: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IpcEvent {
    pub event: String,
    pub data: serde_json::Value,
}

pub type EventSender = Sender<IpcEvent>;

pub fn log_file_path() -> PathBuf {
    std::env::temp_dir().join("badwords_setup.log")
}

fn append_to_logfile(line: &str) {
    use std::io::Write;
    let log_path = log_file_path();
    if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(file, "{}", line);
    }
}

pub fn emit_log(sender: &EventSender, level: &str, message: &str) {
    append_to_logfile(&format!("[{:^4}] {}", level, message));
    let _ = sender.send(IpcEvent {
        event: "log".to_string(),
        data: serde_json::json!({
            "level": level,
            "message": message
        }),
    });
}

pub fn emit_progress_sub(sender: &EventSender, percent: u32, sub_percent: u32, status: &str, details: &str) {
    append_to_logfile(&format!("[STEP] {} - {} ({}% / sub: {}%)", status, details, percent, sub_percent));
    let _ = sender.send(IpcEvent {
        event: "progress".to_string(),
        data: serde_json::json!({
            "percent": percent,
            "sub_percent": sub_percent,
            "status": status,
            "details": details
        }),
    });
}

pub fn emit_progress(sender: &EventSender, percent: u32, step: u32, status: &str, details: &str) {
    let sub_percent = ((step + 1) * 25).min(100);
    emit_progress_sub(sender, percent, sub_percent, status, details);
}

pub fn emit_complete(sender: &EventSender, action: &str, success: bool, message: &str) {
    let tag = if success { " OK " } else { "ERR!" };
    append_to_logfile(&format!("[{}] Complete: {}", tag, message));
    let _ = sender.send(IpcEvent {
        event: "complete".to_string(),
        data: serde_json::json!({
            "action": action,
            "success": success,
            "message": message
        }),
    });
}
