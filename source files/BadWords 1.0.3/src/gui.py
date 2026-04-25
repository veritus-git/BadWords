#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: gui.py
ROLE: Presentation Layer
DESCRIPTION:
Responsible solely for displaying the interface (Tkinter).
Includes High-DPI fixes for Windows and dark theme styling.
Receives user actions and delegates them to Engine or ResolveHandler.
Refactored to be a "Dumb View" - logic delegated to Engine/Algorythms.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import threading
import re
import math
import ctypes # For Windows DPI Awareness & Title Bar
import platform
import subprocess
import os
import time

import config
import algorythms

# ==========================================
# WINDOW POSITIONING & STYLE HELPERS
# ==========================================

def center_on_active_monitor(window, width, height, use_dynamic_height=False):
    """
    Detects which monitor contains the mouse cursor and sets the geometry.
    If use_dynamic_height is True, it queries the requested height from the widgets.
    """
    # Force update to calculate required size
    window.update_idletasks()
    
    if use_dynamic_height:
        req_h = window.winfo_reqheight()
        # Add a little buffer for window decorations if needed, mostly logic is internal
        height = req_h
    
    x_cursor = window.winfo_pointerx()
    y_cursor = window.winfo_pointery()
    
    monitor_x = 0
    monitor_y = 0
    monitor_w = window.winfo_screenwidth()
    monitor_h = window.winfo_screenheight()
    
    # --- LINUX (XRANDR) DETECTION ---
    if platform.system() == "Linux":
        try:
            output = subprocess.check_output("xrandr").decode("utf-8")
            for line in output.splitlines():
                if " connected" in line:
                    match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                    if match:
                        w_curr, h_curr, x_curr, y_curr = map(int, match.groups())
                        if (x_curr <= x_cursor < x_curr + w_curr) and \
                           (y_curr <= y_cursor < y_curr + h_curr):
                            monitor_w = w_curr
                            monitor_h = h_curr
                            monitor_x = x_curr
                            monitor_y = y_curr
                            break
        except Exception:
            pass

    # --- WINDOWS (CTYPES) DETECTION ---
    elif platform.system() == "Windows":
        try:
            user32 = ctypes.windll.user32
            def _monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                rect = lprcMonitor.contents
                m_x = rect.left
                m_y = rect.top
                m_w = rect.right - rect.left
                m_h = rect.bottom - rect.top
                if (m_x <= x_cursor < m_x + m_w) and (m_y <= y_cursor < m_y + m_h):
                    nonlocal monitor_x, monitor_y, monitor_w, monitor_h
                    monitor_x, monitor_y = m_x, m_y
                    monitor_w, monitor_h = m_w, m_h
                    return 0
                return 1
            MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_double)
            user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(_monitor_enum_proc), 0)
        except Exception:
            pass

    # Calculate center relative to detected monitor
    final_x = monitor_x + (monitor_w // 2) - (width // 2)
    final_y = monitor_y + (monitor_h // 2) - (height // 2)
    
    # Apply geometry
    window.geometry(f"{width}x{height}+{final_x}+{final_y}")

def apply_title_bar_style(window):
    """
    Forces Windows 10/11 title bar to use dark mode (DWM).
    """
    if platform.system() == "Windows":
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), 4)
        except Exception:
            pass

# ==========================================
# CUSTOM WIDGETS
# ==========================================

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                       background=config.SIDEBAR_BG, fg="white",
                       relief=tk.SOLID, borderwidth=1,
                       font=(config.UI_FONT_NAME, 8, "normal"))
        label.pack(ipadx=4, ipady=2)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class ModernScrollbar(tk.Canvas):
    def __init__(self, parent, command=None, width=12, bg=config.BG_COLOR, trough_color=config.SCROLL_BG, thumb_color=config.SCROLL_FG, active_color=config.SCROLL_ACTIVE):
        super().__init__(parent, width=width, bg=trough_color, highlightthickness=0, bd=0)
        self.command = command
        self.thumb_color = thumb_color
        self.active_color = active_color
        self.normal_color = thumb_color 
        
        self.lo = 0.0
        self.hi = 1.0
        self.is_dragging = False
        self.start_y = 0
        self.start_lo = 0.0
        
        self.bind("<Configure>", self.on_resize)
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def set(self, lo, hi):
        self.lo = float(lo)
        self.hi = float(hi)
        self.redraw()

    def redraw(self):
        self.delete("all")
        h = self.winfo_height()
        w = self.winfo_width()
        if h == 0: return
        
        extent = self.hi - self.lo
        if extent >= 1.0: return 

        v_pad = 4 
        draw_h = h - (2 * v_pad) 
        if draw_h < 1: draw_h = 1

        thumb_h = max(20, extent * draw_h)
        thumb_y = v_pad + (self.lo * draw_h)
        
        pad = 3.5
        draw_w = w - (pad * 2) 
        if draw_w < 2: draw_w = 2 
        
        x = w / 2
        r = draw_w / 2
        y1 = thumb_y + r
        y2 = thumb_y + thumb_h - r
        if y2 < y1: y2 = y1
        
        self.create_line(x, y1, x, y2, width=draw_w, fill=self.normal_color, capstyle=tk.ROUND)

    def on_resize(self, event):
        self.redraw()
        
    def on_enter(self, event):
        if not self.is_dragging:
            self.normal_color = self.active_color
            self.redraw()

    def on_leave(self, event):
        if not self.is_dragging:
            self.normal_color = self.thumb_color
            self.redraw()

    def on_click(self, event):
        h = self.winfo_height()
        if h == 0: return
        v_pad = 4
        draw_h = h - (2 * v_pad)
        if draw_h < 1: draw_h = 1
        
        thumb_y = v_pad + (self.lo * draw_h)
        thumb_h = max(20, (self.hi - self.lo) * draw_h)
        
        if thumb_y <= event.y <= thumb_y + thumb_h:
            self.is_dragging = True
            self.start_y = event.y
            self.start_lo = self.lo
            self.redraw()
        else:
            if self.command:
                extent = self.hi - self.lo
                click_ratio = (event.y - v_pad) / draw_h
                new_start = click_ratio - (extent / 2)
                self.command("moveto", new_start)

    def on_drag(self, event):
        if not self.is_dragging: return
        h = self.winfo_height()
        if h == 0: return
        v_pad = 4
        draw_h = h - (2 * v_pad)
        if draw_h < 1: draw_h = 1

        delta_y = event.y - self.start_y
        delta_ratio = delta_y / draw_h 
        new_lo = self.start_lo + delta_ratio
        
        if self.command:
            self.command("moveto", new_lo)

    def on_release(self, event):
        self.is_dragging = False
        x, y = self.winfo_pointerxy()
        widget_x = self.winfo_rootx()
        widget_y = self.winfo_rooty()
        w = self.winfo_width()
        h = self.winfo_height()
        
        if (widget_x <= x <= widget_x + w) and (widget_y <= y <= widget_y + h):
             self.normal_color = self.active_color
        else:
             self.normal_color = self.thumb_color
        self.redraw()


class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.overrideredirect(True) 
        self.configure(bg=config.BG_COLOR)
        
        w, h = 300, 150
        
        container = tk.Frame(self, bg=config.BG_COLOR, highlightthickness=1, highlightbackground="black")
        container.pack(fill="both", expand=True)
        
        tk.Label(container, text="BadWords", bg=config.BG_COLOR, fg="white", 
                 font=(config.UI_FONT_NAME, 24, "bold")).pack(pady=(40, 5))
        
        self.loading_var = tk.StringVar(value="loading")
        tk.Label(container, textvariable=self.loading_var, bg=config.BG_COLOR, fg=config.NOTE_COL, 
                 font=(config.UI_FONT_NAME, 12)).pack(pady=0)
        
        center_on_active_monitor(self, w, h)
        self.deiconify()
        self.update()
        
        self.dot_count = 0
        self.animate()
        
    def animate(self):
        try:
            dots = "." * (self.dot_count % 4)
            self.loading_var.set(f"loading{dots}")
            self.dot_count += 1
            self.after(400, self.animate)
        except:
            pass


class ScrollableMenu(tk.Toplevel):
    def __init__(self, parent, options, callback, x_anchor, y_anchor, width=150, font_size=10, on_destroy_cb=None):
        super().__init__(parent)
        self.withdraw()
        self.overrideredirect(True)
        self.configure(bg=config.MENU_BG)
        self.callback = callback
        self.on_destroy_cb = on_destroy_cb
        
        self.ui_font = (config.UI_FONT_NAME, font_size)
        
        outer_frame = tk.Frame(self, bg=config.MENU_BG, highlightthickness=0, bd=0)
        outer_frame.pack(fill="both", expand=True)
        
        ITEM_PAD_Y = 5 
        APPROX_ROW_H = 28 
        MAX_ITEMS_VISIBLE = 5
        total_items = len(options)
        
        visible_items = min(total_items, MAX_ITEMS_VISIBLE)
        window_height = (visible_items * APPROX_ROW_H) + 4
        window_width = width
        
        canvas = tk.Canvas(outer_frame, bg=config.MENU_BG, width=window_width, height=window_height, 
                           highlightthickness=0, bd=0)
        
        scrollbar = ModernScrollbar(outer_frame, command=canvas.yview, width=14, 
                                    trough_color=config.MENU_BG, active_color=config.SCROLL_ACTIVE, thumb_color=config.SCROLL_FG)
        
        inner_frame = tk.Frame(canvas, bg=config.MENU_BG)
        canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor="nw", width=window_width)
        
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())
            
        inner_frame.bind("<Configure>", configure_scroll)
        
        hover_color = "#4a4e56"
        
        for label, val in options:
            lbl = tk.Label(inner_frame, text=f"  {label}", bg=config.MENU_BG, fg=config.MENU_FG, 
                           font=self.ui_font, anchor="w", cursor="hand2")
            lbl.pack(fill="x", pady=0, ipady=ITEM_PAD_Y) 
            
            lbl.bind("<Enter>", lambda e, l=lbl: l.configure(bg=hover_color))
            lbl.bind("<Leave>", lambda e, l=lbl: l.configure(bg=config.MENU_BG))
            lbl.bind("<Button-1>", lambda e, v=val: self.on_click(v))

        if total_items > MAX_ITEMS_VISIBLE:
            scrollbar.pack(side="right", fill="y", padx=2) 
            canvas.configure(yscrollcommand=scrollbar.set)
            
            def on_mousewheel(event):
                if event.num == 5 or event.delta == -120:
                    canvas.yview_scroll(1, "units")
                if event.num == 4 or event.delta == 120:
                    canvas.yview_scroll(-1, "units")
            
            canvas.bind_all("<MouseWheel>", on_mousewheel)
            canvas.bind_all("<Button-4>", on_mousewheel)
            canvas.bind_all("<Button-5>", on_mousewheel)
            
            self.bind("<Destroy>", lambda e: self._unbind_mouse(canvas)) 

        canvas.pack(side="left", fill="both", expand=True)
        self.geometry(f"{window_width}x{window_height}+{x_anchor}+{y_anchor}")
        
        self.after(100, lambda: self.bind_all("<Button-1>", self.check_outside_click))
        self.bind("<Escape>", lambda e: self.destroy_menu())
        
        self.deiconify()
        self.focus_set()

    def check_outside_click(self, event):
        try:
            widget = event.widget
            if str(widget).startswith(str(self)):
                return
            self.destroy_menu()
        except:
            self.destroy_menu()

    def destroy_menu(self):
        if self.winfo_exists():
            self.unbind_all("<Button-1>")
            self.destroy()
            if self.on_destroy_cb:
                self.on_destroy_cb()

    def _unbind_mouse(self, canvas):
        try:
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
            self.unbind_all("<Button-1>")
        except: pass

    def on_click(self, val):
        self.callback(val)
        self.destroy_menu()

