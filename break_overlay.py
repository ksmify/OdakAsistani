# -*- coding: utf-8 -*-
"""
Odak Asistanı — Discord-Style Floating HUD Break Reminder Overlay
Non-activating, always-on-top, smooth fade-out reminder popup for fullscreen games and desktop.
"""

import sys
import time
import ctypes
from ctypes import wintypes
import tkinter as tk

def main():
    try:
        rem_sec = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    except Exception:
        rem_sec = 60

    try:
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.95)
        root.configure(bg="#0c0d14")

        # Win32 extended window styles:
        # WS_EX_TOOLWINDOW (0x80): does not appear on taskbar or alt-tab
        # WS_EX_NOACTIVATE (0x08000000): does NOT steal focus from active game or app!
        # WS_EX_TOPMOST (0x08): always topmost
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOPMOST = 0x00000008

        root.update_idletasks()
        hwnd = root.winfo_id()
        u32 = ctypes.windll.user32
        cur_style = u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        u32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST)

        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        w, h = 460, 114
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2

        root.geometry(f"{w}x{h}+{x}+{y}")
        root.update_idletasks()

        # Native hardware-level rounded window region
        try:
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w, h, 26, 26)
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass

        canvas = tk.Canvas(root, width=w, height=h, bg="#0c0d14", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Border color: Rose/Amber warning if <= 60s, Cyan/Emerald if > 60s
        border_col = "#f43f5e" if rem_sec <= 60 else "#f59e0b"
        tag_col = "#fb7185" if rem_sec <= 60 else "#fbbf24"
        accent_bg = "#881337" if rem_sec <= 60 else "#78350f"

        # Inner subtle frame
        canvas.create_rectangle(1, 1, w-1, h-1, outline=border_col, width=2)

        # Header tag
        canvas.create_text(
            w // 2, 26,
            text="⏳ ODAK ASİSTANI • MOLA SÜRESİ UYARISI",
            fill=tag_col,
            font=("Segoe UI", 9, "bold")
        )

        # Dynamic countdown text
        txt_id = canvas.create_text(
            w // 2, 60,
            text="",
            fill="#ffffff",
            font=("Segoe UI", 18, "bold")
        )

        sub_msg = "Süre dolduğunda tavizsiz kilitler anında devreye girecek!" if rem_sec <= 60 else "Oyununu kaydetmeye ve dersine dönmeye hazırlan."
        canvas.create_text(
            w // 2, 88,
            text=sub_msg,
            fill="#a1a1aa",
            font=("Segoe UI", 8, "normal")
        )

        start_time = time.time()
        base_rem = rem_sec

        def tick():
            elapsed = time.time() - start_time
            curr_rem = max(0, int(base_rem - elapsed))
            m, s = divmod(curr_rem, 60)
            canvas.itemconfig(txt_id, text=f"Kalan molan: {m:02d}:{s:02d}")

            if elapsed < 3.0:
                root.after(100, tick)
            else:
                fade_start = time.time()
                def fade_out():
                    fade_elapsed = time.time() - fade_start
                    if fade_elapsed < 1.0:
                        alpha = max(0.0, 0.95 * (1.0 - fade_elapsed / 1.0))
                        root.attributes("-alpha", alpha)
                        root.after(25, fade_out)
                    else:
                        root.destroy()
                        sys.exit(0)
                fade_out()

        tick()
        root.mainloop()
    except Exception:
        sys.exit(0)

if __name__ == "__main__":
    main()
