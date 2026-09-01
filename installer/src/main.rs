#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
// Copyright (c) 2026 Szymon Wolarz
// Licensed under the MIT License. See LICENSE file in the project root for full license information.


mod dialogs;
mod engine;
mod i18n;
mod os;
mod state;

use eframe::egui;
use engine::APP_VERSION;
use i18n::Language;
use state::IpcEvent;
use std::path::PathBuf;
use std::sync::mpsc::{channel, Receiver, Sender};
use std::time::Duration;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Screen {
    Welcome,
    Menu,
    SelectPath,
    ConfirmAction,
    Progress,
    Complete,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum InstallAction {
    InstallUpdate,
    Repair,
    Move,
    Reset,
    Uninstall,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
struct LogEntry {
    level: String,
    message: String,
}

fn main() -> eframe::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--terminal") {
        return run_standalone_terminal();
    }

    // Reset log file for fresh session
    let _ = std::fs::write(state::log_file_path(), "=== BadWords Setup Session Log ===\n");

    // CLI / Headless integration mode for testing & CI
    if args.iter().any(|a| a == "--cli" || a == "--headless") {
        return run_headless_cli(&args);
    }

    #[cfg(target_os = "macos")]
    let (total_w, total_h) = (650.0, 550.0);
    #[cfg(not(target_os = "macos"))]
    let (total_w, total_h) = (706.0, 606.0);

    let mut viewport = egui::ViewportBuilder::default()
        .with_inner_size([total_w, total_h])
        .with_min_inner_size([total_w, total_h])
        .with_max_inner_size([total_w, total_h])
        .with_resizable(false)
        .with_decorations(false)
        .with_transparent(true)
        .with_icon(
            eframe::icon_data::from_png_bytes(include_bytes!("../../assets/icons/icon_monochrome.png"))
                .expect("Failed to load icon"),
        );

    if let Some((pos_x, pos_y)) = os::get_primary_monitor_center(total_w, total_h) {
        viewport = viewport.with_position([pos_x, pos_y]);
    }

    let options = eframe::NativeOptions {
        viewport,
        ..Default::default()
    };

    let app_args = args.clone();
    eframe::run_native(
        "BadWords Setup",
        options,
        Box::new(move |cc| {
            cc.egui_ctx.set_visuals(egui::Visuals::dark());
            egui_extras::install_image_loaders(&cc.egui_ctx);
            Box::new(InstallerApp::new_with_args(&app_args))
        }),
    )
}

/// Headless CLI runner for GitHub Actions & automated scripts
fn run_headless_cli(args: &[String]) -> eframe::Result<()> {
    println!("[CLI] BadWords Installer {} Headless Engine Initialized", APP_VERSION);
    let (tx, rx) = channel();

    let target_dir = if let Some(idx) = args.iter().position(|a| a == "--install" || a == "--dir") {
        if idx + 1 < args.len() {
            PathBuf::from(&args[idx + 1])
        } else {
            os::default_install_dir()
        }
    } else {
        os::default_install_dir()
    };

    let create_dt = !args.iter().any(|a| a == "--no-desktop-shortcut");
    let create_menu = !args.iter().any(|a| a == "--no-menu-shortcut");

    if args.iter().any(|a| a == "--uninstall") {
        println!("[CLI] Running headless uninstall on: {}", target_dir.display());
        engine::run_uninstall(target_dir, tx);
    } else if args.iter().any(|a| a == "--repair") {
        println!("[CLI] Running headless repair on: {}", target_dir.display());
        engine::run_repair(target_dir, tx);
    } else if args.iter().any(|a| a == "--reset") {
        println!("[CLI] Running headless reset on: {}", target_dir.display());
        engine::run_reset(target_dir, tx);
    } else {
        println!("[CLI] Running headless install to: {}", target_dir.display());
        engine::run_install(target_dir, create_dt, create_menu, tx);
    }

    while let Ok(event) = rx.recv() {
        if event.event == "log" {
            let lvl = event.data.get("level").and_then(|v| v.as_str()).unwrap_or("INFO");
            let msg = event.data.get("message").and_then(|v| v.as_str()).unwrap_or("");
            println!("[{}] {}", lvl, msg);
        } else if event.event == "progress" {
            let pct = event.data.get("percent").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let status = event.data.get("status").and_then(|v| v.as_str()).unwrap_or("");
            let details = event.data.get("details").and_then(|v| v.as_str()).unwrap_or("");
            println!("[STEP {:.0}%] {} - {}", pct, status, details);
        } else if event.event == "complete" {
            let success = event.data.get("success").and_then(|v| v.as_bool()).unwrap_or(true);
            let msg = event.data.get("message").and_then(|v| v.as_str()).unwrap_or("Complete");
            println!("[COMPLETE] success={} message={}", success, msg);
            if !success {
                std::process::exit(1);
            }
            break;
        }
    }

    Ok(())
}

/// Standalone terminal process - 100% niezależny proces OS bez lagów
fn run_standalone_terminal() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("BadWords Setup — Terminal Console")
            .with_inner_size([650.0, 480.0])
            .with_min_inner_size([400.0, 300.0])
            .with_resizable(true)
            .with_decorations(true)
            .with_transparent(false)
            .with_icon(
                eframe::icon_data::from_png_bytes(include_bytes!("../../assets/icons/icon_monochrome.png"))
                    .expect("Failed to load icon"),
            ),
        ..Default::default()
    };

    eframe::run_native(
        "BadWords Setup — Terminal",
        options,
        Box::new(|cc| {
            cc.egui_ctx.set_visuals(egui::Visuals::dark());
            Box::new(StandaloneTerminalApp::new())
        }),
    )
}

struct StandaloneTerminalApp {
    last_content: String,
}

impl StandaloneTerminalApp {
    fn new() -> Self {
        Self {
            last_content: String::new(),
        }
    }
}

impl eframe::App for StandaloneTerminalApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        ctx.request_repaint_after(Duration::from_millis(150));

        if let Ok(content) = std::fs::read_to_string(state::log_file_path()) {
            self.last_content = content;
        }

        egui::CentralPanel::default()
            .frame(egui::Frame::none().fill(egui::Color32::from_rgb(16, 16, 16)).inner_margin(16.0))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label(
                        egui::RichText::new("● Live Execution Console")
                            .size(13.0)
                            .strong()
                            .color(egui::Color32::from_rgb(52, 211, 153))
                            .family(egui::FontFamily::Monospace),
                    );
                    
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if custom_button(ui, ctx, [130.0, 26.0], "Copy All Logs") {
                            ctx.output_mut(|o| o.copied_text = self.last_content.clone());
                        }
                    });
                });
                
                ui.add_space(8.0);
                ui.separator();
                ui.add_space(8.0);

                egui::ScrollArea::vertical()
                    .stick_to_bottom(true)
                    .auto_shrink([false, false])
                    .show(ui, |ui| {
                        for line in self.last_content.lines() {
                            let color = if line.contains("[ OK ]") || line.contains("[OK]") {
                                egui::Color32::from_rgb(52, 211, 153)
                            } else if line.contains("[STEP]") {
                                egui::Color32::from_rgb(56, 189, 248)
                            } else if line.contains("[WARN]") {
                                egui::Color32::from_rgb(251, 191, 36)
                            } else if line.contains("[ERR") || line.contains("ERROR") {
                                egui::Color32::from_rgb(248, 113, 113)
                            } else {
                                egui::Color32::from_gray(210)
                            };

                            ui.label(
                                egui::RichText::new(line)
                                    .size(12.0)
                                    .color(color)
                                    .family(egui::FontFamily::Monospace),
                            );
                        }
                    });
            });
    }
}

struct InstallerApp {
    screen: Screen,
    action: Option<InstallAction>,
    menu_selected_index: usize,
    keyboard_navigation_active: bool,
    language: Language,
    language_dropdown_open: bool,
    create_desktop_shortcut: bool,
    create_start_menu_shortcut: bool,
    install_path_str: String,
    detected_existing: Option<PathBuf>,
    detected_version: String,
    status_title: String,
    status_details: String,
    progress: f32,
    displayed_progress: f32,
    sub_progress: f32,
    displayed_sub_progress: f32,
    launch_on_finish: bool,
    logs: Vec<LogEntry>,
    terminal_child: Option<std::process::Child>,
    tx: Sender<IpcEvent>,
    rx: Receiver<IpcEvent>,
}

