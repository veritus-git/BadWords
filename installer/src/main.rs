#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod dialogs;
mod engine;
mod os;
mod state;

use eframe::egui;
use engine::APP_VERSION;
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

    // 650x550 okno + 28px marginesu na wielowarstwowy cień Gaussa = 706x606
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([706.0, 606.0])
            .with_resizable(false)
            .with_decorations(false)
            .with_transparent(true)
            .with_icon(
                eframe::icon_data::from_png_bytes(include_bytes!("../../assets/icons/icon_monochrome.png"))
                    .expect("Failed to load icon"),
            ),
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
    install_path_str: String,
    detected_existing: Option<PathBuf>,
    status_title: String,
    status_details: String,
    progress: f32,
    displayed_progress: f32,
    sub_progress: f32,
    displayed_sub_progress: f32,
    launch_on_finish: bool,
    logs: Vec<LogEntry>,
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

        Self {
            screen: Screen::Welcome,
            action: None,
            menu_selected_index: 0,
            keyboard_navigation_active: false,
            install_path_str: path_str,
            detected_existing: detected,
            status_title: "Ready to begin.".to_string(),
            status_details: "Click Next to choose an action.".to_string(),
            progress: 0.0,
            displayed_progress: 0.0,
            sub_progress: 0.0,
            displayed_sub_progress: 0.0,
            launch_on_finish: true,
            logs: vec![],
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

    fn spawn_terminal(&self) {
        if let Ok(exe) = std::env::current_exe() {
            let _ = std::process::Command::new(exe).arg("--terminal").spawn();
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
                engine::run_install(target, tx);
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
        // Płynna animacja pasków postępu (lerp)
        if self.screen == Screen::Progress {
            let target_p = self.progress;
            self.displayed_progress += (target_p - self.displayed_progress) * 0.12;
            let target_sub = self.sub_progress;
            self.displayed_sub_progress += (target_sub - self.displayed_sub_progress) * 0.15;
            ctx.request_repaint_after(Duration::from_millis(20));
        }

        // ── Obsługa zdarzeń z wątku instalacyjnego ──
        let mut had_events = false;
        while let Ok(event) = self.rx.try_recv() {
            had_events = true;
            if event.event == "log" {
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
            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
        }

        // Skrót 'T' odpala dedykowany, całkowicie płynny proces terminala
        if ctx.input(|i| i.key_pressed(egui::Key::T) && !i.raw.modifiers.command && !i.raw.modifiers.ctrl) && self.screen != Screen::SelectPath {
            self.spawn_terminal();
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
                        let _ = std::process::Command::new(target.join("BadWords.exe")).spawn();
                        #[cfg(target_os = "macos")]
                        let _ = std::process::Command::new("open").arg("-a").arg("BadWords").spawn();
                        #[cfg(target_os = "linux")]
                        let _ = std::process::Command::new(target.join("main.py")).spawn();
                    }
                    ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                }
            }
        }

        // ── Główny Panel Aplikacji ───────────────────────────────────
        egui::CentralPanel::default()
            .frame(egui::Frame::none().fill(egui::Color32::TRANSPARENT).inner_margin(0.0))
            .show(ctx, |ui| {
                
                let margin = 28.0;
                let window_rect = egui::Rect::from_min_size(
                    ui.min_rect().min + egui::vec2(margin, margin),
                    egui::vec2(650.0, 550.0),
                );

                // 3 warstwy miękkiego cienia Gaussa
                let painter = ui.painter();
                let shadow_layers = [
                    egui::epaint::Shadow {
                        offset: egui::vec2(0.0, 1.0),
                        blur: 8.0,
                        spread: 1.0,
                        color: egui::Color32::from_black_alpha(45),
                    },
                    egui::epaint::Shadow {
                        offset: egui::vec2(0.0, 3.0),
                        blur: 18.0,
                        spread: 2.0,
                        color: egui::Color32::from_black_alpha(35),
                    },
                    egui::epaint::Shadow {
                        offset: egui::vec2(0.0, 5.0),
                        blur: 28.0,
                        spread: 3.0,
                        color: egui::Color32::from_black_alpha(20),
                    },
                ];

                for shadow in shadow_layers {
                    let mesh = shadow.tessellate(window_rect, 0.0);
                    painter.add(egui::Shape::Mesh(mesh));
                }

                // Ciało Okna (650x550px)
                egui::Frame::none()
                    .fill(egui::Color32::from_rgb(30, 30, 30))
                    .inner_margin(0.0)
                    .outer_margin(margin)
                    .rounding(0.0)
                    .show(ui, |ui| {
                        ui.spacing_mut().item_spacing = egui::vec2(0.0, 0.0);

                        ui.vertical(|ui| {
                            // 1. PASEK TYTUŁOWY (36px, RGB 22, 22, 22)
                            egui::Frame::none()
                                .fill(egui::Color32::from_rgb(22, 22, 22))
                                .rounding(0.0)
                                .inner_margin(0.0)
                                .show(ui, |ui| {
                                    ui.set_height(36.0);
                                    ui.set_width(650.0);

                                    let title_bar_rect = ui.max_rect();

                                    ui.horizontal(|ui| {
                                        ui.spacing_mut().item_spacing.x = 0.0;
                                        
                                        let (close_rect, min_rect) = ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                            let button_size = [46.0, 36.0];
                                            let stroke = egui::Stroke::new(1.0_f32, egui::Color32::from_gray(215));
                                            
                                            // Zamknij (X)
                                            let (close_rect, close_resp) = ui.allocate_exact_size(button_size.into(), egui::Sense::click());
                                            if close_resp.clicked() { ctx.send_viewport_cmd(egui::ViewportCommand::Close); }
                                            
                                            let is_close_hovered = close_resp.hovered() || ctx.input(|i| i.pointer.hover_pos().map_or(false, |p| close_rect.contains(p)));
                                            if is_close_hovered {
                                                ui.painter().rect_filled(close_rect, 0.0, egui::Color32::from_rgb(190, 45, 45));
                                            }
                                            let center = close_rect.center();
                                            ui.painter().line_segment([center + egui::vec2(-4.5, -4.5), center + egui::vec2(4.5, 4.5)], stroke);
                                            ui.painter().line_segment([center + egui::vec2(-4.5, 4.5), center + egui::vec2(4.5, -4.5)], stroke);

                                            // Minimalizuj (-)
                                            let (min_rect, min_resp) = ui.allocate_exact_size(button_size.into(), egui::Sense::click());
                                            if min_resp.clicked() { ctx.send_viewport_cmd(egui::ViewportCommand::Minimized(true)); }
                                            
                                            let is_min_hovered = min_resp.hovered() || ctx.input(|i| i.pointer.hover_pos().map_or(false, |p| min_rect.contains(p)));
                                            if is_min_hovered {
                                                ui.painter().rect_filled(min_rect, 0.0, egui::Color32::from_white_alpha(15));
                                            }
                                            let m_center = min_rect.center();
                                            ui.painter().line_segment([m_center + egui::vec2(-4.5, 0.0), m_center + egui::vec2(4.5, 0.0)], stroke);
                                            
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

                                            (close_rect, min_rect)
                                        }).inner;

                                        // Drag okna
                                        if ctx.input(|i| i.pointer.button_pressed(egui::PointerButton::Primary)) {
                                            if let Some(pos) = ctx.input(|i| i.pointer.latest_pos()) {
                                                if title_bar_rect.contains(pos) && !close_rect.contains(pos) && !min_rect.contains(pos) {
                                                    ctx.send_viewport_cmd(egui::ViewportCommand::StartDrag);
                                                }
                                            }
                                        }
                                    });
                                });

                            // 2. GŁÓWNY OBSZAR (459px, RGB 30, 30, 30)
                            egui::Frame::none()
                                .fill(egui::Color32::from_rgb(30, 30, 30))
                                .rounding(0.0)
                                .inner_margin(0.0)
                                .show(ui, |ui| {
                                    ui.set_height(459.0);
                                    ui.set_width(650.0);

                                    ui.horizontal_top(|ui| {
                                        ui.spacing_mut().item_spacing.x = 0.0;
                                        
                                        // Lewa kolumna: Banner Inno Setup (187x459px)
                                        ui.add(
                                            egui::Image::new(egui::include_image!("../setup-banner.png"))
                                                .fit_to_exact_size(egui::vec2(187.0, 459.0))
                                        );
                                        
                                        // Prawa kolumna (463x459px): Dynamiczna treść
                                        ui.allocate_ui_with_layout(
                                            egui::vec2(463.0, 459.0),
                                            egui::Layout::top_down(egui::Align::Min),
                                            |ui| {
                                                egui::Frame::none()
                                                    .inner_margin(egui::Margin::symmetric(24.0, 22.0))
                                                    .show(ui, |ui| {
                                                        ui.set_width(415.0);
                                                        ui.set_max_width(415.0);
                                                        ui.style_mut().wrap = Some(true);

                                                        match self.screen {
                                                            Screen::Welcome => {
                                                                ui.heading(
                                                                    egui::RichText::new("Welcome to BadWords Setup")
                                                                        .size(22.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(18.0);
                                                                
                                                                ui.horizontal_wrapped(|ui| {
                                                                    ui.spacing_mut().item_spacing.x = 4.0;
                                                                    ui.label(
                                                                        egui::RichText::new("This wizard will guide you through the installation or management of BadWords version")
                                                                            .size(13.5)
                                                                            .color(egui::Color32::from_gray(215))
                                                                    );
                                                                    ui.label(
                                                                        egui::RichText::new(APP_VERSION)
                                                                            .size(13.5)
                                                                            .strong()
                                                                            .color(egui::Color32::WHITE)
                                                                    );
                                                                    ui.label(
                                                                        egui::RichText::new(".")
                                                                            .size(13.5)
                                                                            .color(egui::Color32::from_gray(215))
                                                                    );
                                                                });
                                                                ui.add_space(10.0);
                                                                ui.label(
                                                                    egui::RichText::new("It is recommended that you close all other applications before continuing.")
                                                                        .size(13.5)
                                                                        .color(egui::Color32::from_gray(215))
                                                                );
                                                                ui.add_space(10.0);
                                                                ui.label(
                                                                    egui::RichText::new("Click Next to choose an action, or Cancel to exit Setup.")
                                                                        .size(13.5)
                                                                        .color(egui::Color32::from_gray(215))
                                                                );
                                                            }

                                                            Screen::Menu => {
                                                                ui.heading(
                                                                    egui::RichText::new("Installation Options")
                                                                        .size(21.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(4.0);
                                                                ui.label(
                                                                    egui::RichText::new("Select an option with mouse, arrow keys or numbers [1-5]:")
                                                                        .size(12.5)
                                                                        .color(egui::Color32::from_gray(180))
                                                                );
                                                                ui.add_space(12.0);

                                                                // 1. Standard Install / Update
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "1",
                                                                    egui::Color32::from_rgb(52, 211, 153),
                                                                    "Standard Install / Update",
                                                                    "Install or update BadWords. Keeps your settings and models.",
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 0,
                                                                ) {
                                                                    self.menu_selected_index = 0;
                                                                    self.select_menu_option(0);
                                                                }
                                                                ui.add_space(4.0);

                                                                // 2. Repair Installation
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "2",
                                                                    egui::Color32::from_rgb(56, 189, 248),
                                                                    "Repair Installation",
                                                                    "Replace core files only. Keeps your settings and models.",
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 1,
                                                                ) {
                                                                    self.menu_selected_index = 1;
                                                                    self.select_menu_option(1);
                                                                }
                                                                ui.add_space(4.0);

                                                                // 3. Move Installation
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "3",
                                                                    egui::Color32::from_rgb(129, 140, 248),
                                                                    "Move Installation",
                                                                    "Relocate BadWords to a different folder.",
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 2,
                                                                ) {
                                                                    self.menu_selected_index = 2;
                                                                    self.select_menu_option(2);
                                                                }
                                                                ui.add_space(4.0);

                                                                // 4. Complete Reset
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "4",
                                                                    egui::Color32::from_rgb(251, 191, 36),
                                                                    "Complete Reset",
                                                                    "Delete EVERYTHING and reinstall from scratch.",
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 3,
                                                                ) {
                                                                    self.menu_selected_index = 3;
                                                                    self.select_menu_option(3);
                                                                }
                                                                ui.add_space(4.0);

                                                                // 5. Uninstall
                                                                if render_menu_option(
                                                                    ui,
                                                                    ctx,
                                                                    "5",
                                                                    egui::Color32::from_rgb(248, 113, 113),
                                                                    "Uninstall",
                                                                    "Remove BadWords completely from this system.",
                                                                    self.keyboard_navigation_active && self.menu_selected_index == 4,
                                                                ) {
                                                                    self.menu_selected_index = 4;
                                                                    self.select_menu_option(4);
                                                                }
                                                            }

                                                            Screen::SelectPath => {
                                                                let is_move = self.action == Some(InstallAction::Move);
                                                                ui.heading(
                                                                    egui::RichText::new(if is_move { "Select New Location" } else { "Select Destination Location" })
                                                                        .size(21.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(8.0);
                                                                
                                                                ui.label(
                                                                    egui::RichText::new(if is_move {
                                                                        "Where should BadWords be relocated to?"
                                                                    } else {
                                                                        "Where should BadWords be installed on your computer?"
                                                                    })
                                                                    .size(13.0)
                                                                    .color(egui::Color32::from_gray(215))
                                                                );
                                                                
                                                                if let Some(ref detected) = self.detected_existing {
                                                                    ui.add_space(8.0);
                                                                    ui.horizontal(|ui| {
                                                                        ui.label(
                                                                            egui::RichText::new(format!("Existing installation detected: {}", detected.display()))
                                                                                .size(12.0)
                                                                                .color(egui::Color32::from_rgb(52, 211, 153))
                                                                        );
                                                                    });
                                                                }

                                                                ui.add_space(18.0);

                                                                // Czysty, jednolity input ścieżki (bez podwójnych ramek i bez czarnego tła)
                                                                ui.horizontal(|ui| {
                                                                    egui::Frame::none()
                                                                        .fill(egui::Color32::from_rgb(38, 38, 38))
                                                                        .stroke(egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(68, 68, 68)))
                                                                        .inner_margin(egui::Margin::symmetric(10.0, 7.0))
                                                                        .rounding(3.0)
                                                                        .show(ui, |ui| {
                                                                            ui.add_sized(
                                                                                [275.0, 20.0],
                                                                                egui::TextEdit::singleline(&mut self.install_path_str)
                                                                                    .frame(false)
                                                                                    .text_color(egui::Color32::WHITE)
                                                                                    .font(egui::FontId::proportional(13.0))
                                                                            );
                                                                        });
                                                                    
                                                                    ui.add_space(6.0);
                                                                    
                                                                    if custom_button(ui, ctx, [85.0, 36.0], "Browse...") {
                                                                        if let Some(folder) = dialogs::pick_folder(Some(&self.install_path_str)) {
                                                                            self.install_path_str = folder;
                                                                        }
                                                                    }
                                                                });
                                                                
                                                                ui.add_space(22.0);
                                                                ui.label(
                                                                    egui::RichText::new("At least 500 MB of free disk space is required.")
                                                                        .size(12.0)
                                                                        .color(egui::Color32::from_gray(160))
                                                                );
                                                            }

                                                            Screen::ConfirmAction => {
                                                                let is_uninstall = self.action == Some(InstallAction::Uninstall);
                                                                ui.heading(
                                                                    egui::RichText::new(if is_uninstall { "Confirm Uninstallation" } else { "Confirm Complete Reset" })
                                                                        .size(21.0)
                                                                        .strong()
                                                                        .color(if is_uninstall { egui::Color32::from_rgb(248, 113, 113) } else { egui::Color32::from_rgb(251, 191, 36) })
                                                                );
                                                                ui.add_space(14.0);

                                                                if is_uninstall {
                                                                    ui.label(
                                                                        egui::RichText::new("Are you sure you want to completely remove BadWords and its DaVinci Resolve script integrations from this system?")
                                                                            .size(13.5)
                                                                            .color(egui::Color32::from_gray(220))
                                                                    );
                                                                } else {
                                                                    ui.label(
                                                                        egui::RichText::new("Warning: Complete Reset will DELETE all existing files, settings, models, and configuration in:")
                                                                            .size(13.5)
                                                                            .color(egui::Color32::from_gray(220))
                                                                    );
                                                                    ui.add_space(8.0);
                                                                    ui.label(
                                                                        egui::RichText::new(&self.install_path_str)
                                                                            .size(12.5)
                                                                            .monospace()
                                                                            .color(egui::Color32::from_rgb(251, 191, 36))
                                                                    );
                                                                    ui.add_space(8.0);
                                                                    ui.label(
                                                                        egui::RichText::new("A fresh clean copy of BadWords will be installed.")
                                                                            .size(13.0)
                                                                            .color(egui::Color32::from_gray(200))
                                                                    );
                                                                }
                                                            }

                                                            Screen::Progress => {
                                                                let title = match self.action {
                                                                    Some(InstallAction::Repair) => "Repairing BadWords...",
                                                                    Some(InstallAction::Move) => "Relocating BadWords...",
                                                                    Some(InstallAction::Reset) => "Resetting & Reinstalling...",
                                                                    Some(InstallAction::Uninstall) => "Uninstalling BadWords...",
                                                                    _ => "Installing BadWords...",
                                                                };
                                                                ui.heading(
                                                                    egui::RichText::new(title)
                                                                        .size(21.0)
                                                                        .strong()
                                                                        .color(egui::Color32::WHITE)
                                                                );
                                                                ui.add_space(20.0);

                                                                // Płynny, dwupoziomowy pasek postępu Liquid z gradientem BadWords i animacją shimmer
                                                                render_badwords_dual_progress(
                                                                    ui,
                                                                    ctx,
                                                                    self.displayed_progress,
                                                                    self.displayed_sub_progress,
                                                                    &self.status_title,
                                                                    &self.status_details,
                                                                );
                                                            }

                                                            Screen::Complete => {
                                                                ui.heading(
                                                                    egui::RichText::new("Operation Completed")
                                                                        .size(22.0)
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
                                                                    ui.checkbox(&mut self.launch_on_finish, "Launch BadWords now");
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
                                    ui.set_height(32.0);
                                    ui.set_width(610.0);

                                    ui.horizontal(|ui| {
                                        if terminal_icon_button(ui, ctx, [32.0, 32.0]) {
                                            self.spawn_terminal();
                                        }
                                        
                                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                            match self.screen {
                                                Screen::Welcome => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], "Cancel") {
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                    ui.add_space(10.0);
                                                    if custom_button(ui, ctx, [100.0, 32.0], "Next >") {
                                                        self.screen = Screen::Menu;
                                                    }
                                                }

                                                Screen::Menu => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], "Cancel") {
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                    ui.add_space(10.0);
                                                    if custom_button(ui, ctx, [100.0, 32.0], "< Back") {
                                                        self.screen = Screen::Welcome;
                                                    }
                                                }

                                                Screen::SelectPath => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], "Cancel") {
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                    ui.add_space(10.0);
                                                    let btn_label = if self.action == Some(InstallAction::Move) { "Move >" } else { "Next >" };
                                                    if custom_button(ui, ctx, [100.0, 32.0], btn_label) {
                                                        self.start_action();
                                                    }
                                                    ui.add_space(10.0);
                                                    if custom_button(ui, ctx, [100.0, 32.0], "< Back") {
                                                        self.screen = Screen::Menu;
                                                    }
                                                }

                                                Screen::ConfirmAction => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], "Cancel") {
                                                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                                                    }
                                                    ui.add_space(10.0);
                                                    let is_uninstall = self.action == Some(InstallAction::Uninstall);
                                                    let btn_label = if is_uninstall { "Uninstall" } else { "Reset & Install" };
                                                    if custom_button(ui, ctx, [115.0, 32.0], btn_label) {
                                                        self.start_action();
                                                    }
                                                    ui.add_space(10.0);
                                                    if custom_button(ui, ctx, [100.0, 32.0], "< Back") {
                                                        self.screen = Screen::Menu;
                                                    }
                                                }

                                                Screen::Progress => {
                                                    ui.add_enabled_ui(false, |ui| {
                                                        let _ = ui.add_sized([100.0, 32.0], egui::Button::new("Cancel"));
                                                    });
                                                }

                                                Screen::Complete => {
                                                    if custom_button(ui, ctx, [100.0, 32.0], "Finish") {
                                                        if self.launch_on_finish && self.action == Some(InstallAction::InstallUpdate) {
                                                            let target = self.current_target_path();
                                                            #[cfg(target_os = "windows")]
                                                            let _ = std::process::Command::new(target.join("BadWords.exe")).spawn();
                                                            #[cfg(target_os = "macos")]
                                                            let _ = std::process::Command::new("open").arg("-a").arg("BadWords").spawn();
                                                            #[cfg(target_os = "linux")]
                                                            let _ = std::process::Command::new(target.join("main.py")).spawn();
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

/// Rysuje podwójny, animowany pasek postępu Liquid z gradientem BadWords i pod-paskiem operacji
fn render_badwords_dual_progress(
    ui: &mut egui::Ui,
    ctx: &egui::Context,
    main_progress: f32,
    sub_progress: f32,
    status_title: &str,
    status_details: &str,
) {
    let width = ui.available_width().min(405.0);
    let time = ctx.input(|i| i.time);

    // 1. Nagłówek i odczyt procentowy (dokładnie dopasowany do szerokości paska)
    ui.allocate_ui_with_layout(
        egui::vec2(width, 22.0),
        egui::Layout::left_to_right(egui::Align::Center),
        |ui| {
            ui.set_max_width(width);
            let pct_num = (main_progress.clamp(0.0, 1.0) * 100.0).round() as u32;

            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.add(
                    egui::Label::new(
                        egui::RichText::new(format!("{:>3}%", pct_num))
                            .size(13.5)
                            .strong()
                            .family(egui::FontFamily::Monospace)
                            .color(egui::Color32::from_rgb(184, 208, 53)),
                    ).wrap(false)
                );

                ui.with_layout(egui::Layout::left_to_right(egui::Align::Center), |ui| {
                    ui.add(
                        egui::Label::new(
                            egui::RichText::new(status_title)
                                .size(13.5)
                                .strong()
                                .color(egui::Color32::WHITE)
                        ).truncate(true).wrap(false)
                    );
                });
            });
        }
    );
    ui.add_space(6.0);

    // 2. GŁÓWNY PASEK POSTĘPU (10px wysokości, zaokrąglone rogi 5px, gradient #1a7a3e -> #b8d035)
    let (main_rect, _) = ui.allocate_exact_size(egui::vec2(width, 10.0), egui::Sense::hover());
    {
        let painter = ui.painter();

        // Tło paska (#202020) z ciemnoszarą ramką (#363636)
        painter.rect_filled(main_rect, 5.0, egui::Color32::from_rgb(28, 28, 28));
        painter.rect_stroke(main_rect, 5.0, egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(48, 48, 48)));

        let clamped_main = main_progress.clamp(0.0, 1.0);
        if clamped_main > 0.005 {
            let fill_w = (main_rect.width() * clamped_main).max(8.0);
            let fill_rect = egui::Rect::from_min_size(main_rect.min, egui::vec2(fill_w, main_rect.height()));

            // Gradient poziomy od #1a7a3e (RGB 26, 122, 62) do #b8d035 (RGB 184, 208, 53)
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

            // Windows-Style Soft Gloss Shimmer Beam (70px szerokości, stały cykl na całej szerokości ramki paska)
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

            // Subtelny połysk górnej krawędzi
            let gloss_rect = egui::Rect::from_min_size(fill_rect.min, egui::vec2(fill_w, 3.5));
            painter.rect_filled(gloss_rect, 2.5, egui::Color32::from_white_alpha(25));
        }
    }

    ui.add_space(16.0);

    // 3. POD-OPERACJA: Detale mikro-kroku (bez drugiego procenta) i pasek podoperacji / animowana pastylka
    if !status_details.is_empty() {
        ui.allocate_ui_with_layout(
            egui::vec2(width, 18.0),
            egui::Layout::left_to_right(egui::Align::Center),
            |ui| {
                ui.set_max_width(width);
                ui.add(
                    egui::Label::new(
                        egui::RichText::new(status_details)
                            .size(12.0)
                            .color(egui::Color32::from_gray(185))
                    ).truncate(true).wrap(false)
                );
            }
        );
        ui.add_space(5.0);

        let (sub_rect, _) = ui.allocate_exact_size(egui::vec2(width, 6.0), egui::Sense::hover());
        let painter = ui.painter();
        painter.rect_filled(sub_rect, 3.0, egui::Color32::from_rgb(22, 22, 22));
        painter.rect_stroke(sub_rect, 3.0, egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(42, 42, 42)));

        let sub_start = egui::Color32::from_rgb(26, 122, 62);
        let sub_end = egui::Color32::from_rgb(184, 208, 53);

        let clamped_sub = sub_progress.clamp(0.0, 1.0);
        if clamped_sub > 0.01 && clamped_sub <= 1.0 {
            // Tryb określony: Płynne wypełnienie podczas aktywnego pobierania bajtów
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

            // Soft shimmer na pod-pasku (40px, stały cykl na całej szerokości ramki pod-paska)
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
            // Tryb nieokreślony: Nieskończona, płynnie sunąca pastylka BadWords z pełnym gradientem #1a7a3e -> #b8d035
            let pill_w = (sub_rect.width() * 0.25).clamp(65.0, 95.0);
            let cycle_period = sub_rect.width() + pill_w;
            let speed = 190.0; // px per second
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
}

/// Przycisk ikony terminala (bez tła, z płynnym podświetleniem SVG ścieżek terminal.svg)
fn terminal_icon_button(ui: &mut egui::Ui, ctx: &egui::Context, size: [f32; 2]) -> bool {
    let (rect, resp) = ui.allocate_exact_size(size.into(), egui::Sense::click());
    let is_hovered = resp.hovered() || ctx.input(|i| i.pointer.hover_pos().map_or(false, |p| rect.contains(p)));

    let stroke_color = if is_hovered {
        ctx.set_cursor_icon(egui::CursorIcon::PointingHand);
        egui::Color32::from_rgb(255, 255, 255)
    } else {
        egui::Color32::from_gray(160)
    };

    let painter = ui.painter();
    let center = rect.center();
    let stroke = egui::Stroke::new(1.8_f32, stroke_color);

    // Prompt Chevron '>': M4 17l6-6l-6-6 -> (4, 5) -> (10, 11) -> (4, 17) przesunięte względem center
    let p1 = center + egui::vec2(-7.5, -5.5);
    let p2 = center + egui::vec2(-2.0, 0.0);
    let p3 = center + egui::vec2(-7.5, 5.5);
    painter.line_segment([p1, p2], stroke);
    painter.line_segment([p2, p3], stroke);

    // Underscore cursor '_': M12 19h8 -> (12, 19) to (20, 19)
    let c1 = center + egui::vec2(0.5, 5.5);
    let c2 = center + egui::vec2(8.0, 5.5);
    painter.line_segment([c1, c2], stroke);

    resp.on_hover_text("Open Live Terminal Logs (T)").clicked()
}

/// Niezawodny, płynny przycisk z aktywnym stanem hover po dragowaniu
fn custom_button(ui: &mut egui::Ui, ctx: &egui::Context, size: [f32; 2], text: &str) -> bool {
    let (rect, resp) = ui.allocate_exact_size(size.into(), egui::Sense::click());
    let is_hovered = resp.hovered() || ctx.input(|i| i.pointer.hover_pos().map_or(false, |p| rect.contains(p)));

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
    let (rect, resp) = ui.allocate_exact_size(egui::vec2(400.0, 52.0), egui::Sense::click());
    let is_hovered = resp.hovered() || ctx.input(|i| i.pointer.hover_pos().map_or(false, |p| rect.contains(p)));

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

    // 1. Cyfra - powiększona (17.5px), pogrubiona, wyrównana DO GÓRY (zgrana z wierszem tytułu)
    painter.text(
        rect.min + egui::vec2(12.0, 8.0),
        egui::Align2::LEFT_TOP,
        key_digit,
        egui::FontId::proportional(17.5),
        tag_color,
    );

    // 2. Tytuł opcji (na tej samej wysokości co cyfra)
    painter.text(
        rect.min + egui::vec2(34.0, 9.0),
        egui::Align2::LEFT_TOP,
        title,
        egui::FontId::proportional(13.5),
        egui::Color32::WHITE,
    );

    // 3. Opis opcji (drugi wiersz)
    painter.text(
        rect.min + egui::vec2(34.0, 29.0),
        egui::Align2::LEFT_TOP,
        desc,
        egui::FontId::proportional(11.5),
        egui::Color32::from_gray(160),
    );

    resp.clicked()
}