class CustomMessage(tk.Toplevel):
    def __init__(self, parent, title, message, btn_text="OK", is_error=False):
        super().__init__(parent)
        self.withdraw()
        self.configure(bg=config.BG_COLOR)
        
        self.title(title)
        self.resizable(False, True) # Height dynamic
        
        # Calculate width relative to parent or fixed base
        w = 400
        
        container = tk.Frame(self, bg=config.BG_COLOR, highlightthickness=1, highlightbackground="black")
        container.pack(fill="both", expand=True)

        title_fg = config.CANCEL_BG if is_error else "white"
        tk.Label(container, text=title, bg=config.BG_COLOR, fg=title_fg, 
                 font=(config.UI_FONT_NAME, 12, "bold")).pack(pady=(20, 10))
        
        tk.Label(container, text=message, bg=config.BG_COLOR, fg=config.FG_COLOR, 
                 font=(config.UI_FONT_NAME, 10), wraplength=350, justify="center").pack(pady=5, padx=20)
        
        tk.Button(container, text=btn_text, command=self.destroy,
                  bg=config.BTN_BG, fg="white", font=(config.UI_FONT_NAME, 10, "bold"),
                  relief="flat", bd=0, highlightthickness=0, padx=20, pady=5, 
                  cursor="hand2").pack(side="bottom", pady=20)

        self.transient(parent)
        self.grab_set() 
        center_on_active_monitor(self, w, 220, use_dynamic_height=True)

        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.update_idletasks()
        apply_title_bar_style(self) 
        self.deiconify()
        self.focus_set()

class CustomConfirm(tk.Toplevel):
    def __init__(self, parent, title, message, yes_text="Yes", no_text="No"):
        super().__init__(parent)
        self.withdraw()
        self.configure(bg=config.BG_COLOR)
        
        self.title(title)
        self.resizable(False, True) # Dynamic Height
        self.result = False 
        
        w = 400
        
        container = tk.Frame(self, bg=config.BG_COLOR, highlightthickness=1, highlightbackground="black")
        container.pack(fill="both", expand=True)

        tk.Label(container, text=title, bg=config.BG_COLOR, fg="white", 
                 font=(config.UI_FONT_NAME, 12, "bold")).pack(pady=(20, 10))
        
        tk.Label(container, text=message, bg=config.BG_COLOR, fg=config.FG_COLOR, 
                 font=(config.UI_FONT_NAME, 10), wraplength=350, justify="center").pack(pady=5, padx=20)
        
        btn_frame = tk.Frame(container, bg=config.BG_COLOR)
        btn_frame.pack(side="bottom", pady=20)

        tk.Button(btn_frame, text=no_text, command=self.on_no,
                  bg=config.CANCEL_BG, fg="white", font=(config.UI_FONT_NAME, 9, "bold"),
                  relief="flat", bd=0, highlightthickness=0, padx=15, pady=5, 
                  cursor="hand2").pack(side="left", padx=10)

        tk.Button(btn_frame, text=yes_text, command=self.on_yes,
                  bg=config.BTN_BG, fg="white", font=(config.UI_FONT_NAME, 9, "bold"),
                  relief="flat", bd=0, highlightthickness=0, padx=15, pady=5, 
                  cursor="hand2").pack(side="left", padx=10)
        
        self.transient(parent)
        self.grab_set() 
        center_on_active_monitor(self, w, 220, use_dynamic_height=True)

        self.bind("<Escape>", lambda e: self.on_no())
        
        self.update_idletasks()
        apply_title_bar_style(self)
        self.deiconify()
        self.focus_set()
        self.wait_window()

    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()

# ==========================================
# MAIN GUI CLASS
# ==========================================