impl InstallerApp {
    fn new() -> Self {
        let (tx, rx) = channel();
        let detected = os::detect_existing_install();
        let initial_path = detected
            .as_ref()
            .cloned()
            .unwrap_or_else(os::default_install_dir);
        
        let path_str = initial_path.to_string_lossy().into_owned();

        // 1. Priorytet: Lokalne pliki (repozytorium lub wypakowany source code)
        let local_ver = engine::detect_local_version();
        let (initial_version, should_fetch_remote) = if let Some(v) = local_ver {
            (v, false)
        } else {
            (APP_VERSION.to_string(), true)
        };

        // 2. Zdalne zapytanie o Latest Release TYLKO jeśli instalator działa w trybie standalone
        if should_fetch_remote {
            let tx_rel = tx.clone();
            std::thread::spawn(move || {
                if let Some((tag, zip_url)) = engine::fetch_latest_github_release() {
                    let _ = tx_rel.send(IpcEvent {
                        event: "release_detected".to_string(),
                        data: serde_json::json!({
                            "tag": tag,
                            "zip_url": zip_url,
                        }),
                    });
                }
            });
        }

        Self {
            screen: Screen::Welcome,
            action: None,
            menu_selected_index: 0,
            keyboard_navigation_active: false,
            language: Language::auto_detect(),
            language_dropdown_open: false,
            create_desktop_shortcut: true,
            create_start_menu_shortcut: true,
            install_path_str: path_str,
            detected_existing: detected,
            detected_version: initial_version,
            status_title: "Ready to begin.".to_string(),
            status_details: "Click Next to choose an action.".to_string(),
            progress: 0.0,
            displayed_progress: 0.0,
            sub_progress: 0.0,
            displayed_sub_progress: 0.0,
            launch_on_finish: true,
            logs: vec![],
            terminal_child: None,
            tx,
            rx,
        }
    }

    fn new_with_args(args: &[String]) -> Self {
        let mut app = Self::new();
        if args.iter().any(|a| a == "--uninstall") {
            app.action = Some(InstallAction::Uninstall);
            app.screen = Screen::ConfirmAction;
        } else if args.iter().any(|a| a == "--repair") {
            app.action = Some(InstallAction::Repair);
            app.screen = Screen::ConfirmAction;
        }
        app
    }

    fn current_target_path(&self) -> PathBuf {
        PathBuf::from(self.install_path_str.trim())
    }

    fn toggle_terminal(&mut self) {
        if let Some(ref mut child) = self.terminal_child {
            if child.try_wait().ok().flatten().is_none() {
                let _ = child.kill();
                self.terminal_child = None;
                return;
            }
        }
        if let Ok(exe) = std::env::current_exe() {
            if let Ok(child) = std::process::Command::new(exe).arg("--terminal").spawn() {
                self.terminal_child = Some(child);
            }
        }
    }

    fn start_action(&mut self) {
        self.screen = Screen::Progress;
        self.progress = 0.0;
        self.displayed_progress = 0.0;
        self.sub_progress = 0.0;
        self.displayed_sub_progress = 0.0;
        self.status_title = "Starting operation...".to_string();
        self.status_details = "Preparing tasks".to_string();

        let tx = self.tx.clone();
        let target = self.current_target_path();

        match self.action {
            Some(InstallAction::InstallUpdate) => {
                engine::run_install(target, self.create_desktop_shortcut, self.create_start_menu_shortcut, tx);
            }
            Some(InstallAction::Repair) => {
                engine::run_repair(target, tx);
            }
            Some(InstallAction::Move) => {
                let from_dir = self.detected_existing.clone().unwrap_or_else(os::default_install_dir);
                engine::run_move(from_dir, target, tx);
            }
            Some(InstallAction::Reset) => {
                engine::run_reset(target, tx);
            }
            Some(InstallAction::Uninstall) => {
                engine::run_uninstall(target, tx);
            }
            None => {}
        }
    }

    fn select_menu_option(&mut self, index: usize) {
        match index {
            0 => {
                self.action = Some(InstallAction::InstallUpdate);
                self.screen = Screen::SelectPath;
            }
            1 => {
                self.action = Some(InstallAction::Repair);
                self.start_action();
            }
            2 => {
                self.action = Some(InstallAction::Move);
                self.screen = Screen::SelectPath;
            }
            3 => {
                self.action = Some(InstallAction::Reset);
                self.screen = Screen::ConfirmAction;
            }
            4 => {
                self.action = Some(InstallAction::Uninstall);
                self.screen = Screen::ConfirmAction;
            }
            _ => {}
        }
    }
}

impl eframe::App for InstallerApp {
    fn clear_color(&self, _visuals: &egui::Visuals) -> [f32; 4] {
        [0.0, 0.0, 0.0, 0.0]
    }

    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        let t = self.language.t();

        // Płynna animacja pasków postępu (niezależna od klatkażu, ciągły VSync repaint)
        if self.screen == Screen::Progress {
            let dt = ctx.input(|i| i.stable_dt).clamp(0.001, 0.1);
            let factor = 1.0 - (-10.0 * dt).exp();
            self.displayed_progress += (self.progress - self.displayed_progress) * factor;
            self.displayed_sub_progress += (self.sub_progress - self.displayed_sub_progress) * factor;
            ctx.request_repaint();
        }

        // ── Obsługa zdarzeń z wątku instalacyjnego ──
        let mut had_events = false;
        while let Ok(event) = self.rx.try_recv() {
            had_events = true;
            if event.event == "release_detected" {
                if let Some(tag) = event.data.get("tag").and_then(|v| v.as_str()) {
                    self.detected_version = tag.trim_start_matches('v').to_string();
                }
            } else if event.event == "log" {
                let level = event.data.get("level").and_then(|v| v.as_str()).unwrap_or("INFO").to_string();
                let message = event.data.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string();
                if !message.is_empty() {
                    self.status_details = message.clone();
                    self.logs.push(LogEntry { level, message });
                }
            } else if event.event == "progress" {
                if let Some(pct) = event.data.get("percent").and_then(|v| v.as_f64()) {
                    self.progress = (pct as f32) / 100.0;
                }
                if let Some(sub_pct) = event.data.get("sub_percent").and_then(|v| v.as_f64()) {
                    self.sub_progress = (sub_pct as f32) / 100.0;
                } else if let Some(step) = event.data.get("step").and_then(|v| v.as_f64()) {
                    self.sub_progress = ((step + 1.0) / 4.0).clamp(0.1, 1.0) as f32;
                }
                let status = event.data.get("status").and_then(|v| v.as_str()).unwrap_or("");
                let details = event.data.get("details").and_then(|v| v.as_str()).unwrap_or("");
                if !status.is_empty() {
                    self.status_title = status.to_string();
                }
                if !details.is_empty() {
                    self.status_details = details.to_string();
                }
                let pct_str = format!("{:.0}%", self.progress * 100.0);
                self.logs.push(LogEntry {
                    level: "STEP".to_string(),
                    message: format!("{} - {} ({})", self.status_title, self.status_details, pct_str),
                });
            } else if event.event == "complete" {
                self.progress = 1.0;
                self.displayed_progress = 1.0;
                self.sub_progress = 1.0;
                self.displayed_sub_progress = 1.0;
                let success = event.data.get("success").and_then(|v| v.as_bool()).unwrap_or(true);
                let message = event.data.get("message").and_then(|v| v.as_str()).unwrap_or("Operation finished.").to_string();
                self.status_title = message.clone();
                self.status_details = if success { "Done.".to_string() } else { "Error occurred.".to_string() };
                self.logs.push(LogEntry {
                    level: if success { "OK".to_string() } else { "ERR!".to_string() },
                    message,
                });
                self.screen = Screen::Complete;
            }
        }
        if had_events {
            ctx.request_repaint();
        }

        // ── Wykrywanie przełączania klawiatura vs mysz ────────────────
        if ctx.input(|i| i.pointer.delta() != egui::Vec2::ZERO || i.pointer.any_click()) {
            self.keyboard_navigation_active = false;
        }

