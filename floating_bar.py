# -*- coding: utf-8 -*-
"""
Odak Asistanı — Yüzen Mola Barajı Masaüstü HUD Widget'ı
Topmost, non-activating, draggable desktop floating progress bar.
Supports dynamic horizontal (W >= H) and vertical (H > W) modes with top-to-bottom fill.
"""

import sys
import os
import time
import json
import ctypes
from ctypes import wintypes
import tkinter as tk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
SIGNAL_FILE = os.path.join(BASE_DIR, "show_window.signal")


class FloatingBarApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0c0d14")

        # Win32 extended window styles:
        # WS_EX_TOOLWINDOW (0x80): does not show on taskbar
        # WS_EX_NOACTIVATE (0x08000000): does not steal keyboard/game focus
        # WS_EX_TOPMOST (0x08): always topmost
        self.hwnd = None
        self.canvas = None
        self.cur_w = 260
        self.cur_h = 42
        self.cur_x = 40
        self.cur_y = 40
        self.cur_alpha = 0.92
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.last_state_mtime = 0
        self.cached_state = {}

        self._init_window()
        self._setup_bindings()
        self._update_loop()

    def _init_window(self):
        self._read_state()
        st = self.cached_state.get("settings", {})
        self.cur_w = max(30, int(st.get("floating_bar_width", 260)))
        self.cur_h = max(20, int(st.get("floating_bar_height", 42)))
        self.cur_x = int(st.get("floating_bar_pos_x", 40))
        self.cur_y = int(st.get("floating_bar_pos_y", 40))
        self.cur_alpha = max(0.2, min(1.0, float(st.get("floating_bar_opacity", 0.92))))

        self.root.geometry(f"{self.cur_w}x{self.cur_h}+{self.cur_x}+{self.cur_y}")
        self.root.attributes("-alpha", self.cur_alpha)
        self.root.update_idletasks()

        self.hwnd = self.root.winfo_id()
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOPMOST = 0x00000008

        try:
            u32 = ctypes.windll.user32
            cur_style = u32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
            u32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, cur_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST)
            self._apply_rounded_region(self.cur_w, self.cur_h)
        except Exception:
            pass

        self.canvas = tk.Canvas(
            self.root,
            width=self.cur_w,
            height=self.cur_h,
            bg="#0c0d14",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

    def _apply_rounded_region(self, w, h):
        try:
            r = min(18, min(w, h) // 2)
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w, h, r * 2, r * 2)
            ctypes.windll.user32.SetWindowRgn(self.hwnd, rgn, True)
        except Exception:
            pass

    def _setup_bindings(self):
        self.root.bind("<ButtonPress-1>", self._on_drag_start)
        self.root.bind("<B1-Motion>", self._on_drag_motion)
        self.root.bind("<ButtonRelease-1>", self._on_drag_release)
        self.root.bind("<Double-Button-1>", self._on_double_click)

    def _on_drag_start(self, event):
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _on_drag_motion(self, event):
        if not self.is_dragging:
            return
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy
        self.root.geometry(f"+{new_x}+{new_y}")

    def _on_drag_release(self, event):
        self.is_dragging = False
        new_x = self.root.winfo_x()
        new_y = self.root.winfo_y()
        self.cur_x = new_x
        self.cur_y = new_y
        self._save_position(new_x, new_y)

    def _on_double_click(self, event):
        # Open main app window
        try:
            with open(SIGNAL_FILE, "w") as f:
                f.write(str(time.time()))
        except Exception:
            pass

    def _save_position(self, x, y):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "settings" not in data:
                    data["settings"] = {}
                data["settings"]["floating_bar_pos_x"] = int(x)
                data["settings"]["floating_bar_pos_y"] = int(y)
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _read_state(self):
        if not os.path.exists(STATE_FILE):
            return
        try:
            mtime = os.path.getmtime(STATE_FILE)
            if mtime != self.last_state_mtime:
                self.last_state_mtime = mtime
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    self.cached_state = json.load(f)
        except Exception:
            pass

    def _render(self):
        self._read_state()
        st = self.cached_state.get("settings", {})
        study = self.cached_state.get("study", {})

        # If user disabled floating bar in settings, terminate
        if not st.get("floating_bar_enabled", False):
            self.root.destroy()
            sys.exit(0)

        # Check geometry changes from settings
        target_w = max(30, int(st.get("floating_bar_width", self.cur_w)))
        target_h = max(20, int(st.get("floating_bar_height", self.cur_h)))
        target_alpha = max(0.2, min(1.0, float(st.get("floating_bar_opacity", self.cur_alpha))))

        if target_w != self.cur_w or target_h != self.cur_h:
            self.cur_w = target_w
            self.cur_h = target_h
            self.root.geometry(f"{self.cur_w}x{self.cur_h}")
            self.canvas.config(width=self.cur_w, height=self.cur_h)
            self._apply_rounded_region(self.cur_w, self.cur_h)

        if abs(target_alpha - self.cur_alpha) > 0.01:
            self.cur_alpha = target_alpha
            self.root.attributes("-alpha", self.cur_alpha)

        # Determine study / break metrics
        now = time.time()
        rb_id = study.get("reward_break_item_id")
        rb_end = float(study.get("reward_break_end_ts", 0.0))
        in_break = bool(rb_id and rb_end > now)

        watched = float(study.get("study_watched_seconds", 0.0))
        goal = float(study.get("study_goal_seconds", 2700))
        if goal <= 0:
            goal = 2700

        self.canvas.delete("all")
        w = self.cur_w
        h = self.cur_h

        # -------------------------------------------------------------
        # KURAL:
        # Eğer yükseklik genişlikten bir pixel büyük seçilirse (H > W):
        # Bar yatay değil DİKEY olsun ve YUKARIDAN AŞAĞIYA dolsun.
        # Eğer genişlik yükseklikten bir pixel büyük seçilirse (W >= H):
        # Bar YATAY kalsın (soldan sağa dolsun).
        # -------------------------------------------------------------
        is_vertical = (h > w)

        if in_break:
            rem_sec = max(0, int(rb_end - now))
            tot_brk = max(60, int(study.get("reward_break_duration_sec", 600)))
            progress = max(0.0, min(1.0, rem_sec / tot_brk))
            m, s = divmod(rem_sec, 60)
            tag_text = f"{m:02d}:{s:02d}"

            if rb_id == "appless_break":
                break_title = "DİNLENME MOLASI"
                bg_col = "#08131d"
                fill_col = "#0284c7"
                border_col = "#38bdf8"
                text_col = "#e0f2fe"
            else:
                break_title = "MOLA"
                bg_col = "#13100a"
                fill_col = "#d97706"
                border_col = "#f59e0b"
                text_col = "#fef08a"

            self.canvas.create_rectangle(0, 0, w, h, fill=bg_col, outline=border_col, width=1.5)

            if is_vertical:
                fill_h = int(h * progress)
                if fill_h > 0:
                    self.canvas.create_rectangle(1, 1, w - 1, fill_h, fill=fill_col, outline="")
                # Vertical labels
                self.canvas.create_text(w // 2, 14, text=break_title, fill=text_col, font=("Segoe UI", 8, "bold"))
                self.canvas.create_text(w // 2, h // 2, text=tag_text, fill="#ffffff", font=("Segoe UI", 10, "bold"))
                self.canvas.create_text(w // 2, h - 14, text=break_title, fill=border_col, font=("Segoe UI", 8))
            else:
                fill_w = int(w * progress)
                if fill_w > 0:
                    self.canvas.create_rectangle(1, 1, fill_w, h - 1, fill=fill_col, outline="")
                # Horizontal labels
                self.canvas.create_text(
                    w // 2, h // 2,
                    text=f"{break_title} DEVAM EDİYOR • Kalan: {tag_text}",
                    fill=text_col,
                    font=("Segoe UI", 9, "bold")
                )
        else:
            # DERS / ÇALIŞMA MODU (Zümrüt Yeşil Odak)
            progress = max(0.0, min(1.0, watched / goal))
            pct = int(round(progress * 100))
            w_m, w_s = divmod(int(watched), 60)
            g_m, _ = divmod(int(goal), 60)

            bg_col = "#09140e"
            fill_col = "#059669" if pct < 100 else "#10b981"
            border_col = "#10b981" if pct < 100 else "#34d399"
            text_col = "#a7f3d0"

            self.canvas.create_rectangle(0, 0, w, h, fill=bg_col, outline=border_col, width=1.5)

            if is_vertical:
                # DİKEY BAR: YUKARIDAN AŞAĞIYA DOLUŞ
                fill_h = int(h * progress)
                if fill_h > 0:
                    self.canvas.create_rectangle(1, 1, w - 1, fill_h, fill=fill_col, outline="")
                # Vertical labels
                self.canvas.create_text(w // 2, 14, text=f"%{pct}", fill="#ffffff", font=("Segoe UI", 9, "bold"))
                if h >= 100:
                    self.canvas.create_text(w // 2, h // 2, text=f"{w_m}m", fill=text_col, font=("Segoe UI", 8, "bold"))
                    self.canvas.create_text(w // 2, h - 14, text=f"{g_m}m", fill="#6ee7b7", font=("Segoe UI", 7, "bold"))
            else:
                # YATAY BAR: SOLDAN SAĞA DOLUŞ
                fill_w = int(w * progress)
                if fill_w > 0:
                    self.canvas.create_rectangle(1, 1, fill_w, h - 1, fill=fill_col, outline="")
                # Horizontal labels
                time_str = f"{w_m:02d}:{w_s:02d} / {g_m:02d}:00"
                label_str = f"ODAK BARAJI: %{pct} ({time_str})"
                self.canvas.create_text(
                    w // 2, h // 2,
                    text=label_str,
                    fill="#ffffff",
                    font=("Segoe UI", 9, "bold")
                )

    def _update_loop(self):
        try:
            self._render()
        except Exception:
            pass
        self.root.after(400, self._update_loop)

    def run(self):
        self.root.mainloop()


def main():
    try:
        app = FloatingBarApp()
        app.run()
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