class BadWordsGUI:
    def __init__(self, root, engine, resolve_handler):
        self.root = root
        self.root.withdraw()
        
        self.engine = engine
        self.resolve_handler = resolve_handler
        
        self.resize_timer = None
        self._apply_windows_dpi_fix()
        
        try:
            current_dpi = self.root.winfo_fpixels('1i')
            self.scale_factor = current_dpi / 96.0
        except:
            self.scale_factor = 1.0

        self.window_w = int(config.CFG_WINDOW_W_BASE * self.scale_factor)
        # We don't force height base anymore for config, only width is reference
        
        self.lang = "en"
        self.menu_window = None 
        self.root.title(config.APP_NAME)
        self.root.configure(bg=config.BG_COLOR)
        
        self.root.update_idletasks()
        apply_title_bar_style(self.root)
        
        self.font_norm = (config.UI_FONT_NAME, 10)
        self.font_bold = (config.UI_FONT_NAME, 10, "bold")
        self.font_head = (config.UI_FONT_NAME, 16, "bold")
        self.font_small = (config.UI_FONT_NAME, 8)
        self.font_small_bold = (config.UI_FONT_NAME, 8, "bold")

        self.words_data = []
        self.segments_data = []
        self.filler_words = list(config.DEFAULT_BAD_WORDS)
        self.separator_frames = []
        
        self.page_size = 25  
        self.current_page = 0
        self.total_pages = 1
        
        self.current_status_text = self.txt("status_ready")
        self.current_progress_val = 0.0
        
        # --- ANIMATION VARIABLES ---
        self.indeterminate_anim_job = None
        self.indeterminate_pos = 0.0
        
        self.current_frame = None
        self.current_stage_name = "config"
        self.last_analysis_mode = "standalone"
        
        self.is_dragging = False
        self.last_dragged_id = -1
        
        self.model_map = {}

        # --- CONFIG VARS ---
        self.var_lang = tk.StringVar(value="Auto")
        self.var_model = tk.StringVar(value="") 
        self.var_device = tk.StringVar(value="GPU (cuda/rocm)")
        self.var_threshold = tk.StringVar(value="-40")
        
        self.var_snap_margin = tk.StringVar(value="0.25") 
        self.var_offset = tk.StringVar(value="-0.05")     
        self.var_pad = tk.StringVar(value="0.05")         
        
        self.var_enable_reviewer = tk.BooleanVar(value=True)
        self.var_compound = tk.BooleanVar(value=False)
        self.var_silence_cut = tk.BooleanVar(value=False)
        self.var_silence_mark = tk.BooleanVar(value=False)
        self.var_show_inaudible = tk.BooleanVar(value=True)
        self.var_mark_tool = tk.StringVar(value="bad")
        self.var_auto_filler = tk.BooleanVar(value=True) # Checked by default
        self.var_auto_del = tk.BooleanVar(value=False)
        
        self.btn_dl_model = None

        self.setup_styles()
        self.show_config_stage()
        self.root.bind("<Button-1>", self.close_menu_if_open)
        self.root.update_idletasks()
        # Don't use force center on init, rely on show_config_stage logic
        self.update_download_btn_state()
        self.var_model.trace_add("write", lambda *args: self.update_download_btn_state())
        self.root.deiconify()

    def _apply_windows_dpi_fix(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1) 
        except:
            try: ctypes.windll.user32.SetProcessDPIAware()
            except: pass

    # --- HELPERS ---

    def txt(self, key, **kwargs):
        text = config.TRANS.get(self.lang, config.TRANS["en"]).get(key, key)
        if kwargs: return text.format(**kwargs)
        return text

    def set_language(self, lang_code):
        if self.lang == lang_code: return
        self.lang = lang_code
        self.root.title(self.txt("title"))
        if "Ready" in self.current_status_text or "Gotowy" in self.current_status_text:
             self.set_status(self.txt("status_ready"))
        
        if self.current_stage_name == "config": self.show_config_stage()
        elif self.current_stage_name == "reviewer": self.show_reviewer_stage()

    def close_menu_if_open(self, event=None):
        if self.menu_window and self.menu_window.winfo_exists():
            self.menu_window.destroy_menu()
            self.menu_window = None

    def center_window_force(self, w, h):
        center_on_active_monitor(self.root, w, h)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        self.root.option_add('*borderwidth', 0)
        self.root.option_add('*highlightthickness', 0)
        self.root.option_add('*relief', 'flat')
        self.root.option_add('*selectBorderWidth', 0)

        style.configure("TCheckbutton", background=config.BG_COLOR, foreground=config.FG_COLOR, 
                        font=self.font_norm, indicatorbackground=config.CHECKBOX_BG, 
                        indicatorforeground="black", borderwidth=0, focuscolor=config.BG_COLOR)
        style.map("TCheckbutton",
                  background=[('active', config.BG_COLOR), ('!disabled', config.BG_COLOR)],
                  foreground=[('active', config.FG_COLOR), ('!disabled', config.FG_COLOR)],
                  indicatorcolor=[('selected', config.BTN_BG), ('active', config.BTN_BG)])
        
        style.configure("Sidebar.TCheckbutton", background=config.SIDEBAR_BG, foreground=config.FG_COLOR, 
                        font=self.font_norm, indicatorbackground=config.CHECKBOX_BG, 
                        indicatorforeground="black", borderwidth=0, focuscolor=config.SIDEBAR_BG)
        style.map("Sidebar.TCheckbutton",
                  background=[('active', config.SIDEBAR_BG), ('!disabled', config.SIDEBAR_BG)],
                  foreground=[('active', config.FG_COLOR), ('!disabled', config.FG_COLOR)])

    def clear_window(self):
        if self.current_frame: self.current_frame.destroy()
        for widget in self.root.winfo_children(): 
            if isinstance(widget, tk.Toplevel): continue 
            widget.destroy()

    # --- STATUS BAR ---
    def set_status(self, text):
        self.current_status_text = text
        self.root.after(0, self._update_status_ui)
        self.root.after(0, self._update_sidebar_status)

    def set_progress(self, value):
        prev_val = self.current_progress_val
        self.current_progress_val = value
        
        # ANIMATION STATE LOGIC (Indeterminate)
        if value == -1:
            if prev_val != -1: # Just switched to indeterminate
                self.indeterminate_pos = -0.2
                if self.indeterminate_anim_job: 
                    self.root.after_cancel(self.indeterminate_anim_job)
                self._animate_indeterminate()
        else:
            if prev_val == -1: # Just switched from indeterminate
                if self.indeterminate_anim_job:
                    self.root.after_cancel(self.indeterminate_anim_job)
                    self.indeterminate_anim_job = None
            
            # Static update triggers
            self.root.after(0, self._update_status_ui)
            self.root.after(0, self._update_sidebar_status)

    def _animate_indeterminate(self):
        # Stop if state changed
        if self.current_progress_val != -1:
            self.indeterminate_anim_job = None
            return

        # Update position (0.0 to 1.0) with loop
        self.indeterminate_pos += 0.02
        if self.indeterminate_pos > 1.0:
            self.indeterminate_pos = -0.2 # Reset to start (loop)

        # Update Main Status Bar
        if hasattr(self, 'status_canvas') and self.status_canvas.winfo_exists():
            try:
                w = self.status_canvas.winfo_width()
                block_w = w * 0.2
                x1 = self.indeterminate_pos * w
                x2 = x1 + block_w
                self.status_canvas.configure(bg=config.PROGRESS_TRACK_COLOR)
                self.status_canvas.coords(self.status_rect_id, x1, 0, x2, config.PROGRESS_HEIGHT)
                self.status_canvas.itemconfig(self.status_rect_id, fill=config.PROGRESS_FILL_COLOR, width=0)
                # Ensure text is on top
                self.status_canvas.tag_raise(self.status_text_id)
            except: pass

        # Update Sidebar Status Bar
        if hasattr(self, 'sidebar_status_canvas') and self.sidebar_status_canvas.winfo_exists():
            try:
                w = self.sidebar_status_canvas.winfo_width()
                block_w = w * 0.2
                x1 = self.indeterminate_pos * w
                x2 = x1 + block_w
                self.sidebar_status_canvas.configure(bg=config.PROGRESS_TRACK_COLOR)
                self.sidebar_status_canvas.coords(self.sb_rect_id, x1, 0, x2, 24)
                self.sidebar_status_canvas.itemconfig(self.sb_rect_id, fill=config.PROGRESS_FILL_COLOR, width=0)
                self.sidebar_status_canvas.tag_raise(self.sb_text_id)
            except: pass

        # Schedule next frame (30fps -> ~33ms)
        self.indeterminate_anim_job = self.root.after(30, self._animate_indeterminate)

    def _update_status_ui(self):
        if hasattr(self, 'status_canvas') and self.status_canvas.winfo_exists(): 
            try:
                self.status_canvas.itemconfig(self.status_text_id, text=self.current_status_text)
                
                # If indeterminate, skip static rect drawing (animation loop handles it)
                if self.current_progress_val == -1:
                    return

                canvas_width = self.status_canvas.winfo_width()
                if canvas_width < 10: canvas_width = 400 
                new_width = (self.current_progress_val / 100.0) * canvas_width
                
                if self.current_progress_val <= 0:
                    self.status_canvas.configure(bg=config.BG_COLOR)
                    self.status_canvas.itemconfig(self.status_rect_id, fill=config.BG_COLOR, width=0)
                else:
                    self.status_canvas.configure(bg=config.PROGRESS_TRACK_COLOR)
                    self.status_canvas.coords(self.status_rect_id, 0, 0, new_width, config.PROGRESS_HEIGHT)
                    self.status_canvas.itemconfig(self.status_rect_id, fill=config.PROGRESS_FILL_COLOR, width=0)
            except: pass
            
    def _update_sidebar_status(self):
        if hasattr(self, 'sidebar_status_canvas') and self.sidebar_status_canvas.winfo_exists():
            try:
                self.sidebar_status_canvas.itemconfig(self.sb_text_id, text=self.current_status_text)
                
                # If indeterminate, skip static rect drawing
                if self.current_progress_val == -1:
                    return

                w = self.sidebar_status_canvas.winfo_width()
                if w < 10: w = 260
                new_w = (self.current_progress_val / 100.0) * w
                
                if self.current_progress_val <= 0:
                    self.sidebar_status_canvas.configure(bg=config.SIDEBAR_BG)
                    self.sidebar_status_canvas.itemconfig(self.sb_rect_id, fill=config.SIDEBAR_BG, width=0)
                else:
                    self.sidebar_status_canvas.configure(bg=config.PROGRESS_TRACK_COLOR)
                    self.sidebar_status_canvas.coords(self.sb_rect_id, 0, 0, new_w, 24)
                    self.sidebar_status_canvas.itemconfig(self.sb_rect_id, fill=config.PROGRESS_FILL_COLOR, width=0)
            except: pass

    # ==========================
    # SAVE / LOAD SYSTEM (Delegated)
    # ==========================

    def save_project(self):
        try:
            saves_dir = self.engine.os_doc.get_saves_folder()
            
            # Pack current GUI state for engine to save
            data_packet = {
                "lang_code": self.lang,
                "settings": {
                    "lang": self.var_lang.get(),
                    "model": self.var_model.get(),
                    "device": self.var_device.get(),
                    "threshold": self.var_threshold.get(),
                    "snap_margin": self.var_snap_margin.get(),
                    "offset": self.var_offset.get(),
                    "pad": self.var_pad.get(),
                    "enable_reviewer": self.var_enable_reviewer.get(),
                    "compound": self.var_compound.get(),
                    "silence_cut": self.var_silence_cut.get(),
                    "silence_mark": self.var_silence_mark.get(),
                    "show_inaudible": self.var_show_inaudible.get(),
                    "mark_tool": self.var_mark_tool.get(),
                    "auto_filler": self.var_auto_filler.get(),
                    "auto_del": self.var_auto_del.get(),
                },
                "filler_words": self.filler_words,
                "words_data": self.words_data,
                "script_content": ""
            }
            
            if hasattr(self, 'script_area') and self.script_area:
                 raw_script = self.script_area.get("1.0", tk.END).strip()
                 ph = self.txt("ph_script")
                 if raw_script != ph:
                     data_packet["script_content"] = raw_script

            file_path = filedialog.asksaveasfilename(
                parent=self.root,
                initialdir=saves_dir,
                title="Save Project",
                defaultextension=".json",
                filetypes=[("BadWords Project", "*.json"), ("All Files", "*.*")]
            )
            
            if not file_path: return

            # Delegate saving to Engine
            self.engine.save_project_state(file_path, data_packet)
            
            CustomMessage(self.root, "Saved", f"Project saved to:\n{os.path.basename(file_path)}")
            
        except Exception as e:
            CustomMessage(self.root, "Error", f"Failed to save project:\n{e}", is_error=True)

    def load_project(self):
        try:
            saves_dir = self.engine.os_doc.get_saves_folder()
            
            file_path = filedialog.askopenfilename(
                parent=self.root,
                initialdir=saves_dir,
                title="Load Project",
                filetypes=[("BadWords Project", "*.json"), ("All Files", "*.*")]
            )
            
            if not file_path: return
            
            # Delegate loading to Engine
            project_state, segments = self.engine.load_project_state(file_path)
            
            s = project_state.get("settings", {})
            self.set_language(project_state.get("lang_code", "en"))
            
            self.var_lang.set(s.get("lang", "Auto"))
            self.var_model.set(s.get("model", ""))
            self.var_device.set(s.get("device", "GPU (cuda/rocm)"))
            self.var_threshold.set(s.get("threshold", "-40"))
            self.var_snap_margin.set(s.get("snap_margin", "0.25"))
            self.var_offset.set(s.get("offset", "-0.05"))
            self.var_pad.set(s.get("pad", "0.05"))
            self.var_enable_reviewer.set(s.get("enable_reviewer", True))
            self.var_compound.set(s.get("compound", False))
            self.var_silence_cut.set(s.get("silence_cut", False))
            self.var_silence_mark.set(s.get("silence_mark", False))
            self.var_show_inaudible.set(s.get("show_inaudible", True))
            self.var_mark_tool.set(s.get("mark_tool", "bad"))
            self.var_auto_filler.set(s.get("auto_filler", True))
            self.var_auto_del.set(s.get("auto_del", False))
            
            self.filler_words = project_state.get("filler_words", config.DEFAULT_BAD_WORDS)
            self.words_data = project_state.get("words_data", [])
            self.segments_data = segments
            
            self.show_reviewer_stage()
            
            script_content = project_state.get("script_content", "")
            if script_content and hasattr(self, 'script_area') and self.script_area:
                 self.script_area.delete("1.0", tk.END)
                 self.script_area.insert("1.0", script_content)
                 self.script_area.configure(fg=config.FG_COLOR)
            
            self.set_status("Project Loaded.")
            
        except Exception as e:
            CustomMessage(self.root, "Error", f"Failed to load project:\n{e}", is_error=True)

    # ==========================
    # STAGE 1: CONFIGURATION
    # ==========================

    def build_header(self, parent, title_key, show_gear=True):
        header_frame = tk.Frame(parent, bg=config.BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 15))
        tk.Label(header_frame, text=self.txt(title_key), font=self.font_head, 
                 bg=config.BG_COLOR, fg="white").pack(side="left", anchor="w")
        if show_gear: self._add_gear_button(header_frame, bg_color=config.BG_COLOR)

    def _add_gear_button(self, parent, bg_color):
        settings_btn = tk.Label(parent, text="≡", font=(config.UI_FONT_NAME, 20), 
                                bg=bg_color, fg=config.GEAR_COLOR, cursor="hand2", bd=0)
        settings_btn.pack(side="right", anchor="center")
        
        def show_scrollable_menu(event):
            if self.menu_window and self.menu_window.winfo_exists():
                self.menu_window.destroy_menu()
                return

            menu_w = 150
            x = settings_btn.winfo_rootx() + settings_btn.winfo_width() - menu_w
            y = settings_btn.winfo_rooty()
            
            options = []
            for code, data in config.TRANS.items():
                name = data.get("name", code.upper())
                options.append((name, code))
            
            options.sort(key=lambda x: x[0])

            self.menu_window = ScrollableMenu(self.root, options, self.set_language, x, y, width=menu_w)
            return "break"

        settings_btn.bind("<Button-1>", show_scrollable_menu)

    def on_analyze_click(self):
        self.close_menu_if_open()
        
        if not self.engine.os_doc.needs_manual_model_install():
             self.run_analysis_pipeline()
             return

        display_name = self.var_model.get()
        tech_name = self.get_model_technical_name(display_name)
        
        if not self.engine.check_model_exists(tech_name):
            confirm = CustomConfirm(self.root, 
                                    self.txt("title_model_missing"), 
                                    self.txt("msg_model_missing", model=display_name),
                                    yes_text=self.txt("btn_dl_analyze"), 
                                    no_text=self.txt("btn_cancel"))
            if confirm.result:
                self._start_download_sequence(tech_name, on_success=self.run_analysis_pipeline)
            return

        self.run_analysis_pipeline()

    def on_quit_click(self):
        confirm = CustomConfirm(self.root, self.txt("title_confirm"), self.txt("msg_confirm_quit"),
                                yes_text=self.txt("btn_quit"), no_text=self.txt("btn_cancel"))
        if confirm.result:
            self.root.destroy()

    def show_config_stage(self):
        self.current_stage_name = "config"
        self.clear_window()
        
        # --- DYNAMIC HEIGHT / FIXED WIDTH LOGIC ---
        # Allow vertical resizing, disable horizontal resizing
        self.root.resizable(False, True)
        
        # We rely on pack() to determine height, then center dynamically
        main_frame = tk.Frame(self.root, bg=config.BG_COLOR, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        self.current_frame = main_frame

        self.build_header(main_frame, "header_main")

        self.last_menu_close_time = 0

        def create_input_row(parent, label, var, values=None, hint=""):
            container = tk.Frame(parent, bg=config.BG_COLOR)
            container.pack(fill="x", pady=(0, 8))
            lbl_fr = tk.Frame(container, bg=config.BG_COLOR)
            lbl_fr.pack(fill="x")
            tk.Label(lbl_fr, text=label, bg=config.BG_COLOR, fg=config.FG_COLOR, font=self.font_norm).pack(side="left")
            if hint: tk.Label(lbl_fr, text=f" {hint}", bg=config.BG_COLOR, fg=config.NOTE_COL, font=self.font_small).pack(side="left")
            
            if values:
                cb_frame = tk.Frame(container, bg=config.INPUT_BG, cursor="hand2")
                cb_frame.pack(fill="x", pady=(2,0), ipady=3) 
                
                val_lbl = tk.Label(cb_frame, textvariable=var, bg=config.INPUT_BG, fg=config.INPUT_FG, 
                                   font=(config.UI_FONT_NAME, 8), anchor="w", padx=5)
                val_lbl.pack(side="left", fill="x", expand=True)
                
                arrow_lbl = tk.Label(cb_frame, text="▼", bg=config.INPUT_BG, fg=config.NOTE_COL, 
                                     font=(config.UI_FONT_NAME, 8), padx=5)
                arrow_lbl.pack(side="right")
                
                hover_bg = "#404249"

                def on_enter(e):
                    cb_frame.config(bg=hover_bg)
                    val_lbl.config(bg=hover_bg)
                    arrow_lbl.config(bg=hover_bg)
                    
                def on_leave(e):
                    cb_frame.config(bg=config.INPUT_BG)
                    val_lbl.config(bg=config.INPUT_BG)
                    arrow_lbl.config(bg=config.INPUT_BG)
                
                cb_frame.bind("<Enter>", on_enter)
                cb_frame.bind("<Leave>", on_leave)
                val_lbl.bind("<Enter>", on_enter)
                arrow_lbl.bind("<Enter>", on_enter)

                def mark_closed():
                    self.last_menu_close_time = time.time()
                    self.menu_window = None

                def open_menu(event):
                    if time.time() - self.last_menu_close_time < 0.2:
                        return "break"

                    if self.menu_window and self.menu_window.winfo_exists():
                        self.menu_window.destroy_menu()
                        return "break"
                    
                    x = cb_frame.winfo_rootx()
                    y = cb_frame.winfo_rooty() + cb_frame.winfo_height()
                    w = cb_frame.winfo_width()
                    
                    menu_options = [(v, v) for v in values]
                    
                    def cb(val):
                        var.set(val)
                    
                    self.menu_window = ScrollableMenu(self.root, options=menu_options, callback=cb, x_anchor=x, y_anchor=y, width=w, font_size=8, on_destroy_cb=mark_closed)
                    return "break"

                cb_frame.bind("<Button-1>", open_menu)
                val_lbl.bind("<Button-1>", open_menu)
                arrow_lbl.bind("<Button-1>", open_menu)

            else:
                ent = tk.Entry(container, textvariable=var, bg=config.INPUT_BG, fg=config.INPUT_FG, 
                               relief="flat", bd=0, highlightthickness=0, insertbackground="white", font=self.font_norm)
                ent.pack(fill="x", ipady=3, pady=(2,0)) 
                ent.bind("<Button-1>", lambda e: self.close_menu_if_open())

        tk.Label(main_frame, text=self.txt("sec_whisper"), bg=config.BG_COLOR, fg=config.NOTE_COL, font=self.font_small_bold, anchor="w").pack(fill="x", pady=(0, 5))
        
        whisper_langs = [
            "Auto", 
            "English", "Polish", "German", "Spanish", "French", "Italian", "Portuguese",
            "Dutch", "Turkish", "Swedish", "Indonesian", "Vietnamese", "Ukrainian"
        ]
        create_input_row(main_frame, self.txt("lbl_lang"), self.var_lang, whisper_langs)
        
        model_container = tk.Frame(main_frame, bg=config.BG_COLOR)
        model_container.pack(fill="x", pady=(0, 10)) # Increased Margin
        lbl_fr = tk.Frame(model_container, bg=config.BG_COLOR)
        lbl_fr.pack(fill="x")
        tk.Label(lbl_fr, text=self.txt("lbl_model"), bg=config.BG_COLOR, fg=config.FG_COLOR, font=self.font_norm).pack(side="left")
        
        row_inner = tk.Frame(model_container, bg=config.BG_COLOR)
        row_inner.pack(fill="x", pady=(2,0))
        
        self.model_map = {
            self.txt("model_tiny"): "tiny",
            self.txt("model_base"): "base",
            self.txt("model_small"): "small",
            self.txt("model_medium"): "medium",
            self.txt("model_large_turbo"): "large-v3-turbo",
            self.txt("model_large"): "large"
        }
        
        model_options = list(self.model_map.keys())
        
        current_model_display = self.var_model.get()
        if not current_model_display or current_model_display not in model_options:
             self.var_model.set(self.txt("model_medium"))
        
        cb_frame_model = tk.Frame(row_inner, bg=config.INPUT_BG, cursor="hand2")
        cb_frame_model.pack(side="left", fill="x", expand=True, ipady=3)
        
        val_lbl_m = tk.Label(cb_frame_model, textvariable=self.var_model, bg=config.INPUT_BG, fg=config.INPUT_FG, 
                           font=(config.UI_FONT_NAME, 8), anchor="w", padx=5)
        val_lbl_m.pack(side="left", fill="x", expand=True)
        
        arrow_lbl_m = tk.Label(cb_frame_model, text="▼", bg=config.INPUT_BG, fg=config.NOTE_COL, 
                             font=(config.UI_FONT_NAME, 8), padx=5)
        arrow_lbl_m.pack(side="right")
        
        hover_bg_m = "#404249"

        def on_enter_m(e):
            cb_frame_model.config(bg=hover_bg_m)
            val_lbl_m.config(bg=hover_bg_m)
            arrow_lbl_m.config(bg=hover_bg_m)
            
        def on_leave_m(e):
            cb_frame_model.config(bg=config.INPUT_BG)
            val_lbl_m.config(bg=config.INPUT_BG)
            arrow_lbl_m.config(bg=config.INPUT_BG)
        
        cb_frame_model.bind("<Enter>", on_enter_m)
        cb_frame_model.bind("<Leave>", on_leave_m)
        val_lbl_m.bind("<Enter>", on_enter_m)
        arrow_lbl_m.bind("<Enter>", on_enter_m)

        def mark_closed_m():
            self.last_menu_close_time = time.time()
            self.menu_window = None

        def open_menu_model(event):
            if time.time() - self.last_menu_close_time < 0.2:
                return "break"

            if self.menu_window and self.menu_window.winfo_exists():
                self.menu_window.destroy_menu()
                return "break"

            x = cb_frame_model.winfo_rootx()
            y = cb_frame_model.winfo_rooty() + cb_frame_model.winfo_height()
            w = cb_frame_model.winfo_width()
            menu_options = [(v, v) for v in model_options]
            def cb(val): self.var_model.set(val)
            self.menu_window = ScrollableMenu(self.root, options=menu_options, callback=cb, x_anchor=x, y_anchor=y, width=w, font_size=8, on_destroy_cb=mark_closed_m)
            return "break"

        cb_frame_model.bind("<Button-1>", open_menu_model)
        val_lbl_m.bind("<Button-1>", open_menu_model)
        arrow_lbl_m.bind("<Button-1>", open_menu_model)
        
        if self.engine.os_doc.needs_manual_model_install():
            self.btn_dl_model = tk.Button(row_inner, text=self.txt("btn_dl_model"),
                      bg=config.BTN_GHOST_BG, fg="white", 
                      activebackground=config.BTN_GHOST_ACTIVE, activeforeground="white",
                      font=(config.UI_FONT_NAME, 8), relief="flat", bd=0, highlightthickness=0,
                      cursor="hand2", command=self.on_download_model_click)
            self.btn_dl_model.pack(side="left", padx=(10,0), ipady=0)
        else:
            self.btn_dl_model = None 

        create_input_row(main_frame, self.txt("lbl_device"), self.var_device, ["Auto", "GPU (cuda/rocm)", "CPU"], hint="(AMD users: select GPU)")

        fill_container = tk.Frame(main_frame, bg=config.BG_COLOR)
        fill_container.pack(fill="x", pady=(0, 10)) # Increased Margin
        tk.Label(fill_container, text=self.txt("lbl_fillers"), bg=config.BG_COLOR, fg=config.FG_COLOR, font=self.font_norm).pack(side="left", anchor="w")
        
        btn_fillers = tk.Button(main_frame, text=self.txt("btn_edit_fillers"), command=self.open_filler_editor,
                  bg=config.INPUT_BG, fg=config.INPUT_FG, 
                  activebackground=config.INPUT_BG, activeforeground="white",
                  font=(config.UI_FONT_NAME, 8), relief="flat", bd=0, highlightthickness=0,
                  cursor="hand2", anchor="w", padx=5)
        btn_fillers.pack(fill="x", ipady=1, pady=(0, 8))

        tk.Frame(main_frame, height=1, bg=config.INPUT_BG).pack(fill="x", pady=15) # Increased Separator Padding

        # Sync
        tk.Label(main_frame, text=self.txt("sec_sync"), bg=config.BG_COLOR, fg=config.NOTE_COL, font=self.font_small_bold, anchor="w").pack(fill="x", pady=(0, 5))
        grid_fr = tk.Frame(main_frame, bg=config.BG_COLOR)
        grid_fr.pack(fill="x", pady=0)
        col1 = tk.Frame(grid_fr, bg=config.BG_COLOR); col1.pack(side="left", fill="both", expand=True, padx=(0, 5))
        create_input_row(col1, self.txt("lbl_offset"), self.var_offset, hint="(-0.05s)")
        create_input_row(col1, self.txt("lbl_pad"), self.var_pad, hint="(0.05s)")
        col2 = tk.Frame(grid_fr, bg=config.BG_COLOR); col2.pack(side="left", fill="both", expand=True, padx=(5, 0))
        create_input_row(col2, self.txt("lbl_snap"), self.var_snap_margin, hint="(0.25s)")
        create_input_row(col2, self.txt("lbl_thresh"), self.var_threshold, hint="(-40dB)")

        chk_frame = tk.Frame(main_frame, bg=config.BG_COLOR)
        chk_frame.pack(fill="x", pady=(15, 5)) # Increased Margin
        
        ttk.Checkbutton(chk_frame, text=self.txt("chk_reviewer"), variable=self.var_enable_reviewer, style="TCheckbutton").pack(anchor="w", pady=(0,5))
        ttk.Checkbutton(chk_frame, text=self.txt("chk_compound"), variable=self.var_compound, style="TCheckbutton").pack(anchor="w", pady=(5,0))
        
        # FIX: Using proper key for hint label
        tk.Label(chk_frame, text=self.txt("lbl_compound_help"), bg=config.BG_COLOR, fg=config.NOTE_COL, font=self.font_small).pack(anchor="w", padx=(22, 0))

        # Filler (Expanding spacer if window is resized vertically)
        tk.Frame(main_frame, bg=config.BG_COLOR).pack(expand=True, fill="both")
        
        status_container = tk.Frame(main_frame, bg=config.BG_COLOR, height=config.PROGRESS_HEIGHT)
        status_container.pack(fill="x", side="bottom", pady=(0, 10))
        status_container.pack_propagate(False)
        self.status_canvas = tk.Canvas(status_container, bg=config.BG_COLOR, height=config.PROGRESS_HEIGHT, highlightthickness=0, relief="flat")
        self.status_canvas.pack(fill="both", expand=True)
        self.status_rect_id = self.status_canvas.create_rectangle(0, 0, 0, config.PROGRESS_HEIGHT, fill=config.BG_COLOR, width=0)
        self.status_text_id = self.status_canvas.create_text(0, config.PROGRESS_HEIGHT/2, text=self.current_status_text, fill=config.STATUS_TEXT_COLOR, font=(config.UI_FONT_NAME, 9))
        self.status_canvas.bind("<Configure>", lambda e: (self.status_canvas.coords(self.status_text_id, e.width/2, config.PROGRESS_HEIGHT/2), self._update_status_ui()))

        btn_frame = tk.Frame(self.root, bg=config.FOOTER_COLOR, pady=20)
        btn_frame.pack(side="bottom", fill="x")
        
        tk.Button(btn_frame, text=self.txt("btn_import_proj"), command=self.load_project,
                  bg=config.BTN_GHOST_BG, fg="white", 
                  activebackground=config.BTN_GHOST_ACTIVE, activeforeground="white",
                  font=self.font_bold, relief="flat", bd=0, highlightthickness=0,
                  padx=15, pady=5, cursor="hand2").pack(side="left", padx=20)

        self.btn_analyze = tk.Button(btn_frame, text=self.txt("btn_analyze"), command=self.on_analyze_click,
                  bg=config.BTN_BG, fg=config.BTN_FG, 
                  activebackground=config.BTN_ACTIVE, activeforeground="white",
                  font=self.font_bold, relief="flat", bd=0, highlightthickness=0,
                  padx=20, pady=5, cursor="hand2")
        self.btn_analyze.pack(side="right", padx=20)
        
        tk.Button(btn_frame, text=self.txt("btn_quit"), command=self.on_quit_click,
                  bg=config.CANCEL_BG, fg="white", 
                  activebackground=config.CANCEL_ACTIVE, activeforeground="white",
                  font=self.font_bold, relief="flat", bd=0, highlightthickness=0,
                  padx=20, pady=5, cursor="hand2").pack(side="right", padx=0)
        
        # --- RE-CENTER WITH DYNAMIC HEIGHT ---
        center_on_active_monitor(self.root, self.window_w, 0, use_dynamic_height=True)
        
        self._update_status_ui()
        self.update_download_btn_state()

    def update_download_btn_state(self):
        if not self.btn_dl_model: return

        display_name = self.var_model.get()
        if not display_name: return
        
        tech_name = self.get_model_technical_name(display_name)
        
        if self.engine.check_model_exists(tech_name):
            self.btn_dl_model.config(
                text=self.txt("lbl_model_installed"), 
                bg=config.BG_COLOR, 
                fg=config.WORD_TYPO_BG, 
                cursor="arrow", 
                state="disabled"
            )
        else:
            self.btn_dl_model.config(
                text=self.txt("btn_dl_model"),
                bg=config.BTN_GHOST_BG,
                fg="white",
                cursor="hand2",
                state="normal"
            )

    def on_download_model_click(self):
        display_name = self.var_model.get()
        if not display_name: return
        tech_name = self.get_model_technical_name(display_name)
        self._start_download_sequence(tech_name)

    def _start_download_sequence(self, tech_name, on_success=None):
        if self.btn_dl_model:
            self.btn_dl_model.config(state="disabled", text="...", bg=config.BTN_GHOST_ACTIVE)
            
        self.set_status(self.txt("status_downloading", model=tech_name))
        self.set_progress(0)
        
        def run_dl():
            success = self.engine.download_whisper_model_interactive(
                tech_name, 
                progress_callback=self.set_progress
            )
            
            if success:
                self.root.after(0, lambda: self._on_download_success(tech_name, on_success))
            else:
                self.root.after(0, self._on_download_fail)

        threading.Thread(target=run_dl, daemon=True).start()

    def _on_download_success(self, model_name, next_action=None):
        self.set_status(self.txt("status_ready"))
        self.set_progress(0)
        self.update_download_btn_state()
        
        if next_action:
            next_action()
        else:
            CustomMessage(self.root, "Success", self.txt("msg_dl_success", model=model_name))

    def _on_download_fail(self):
        self.set_status(self.txt("err_download"))
        self.set_progress(0)
        self.update_download_btn_state()
        CustomMessage(self.root, "Error", self.txt("err_download"), is_error=True)

    def open_filler_editor(self):
        editor = tk.Toplevel(self.root)
        editor.withdraw()
        editor.configure(bg=config.BG_COLOR)
        
        w, h = 325, 600
        
        lbl = tk.Label(editor, text=self.txt("lbl_fillers_instr"), bg=config.BG_COLOR, fg=config.FG_COLOR, font=(config.UI_FONT_NAME, 9))
        lbl.pack(pady=10, padx=10, anchor="w")
        
        txt_frame = tk.Frame(editor, bg=config.INPUT_BG)
        txt_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        text_widget = tk.Text(txt_frame, bg=config.INPUT_BG, fg="white", font=self.font_norm, bd=0, highlightthickness=0)
        text_widget.pack(fill="both", expand=True, padx=5, pady=5)
        
        current_text = ", ".join(self.filler_words)
        text_widget.insert("1.0", current_text)
        
        btn_frame = tk.Frame(editor, bg=config.BG_COLOR)
        btn_frame.pack(fill="x", pady=15, padx=10)
        
        def on_apply():
            confirm = CustomConfirm(editor, self.txt("title_confirm"), self.txt("msg_confirm_apply"),
                                    yes_text=self.txt("btn_apply"), no_text=self.txt("btn_cancel"))
            if confirm.result:
                raw = text_widget.get("1.0", tk.END).strip()
                new_list = [w.strip() for w in raw.split(',') if w.strip()]
                self.filler_words = new_list
                editor.destroy()
            
        def on_cancel():
            confirm = CustomConfirm(editor, self.txt("title_confirm"), self.txt("msg_confirm_cancel"),
                                    yes_text=self.txt("btn_quit"), no_text=self.txt("btn_cancel"))
            if confirm.result:
                editor.destroy()
        
        tk.Button(btn_frame, text=self.txt("btn_apply"), command=on_apply, 
                  bg=config.BTN_BG, fg="white", 
                  activebackground=config.BTN_ACTIVE, activeforeground="white",
                  font=(config.UI_FONT_NAME, 9, "bold"), relief="flat", highlightthickness=0,
                  padx=15, cursor="hand2").pack(side="right", padx=5)
        tk.Button(btn_frame, text=self.txt("btn_cancel"), command=on_cancel, 
                  bg=config.CANCEL_BG, fg="white", 
                  activebackground=config.CANCEL_ACTIVE, activeforeground="white",
                  font=(config.UI_FONT_NAME, 9, "bold"), relief="flat", highlightthickness=0,
                  padx=15, cursor="hand2").pack(side="right")
        
        editor.transient(self.root)
        editor.grab_set() 
        center_on_active_monitor(editor, w, h)
        
        editor.update_idletasks()
        apply_title_bar_style(editor)
        editor.deiconify()

    # ==========================
    # ENGINE INVOCATION LOGIC
    # ==========================

    def get_model_technical_name(self, display_name):
        return self.model_map.get(display_name, "medium")

    def run_analysis_pipeline(self):
        if not self.resolve_handler.project:
            CustomMessage(self.root, "Error", self.txt("err_resolve"), is_error=True)
            return
        
        tech_model = self.get_model_technical_name(self.var_model.get())
            
        settings = {
            "lang": self.var_lang.get(),
            "model": tech_model,
            "device": self.var_device.get(),
            "threshold": self.var_threshold.get(),
            "filler_words": self.filler_words,
            "compound": self.var_compound.get(),
            "trans_status": {
                "nesting": self.txt("status_nesting"),
                "render": self.txt("status_render"),
                "check_model": self.txt("status_check_model", model=tech_model),
                "whisper_dl": self.txt("status_whisper_dl", model=tech_model),
                "whisper_run": self.txt("status_whisper_run", model=tech_model),
                "norm": self.txt("status_norm"),
                "silence": self.txt("status_silence"),
                "processing": self.txt("status_processing"),
                "cleanup": self.txt("status_cleanup"),
                "init_analysis": self.txt("status_reps"),
                "txt_inaudible": self.txt("txt_inaudible")
            }
        }
        
        self.btn_analyze.config(state="disabled", bg=config.INPUT_BG)
        
        def run_thread():
            words, segments = self.engine.run_analysis_pipeline(
                settings, 
                callback_status=self.set_status, 
                callback_progress=self.set_progress
            )
            
            if words:
                # 1. Clear Engine Defaults (keep logic as is, then apply new auto logic)
                for w in words:
                    if w.get('status') in ['bad', 'repeat', 'typo']:
                        w['status'] = None
                        w['selected'] = False
                
                # 2. APPLY AUTO-FILLER LOGIC IMMEDIATELY (Requested Feature)
                if self.var_auto_filler.get():
                     words = algorythms.apply_auto_filler_logic(words, self.filler_words, True)
                        
                self.words_data = words
                self.segments_data = segments
                self.root.after(0, self.show_reviewer_stage)
            else:
                self.root.after(0, lambda: self.btn_analyze.config(state="normal", bg=config.BTN_BG))
                self.root.after(0, lambda: self.set_status("Error."))

        threading.Thread(target=run_thread, daemon=True).start()

    # ==========================
    # STAGE 2: REVIEWER UI
    # ==========================

    def show_reviewer_stage(self):
        self.current_stage_name = "reviewer"
        self.clear_window()
        
        # --- FIXED SIZE CONSTRAINT ---
        self.root.resizable(False, False) # Fixed Width & Height
        
        w_rev = int(1450 * self.scale_factor)
        h_rev = int(850 * self.scale_factor)
        
        self.center_window_force(w_rev, h_rev)
        
        self.current_frame = tk.Frame(self.root, bg=config.BG_COLOR)
        self.current_frame.pack(fill="both", expand=True)

        content_area = tk.Frame(self.current_frame, bg=config.BG_COLOR)
        content_area.pack(fill="both", expand=True, padx=10, pady=10)

        # Right Col (Fixed Sidebar)
        frame_sidebar = tk.Frame(content_area, bg=config.SIDEBAR_BG, width=int(260 * self.scale_factor)) 
        frame_sidebar.pack(side="right", fill="y", padx=0)
        frame_sidebar.pack_propagate(False)

        # Content (Script + Trans)
        frame_texts = tk.Frame(content_area, bg=config.BG_COLOR)
        frame_texts.pack(side="left", fill="both", expand=True)
        
        is_reviewer_mode = self.var_enable_reviewer.get()
        
        if is_reviewer_mode:
            frame_script = tk.Frame(frame_texts, bg=config.BG_COLOR)
            frame_script.pack(side="left", fill="y", padx=(0,0))
            tk.Label(frame_script, text=self.txt("header_rev_script"), bg=config.BG_COLOR, fg=config.NOTE_COL, font=self.font_bold).pack(anchor="w", pady=(0,5))
            self.script_area = tk.Text(frame_script, bg=config.INPUT_BG, fg=config.FG_COLOR, font=(config.UI_FONT_NAME, 11), width=50, wrap="word", relief="flat", padx=10, pady=10, bd=0, highlightthickness=0)
            self.script_area.pack(fill="both", expand=True)
            self.script_area.tag_configure("missing", background=config.WORD_MISSING_BG, foreground=config.WORD_MISSING_FG)
            self._setup_placeholder(self.script_area, self.txt("ph_script"))
        else:
            self.script_area = None

        frame_trans = tk.Frame(frame_texts, bg=config.BG_COLOR)
        frame_trans.pack(side="left", fill="both", expand=True, padx=(10,10))
        tk.Label(frame_trans, text=self.txt("header_rev_trans"), bg=config.BG_COLOR, fg=config.NOTE_COL, font=self.font_bold).pack(anchor="w", pady=(0,5))
        
        self.pagination_frame = tk.Frame(frame_trans, bg=config.BG_COLOR)
        self.pagination_frame.pack(side="bottom", fill="x", pady=5)
        
        self.btn_prev_page = tk.Button(self.pagination_frame, text=self.txt("btn_prev"), command=self.prev_page,
                                       bg=config.INPUT_BG, fg=config.FG_COLOR, 
                                       activebackground=config.INPUT_BG, activeforeground="white",
                                       relief="flat", bd=0, highlightthickness=0,
                                       font=self.font_small, cursor="hand2")
        self.btn_prev_page.pack(side="left")
        
        self.lbl_page_info = tk.Label(self.pagination_frame, text=self.txt("lbl_page", current=1, total=1), 
                                      bg=config.BG_COLOR, fg=config.NOTE_COL, font=self.font_small)
        self.lbl_page_info.pack(side="left", padx=10)
        
        self.btn_next_page = tk.Button(self.pagination_frame, text=self.txt("btn_next"), command=self.next_page,
                                       bg=config.INPUT_BG, fg=config.FG_COLOR, 
                                       activebackground=config.INPUT_BG, activeforeground="white",
                                       relief="flat", bd=0, highlightthickness=0,
                                       font=self.font_small, cursor="hand2")
        self.btn_next_page.pack(side="left")
        
        text_scroll = ModernScrollbar(frame_trans, width=14, active_color="#303031")
        text_scroll.pack(side="right", fill="y", padx=(0, 0)) 
        
        self.text_area = tk.Text(frame_trans, bg=config.INPUT_BG, fg=config.WORD_NORMAL_FG, insertbackground="white",
                                 relief="flat", bd=0, highlightthickness=0, font=(config.UI_FONT_NAME, 12), wrap="word", 
                                 padx=15, pady=15, cursor="arrow", yscrollcommand=text_scroll.set,
                                 selectbackground=config.INPUT_BG, selectforeground=config.WORD_NORMAL_FG, inactiveselectbackground=config.INPUT_BG)
        self.text_area.pack(fill="both", expand=True)
        
        text_scroll.command = self.text_area.yview
        
        self._configure_text_tags()
        self.text_area.configure(state="disabled")

        self.text_area.update_idletasks()
        self.text_area.bind("<Configure>", self.on_text_resize)

        sb_header = tk.Frame(frame_sidebar, bg=config.SIDEBAR_BG)
        sb_header.pack(fill="x", padx=15, pady=15)
        tk.Label(sb_header, text=self.txt("header_rev_tools"), bg=config.SIDEBAR_BG, fg="white", font=(config.UI_FONT_NAME, 12, "bold")).pack(side="left")
        self._add_gear_button(sb_header, bg_color=config.SIDEBAR_BG)

        tk.Label(frame_sidebar, text=self.txt("lbl_mark_color"), bg=config.SIDEBAR_BG, fg=config.NOTE_COL, font=(config.UI_FONT_NAME, 9)).pack(anchor="w", padx=15, pady=(5,5))
        
        style = ttk.Style()
        style.configure("TRadiobutton", background=config.SIDEBAR_BG, foreground="white", font=self.font_norm)
        
        def add_tool_rb(text_key, val, color, white_mode=False):
             tk.Radiobutton(frame_sidebar, text=self.txt(text_key), variable=self.var_mark_tool, value=val,
                       bg=config.SIDEBAR_BG, fg=color, selectcolor="black" if not white_mode else "gray", 
                       activebackground=config.SIDEBAR_BG, activeforeground=color,
                       font=self.font_bold, indicatoron=1, cursor="hand2", bd=0, highlightthickness=0).pack(anchor="w", padx=10, pady=2)

        add_tool_rb("rb_mark_red", "bad", config.WORD_BAD_BG)
        add_tool_rb("rb_mark_blue", "repeat", config.WORD_REPEAT_BG)
        add_tool_rb("rb_mark_green", "typo", config.WORD_TYPO_BG)
        add_tool_rb("rb_mark_white", "eraser", "#cccccc")

        tk.Frame(frame_sidebar, height=1, bg=config.SEPARATOR_COL).pack(fill="x", padx=10, pady=15)

        if is_reviewer_mode:
            def import_script_action():
                path = filedialog.askopenfilename(parent=self.root, filetypes=[(self.txt("file_types"), "*.txt *.docx *.pdf")])
                if path:
                    text_content = ""
                    if path.lower().endswith(".docx"):
                        text_content = algorythms.read_docx_text(path)
                    elif path.lower().endswith(".pdf"):
                        text_content = algorythms.read_pdf_text(path)
                    else:
                        try:
                            with open(path, 'r', encoding='utf-8') as f: text_content = f.read()
                        except Exception as e: text_content = str(e)
                    
                    self.script_area.delete("1.0", tk.END)
                    self.script_area.insert("1.0", text_content)
                    self.script_area.configure(fg=config.FG_COLOR) 

            tk.Button(frame_sidebar, text=self.txt("btn_import"), bg=config.INPUT_BG, fg="white", font=(config.UI_FONT_NAME, 9),
                      activebackground=config.INPUT_BG, activeforeground="white",
                      relief="flat", bd=0, highlightthickness=0,
                      pady=5, cursor="hand2", command=import_script_action).pack(fill="x", padx=15, pady=5)
            
            def run_compare_click():
                self.close_menu_if_open()
                if self.script_area:
                     raw_script = self.script_area.get("1.0", "end-1c").strip()
                     if not raw_script or raw_script == self.txt("ph_script"):
                         CustomMessage(self.root, self.txt("title_confirm"), self.txt("err_noscript"))
                         return
                
                self.last_analysis_mode = "compare" 
                self.start_comparison_thread()

            tk.Button(frame_sidebar, text=self.txt("btn_compare"), bg=config.BTN_BG, fg="white", font=(config.UI_FONT_NAME, 9, "bold"),
                      activebackground=config.BTN_ACTIVE, activeforeground="white",
                      relief="flat", bd=0, highlightthickness=0,
                      pady=5, cursor="hand2", command=run_compare_click).pack(fill="x", padx=15, pady=5)

        def run_standalone_click():
            self.close_menu_if_open()
            self.last_analysis_mode = "standalone"
            self.start_standalone_thread()

        lbl_standalone = self.txt("btn_analyze") if not is_reviewer_mode else self.txt("btn_standalone")
        
        btn_standalone = tk.Button(frame_sidebar, text=lbl_standalone, bg=config.BTN_GHOST_BG, fg=config.NOTE_COL, font=(config.UI_FONT_NAME, 9, "bold"),
                  activebackground=config.BTN_GHOST_BG, activeforeground=config.NOTE_COL,
                  relief="flat", bd=0, highlightthickness=0,
                  pady=5, cursor="arrow", state="disabled", command=run_standalone_click)
        btn_standalone.pack(fill="x", padx=15, pady=5)
        
        Tooltip(btn_standalone, self.txt("tooltip_dev"))

        tk.Frame(frame_sidebar, height=1, bg=config.SEPARATOR_COL).pack(fill="x", padx=10, pady=15)

        def create_wrapped_checkbox(var, text_key, cmd=None):
            row = tk.Frame(frame_sidebar, bg=config.SIDEBAR_BG)
            row.pack(fill="x", padx=15, pady=5)
            cb = ttk.Checkbutton(row, variable=var, style="Sidebar.TCheckbutton", command=cmd)
            cb.pack(side="left", anchor="n")
            lbl = tk.Label(row, text=self.txt(text_key), bg=config.SIDEBAR_BG, fg=config.FG_COLOR, font=(config.UI_FONT_NAME, 9), justify="left", wraplength=int(200 * self.scale_factor), anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=(5,0))

        create_wrapped_checkbox(self.var_auto_filler, "chk_auto_filler", cmd=self.toggle_auto_fillers)
        
        def toggle_inaudible_live():
            if self.words_data:
                self.populate_text_area()

        create_wrapped_checkbox(self.var_show_inaudible, "chk_show_inaudible", cmd=toggle_inaudible_live)

        create_wrapped_checkbox(self.var_auto_del, "chk_auto_del")

        def toggle_cut():
             if self.var_silence_cut.get(): self.var_silence_mark.set(False)
        def toggle_mark():
             if self.var_silence_mark.get(): self.var_silence_cut.set(False)

        create_wrapped_checkbox(self.var_silence_cut, "chk_silence_cut", cmd=toggle_cut)
        create_wrapped_checkbox(self.var_silence_mark, "chk_silence_mark", cmd=toggle_mark)

        tk.Frame(frame_sidebar, height=1, bg=config.SEPARATOR_COL).pack(fill="x", padx=10, pady=15)

        tk.Frame(frame_sidebar, bg=config.SIDEBAR_BG).pack(fill="y", expand=True) 
        sb_status_frame = tk.Frame(frame_sidebar, bg=config.SIDEBAR_BG, height=24)
        sb_status_frame.pack(fill="x", padx=15, pady=(0, 10))
        sb_status_frame.pack_propagate(False)
        self.sidebar_status_canvas = tk.Canvas(sb_status_frame, bg=config.SIDEBAR_BG, height=24, highlightthickness=0, relief="flat")
        self.sidebar_status_canvas.pack(fill="both", expand=True)
        self.sb_rect_id = self.sidebar_status_canvas.create_rectangle(0, 0, 0, 24, fill=config.SIDEBAR_BG, width=0)
        self.sb_text_id = self.sidebar_status_canvas.create_text(0, 12, text=self.current_status_text, fill=config.STATUS_TEXT_COLOR, font=(config.UI_FONT_NAME, 8))
        self.sidebar_status_canvas.bind("<Configure>", lambda e: (self.sidebar_status_canvas.coords(self.sb_text_id, e.width/2, 12), self._update_sidebar_status()))

        def run_generate_click():
            self.close_menu_if_open()
            self.run_generation_logic()

        def on_quit_click():
            confirm = CustomConfirm(self.root, self.txt("title_confirm"), self.txt("msg_confirm_quit"),
                                    yes_text=self.txt("btn_quit"), no_text=self.txt("btn_cancel"))
            if confirm.result:
                self.root.destroy()

        tk.Button(frame_sidebar, text=self.txt("btn_quit"), command=on_quit_click,
                  bg=config.CANCEL_BG, fg="white", 
                  activebackground=config.CANCEL_ACTIVE, activeforeground="white",
                  font=self.font_bold, relief="flat", bd=0, highlightthickness=0,
                  pady=5, cursor="hand2").pack(side="bottom", fill="x", padx=15, pady=(5, 15))

        tk.Button(frame_sidebar, text=self.txt("btn_export_proj"), command=self.save_project,
                  bg=config.BTN_GHOST_BG, fg="white", 
                  activebackground=config.BTN_GHOST_ACTIVE, activeforeground="white",
                  font=self.font_bold, relief="flat", bd=0, highlightthickness=0, 
                  pady=5, cursor="hand2").pack(side="bottom", fill="x", padx=15, pady=5)

        tk.Button(frame_sidebar, text=self.txt("btn_generate"), command=run_generate_click,
                  bg=config.BTN_BG, fg=config.BTN_FG, 
                  activebackground=config.BTN_ACTIVE, activeforeground="white",
                  font=self.font_bold, relief="flat", bd=0, highlightthickness=0, 
                  pady=8, cursor="hand2").pack(side="bottom", fill="x", padx=15, pady=(5, 5))
        
        tk.Label(self.current_frame, text=self.txt("disclaimer"), bg=config.BG_COLOR, fg=config.DISCLAIMER_FG, font=(config.UI_FONT_NAME, 7), pady=5).pack(side="bottom", fill="x")

        self.populate_text_area()
        self._update_sidebar_status()
        
        self.set_status(self.txt("status_ready"))
        self.set_progress(0)

    # ==========================
    # LOGIKA LOKALNA (DELEGACJA)
    # ==========================

    def start_standalone_thread(self):
        self.set_status(self.txt("status_standalone"))
        self.set_progress(10)
        threading.Thread(target=self.run_standalone_logic, daemon=True).start()

    def run_standalone_logic(self):
        # Auto-cleaning removed per user request
        
        self.set_progress(40)
        
        self.words_data, count = self.engine.run_standalone_analysis(self.words_data, show_inaudible=self.var_show_inaudible.get())
        
        self.set_progress(100)
        self.root.after(0, lambda: self.populate_text_area())
        self.set_status(self.txt("status_done"))
        self.root.after(2000, lambda: self.set_progress(0))

    def start_comparison_thread(self):
        raw_script = self.script_area.get("1.0", tk.END).strip()
        ph = self.txt("ph_script")
        if raw_script == ph or not raw_script:
            script_text = ""
        else:
            script_text = raw_script
            
        self.set_status(self.txt("status_reps"))
        self.set_progress(10)
        
        if script_text:
            threading.Thread(target=self.run_comparison_logic, args=(script_text,), daemon=True).start()
        else:
            self.set_progress(0)
            self.set_status(self.txt("status_ready"))
            CustomMessage(self.root, self.txt("title_confirm"), self.txt("err_noscript"))

    def run_comparison_logic(self, script_text):
        self.set_status(self.txt("status_comparing"))
        self.set_progress(20)
        
        result = self.engine.run_comparison_analysis(script_text, self.words_data)
        self.words_data = result
        
        if hasattr(result, 'missing_indices'):
             self.root.after(0, lambda: self.highlight_script_missing(script_text, result.missing_indices))

        self.set_progress(100)
        self.root.after(0, lambda: self.populate_text_area())
        self.set_status(self.txt("status_compared", diffs="Done"))
        self.root.after(2000, lambda: self.set_progress(0))
        
    def highlight_script_missing(self, text_content, missing_indices):
        if not self.script_area or not missing_indices: return
        self.script_area.tag_remove("missing", "1.0", tk.END)
        
        ranges = algorythms.calculate_script_missing_ranges(text_content, missing_indices)
        
        for start, end in ranges:
            start_idx = f"1.0 + {start} chars"
            end_idx = f"1.0 + {end} chars"
            self.script_area.tag_add("missing", start_idx, end_idx)

    # ==========================================
    # GENERATION LOGIC (Refactored to Delegate)
    # ==========================================

    def run_generation_logic(self):
        # 1. Gather Settings
        try:
            settings = {
                "offset": float(self.var_offset.get()),
                "pad": float(self.var_pad.get()),
                "snap_max": float(self.var_snap_margin.get()),
                "silence_cut": self.var_silence_cut.get(),
                "silence_mark": self.var_silence_mark.get(),
                "show_inaudible": self.var_show_inaudible.get(),
                "auto_del": self.var_auto_del.get(),
                "compound": self.var_compound.get() # Pass the compound flag
            }
        except ValueError:
            CustomMessage(self.root, "Error", self.txt("err_num"), is_error=True)
            return

        # 2. Define Callbacks
        callbacks = {
            'on_status': self.set_status,
            'on_progress': self.set_progress,
            'on_success': self._on_generation_success,
            'on_error': self._on_generation_error
        }

        # 3. Delegate to Engine
        self.engine.start_timeline_generation(self.words_data, settings, callbacks)

    def _on_generation_success(self, warning_code=None):
        self.set_status(self.txt("status_done"))
        self.set_progress(100)
        
        # Determine success message based on warning_code from Engine
        msg_key = "msg_success"
        if warning_code == "unsynced_warning":
            msg_key = "msg_success_unsynced"
            
        self.root.after(0, lambda: CustomMessage(self.root, "Success", self.txt(msg_key)))
        self.root.after(2000, lambda: self.set_progress(0))

    def _on_generation_error(self, error_msg):
        self.set_status("Error")
        self.set_progress(0)
        self.root.after(0, lambda: CustomMessage(self.root, "Error", error_msg, is_error=True))

    def _animate_generation(self, thread):
        # Deprecated: Animation is now handled via callback events
        pass

    # ==========================
    # LOGIKA EDYTORA TEKSTU (VIEW LOGIC)
    # ==========================

    def _setup_placeholder(self, text_widget, placeholder):
        text_widget.insert("1.0", placeholder)
        text_widget.configure(fg=config.NOTE_COL)
        
        def on_focus_in(event):
            current_text = text_widget.get("1.0", "end-1c")
            if current_text == placeholder:
                text_widget.delete("1.0", tk.END)
                text_widget.configure(fg=config.FG_COLOR)
        
        def on_focus_out(event):
            current_text = text_widget.get("1.0", "end-1c")
            if not current_text.strip():
                text_widget.insert("1.0", placeholder)
                text_widget.configure(fg=config.NOTE_COL)
                
        text_widget.bind("<FocusIn>", on_focus_in)
        text_widget.bind("<FocusOut>", on_focus_out)

    def toggle_auto_fillers(self):
        enabled = self.var_auto_filler.get()
        self.words_data = algorythms.apply_auto_filler_logic(self.words_data, self.filler_words, enabled)
        self.populate_text_area()

    def _configure_text_tags(self):
        self.text_area.tag_configure("normal", foreground=config.WORD_NORMAL_FG, background=config.INPUT_BG)
        self.text_area.tag_configure("bad", background=config.WORD_BAD_BG, foreground=config.WORD_BAD_FG)
        self.text_area.tag_configure("repeat", background=config.WORD_REPEAT_BG, foreground=config.WORD_REPEAT_FG)
        self.text_area.tag_configure("typo", background=config.WORD_TYPO_BG, foreground=config.WORD_TYPO_FG)
        self.text_area.tag_configure("inaudible", background=config.WORD_INAUDIBLE_BG, foreground=config.WORD_INAUDIBLE_FG)
        self.text_area.tag_configure("hover", background=config.WORD_HOVER_BG) 
        self.text_area.tag_configure("timestamp_style", foreground=config.NOTE_COL, font=(config.UI_FONT_NAME, 9, "bold"))

    def update_pagination_ui(self):
        if self.lbl_page_info:
            self.lbl_page_info.config(text=self.txt("lbl_page", current=self.current_page + 1, total=self.total_pages))
            
            if self.current_page > 0: self.btn_prev_page.config(state="normal")
            else: self.btn_prev_page.config(state="disabled")
            
            if self.current_page < self.total_pages - 1: self.btn_next_page.config(state="normal")
            else: self.btn_next_page.config(state="disabled")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.populate_text_area()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.populate_text_area()

    def format_seconds(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def populate_text_area(self):
        total_segments = len(self.segments_data)
        if total_segments == 0:
            self.total_pages = 1
        else:
            self.total_pages = (total_segments + self.page_size - 1) // self.page_size
            
        if self.current_page >= self.total_pages: self.current_page = self.total_pages - 1
        if self.current_page < 0: self.current_page = 0
        
        self.update_pagination_ui()
        
        current_y_view = self.text_area.yview()
        
        self.separator_frames = []
        
        start_seg_idx = self.current_page * self.page_size
        end_seg_idx = start_seg_idx + self.page_size
        current_batch_segments = self.segments_data[start_seg_idx:end_seg_idx]
        current_batch_words = [w for seg in current_batch_segments for w in seg]
        
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", tk.END)
        
        show_inaudible = self.var_show_inaudible.get()
        
        batch_len = len(current_batch_words)
        i = 0
        
        current_w = self.text_area.winfo_width()
        font_obj = font.Font(font=self.text_area.cget("font"))
        
        while i < batch_len:
            w_obj = current_batch_words[i]
            
            if w_obj.get('type') == 'silence': 
                i += 1
                continue

            if w_obj.get('is_inaudible') and not show_inaudible:
                i += 1
                continue

            if w_obj.get('is_segment_start'):
                if self.text_area.index("end-1c") != "1.0":
                    self.text_area.insert(tk.END, "\n\n")
                
                start_str = self.format_seconds(w_obj.get('seg_start', 0))
                end_str = self.format_seconds(w_obj.get('seg_end', 0))
                header_text = f"[{start_str}] - [{end_str}]"
                tag_time = f"time_{w_obj['id']}"
                
                self.text_area.insert(tk.END, header_text, ("timestamp_style", tag_time))
                self.text_area.insert(tk.END, "  ") 
                
                text_width = font_obj.measure(header_text + "  ")
                sep_width = max(10, current_w - text_width - 20)
                
                sep_frame = tk.Frame(self.text_area, bg=config.NOTE_COL, height=1, width=sep_width)
                self.text_area.window_create(tk.END, window=sep_frame, align="baseline")
                self.separator_frames.append(sep_frame)
                self.text_area.insert(tk.END, "\n")
                
                self.text_area.tag_bind(tag_time, "<Button-1>", lambda e, t=w_obj.get('seg_start', 0): self.resolve_handler.jump_to_seconds(t))
                self.text_area.tag_bind(tag_time, "<Enter>", lambda e: self.text_area.config(cursor="hand2"))
                self.text_area.tag_bind(tag_time, "<Leave>", lambda e: self.text_area.config(cursor="arrow"))

            if w_obj.get('is_inaudible'):
                k = i + 1
                count_to_skip = 1 
                
                while k < batch_len:
                    next_w = current_batch_words[k]
                    if next_w.get('type') == 'silence':
                        k += 1
                        count_to_skip += 1
                    elif next_w.get('is_inaudible'):
                        k += 1
                        count_to_skip += 1
                    else:
                        break
                
                tag_name = f"w_{w_obj['id']}"
                state = w_obj.get('status')
                display_text = self.txt("lbl_inaudible_tag")
                
                if w_obj.get('selected') and not state: 
                     state = "inaudible"
                
                state_tag = state if state else "normal"
                self.text_area.insert(tk.END, display_text, (tag_name, "normal", state_tag))
                
                if state:
                    self.text_area.tag_add(state, f"{tag_name}.first", f"{tag_name}.last")
                
                space_tag = "normal"
                if k < batch_len:
                    real_next_w = current_batch_words[k]
                    next_state = real_next_w.get('status')
                    if real_next_w.get('selected') and not next_state: 
                        if real_next_w.get('is_inaudible'): next_state = "inaudible"
                        else: next_state = "bad"
                    if state and next_state: space_tag = state_tag 
                
                self.text_area.insert(tk.END, " ", (tag_name, "normal", space_tag))
                
                i += count_to_skip
                continue 

            else:
                tag_name = f"w_{w_obj['id']}"
                state = w_obj.get('status', None)
                
                if w_obj.get('selected') and not state: 
                     state = "bad"
                     w_obj['status'] = "bad"
                
                state_tag = state if state else "normal"
                self.text_area.insert(tk.END, w_obj['text'], (tag_name, "normal", state_tag))
                
                if state:
                    self.text_area.tag_add(state, f"{tag_name}.first", f"{tag_name}.last")
                
                space_tag = "normal"
                if state: 
                    if i + 1 < batch_len:
                        next_idx = i + 1
                        while next_idx < batch_len and current_batch_words[next_idx].get('type') == 'silence':
                            next_idx += 1
                        while next_idx < batch_len and current_batch_words[next_idx].get('is_inaudible') and not show_inaudible:
                            next_idx += 1
                        
                        if next_idx < batch_len:
                            next_w = current_batch_words[next_idx]
                            next_state = next_w.get('status')
                            if next_w.get('selected') and not next_state: 
                                if next_w.get('is_inaudible'): next_state = "inaudible"
                                else: next_state = "bad"
                            if next_state: space_tag = state_tag 
                
                self.text_area.insert(tk.END, " ", (tag_name, "normal", space_tag))
                i += 1

        self.setup_bindings()
        self.text_area.configure(state="disabled")
        
        self.text_area.update_idletasks()
        
        if current_y_view:
            self.text_area.yview_moveto(current_y_view[0])
            
        self.on_text_resize(None)
        self.text_area.bind("<Configure>", self.on_text_resize)

    def on_text_resize(self, event):
        if self.resize_timer:
            self.root.after_cancel(self.resize_timer)
        self.resize_timer = self.root.after(50, lambda: self._perform_resize_update(self.text_area.winfo_width()))

    def _perform_resize_update(self, width):
        if width > 1:
            new_w = width - 180 
            
            if new_w < 10: new_w = 10
            for frame in self.separator_frames:
                try: frame.config(width=new_w)
                except: pass

    def setup_bindings(self):
        self.text_area.bind("<Button-1>", lambda e: (self.close_menu_if_open(), self.on_click_start(e)))
        self.text_area.bind("<B1-Motion>", self.on_drag)
        self.text_area.bind("<ButtonRelease-1>", self.on_click_end)

    def get_word_id_at_index(self, index):
        tags = self.text_area.tag_names(index)
        for t in tags:
            if t.startswith("w_"): return int(t.split("_")[1])
        return None

    def on_click_start(self, event):
        index = self.text_area.index(f"@{event.x},{event.y}")
        tags = self.text_area.tag_names(index)
        for t in tags:
            if t.startswith("time_"): return "break" 

        wid = self.get_word_id_at_index(index)
        if (event.state & 0x4) != 0 and wid is not None: 
            self.resolve_handler.jump_to_seconds(self.words_data[wid]['start'])
            return "break"
        
        self.is_dragging = True
        if wid is not None:
            current_tool = self.var_mark_tool.get()
            new_status = None if current_tool == "eraser" else current_tool
            self.update_word_status(wid, new_status)
            self.last_dragged_id = wid
        return "break"

    def on_drag(self, event):
        if not self.is_dragging: return "break"
        index = self.text_area.index(f"@{event.x},{event.y}")
        wid = self.get_word_id_at_index(index)
        if wid is not None and wid != self.last_dragged_id:
            current_tool = self.var_mark_tool.get()
            new_status = None if current_tool == "eraser" else current_tool
            self.update_word_status(wid, new_status)
            self.last_dragged_id = wid
        return "break"

    def on_click_end(self, event):
        self.is_dragging = False
        self.last_dragged_id = -1
        return "break"

    def update_word_status(self, word_id, status):
        # Delegated to algorithms
        updates = algorythms.propagate_status_change(self.words_data, word_id, status)
        
        if not updates: return

        self.text_area.configure(state="normal")
        
        def apply_tag_to_word(w_id, new_stat):
            tag_name = f"w_{w_id}"
            for s in ["bad", "repeat", "typo", "inaudible", "normal"]:
                try: self.text_area.tag_remove(s, f"{tag_name}.first", f"{tag_name}.last")
                except: pass
            
            if new_stat and new_stat != "normal":
                try: self.text_area.tag_add(new_stat, f"{tag_name}.first", f"{tag_name}.last")
                except: pass

        for wid, stat in updates:
            apply_tag_to_word(wid, stat)
            
        self.text_area.configure(state="disabled")