        // ── Sterowanie Klawiaturą ─────────────────────────────────────
        if ctx.input(|i| i.key_pressed(egui::Key::Escape)) {
            if self.language_dropdown_open {
                self.language_dropdown_open = false;
            } else {
                ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            }
        }

        // Skrót 'T' przełącza (otwiera/chowa) okno terminala
        if ctx.input(|i| i.key_pressed(egui::Key::T) && !i.raw.modifiers.command && !i.raw.modifiers.ctrl) && self.screen != Screen::SelectPath {
            self.toggle_terminal();
        }

        match self.screen {
            Screen::Welcome => {
                if ctx.input(|i| i.key_pressed(egui::Key::Enter) || i.key_pressed(egui::Key::ArrowRight) || i.key_pressed(egui::Key::Space)) {
                    self.keyboard_navigation_active = true;
                    self.screen = Screen::Menu;
                }
            }
            Screen::Menu => {
                if ctx.input(|i| i.key_pressed(egui::Key::ArrowUp)) {
                    self.keyboard_navigation_active = true;
                    self.menu_selected_index = (self.menu_selected_index + 4) % 5;
                } else if ctx.input(|i| i.key_pressed(egui::Key::ArrowDown)) {
                    self.keyboard_navigation_active = true;
                    self.menu_selected_index = (self.menu_selected_index + 1) % 5;
                } else if ctx.input(|i| i.key_pressed(egui::Key::Enter) || i.key_pressed(egui::Key::ArrowRight) || i.key_pressed(egui::Key::Space)) {
                    self.select_menu_option(self.menu_selected_index);
                } else if ctx.input(|i| i.key_pressed(egui::Key::Num1)) {
                    self.keyboard_navigation_active = true;
                    self.select_menu_option(0);
                } else if ctx.input(|i| i.key_pressed(egui::Key::Num2)) {
                    self.keyboard_navigation_active = true;
                    self.select_menu_option(1);
                } else if ctx.input(|i| i.key_pressed(egui::Key::Num3)) {
                    self.keyboard_navigation_active = true;
                    self.select_menu_option(2);
                } else if ctx.input(|i| i.key_pressed(egui::Key::Num4)) {
                    self.keyboard_navigation_active = true;
                    self.select_menu_option(3);
                } else if ctx.input(|i| i.key_pressed(egui::Key::Num5)) {
                    self.keyboard_navigation_active = true;
                    self.select_menu_option(4);
                } else if ctx.input(|i| i.key_pressed(egui::Key::Backspace) || i.key_pressed(egui::Key::ArrowLeft)) {
                    self.screen = Screen::Welcome;
                }
            }
            Screen::SelectPath => {
                if ctx.input(|i| i.key_pressed(egui::Key::Enter) || i.key_pressed(egui::Key::ArrowRight)) {
                    self.start_action();
                } else if ctx.input(|i| i.key_pressed(egui::Key::ArrowLeft) || i.key_pressed(egui::Key::Escape)) {
                    self.screen = Screen::Menu;
                }
            }
            Screen::ConfirmAction => {
                if ctx.input(|i| i.key_pressed(egui::Key::Enter) || i.key_pressed(egui::Key::ArrowRight)) {
                    self.start_action();
                } else if ctx.input(|i| i.key_pressed(egui::Key::Backspace) || i.key_pressed(egui::Key::ArrowLeft)) {
                    self.screen = Screen::Menu;
                }
            }
            Screen::Progress => {}
            Screen::Complete => {
                if ctx.input(|i| i.key_pressed(egui::Key::Enter) || i.key_pressed(egui::Key::ArrowRight) || i.key_pressed(egui::Key::Space)) {
                    if self.launch_on_finish && self.action == Some(InstallAction::InstallUpdate) {
                        let target = self.current_target_path();
                        #[cfg(target_os = "windows")]
                        {
                            let pythonw = target.join("venv").join("Scripts").join("pythonw.exe");
                            let main_py = target.join("main.py");
                            let _ = os::create_hidden_command(&pythonw).arg(&main_py).spawn();
                        }
                        #[cfg(target_os = "macos")]
                        {
                            let python = target.join("venv").join("bin").join("python3");
                            let main_py = target.join("main.py");
                            let _ = std::process::Command::new(&python).arg(&main_py).spawn();
                        }
                        #[cfg(target_os = "linux")]
                        {
                            let python = target.join("venv").join("bin").join("python");
                            let main_py = target.join("main.py");
                            let _ = std::process::Command::new(&python).arg(&main_py).spawn();
                        }
                    }
                    ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                }
            }
        }

        // ── Główny Panel Aplikacji (Ścisłe wymiary) ──
        #[cfg(target_os = "macos")]
        let (win_w, win_h, margin) = (650.0, 550.0, 0.0);
        #[cfg(not(target_os = "macos"))]
        let (win_w, win_h, margin) = (706.0, 606.0, 28.0);

