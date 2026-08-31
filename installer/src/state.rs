//! Shared state and IPC event messaging for the installer

use serde::{Deserialize, Serialize};
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

fn append_to_logfile(line: &str) {
    use std::io::Write;
    if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true).open("/tmp/badwords_setup.log") {
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

pub fn emit_progress(sender: &EventSender, percent: u32, step: u32, status: &str, details: &str) {
    append_to_logfile(&format!("[STEP] {} - {} ({}%)", status, details, percent));
    let _ = sender.send(IpcEvent {
        event: "progress".to_string(),
        data: serde_json::json!({
            "percent": percent,
            "step": step,
            "status": status,
            "details": details
        }),
    });
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