        egui::CentralPanel::default()
            .frame(egui::Frame::none().fill(egui::Color32::TRANSPARENT).inner_margin(0.0))
            .show(ctx, |ui| {
                ui.set_min_size(egui::vec2(win_w, win_h));
                ui.set_max_size(egui::vec2(win_w, win_h));

                #[cfg(not(target_os = "macos"))]
                {
                    let window_rect = egui::Rect::from_min_size(
                        ui.min_rect().min + egui::vec2(margin, margin),
                        egui::vec2(650.0, 550.0),
                    );

                    let painter = ui.painter();

                    // 8-warstwowy, ultra-gładki cień Gaussa wokół okna
                    let shadow_layers = [
                        egui::epaint::Shadow { offset: egui::vec2(0.0, 1.0), blur: 3.0, spread: 0.0, color: egui::Color32::from_black_alpha(65) },
                        egui::epaint::Shadow { offset: egui::vec2(0.0, 2.0), blur: 6.0, spread: 0.5, color: egui::Color32::from_black_alpha(55) },
                        egui::epaint::Shadow { offset: egui::vec2(0.0, 3.0), blur: 10.0, spread: 1.0, color: egui::Color32::from_black_alpha(45) },
                        egui::epaint::Shadow { offset: egui::vec2(0.0, 4.0), blur: 18.0, spread: 2.0, color: egui::Color32::from_black_alpha(35) },
                        egui::epaint::Shadow { offset: egui::vec2(0.0, 6.0), blur: 28.0, spread: 3.0, color: egui::Color32::from_black_alpha(25) },
                    ];

                    for shadow in shadow_layers {
                        let mesh = shadow.tessellate(window_rect, 0.0);
                        painter.add(egui::Shape::Mesh(mesh));
                    }
                }

                // Ciało Okna (Dokładnie 650x550px)
                egui::Frame::none()
                    .fill(egui::Color32::from_rgb(30, 30, 30))
                    .inner_margin(0.0)
                    .outer_margin(margin)
                    .rounding(0.0)
                    .show(ui, |ui| {
                        ui.set_min_size(egui::vec2(650.0, 550.0));
                        ui.set_max_size(egui::vec2(650.0, 550.0));
                        ui.spacing_mut().item_spacing = egui::vec2(0.0, 0.0);

                        ui.vertical(|ui| {
                            // 1. PASEK TYTUŁOWY (36px, RGB 22, 22, 22)
                            egui::Frame::none()
                                .fill(egui::Color32::from_rgb(22, 22, 22))
                                .rounding(0.0)
                                .inner_margin(0.0)
                                .show(ui, |ui| {
                                    ui.set_min_size(egui::vec2(650.0, 36.0));
                                    ui.set_max_size(egui::vec2(650.0, 36.0));

                                    let title_bar_rect = ui.max_rect();

                                    ui.horizontal(|ui| {
                                        ui.spacing_mut().item_spacing.x = 0.0;
                                        
                                        let (close_rect, min_rect, term_rect) = ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                            let button_size = [46.0, 36.0];
                                            let stroke = egui::Stroke::new(1.0_f32, egui::Color32::from_gray(215));
                                            
                                            // Zamknij (X)
                                            let (close_rect, close_resp) = ui.allocate_exact_size(button_size.into(), egui::Sense::click());
                                            if close_resp.clicked() { ctx.send_viewport_cmd(egui::ViewportCommand::Close); }
                                            
                                            let is_close_hovered = close_resp.hovered() || ctx.input(|i| i.pointer.hover_pos().is_some_and(|p| close_rect.contains(p)));
                                            if is_close_hovered {
                                                ui.painter().rect_filled(close_rect, 0.0, egui::Color32::from_rgb(190, 45, 45));
                                            }
                                            let center = close_rect.center();
                                            ui.painter().line_segment([center + egui::vec2(-4.5, -4.5), center + egui::vec2(4.5, 4.5)], stroke);
                                            ui.painter().line_segment([center + egui::vec2(-4.5, 4.5), center + egui::vec2(4.5, -4.5)], stroke);
                                            close_resp.on_hover_text(t.close_tooltip);

                                            // Minimalizuj (-)
                                            let (min_rect, min_resp) = ui.allocate_exact_size(button_size.into(), egui::Sense::click());
                                            if min_resp.clicked() { ctx.send_viewport_cmd(egui::ViewportCommand::Minimized(true)); }
                                            
                                            let is_min_hovered = min_resp.hovered() || ctx.input(|i| i.pointer.hover_pos().is_some_and(|p| min_rect.contains(p)));
                                            if is_min_hovered {
                                                ui.painter().rect_filled(min_rect, 0.0, egui::Color32::from_white_alpha(15));
                                            }
                                            let m_center = min_rect.center();
                                            ui.painter().line_segment([m_center + egui::vec2(-4.5, 0.0), m_center + egui::vec2(4.5, 0.0)], stroke);
                                            min_resp.on_hover_text(t.minimize_tooltip);

                                            // Przycisk Terminala (Wektorowy prompt '>' i kursor '_')
                                            let term_size = [36.0, 36.0];
                                            let (term_rect, term_resp) = ui.allocate_exact_size(term_size.into(), egui::Sense::click());
                                            if term_resp.clicked() {
                                                self.toggle_terminal();
                                            }
                                            let is_term_hovered = term_resp.hovered() || ctx.input(|i| i.pointer.hover_pos().is_some_and(|p| term_rect.contains(p)));
                                            let term_stroke_color = if is_term_hovered {
                                                ui.painter().rect_filled(term_rect, 0.0, egui::Color32::from_white_alpha(15));
                                                egui::Color32::WHITE
                                            } else {
                                                egui::Color32::from_gray(180)
                                            };
                                            let t_center = term_rect.center();
                                            let t_stroke = egui::Stroke::new(1.6_f32, term_stroke_color);
                                            let p1 = t_center + egui::vec2(-6.0, -4.5);
                                            let p2 = t_center + egui::vec2(-1.5, 0.0);
                                            let p3 = t_center + egui::vec2(-6.0, 4.5);
                                            ui.painter().line_segment([p1, p2], t_stroke);
                                            ui.painter().line_segment([p2, p3], t_stroke);
                                            let c1 = t_center + egui::vec2(0.5, 4.5);
                                            let c2 = t_center + egui::vec2(6.5, 4.5);
                                            ui.painter().line_segment([c1, c2], t_stroke);
                                            term_resp.on_hover_text(t.terminal_tooltip);
                                            
                                            // Lewa strona (ikona + tytuł)
                                            ui.with_layout(egui::Layout::left_to_right(egui::Align::Center), |ui| {
                                                ui.add_space(10.0);
                                                ui.add(
                                                    egui::Image::new(egui::include_image!("../../assets/icons/icon_monochrome.png"))
                                                        .max_height(16.0)
                                                );
                                                ui.add_space(8.0);
                                                ui.label(
                                                    egui::RichText::new("BadWords Setup")
                                                        .size(13.0)
                                                        .color(egui::Color32::from_gray(215))
                                                );
                                            });

                                            (close_rect, min_rect, term_rect)
                                        }).inner;

                                        // Drag okna (wykluczając przyciski)
                                        if ctx.input(|i| i.pointer.button_pressed(egui::PointerButton::Primary)) {
                                            if let Some(pos) = ctx.input(|i| i.pointer.latest_pos()) {
                                                if title_bar_rect.contains(pos) && !close_rect.contains(pos) && !min_rect.contains(pos) && !term_rect.contains(pos) {
                                                    ctx.send_viewport_cmd(egui::ViewportCommand::StartDrag);
                                                }
                                            }
                                        }
                                    });
                                });

                            // 2. GŁÓWNY OBSZAR ZAWARTOSCI (650x459px, ścisłe ograniczenie szerokości)
                            egui::Frame::none()
                                .fill(egui::Color32::from_rgb(30, 30, 30))
                                .rounding(0.0)
                                .inner_margin(0.0)
                                .show(ui, |ui| {
                                    ui.set_min_size(egui::vec2(650.0, 459.0));
                                    ui.set_max_size(egui::vec2(650.0, 459.0));

                                    ui.horizontal(|ui| {
                                        ui.spacing_mut().item_spacing.x = 0.0;

                                        // Lewy Panel: Banner Wizualny (210x459px z zachowaniem 100% proporcji logo)
                                        let banner_size = egui::vec2(210.0, 459.0);
                                        let (banner_rect, _) = ui.allocate_exact_size(banner_size, egui::Sense::hover());
                                        let uv_y_crop = (515.0_f32 - 459.0_f32) / (2.0 * 515.0_f32);
                                        let uv_rect = egui::Rect::from_min_max(
                                            egui::pos2(0.0, uv_y_crop),
                                            egui::pos2(1.0, 1.0 - uv_y_crop),
                                        );
                                        egui::Image::new(egui::include_image!("../setup-banner.png"))
                                            .uv(uv_rect)
                                            .paint_at(ui, banner_rect);

                                        // Prawy Panel: Zawartość Ekranu w układzie pionowym (440x459px z 24px marginesem)
                                        ui.allocate_ui_with_layout(
                                            egui::vec2(440.0, 459.0),
                                            egui::Layout::top_down(egui::Align::LEFT),
                                            |ui| {
                                                egui::Frame::none()
                                                    .inner_margin(egui::Margin { left: 24.0, right: 24.0, top: 24.0, bottom: 20.0 })
                                                    .show(ui, |ui| {
                                                        ui.set_width(392.0);
                                                        ui.style_mut().wrap = Some(true);

                                                        match self.screen {
                                                            Screen::Welcome => {
                                                                ui.heading(
                                                                    egui::RichText::new(t.welcome_title)
                                                                        .size(21.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(16.0);
                                                                
                                                                let mut intro_job = egui::text::LayoutJob::default();
                                                                intro_job.append(
                                                                    t.welcome_intro_prefix,
                                                                    0.0,
                                                                    egui::TextFormat {
                                                                        font_id: egui::FontId::proportional(13.5),
                                                                        color: egui::Color32::from_gray(215),
                                                                        ..Default::default()
                                                                    },
                                                                );
                                                                intro_job.append(
                                                                    &format!(" {}", self.detected_version),
                                                                    0.0,
                                                                    egui::TextFormat {
                                                                        font_id: egui::FontId::proportional(13.5),
                                                                        color: egui::Color32::WHITE,
                                                                        ..Default::default()
                                                                    },
                                                                );
                                                                intro_job.append(
                                                                    ".",
                                                                    0.0,
                                                                    egui::TextFormat {
                                                                        font_id: egui::FontId::proportional(13.5),
                                                                        color: egui::Color32::from_gray(215),
                                                                        ..Default::default()
                                                                    },
                                                                );
                                                                ui.label(intro_job);
                                                                
                                                                ui.add_space(12.0);
                                                                ui.label(
                                                                    egui::RichText::new(t.welcome_close_apps)
                                                                        .size(13.5)
                                                                        .color(egui::Color32::from_gray(215))
                                                                );
                                                                ui.add_space(12.0);
                                                                ui.label(
                                                                    egui::RichText::new(t.welcome_prompt)
                                                                        .size(13.5)
                                                                        .color(egui::Color32::from_gray(215))
                                                                );
                                                            }

                                                            Screen::Menu => {
                                                                ui.heading(
                                                                    egui::RichText::new(t.menu_title)
                                                                        .size(20.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(4.0);
                                                                ui.label(
                                                                    egui::RichText::new(t.menu_prompt)
                                                                        .size(12.0)
                                                                        .color(egui::Color32::from_gray(180))
                                                                );
                                                                ui.add_space(10.0);

                                                                // 1. Standard Install / Update
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "1",
                                                                    egui::Color32::from_rgb(52, 211, 153),
                                                                    t.opt_install_title,
                                                                    t.opt_install_desc,
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 0,
                                                                ) {
                                                                    self.menu_selected_index = 0;
                                                                    self.select_menu_option(0);
                                                                }
                                                                ui.add_space(3.0);

                                                                // 2. Repair Installation
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "2",
                                                                    egui::Color32::from_rgb(56, 189, 248),
                                                                    t.opt_repair_title,
                                                                    t.opt_repair_desc,
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 1,
                                                                ) {
                                                                    self.menu_selected_index = 1;
                                                                    self.select_menu_option(1);
                                                                }
                                                                ui.add_space(3.0);

                                                                // 3. Move Installation
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "3",
                                                                    egui::Color32::from_rgb(129, 140, 248),
                                                                    t.opt_move_title,
                                                                    t.opt_move_desc,
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 2,
                                                                ) {
                                                                    self.menu_selected_index = 2;
                                                                    self.select_menu_option(2);
                                                                }
                                                                ui.add_space(3.0);

                                                                // 4. Complete Reset
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "4",
                                                                    egui::Color32::from_rgb(251, 191, 36),
                                                                    t.opt_reset_title,
                                                                    t.opt_reset_desc,
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 3,
                                                                ) {
                                                                    self.menu_selected_index = 3;
                                                                    self.select_menu_option(3);
                                                                }
                                                                ui.add_space(3.0);

                                                                // 5. Uninstall
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "5",
                                                                    egui::Color32::from_rgb(248, 113, 113),
                                                                    t.opt_uninstall_title,
                                                                    t.opt_uninstall_desc,
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 4,
                                                                ) {
                                                                    self.menu_selected_index = 4;
                                                                    self.select_menu_option(4);
                                                                }
                                                            }

                                                            Screen::SelectPath => {
                                                                let is_move = self.action == Some(InstallAction::Move);
                                                                ui.heading(
                                                                    egui::RichText::new(if is_move { t.opt_move_title } else { t.select_path_title })
                                                                        .size(20.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(6.0);
                                                                
                                                                ui.label(
                                                                    egui::RichText::new(t.select_path_label)
                                                                        .size(13.0)
                                                                        .color(egui::Color32::from_gray(215))
                                                                );
                                                                
                                                                if let Some(ref detected) = self.detected_existing {
                                                                    ui.add_space(6.0);
                                                                    ui.label(
                                                                        egui::RichText::new(format!("Existing: {}", detected.display()))
                                                                            .size(11.5)
                                                                            .color(egui::Color32::from_rgb(52, 211, 153))
                                                                    );
                                                                }

                                                                ui.add_space(14.0);

                                                                // Czysty input ścieżki i przycisk Przeglądaj
                                                                ui.horizontal(|ui| {
                                                                    egui::Frame::none()
                                                                        .fill(egui::Color32::from_rgb(38, 38, 38))
                                                                        .stroke(egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(68, 68, 68)))
                                                                        .inner_margin(egui::Margin::symmetric(10.0, 7.0))
                                                                        .rounding(3.0)
                                                                        .show(ui, |ui| {
                                                                            ui.add_sized(
                                                                                [270.0, 20.0],
                                                                                egui::TextEdit::singleline(&mut self.install_path_str)
                                                                                    .frame(false)
                                                                                    .text_color(egui::Color32::WHITE)
                                                                                    .font(egui::FontId::proportional(13.0))
                                                                            );
                                                                        });
                                                                    
                                                                    ui.add_space(6.0);
                                                                    
                                                                    if custom_button(ui, ctx, [90.0, 36.0], t.browse_btn) {
                                                                        if let Some(folder) = dialogs::pick_folder(Some(&self.install_path_str)) {
                                                                            self.install_path_str = folder;
                                                                        }
                                                                    }
                                                                });
                                                                
                                                                ui.add_space(16.0);
                                                                ui.checkbox(&mut self.create_desktop_shortcut, t.shortcut_desktop);

                                                                #[cfg(not(target_os = "macos"))]
                                                                {
                                                                    ui.add_space(8.0);
                                                                    ui.checkbox(&mut self.create_start_menu_shortcut, t.shortcut_menu);
                                                                }

                                                                ui.add_space(14.0);
                                                                ui.label(
                                                                    egui::RichText::new("At least 500 MB of free disk space is required.")
                                                                        .size(11.5)
                                                                        .color(egui::Color32::from_gray(160))
                                                                );
                                                            }

                                                            Screen::ConfirmAction => {
                                                                let is_uninstall = self.action == Some(InstallAction::Uninstall);
                                                                ui.heading(
                                                                    egui::RichText::new(t.confirm_title)
                                                                        .size(20.0)
                                                                        .strong()
                                                                        .color(if is_uninstall { egui::Color32::from_rgb(248, 113, 113) } else { egui::Color32::from_rgb(251, 191, 36) })
                                                                );
                                                                ui.add_space(14.0);

                                                                if is_uninstall {
                                                                    ui.label(
                                                                        egui::RichText::new(t.confirm_uninstall_warn)
                                                                            .size(13.5)
                                                                            .color(egui::Color32::from_gray(220))
                                                                    );
                                                                } else {
                                                                    ui.label(
                                                                        egui::RichText::new(t.confirm_reset_warn)
                                                                            .size(13.5)
                                                                            .color(egui::Color32::from_gray(220))
                                                                    );
                                                                    ui.add_space(8.0);
                                                                    ui.label(
                                                                        egui::RichText::new(&self.install_path_str)
                                                                            .size(12.0)
                                                                            .monospace()
                                                                            .color(egui::Color32::from_rgb(251, 191, 36))
                                                                    );
                                                                }
                                                            }

                                                            Screen::Progress => {
                                                                let title = match self.action {
                                                                    Some(InstallAction::Repair) => match self.language {
                                                                        Language::Pl => "Naprawianie BadWords...",
                                                                        Language::De => "BadWords reparieren...",
                                                                        Language::Es => "Reparando BadWords...",
                                                                        Language::Fr => "Réparation de BadWords...",
                                                                        Language::It => "Riparazione di BadWords...",
                                                                        Language::Nl => "BadWords repareren...",
                                                                        Language::Pt => "Reparando o BadWords...",
                                                                        Language::Ru => "Восстановление BadWords...",
                                                                        Language::Uk => "Відновлення BadWords...",
                                                                        _ => "Repairing BadWords...",
                                                                    },
                                                                    Some(InstallAction::Move) => match self.language {
                                                                        Language::Pl => "Przenoszenie BadWords...",
                                                                        Language::De => "BadWords verschieben...",
                                                                        Language::Es => "Moviendo BadWords...",
                                                                        Language::Fr => "Déplacement de BadWords...",
                                                                        Language::It => "Spostamento di BadWords...",
                                                                        Language::Nl => "BadWords verplaatsen...",
                                                                        Language::Pt => "Movendo o BadWords...",
                                                                        Language::Ru => "Перемещение BadWords...",
                                                                        Language::Uk => "Переміщення BadWords...",
                                                                        _ => "Relocating BadWords...",
                                                                    },
                                                                    Some(InstallAction::Reset) => match self.language {
                                                                        Language::Pl => "Resetowanie i ponowna instalacja...",
                                                                        Language::De => "Zurücksetzen & Neuinstallation...",
                                                                        Language::Es => "Restableciendo y reinstalando...",
                                                                        Language::Fr => "Réinitialisation et réinstallation...",
                                                                        Language::It => "Ripristino e reinstallazione...",
                                                                        Language::Nl => "Resetten en opnieuw installeren...",
                                                                        Language::Pt => "Redefinindo e reinstalando...",
                                                                        Language::Ru => "Сброс и переустановка...",
                                                                        Language::Uk => "Скидання та перевстановлення...",
                                                                        _ => "Resetting & Reinstalling...",
                                                                    },
                                                                    Some(InstallAction::Uninstall) => match self.language {
                                                                        Language::Pl => "Odinstalowywanie BadWords...",
                                                                        Language::De => "BadWords deinstallieren...",
                                                                        Language::Es => "Desinstalando BadWords...",
                                                                        Language::Fr => "Désinstallation de BadWords...",
                                                                        Language::It => "Disinstallazione di BadWords...",
                                                                        Language::Nl => "BadWords verwijderen...",
                                                                        Language::Pt => "Desinstalando o BadWords...",
                                                                        Language::Ru => "Удаление BadWords...",
                                                                        Language::Uk => "Видалення BadWords...",
                                                                        _ => "Uninstalling BadWords...",
                                                                    },
                                                                    _ => match self.language {
                                                                        Language::Pl => "Instalowanie BadWords...",
                                                                        Language::De => "BadWords installieren...",
                                                                        Language::Es => "Instalando BadWords...",
                                                                        Language::Fr => "Installation de BadWords...",
                                                                        Language::It => "Installazione di BadWords...",
                                                                        Language::Nl => "BadWords installeren...",
                                                                        Language::Pt => "Instalando o BadWords...",
                                                                        Language::Ru => "Установка BadWords...",
                                                                        Language::Uk => "Встановлення BadWords...",
                                                                        _ => "Installing BadWords...",
                                                                    },
                                                                };
                                                                ui.heading(
                                                                    egui::RichText::new(title)
                                                                        .size(20.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(18.0);

                                                                // Płynny, dwupoziomowy pasek postępu ze statusem przetłumaczonym na żywo na wybrany język
                                                                let disp_title = i18n::translate_phrase(&self.status_title, self.language);
                                                                let disp_details = i18n::translate_phrase(&self.status_details, self.language);
                                                                render_badwords_dual_progress(
                                                                    ui,
                                                                    ctx,
                                                                    self.displayed_progress,
                                                                    self.displayed_sub_progress,
                                                                    &disp_title,
                                                                    &disp_details,
                                                                );
                                                            }

                                                            Screen::Complete => {
                                                                ui.heading(
                                                                    egui::RichText::new(t.complete_title)
                                                                        .size(21.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(16.0);

                                                                ui.label(
                                                                    egui::RichText::new(&self.status_title)
                                                                        .size(13.5)
                                                                        .color(egui::Color32::from_gray(220))
                                                                );
                                                                
                                                                if self.action == Some(InstallAction::InstallUpdate) {
                                                                    ui.add_space(20.0);
                                                                    ui.checkbox(&mut self.launch_on_finish, t.launch_checkbox);
                                                                }
                                                            }
                                                        }
                                                    });
                                            },
                                        );
                                    });
                                });

                            // 3. STOPKA (55px, RGB 24, 24, 24)
                            egui::Frame::none()
                                .fill(egui::Color32::from_rgb(24, 24, 24))
                                .rounding(0.0)
                                .inner_margin(egui::Margin::symmetric(20.0, 11.5))
                                .show(ui, |ui| {
                                    ui.set_min_size(egui::vec2(610.0, 32.0));
                                    ui.set_max_size(egui::vec2(610.0, 32.0));

                                    ui.horizontal(|ui| {
                                        // Wybór Języka - czysty tekst (np. "Polski") w stylu przycisków
                                        let lang_text = self.language.display_name();
                                        let lang_btn_size = [100.0, 32.0];
                                        let (lang_rect, lang_resp) = ui.allocate_exact_size(lang_btn_size.into(), egui::Sense::click());
                                        let is_lang_hover = lang_resp.hovered() || ctx.input(|i| i.pointer.hover_pos().is_some_and(|p| lang_rect.contains(p)));

                                        if is_lang_hover || self.language_dropdown_open {
                                            ctx.set_cursor_icon(egui::CursorIcon::PointingHand);
                                            ui.painter().rect_filled(lang_rect, 3.0, egui::Color32::from_rgb(58, 58, 58));
                                        } else {
                                            ui.painter().rect_filled(lang_rect, 3.0, egui::Color32::from_rgb(44, 44, 44));
                                        }
                                        ui.painter().rect_stroke(lang_rect, 3.0, egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(66, 66, 66)));

                                        ui.painter().text(
                                            lang_rect.center(),
                                            egui::Align2::CENTER_CENTER,
                                            lang_text,
                                            egui::FontId::proportional(12.5),
                                            egui::Color32::WHITE,
                                        );

                                        if lang_resp.clicked() {
                                            self.language_dropdown_open = !self.language_dropdown_open;
                                        }

                                        // Popup menu z 10 językami - zaczyna się dokładnie NAD przyciskiem (bez zasłaniania go!)
                                        if self.language_dropdown_open {
                                            let item_h = 24.0;
                                            let popup_pad = 4.0;
                                            let popup_h = Language::ALL.len() as f32 * item_h + popup_pad * 2.0;
                                            let popup_rect = egui::Rect::from_min_size(
                                                egui::pos2(lang_rect.min.x, lang_rect.min.y - popup_h - 2.0),
                                                egui::vec2(lang_btn_size[0], popup_h),
                                            );
                                            let dropdown_full_rect = popup_rect.union(lang_rect);

                                            // Zamknięcie po kliknięciu w dowolny inny obszar okna
                                            if ctx.input(|i| i.pointer.any_click()) {
                                                if let Some(pos) = ctx.input(|i| i.pointer.interact_pos()) {
                                                    if !dropdown_full_rect.contains(pos) {
                                                        self.language_dropdown_open = false;
                                                    }
                                                }
                                            }

                                            if self.language_dropdown_open {
                                                egui::Area::new(egui::Id::new("lang_popup_menu"))
                                                    .fixed_pos(popup_rect.min)
                                                    .order(egui::Order::Foreground)
                                                    .show(ctx, |ui| {
                                                        egui::Frame::none()
                                                            .fill(egui::Color32::from_rgb(34, 34, 34))
                                                            .stroke(egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(66, 66, 66)))
                                                            .rounding(3.0)
                                                            .inner_margin(egui::Margin::symmetric(3.0, popup_pad))
                                                            .show(ui, |ui| {
                                                                ui.spacing_mut().item_spacing = egui::vec2(0.0, 0.0);
                                                                ui.set_width(lang_btn_size[0] - 6.0);
                                                                for lang in Language::ALL {
                                                                    let is_curr = lang == self.language;
                                                                    let (item_rect, item_resp) = ui.allocate_exact_size(
                                                                        egui::vec2(lang_btn_size[0] - 6.0, item_h),
                                                                        egui::Sense::click(),
                                                                    );
                                                                    let is_item_hover = item_resp.hovered() || ctx.input(|i| i.pointer.hover_pos().is_some_and(|p| item_rect.contains(p)));

                                                                    if is_item_hover {
                                                                        ctx.set_cursor_icon(egui::CursorIcon::PointingHand);
                                                                        ui.painter().rect_filled(item_rect, 2.0, egui::Color32::from_rgb(54, 54, 54));
                                                                    } else if is_curr {
                                                                        ui.painter().rect_filled(item_rect, 2.0, egui::Color32::from_white_alpha(20));
                                                                    }

                                                                    let (text_color, font) = if is_curr || is_item_hover {
                                                                        (egui::Color32::WHITE, egui::FontId::proportional(12.0))
                                                                    } else {
                                                                        (egui::Color32::from_gray(215), egui::FontId::proportional(12.0))
                                                                    };

                                                                    ui.painter().text(
                                                                        item_rect.center(),
                                                                        egui::Align2::CENTER_CENTER,
                                                                        lang.display_name(),
                                                                        font,
                                                                        text_color,
                                                                    );

                                                                    if item_resp.clicked() {
                                                                        self.language = lang;
                                                                        self.language_dropdown_open = false;
                                                                        ctx.request_repaint();
                                                                    }
                                                                }
                                                            });
                                                    });
                                            }
                                        }
                                        
                                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                            match self.screen {
                                                Screen::Welcome => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_cancel) {
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                    ui.add_space(10.0);
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_next) {
                                                        self.screen = Screen::Menu;
                                                    }
                                                }

                                                Screen::Menu => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_cancel) {
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                    ui.add_space(10.0);
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_back) {
                                                        self.screen = Screen::Welcome;
                                                    }
                                                }

                                                Screen::SelectPath => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_cancel) {
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                    ui.add_space(10.0);
                                                    let btn_label = if self.action == Some(InstallAction::Move) { t.btn_move } else { t.btn_next };
                                                    if custom_button(ui, ctx, [100.0, 32.0], btn_label) {
                                                        self.start_action();
                                                    }
                                                    ui.add_space(10.0);
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_back) {
                                                        self.screen = Screen::Menu;
                                                    }
                                                }

                                                Screen::ConfirmAction => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_cancel) {
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                    ui.add_space(10.0);
                                                    let is_uninstall = self.action == Some(InstallAction::Uninstall);
                                                    let btn_label = if is_uninstall { t.btn_uninstall } else { t.btn_reset };
                                                    if custom_button(ui, ctx, [115.0, 32.0], btn_label) {
                                                        self.start_action();
                                                    }
                                                    ui.add_space(10.0);
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_back) {
                                                        self.screen = Screen::Menu;
                                                    }
                                                }

                                                Screen::Progress => {
                                                    ui.add_enabled_ui(false, |ui| {
                                                        let _ = ui.add_sized([100.0, 32.0], egui::Button::new(t.btn_cancel));
                                                    });
                                                }

                                                Screen::Complete => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], t.btn_finish) {
                                                        if self.launch_on_finish && self.action == Some(InstallAction::InstallUpdate) {
                                                            let target = self.current_target_path();
                                                            #[cfg(target_os = "windows")]
                                                            {
                                                                let pythonw = target.join("venv").join("Scripts").join("pythonw.exe");
                                                                let main_py = target.join("main.py");
                                                                let _ = os::create_hidden_command(&pythonw).arg(&main_py).spawn();
                                                            }
                                                            #[cfg(target_os = "macos")]
                                                            {
                                                                let python = target.join("venv").join("bin").join("python3");
                                                                let main_py = target.join("main.py");
                                                                let _ = std::process::Command::new(&python).arg(&main_py).spawn();
                                                            }
                                                            #[cfg(target_os = "linux")]
                                                            {
                                                                let python = target.join("venv").join("bin").join("python");
                                                                let main_py = target.join("main.py");
                                                                let _ = std::process::Command::new(&python).arg(&main_py).spawn();
                                                            }
                                                        }
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                }
                                            }
                                        });
                                    });
                                }); // Footer
                        }); // ui.vertical
                    }); // inner frame
            }); // CentralPanel
    }
}

/// Rysuje podwójny, animowany pasek postępu Liquid ze statusem POD każdym paskiem
fn render_badwords_dual_progress(
    ui: &mut egui::Ui,
    ctx: &egui::Context,
    main_progress: f32,
    sub_progress: f32,
    status_title: &str,
    status_details: &str,
) {
    let width = 392.0;
    let time = ctx.input(|i| i.time);

    // 1. GŁÓWNY PASEK POSTĘPU (10px wysokości)
    let pct_str = format!("{:.0}%", (main_progress * 100.0).clamp(0.0, 100.0));
    let (main_rect, _) = ui.allocate_exact_size(egui::vec2(width, 10.0), egui::Sense::hover());
    let painter = ui.painter();
    painter.rect_filled(main_rect, 5.0, egui::Color32::from_rgb(26, 26, 26));
    painter.rect_stroke(main_rect, 5.0, egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(48, 48, 48)));

    let clamped_main = main_progress.clamp(0.0, 1.0);
    if clamped_main > 0.005 {
        let fill_w = (main_rect.width() * clamped_main).max(8.0);
        let fill_rect = egui::Rect::from_min_size(main_rect.min, egui::vec2(fill_w, main_rect.height()));

        let start_col = egui::Color32::from_rgb(26, 122, 62);
        let end_col = egui::Color32::from_rgb(184, 208, 53);

        let mut mesh = egui::Mesh::default();
        mesh.colored_vertex(fill_rect.left_top(), start_col);
        mesh.colored_vertex(fill_rect.left_bottom(), start_col);
        mesh.colored_vertex(fill_rect.right_top(), end_col);
        mesh.colored_vertex(fill_rect.right_bottom(), end_col);
        mesh.add_triangle(0, 1, 2);
        mesh.add_triangle(2, 1, 3);
        painter.add(egui::Shape::Mesh(mesh));

        // Windows-Style Soft Gloss Shimmer Beam
        let beam_w = 70.0;
        let full_cycle = main_rect.width() + beam_w * 2.0;
        let cycle = ((time * 160.0) as f32) % full_cycle;
        let beam_center = main_rect.min.x + cycle - beam_w;

        let b_left = (beam_center - beam_w * 0.5).max(fill_rect.min.x);
        let b_mid = beam_center.clamp(fill_rect.min.x, fill_rect.max.x);
        let b_right = (beam_center + beam_w * 0.5).min(fill_rect.max.x);

        if b_right > b_left {
            if b_mid > b_left {
                let mut left_mesh = egui::Mesh::default();
                left_mesh.colored_vertex(egui::pos2(b_left, fill_rect.min.y), egui::Color32::from_white_alpha(0));
                left_mesh.colored_vertex(egui::pos2(b_left, fill_rect.max.y), egui::Color32::from_white_alpha(0));
                left_mesh.colored_vertex(egui::pos2(b_mid, fill_rect.min.y), egui::Color32::from_white_alpha(90));
                left_mesh.colored_vertex(egui::pos2(b_mid, fill_rect.max.y), egui::Color32::from_white_alpha(90));
                left_mesh.add_triangle(0, 1, 2);
                left_mesh.add_triangle(2, 1, 3);
                painter.add(egui::Shape::Mesh(left_mesh));
            }
            if b_right > b_mid {
                let mut right_mesh = egui::Mesh::default();
                right_mesh.colored_vertex(egui::pos2(b_mid, fill_rect.min.y), egui::Color32::from_white_alpha(90));
                right_mesh.colored_vertex(egui::pos2(b_mid, fill_rect.max.y), egui::Color32::from_white_alpha(90));
                right_mesh.colored_vertex(egui::pos2(b_right, fill_rect.min.y), egui::Color32::from_white_alpha(0));
                right_mesh.colored_vertex(egui::pos2(b_right, fill_rect.max.y), egui::Color32::from_white_alpha(0));
                right_mesh.add_triangle(0, 1, 2);
                right_mesh.add_triangle(2, 1, 3);
                painter.add(egui::Shape::Mesh(right_mesh));
            }
        }

        let gloss_rect = egui::Rect::from_min_size(fill_rect.min, egui::vec2(fill_w, 3.5));
        painter.rect_filled(gloss_rect, 2.5, egui::Color32::from_white_alpha(25));
    }

    ui.add_space(6.0);

    // GŁÓWNY TYTUŁ + PROCENT: Umieszczony POD głównym paskiem
    let (header_rect, _) = ui.allocate_exact_size(egui::vec2(width, 18.0), egui::Sense::hover());
    let title_max_w = width - 55.0;
    let title_galley = ui.painter().layout(
        status_title.to_string(),
        egui::FontId::proportional(13.0),
        egui::Color32::from_gray(225),
        title_max_w,
    );
    let title_clip = egui::Rect::from_min_size(header_rect.min, egui::vec2(title_max_w, 18.0));
    ui.painter().with_clip_rect(title_clip).galley(header_rect.min, title_galley, egui::Color32::from_gray(225));

    ui.painter().text(
        header_rect.right_top(),
        egui::Align2::RIGHT_TOP,
        pct_str,
        egui::FontId::proportional(13.0),
        egui::Color32::from_rgb(184, 208, 53),
    );

    ui.add_space(14.0);

    // 2. POD-PASEK POSTĘPU: Animowany pasek mikro-kroku
    {
        let (sub_rect, _) = ui.allocate_exact_size(egui::vec2(width, 6.0), egui::Sense::hover());
        let painter = ui.painter();
        painter.rect_filled(sub_rect, 3.0, egui::Color32::from_rgb(22, 22, 22));
        painter.rect_stroke(sub_rect, 3.0, egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(42, 42, 42)));

        let sub_start = egui::Color32::from_rgb(26, 122, 62);
        let sub_end = egui::Color32::from_rgb(184, 208, 53);

        let clamped_sub = sub_progress.clamp(0.0, 1.0);
        if clamped_sub > 0.01 && clamped_sub <= 1.0 {
            let sub_fill_w = (sub_rect.width() * clamped_sub).max(6.0);
            let sub_fill_rect = egui::Rect::from_min_size(sub_rect.min, egui::vec2(sub_fill_w, sub_rect.height()));

            let mut sub_mesh = egui::Mesh::default();
            sub_mesh.colored_vertex(sub_fill_rect.left_top(), sub_start);
            sub_mesh.colored_vertex(sub_fill_rect.left_bottom(), sub_start);
            sub_mesh.colored_vertex(sub_fill_rect.right_top(), sub_end);
            sub_mesh.colored_vertex(sub_fill_rect.right_bottom(), sub_end);
            sub_mesh.add_triangle(0, 1, 2);
            sub_mesh.add_triangle(2, 1, 3);
            painter.add(egui::Shape::Mesh(sub_mesh));

            // Soft shimmer
            let sub_beam_w = 40.0;
            let sub_full_cycle = sub_rect.width() + sub_beam_w * 2.0;
            let sub_cycle = ((time * 180.0) as f32) % sub_full_cycle;
            let sub_beam_center = sub_rect.min.x + sub_cycle - sub_beam_w;
            let sb_left = (sub_beam_center - sub_beam_w * 0.5).max(sub_fill_rect.min.x);
            let sb_mid = sub_beam_center.clamp(sub_fill_rect.min.x, sub_fill_rect.max.x);
            let sb_right = (sub_beam_center + sub_beam_w * 0.5).min(sub_fill_rect.max.x);

            if sb_right > sb_left {
                if sb_mid > sb_left {
                    let mut sm = egui::Mesh::default();
                    sm.colored_vertex(egui::pos2(sb_left, sub_fill_rect.min.y), egui::Color32::from_white_alpha(0));
                    sm.colored_vertex(egui::pos2(sb_left, sub_fill_rect.max.y), egui::Color32::from_white_alpha(0));
                    sm.colored_vertex(egui::pos2(sb_mid, sub_fill_rect.min.y), egui::Color32::from_white_alpha(60));
                    sm.colored_vertex(egui::pos2(sb_mid, sub_fill_rect.max.y), egui::Color32::from_white_alpha(60));
                    sm.add_triangle(0, 1, 2);
                    sm.add_triangle(2, 1, 3);
                    painter.add(egui::Shape::Mesh(sm));
                }
                if sb_right > sb_mid {
                    let mut sm = egui::Mesh::default();
                    sm.colored_vertex(egui::pos2(sb_mid, sub_fill_rect.min.y), egui::Color32::from_white_alpha(60));
                    sm.colored_vertex(egui::pos2(sb_mid, sub_fill_rect.max.y), egui::Color32::from_white_alpha(60));
                    sm.colored_vertex(egui::pos2(sb_right, sub_fill_rect.min.y), egui::Color32::from_white_alpha(0));
                    sm.colored_vertex(egui::pos2(sb_right, sub_fill_rect.max.y), egui::Color32::from_white_alpha(0));
                    sm.add_triangle(0, 1, 2);
                    sm.add_triangle(2, 1, 3);
                    painter.add(egui::Shape::Mesh(sm));
                }
            }
        } else {
            let pill_w = (sub_rect.width() * 0.25).clamp(65.0, 95.0);
            let cycle_period = sub_rect.width() + pill_w;
            let speed = 190.0;
            let x_rel = ((time * speed) as f32) % cycle_period - pill_w;

            let pill_left = (sub_rect.min.x + x_rel).max(sub_rect.min.x);
            let pill_right = (sub_rect.min.x + x_rel + pill_w).min(sub_rect.max.x);

            if pill_right > pill_left {
                let pill_rect = egui::Rect::from_min_max(
                    egui::pos2(pill_left, sub_rect.min.y),
                    egui::pos2(pill_right, sub_rect.max.y),
                );

                let mut pill_mesh = egui::Mesh::default();
                pill_mesh.colored_vertex(pill_rect.left_top(), sub_start);
                pill_mesh.colored_vertex(pill_rect.left_bottom(), sub_start);
                pill_mesh.colored_vertex(pill_rect.right_top(), sub_end);
                pill_mesh.colored_vertex(pill_rect.right_bottom(), sub_end);
                pill_mesh.add_triangle(0, 1, 2);
                pill_mesh.add_triangle(2, 1, 3);
                painter.add(egui::Shape::Mesh(pill_mesh));
            }
        }
    }

    ui.add_space(6.0);

    // 3. DETALE MIKRO-KROKU: Umieszczone POD dolnym paskiem z pełną, dynamiczną wysokością na łamanie tekstu
    if !status_details.is_empty() {
        let details_galley = ui.painter().layout(
            status_details.to_string(),
            egui::FontId::proportional(11.5),
            egui::Color32::from_gray(185),
            width,
        );
        let g_height = details_galley.size().y.max(18.0);
        let (details_rect, _) = ui.allocate_exact_size(egui::vec2(width, g_height), egui::Sense::hover());
        ui.painter().galley(details_rect.min, details_galley, egui::Color32::from_gray(185));
    }
}

/// Niezawodny, płynny przycisk z aktywnym stanem hover po dragowaniu
fn custom_button(ui: &mut egui::Ui, ctx: &egui::Context, size: [f32; 2], text: &str) -> bool {
    let (rect, resp) = ui.allocate_exact_size(size.into(), egui::Sense::click());
    let is_hovered = resp.hovered() || ctx.input(|i| i.pointer.hover_pos().is_some_and(|p| rect.contains(p)));

    if is_hovered {
        ctx.set_cursor_icon(egui::CursorIcon::PointingHand);
        ui.painter().rect_filled(rect, 3.0, egui::Color32::from_rgb(58, 58, 58));
    } else {
        ui.painter().rect_filled(rect, 3.0, egui::Color32::from_rgb(44, 44, 44));
    }
    ui.painter().rect_stroke(rect, 3.0, egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(66, 66, 66)));

    ui.painter().text(
        rect.center(),
        egui::Align2::CENTER_CENTER,
        text,
        egui::FontId::proportional(12.5),
        egui::Color32::WHITE,
    );

    resp.clicked()
}

fn render_menu_option(
    ui: &mut egui::Ui,
    ctx: &egui::Context,
    key_digit: &str,
    tag_color: egui::Color32,
    title: &str,
    desc: &str,
    is_keyboard_selected: bool,
) -> bool {
    let width = 392.0;
    let height = 56.0;
    let (rect, resp) = ui.allocate_exact_size(egui::vec2(width, height), egui::Sense::click());
    let is_hovered = resp.hovered() || ctx.input(|i| i.pointer.hover_pos().is_some_and(|p| rect.contains(p)));

    if is_hovered || is_keyboard_selected {
        ctx.set_cursor_icon(egui::CursorIcon::PointingHand);
        let fill_color = if is_hovered {
            egui::Color32::from_white_alpha(18)
        } else {
            egui::Color32::from_white_alpha(10)
        };
        ui.painter().rect_filled(rect, 4.0, fill_color);
        if is_keyboard_selected {
            ui.painter().rect_stroke(rect, 4.0, egui::Stroke::new(1.0_f32, tag_color));
        }
    }

    let painter = ui.painter();

    // 1. Cyfra - powiększona (16.5px), pogrubiona
    painter.text(
        rect.min + egui::vec2(10.0, 8.0),
        egui::Align2::LEFT_TOP,
        key_digit,
        egui::FontId::proportional(16.5),
        tag_color,
    );

    // 2. Tytuł Opcji (13.5px, Bold, czysta biel)
    painter.text(
        rect.min + egui::vec2(28.0, 8.0),
        egui::Align2::LEFT_TOP,
        title,
        egui::FontId::proportional(13.5),
        egui::Color32::WHITE,
    );

    // 3. Opis Opcji z gwarantowanym łamaniem w granicach 355px
    let desc_galley = painter.layout(
        desc.to_string(),
        egui::FontId::proportional(11.0),
        egui::Color32::from_gray(170),
        355.0,
    );
    painter.galley(rect.min + egui::vec2(28.0, 26.0), desc_galley, egui::Color32::from_gray(170));

    resp.clicked()
}
