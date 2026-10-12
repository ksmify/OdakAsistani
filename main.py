# -*- coding: utf-8 -*-
"""
Odak Asistanı — Flagship Dark UI (Linear / Spotify / Vercel Obsidian Design)
- Sıfır Titreme (Zero-Flicker In-Place DOM/Widget Sync): Butonlara veya sekmelere basıldığında
  sayfa yenileniyormuş (F5) gibi silinip yüklenme efekti %100 engellendi; tüm bileşenler yerinde (in-place) güncellenir.
- Modern Obsidian & Carbon Renk Sistemi (#09090b / #121215 / #18181c), Özel Süper-Örneklemeli (2x Anti-Aliased)
  Vektörel Ders Rozetleri ve Bento-Grid İstatistik Kartları.
- Ders Sürelerim: Bugün, Bu Hafta, Bu Ay ve Tüm Zamanlar filtreleme.
- Kümülatif Soru Sayacı + "Soru Çözmedim (Konu)" Desteği: Her dersin altında hem üzerine eklemeli soru girişi
  hem de soru çözülmeyen periyotlar için tek tıkla "Soru Çözmedim" (veya 0) kaydetme özelliği.
"""

import ctypes
from ctypes import wintypes
import math
import os
import sys
from datetime import datetime
import threading
import time
import winreg
import winsound

# Uygulama hangi arka plan/terminal oturumundan başlatılırsa başlatılsın,
# pencerenin her zaman kullanıcının gerçek "Default" masaüstünde açılmasını garanti et:
try:
    _u32 = ctypes.windll.user32
    _hdesk = _u32.OpenDesktopW("Default", 0, False, 0x01FF)
    if _hdesk:
        _u32.SetThreadDesktop(_hdesk)
except Exception:
    pass

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
import pystray

from blocker_engine import BlockerEngine, is_admin
from nlp_parser import CommandParser
from self_defense import get_lock_target_presets, TR_MONTH_NAMES, format_turkish_date_full
from study_tracker import (
    SUBJECT_DEFINITIONS,
    STUDY_GOAL_OPTIONS,
    REWARD_BREAK_OPTIONS,
    SOURCE_CATEGORY_OPTIONS,
    get_subject_info,
    get_source_category_label,
    get_source_benefit_description,
    get_source_badge_code,
    format_goal_short_tr,
    format_goal_bar_target,
)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHOW_SIGNAL_FILE = os.path.join(BASE_DIR, "show_window.signal")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ======================================================================
# FLAGSHIP OBSIDIAN DARK RENK SİSTEMİ (Linear / Spotify / Vercel)
# ======================================================================
BG_CANVAS = "#09090b"           # Ana derin obsidian arka plan
BG_SURFACE = "#121216"          # Ana konteyner / Bento yüzeyi
BG_CARD = "#18181e"             # Kart yüzeyi
BG_CARD_HOVER = "#1f1f27"       # Kart vurgu yüzeyi
BG_ELEVATED = "#23232b"         # İkincil buton / Chip yüzeyi
BG_ELEVATED_HOVER = "#2e2e38"   # İkincil buton hover
BG_INPUT = "#0d0d11"            # Giriş kutusu zemini

BORDER_SUBTLE = "#22222a"       # İnce modern kenarlık
BORDER_DEFAULT = "#2e2e38"      # Standart kenarlık
BORDER_STRONG = "#3f3f46"       # Vurgulu kenarlık
BORDER_FOCUS = "#52525b"        # Odak kenarlığı (Nötr Çinko)

TEXT_PRIMARY = "#f4f4f6"        # Kristal netliğinde beyaz metin
TEXT_SECONDARY = "#a1a1aa"      # Modern çinko gri ikincil metin
TEXT_MUTED = "#71717a"          # Soluk bilgi metni

ACCENT_WHITE = "#f4f4f6"        # Seçili sekme / Ana aksiyon beyazı
ACCENT_INDIGO = "#27272a"       # Koyu Karbon / Çinko Buton (Mavi kaldırıldı)
ACCENT_INDIGO_HOVER = "#3f3f46"
ACCENT_CYAN = "#e4e4e7"         # Parlak Gümüş/Beyaz Metin (Mavi kaldırıldı)
ACCENT_EMERALD = "#10b981"      # Zümrüt Yeşili (Buton)
ACCENT_EMERALD_TEXT = "#34d399" # Parlak Zümrüt (Metin/Rozet)
ACCENT_ROSE = "#f43f5e"         # Modern Mercan Kırmızısı
ACCENT_ROSE_DARK = "#e11d48"
ACCENT_AMBER = "#f59e0b"        # Kehribar / Vurgu

PERIOD_LABELS = {
    "Bugün": "today",
    "Bu Hafta": "week",
    "Bu Ay": "month",
    "Tüm Zamanlar": "all",
}

SUBJECT_BADGE_CODES = {
    "matematik": "MAT",
    "geometri": "GEO",
    "fizik": "FİZ",
    "kimya": "KİM",
    "biyoloji": "BİY",
    "turkce": "TÜR",
    "sosyal": "SOS",
    "tarih": "TAR",
    "cografya": "COĞ",
    "felsefe": "FEL",
    "din": "DİN",
    "soru_cozum": "DEN",
    "genel_ders": "GEN",
}

# ======================================================================
# 0 -> 100.000 SORU RÜTBE VE ÇERÇEVE RENK EVRİM ALGORİTMASI (MAVİ/LACİVERT YOK)
# ======================================================================
QUESTION_RANK_TIERS = [
    # (min_q, next_q, rank_title, border_hex, text_hex, pill_bg_hex, card_bg_hex, row_bg_hex)
    (0,      10,     "Başlangıç",             "#2e2e38", "#a1a1aa", "#18181e", "#18181e", "#0d0d11"),
    (1,      10,     "I • Kıvılcım Avcısı",   "#b45309", "#fbbf24", "#26180a", "#19140e", "#120e0a"),
    (10,     50,     "II • Bronz Savaşçı",    "#d97706", "#fbbf24", "#2e1d0a", "#1c1610", "#16110b"),
    (50,     100,    "III • Yeşim Muhafız",   "#22c55e", "#4ade80", "#0d2b18", "#111e16", "#0b1610"),
    (100,    250,    "IV • Zümrüt Şövalye",   "#10b981", "#34d399", "#092e22", "#0f201b", "#0a1713"),
    (250,    500,    "V • Altın Uzman",       "#eab308", "#facc15", "#2e2408", "#1d190c", "#141108"),
    (500,    1000,   "VI • Kor Alevi",        "#f97316", "#fb923c", "#331809", "#20130c", "#160d08"),
    (1000,   2500,   "VII • Mercan Üstat",    "#f43f5e", "#fb7185", "#331019", "#201015", "#160b0e"),
    (2500,   5000,   "VIII • Kızıl Baron",    "#ef4444", "#f87171", "#361111", "#221010", "#170b0b"),
    (5000,   10000,  "IX • Ametist Seçkin",   "#8b5cf6", "#a78bfa", "#241442", "#191328", "#120d1e"),
    (10000,  20000,  "X • Destansı (Epic)",   "#a855f7", "#c084fc", "#2d1245", "#1d1129", "#150c1f"),
    (20000,  35000,  "XI • Fuşya Mareşal",    "#d946ef", "#e879f9", "#36103b", "#221025", "#180b1b"),
    (35000,  50000,  "XII • Yakut Lordu",     "#ec4899", "#f472b6", "#381024", "#24101a", "#1a0b12"),
    (50000,  75000,  "XIII • Güneş İmparatoru","#f59e0b","#fde047", "#382a07", "#241d0b", "#1a1507"),
    (75000,  100000, "XIV • Platin Efsane",   "#e4e4e7", "#ffffff", "#27272a", "#1f1f23", "#151518"),
    (100000, None,   "XV • YKS EFSANESİ",     "#10b981", "#6ee7b7", "#06382c", "#0c2620", "#081b16"),
]


def get_question_rank_tier(question_count: int) -> dict:
    """Çözülen soru sayısına göre (0 -> 100.000+) rütbe, çerçeve rengi ve sonraki hedef bilgisini döndürür."""
    q = max(0, int(question_count))
    chosen = QUESTION_RANK_TIERS[0]
    tier_index = 0
    for idx, t in enumerate(QUESTION_RANK_TIERS):
        if q >= t[0]:
            chosen = t
            tier_index = idx
        else:
            break

    min_q, next_q, title, border_c, text_c, pill_bg, card_bg, row_bg = chosen
    if next_q is not None:
        rem = max(0, next_q - q)
        next_info = f"Hedef: {next_q:,} Soru ({rem:,} kaldı)".replace(",", ".")
    else:
        next_info = "MAKSİMUM RÜTBE (100.000+ EFSANE)"

    return {
        "tier_index": tier_index,
        "min_q": min_q,
        "next_q": next_q,
        "title": title,
        "border": border_c,
        "text": text_c,
        "pill_bg": pill_bg,
        "card_bg": card_bg,
        "row_bg": row_bg,
        "next_info": next_info,
    }


def hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.lstrip("#")
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (16, 185, 129)


def apply_windows_dark_titlebar(win):
    """Windows 10/11 pencere başlık çubuğunu ve dış çerçevesini Obsidian (#09090b / #22222a) rengine boyar."""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        dwmapi = ctypes.windll.dwmapi
        dark_mode = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
        dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
        # DWMWA_BORDER_COLOR (34): Mavi Windows 11 kenarlığını koyu karbon (#22222a -> 0x002A2222) yap
        border_color = ctypes.c_int(0x002A2222)
        dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), ctypes.sizeof(border_color))
        # DWMWA_CAPTION_COLOR (35): COLORREF 0x00BBGGRR -> #09090b = 0x000B0909
        caption_color = ctypes.c_int(0x000B0909)
        dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))
    except Exception:
        pass


def format_duration_tr(seconds: float) -> str:
    total = max(0, int(seconds))
    hrs, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs} sa {mins:02d} dk {secs:02d} sn"
    return f"{mins} dk {secs:02d} sn"


def ensure_startup_registered():
    """
    Bilgisayar açılır açılmaz Odak Asistanı'nın otomatik olarak ekranda açılması için
    Windows Başlangıç (Startup) kayıtlarına ekler ve eski 'Ders Odak' uygulamasını kaldırır.
    """
    try:
        startup_dir = os.path.join(
            os.environ.get("APPDATA", ""),
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        legacy_lnk = os.path.join(startup_dir, "Ders Odak.lnk")
        if os.path.exists(legacy_lnk):
            try:
                os.remove(legacy_lnk)
            except Exception:
                pass
    except Exception:
        pass

    try:
        pythonw_exe = sys.executable
        if pythonw_exe.lower().endswith("python.exe"):
            pw = pythonw_exe[:-10] + "pythonw.exe"
            if os.path.exists(pw):
                pythonw_exe = pw
        script_path = os.path.abspath(__file__)
        cmd = f'"{pythonw_exe}" "{script_path}" --boot'
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        ) as key:
            winreg.SetValueEx(key, "OdakAsistani", 0, winreg.REG_SZ, cmd)
            for old_name in ("Ders Odak", "DersOdak", "DersMotivasyon"):
                try:
                    winreg.DeleteValue(key, old_name)
                except Exception:
                    pass

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as app_key:
            enabled_bytes = b"\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            winreg.SetValueEx(app_key, "OdakAsistani", 0, winreg.REG_BINARY, enabled_bytes)
            for old_name in ("Ders Odak", "DersOdak", "DersMotivasyon"):
                try:
                    winreg.DeleteValue(app_key, old_name)
                except Exception:
                    pass
    except Exception:
        pass


def create_tray_icon_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((4, 4, 60, 60), radius=16, fill=(18, 18, 22, 255), outline=(63, 63, 70, 255), width=3)
    draw.ellipse((17, 17, 47, 47), fill=(9, 9, 11, 255), outline=(16, 185, 129, 255), width=3)
    draw.ellipse((26, 26, 38, 38), fill=(244, 244, 246, 255))
    return img


def create_brand_emblem_ctk() -> ctk.CTkImage:
    """Üst bar için 2x süper-örneklemeli (anti-aliased) özgün koyu karbon/zümrüt Odak Asistanı amblemi üretir."""
    size = 72
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Dış koyu karbon squircle
    draw.rounded_rectangle((2, 2, size - 3, size - 3), radius=20, fill=(24, 24, 28, 255), outline=(63, 63, 70, 255), width=3)
    # İç zümrüt odak halkası
    draw.ellipse((16, 16, size - 16, size - 16), outline=(16, 185, 129, 255), width=4)
    # Merkez kristal beyaz odak çekirdeği
    draw.ellipse((28, 28, size - 28, size - 28), fill=(244, 244, 246, 255))
    smooth = img.resize((34, 34), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=smooth, dark_image=smooth, size=(34, 34))


def create_subject_badge_ctk(code_str: str, hex_color: str) -> ctk.CTkImage:
    """
    Windows'un soluk tek renkli tel-çerçeve emojileri yerine her dersin kendi renginde
    2x süper-örneklemeli (anti-aliased) modern yuvarlatılmış ders rozeti üretir.
    """
    w, h = 88, 76
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r, g, b = hex_to_rgb(hex_color)
    fill_rgba = (int(r * 0.22 + 14), int(g * 0.22 + 14), int(b * 0.22 + 18), 255)
    border_rgba = (r, g, b, 230)
    draw.rounded_rectangle((2, 2, w - 3, h - 3), radius=20, fill=fill_rgba, outline=border_rgba, width=3)

    try:
        font = ImageFont.truetype("segoeuib.ttf", 23)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), code_str, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w - tw) / 2 - bbox[0]
    ty = (h - th) / 2 - bbox[1]
    draw.text((tx, ty), code_str, font=font, fill=(min(255, r + 55), min(255, g + 55), min(255, b + 55), 255))

    smooth = img.resize((44, 38), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=smooth, dark_image=smooth, size=(44, 38))


def create_settings_gear_ctk() -> ctk.CTkImage:
    """Mola barajının en sağındaki ayar butonu için 2x anti-aliased vektörel dişli (gear) simgesi üretir."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2.0, size / 2.0
    gear_color = (228, 228, 231, 255)
    # 8 dişli çark kolları
    for i in range(8):
        angle = i * (math.pi / 4.0)
        x1 = cx + math.cos(angle) * 14.0
        y1 = cy + math.sin(angle) * 14.0
        x2 = cx + math.cos(angle) * 24.5
        y2 = cy + math.sin(angle) * 24.5
        draw.line((x1, y1, x2, y2), fill=gear_color, width=7)
    # Çark gövde halkası ve iç boşluk
    draw.ellipse((cx - 19, cy - 19, cx + 19, cy + 19), fill=gear_color)
    draw.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=(24, 24, 30, 255), outline=(16, 185, 129, 255), width=3)
    smooth = img.resize((20, 20), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=smooth, dark_image=smooth, size=(20, 20))


class OdakAsistaniApp(ctk.CTk):
    def __init__(self, start_hidden: bool = False, reset_study_on_boot: bool = False):
        super().__init__()

        self.title("Odak Asistanı")
        self.geometry("1150x800")
        self.minsize(940, 640)
        self.configure(fg_color=BG_CANVAS)

        icon_path = os.path.join(BASE_DIR, "odak_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.current_tab = "Antigravity'nin Seçtikleri"
        self.current_stats_period_label = "Bugün"
        self.search_query = ""
        self._ui_dirty = False
        self.tray_icon = None
        self._ctk_icons = {}
        self._subject_badge_icons = {}
        self.reward_popup_win = None
        self.emergency_confirm_win = None
        self.break_settings_win = None
        self.custom_lock_win = None

        # Zero-Flicker (In-Place) görünüm referansları ve imza önbellekleri
        self._stats_built = False
        self._sources_built = False
        self._sources_list_frame = None
        self._subject_ui_refs = {}
        self._period_btn_refs = {}
        self._item_card_refs = {}
        self._rendered_items_signature = None
        self._last_bento_header_sig = None

        ensure_startup_registered()

        self.engine = BlockerEngine(
            on_state_change=self._schedule_ui_refresh,
            reset_study_on_boot=(reset_study_on_boot or start_hidden)
        )
        self.parser = CommandParser(self.engine)

        self._build_ui()
        self.after(60, lambda: apply_windows_dark_titlebar(self))

        # Kullanıcı X tuşuna bastığında pencere gizlenir, arka plan koruması devam eder
        self.protocol("WM_DELETE_WINDOW", self._on_close_button_pressed)

        self._switch_active_view(force_rebuild=True)
        self._refresh_status()

        self._pending_initial_hide = start_hidden
        if start_hidden:
            self.attributes("-alpha", 0.0)
        else:
            # Bilgisayar açıldığında veya kısayoldan başlatıldığında pencereyi doğrudan ekrana getir
            self.after(120, lambda: (self.deiconify(), self.lift(), self.focus_force()))

        self.after(180, self._tick)

    def _font(self, size: int = 13, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(family="Segoe UI", size=int(round(size)), weight=weight)

    def _get_ctk_icon(self, png_path: str):
        if not png_path or not os.path.exists(png_path):
            return None
        if png_path in self._ctk_icons:
            return self._ctk_icons[png_path]
        try:
            pil_img = Image.open(png_path).convert("RGBA")
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(28, 28))
            self._ctk_icons[png_path] = ctk_img
            return ctk_img
        except Exception:
            return None

    def _get_subject_badge_icon(self, subj_id: str, color_hex: str) -> ctk.CTkImage:
        if subj_id in self._subject_badge_icons:
            return self._subject_badge_icons[subj_id]
        code = SUBJECT_BADGE_CODES.get(subj_id, subj_id[:3].upper())
        badge = create_subject_badge_ctk(code, color_hex)
        self._subject_badge_icons[subj_id] = badge
        return badge

    # ==================================================================
    # ANA ARAYÜZ İSKELETİ (BENTO & OBSIDIAN TASARIM)
    # ==================================================================
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --------------------------------------------------------------
        # 1. ÜST HEADER BAR (Özgün Odak Amblemi + Canlı Durum + Kilit Hedefi Sayacı + Acil Durum)
        # --------------------------------------------------------------
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 10))
        top_bar.grid_columnconfigure(1, weight=1)

        # Sol: Özgün Odak Asistanı Amblemi & Başlık
        brand_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, sticky="w")

        self._brand_emblem = create_brand_emblem_ctk()
        ctk.CTkLabel(
            brand_frame,
            text="",
            image=self._brand_emblem,
            width=34
        ).pack(side="left", padx=(0, 10))

        title_col = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_col.pack(side="left")

        title_line = ctk.CTkFrame(title_col, fg_color="transparent")
        title_line.pack(anchor="w")

        ctk.CTkLabel(
            title_line,
            text="Odak Asistanı",
            font=self._font(20, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        init_cd = self.engine.get_tyt_countdown()
        self.header_badge_btn = ctk.CTkButton(
            title_line,
            text=init_cd.get("target_badge", "YKS 2027"),
            font=self._font(10, "bold"),
            fg_color="#1c1c22",
            hover_color=BG_ELEVATED_HOVER,
            text_color="#e4e4e7",
            border_color="#3f3f46",
            border_width=1,
            height=22,
            width=66,
            corner_radius=8,
            command=self._open_custom_lock_chooser_popup
        )
        self.header_badge_btn.pack(side="left", padx=(8, 0), pady=2)

        # Orta-Sol: Canlı Kilit Durumu Rozeti
        status_chip = ctk.CTkFrame(
            top_bar,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=18
        )
        status_chip.grid(row=0, column=1, padx=16, sticky="w")

        self.status_label = ctk.CTkLabel(
            status_chip,
            text="● Her şey açık ve normal çalışıyor",
            font=self._font(12, "bold"),
            text_color=ACCENT_EMERALD_TEXT,
            anchor="w"
        )
        self.status_label.pack(padx=14, pady=6)

        # Sağ: Kilit Hedefi & Geri Sayım Seçici (Custom Lock Chooser) + Yönetici İzni + Acil Durum Butonu
        right_btns = ctk.CTkFrame(top_bar, fg_color="transparent")
        right_btns.grid(row=0, column=2, sticky="e")

        self.tyt_countdown_label = ctk.CTkButton(
            right_btns,
            text=f"🔒 {init_cd.get('countdown_prefix', 'TYT Kilidi')}: --G --S --D --Sn  ▾",
            font=self._font(12, "bold"),
            fg_color=BG_SURFACE,
            hover_color=BG_ELEVATED_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=BORDER_DEFAULT,
            border_width=1,
            height=34,
            corner_radius=17,
            command=self._open_custom_lock_chooser_popup
        )
        self.tyt_countdown_label.pack(side="left", padx=(0, 10))

        if not is_admin():
            ctk.CTkButton(
                right_btns,
                text="Yönetici İzni",
                font=self._font(12, "bold"),
                fg_color=BG_ELEVATED,
                hover_color=BG_ELEVATED_HOVER,
                text_color=TEXT_PRIMARY,
                height=34,
                width=120,
                corner_radius=17,
                command=self._restart_as_admin
            ).pack(side="left", padx=(0, 8))

        self.emergency_btn = ctk.CTkButton(
            right_btns,
            text="Acil Durum (30 Dk)",
            font=self._font(12, "bold"),
            fg_color="#281117",
            hover_color="#3b1620",
            text_color="#fb7185",
            border_color="#591c2b",
            border_width=1,
            height=34,
            width=175,
            corner_radius=17,
            command=self._on_emergency_button_clicked
        )
        self.emergency_btn.pack(side="left")

        # --------------------------------------------------------------
        # 2. KOMUT & HIZLI ENGELLEME BARI (Raycast / Linear Spotlight Tarzı)
        # --------------------------------------------------------------
        cmd_box = ctk.CTkFrame(
            self,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=16
        )
        cmd_box.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        cmd_box.grid_columnconfigure(0, weight=1)

        entry_row = ctk.CTkFrame(cmd_box, fg_color="transparent")
        entry_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        entry_row.grid_columnconfigure(0, weight=1)

        self.cmd_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text='Kilitlenecek uygulama veya web sitesi yazın... (Örn: "instagram ve discord\'u kapat", "ornek.com kapat")',
            height=42,
            font=self._font(13),
            fg_color=BG_INPUT,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            border_color=BORDER_DEFAULT,
            border_width=1,
            corner_radius=12
        )
        self.cmd_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.cmd_entry.bind("<Return>", lambda e: self._execute_command())
        self.cmd_entry.bind("<KeyRelease>", self._on_entry_key_release)

        ctk.CTkButton(
            entry_row,
            text="Kilitle",
            font=self._font(13, "bold"),
            fg_color=ACCENT_WHITE,
            hover_color="#d4d4d8",
            text_color=BG_CANVAS,
            height=42,
            width=124,
            corner_radius=12,
            command=self._execute_command
        ).grid(row=0, column=1)

        info_row = ctk.CTkFrame(cmd_box, fg_color="transparent")
        info_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        info_row.grid_columnconfigure(0, weight=1)

        self.feedback_label = ctk.CTkLabel(
            info_row,
            text="Katı Odak Modu aktif • Kilitlenen uygulama ve siteler 18 Haziran 2027 (TYT'den 1 gün öncesi) tarihine kadar açılamaz.",
            font=self._font(12),
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        self.feedback_label.grid(row=0, column=0, sticky="ew")

        self.tyt_info_label = ctk.CTkLabel(
            info_row,
            text="Silinemezlik Koruması Aktif",
            font=self._font(11, "bold"),
            text_color=TEXT_MUTED,
            anchor="e"
        )
        self.tyt_info_label.grid(row=0, column=1, sticky="e", padx=(12, 0))

        # --------------------------------------------------------------
        # 3. ANA SAHNE & SEKME NAVİGASYONU (SIFIR TİTREME MİMARİSİ)
        # --------------------------------------------------------------
        list_container = ctk.CTkFrame(
            self,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=16
        )
        list_container.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 12))
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(1, weight=1)

        tab_bar = ctk.CTkFrame(list_container, fg_color="transparent")
        tab_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        tab_bar.grid_columnconfigure(0, weight=1)

        # Özel Pill Sekme Çubuğu (Titreme yapmayan hızlı sekme butonları)
        tabs_wrap = ctk.CTkFrame(tab_bar, fg_color=BG_INPUT, corner_radius=12, border_color=BORDER_SUBTLE, border_width=1)
        tabs_wrap.grid(row=0, column=0, sticky="w")

        self._nav_buttons = {}
        nav_items = [
            "Uygulamalarım",
            "Antigravity'nin Seçtikleri",
            "Web Siteleri",
            "📊 Ders Sürelerim",
            "🌐 Kaynak Siteler",
            "Şu An Açık",
            "Kapalı Olanlar",
        ]
        for t_name in nav_items:
            b = ctk.CTkButton(
                tabs_wrap,
                text=t_name,
                font=self._font(12, "bold"),
                fg_color="transparent",
                hover_color=BG_ELEVATED,
                text_color=TEXT_SECONDARY,
                height=32,
                corner_radius=9,
                command=lambda tn=t_name: self._on_tab_changed(tn)
            )
            b.pack(side="left", padx=2, pady=3)
            self._nav_buttons[t_name] = b

        self._update_nav_tab_styles()

        self.search_entry = ctk.CTkEntry(
            tab_bar,
            placeholder_text="Listede ara...",
            height=36,
            width=180,
            font=self._font(12),
            fg_color=BG_INPUT,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            border_color=BORDER_DEFAULT,
            border_width=1,
            corner_radius=10
        )
        self.search_entry.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        # Üç Ayrı Kalıcı Scrollable Katman:
        # 1) self.items_scroll_frame (Uygulama / Site listeleri için)
        # 2) self.stats_scroll_frame (Ders Sürelerim Bento Dashboard için — 1 kez oluşturulur, asla silinmez!)
        # 3) self.sources_scroll_frame (Kaynak Siteler yönetimi için)
        self.stage_holder = ctk.CTkFrame(list_container, fg_color="transparent")
        self.stage_holder.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.stage_holder.grid_columnconfigure(0, weight=1)
        self.stage_holder.grid_rowconfigure(0, weight=1)

        self.items_scroll_frame = ctk.CTkScrollableFrame(
            self.stage_holder,
            fg_color=BG_CANVAS,
            corner_radius=12,
            scrollbar_button_color=BG_ELEVATED,
            scrollbar_button_hover_color=BG_ELEVATED_HOVER
        )
        self.items_scroll_frame.grid(row=0, column=0, sticky="nsew")
        self.items_scroll_frame.grid_columnconfigure(0, weight=1)
        self.items_scroll_frame.grid_columnconfigure(1, weight=1)

        self.stats_scroll_frame = ctk.CTkScrollableFrame(
            self.stage_holder,
            fg_color=BG_CANVAS,
            corner_radius=12,
            scrollbar_button_color=BG_ELEVATED,
            scrollbar_button_hover_color=BG_ELEVATED_HOVER
        )
        self.stats_scroll_frame.grid_columnconfigure(0, weight=1)
        self.stats_scroll_frame.grid_columnconfigure(1, weight=1)

        self.sources_scroll_frame = ctk.CTkScrollableFrame(
            self.stage_holder,
            fg_color=BG_CANVAS,
            corner_radius=12,
            scrollbar_button_color=BG_ELEVATED,
            scrollbar_button_hover_color=BG_ELEVATED_HOVER
        )
        self.sources_scroll_frame.grid_columnconfigure(0, weight=1)

        # Ders Sürelerim ve Kaynak Siteler görünümlerini başlangıçta inşa et
        self._build_subject_stats_view_once()
        self._build_sources_view_once()

        # --------------------------------------------------------------
        # 4. ALT ODAK & ÖDÜL MOLA DOCK ÇUBUĞU (Spotify / Linear Dock)
        # --------------------------------------------------------------
        bottom_bar = ctk.CTkFrame(
            self,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=16
        )
        bottom_bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 16))
        bottom_bar.grid_columnconfigure(1, weight=1)

        init_goal = int(getattr(self.engine, "study_goal_seconds", 7200))
        init_break_min = int(getattr(self.engine, "reward_break_minutes", 10))
        self.study_time_label = ctk.CTkLabel(
            bottom_bar,
            text=f"Mola Barajı: 00s 00dk 00sn / {format_goal_bar_target(init_goal)}  •  Mola: {init_break_min} Dk",
            font=self._font(13, "bold"),
            text_color=TEXT_PRIMARY
        )
        self.study_time_label.grid(row=0, column=0, padx=(16, 14), pady=(10, 4), sticky="w")

        self.study_video_label = ctk.CTkLabel(
            bottom_bar,
            text="YouTube / Kaynak Siteler ders videosu veya Ders Sürelerim'den manuel sayaç bekleniyor",
            font=self._font(12),
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        self.study_video_label.grid(row=0, column=1, padx=(0, 10), pady=(10, 4), sticky="ew")

        self.bottom_manual_stop_btn = ctk.CTkButton(
            bottom_bar,
            text="Çalışmayı Bitir & Soru Gir",
            font=self._font(12, "bold"),
            fg_color=ACCENT_AMBER,
            hover_color="#d97706",
            text_color="#09090b",
            height=28,
            width=190,
            corner_radius=14,
            command=self._on_stop_manual_from_bottom
        )

        self.study_progress = ctk.CTkProgressBar(
            bottom_bar,
            height=6,
            fg_color=BG_INPUT,
            progress_color=ACCENT_EMERALD,
            corner_radius=3
        )
        self.study_progress.grid(row=1, column=0, columnspan=3, sticky="ew", padx=(16, 6), pady=(2, 10))
        self.study_progress.set(0.0)

        self._gear_ctk_img = create_settings_gear_ctk()
        self.break_bar_settings_btn = ctk.CTkButton(
            bottom_bar,
            text="",
            image=self._gear_ctk_img,
            width=36,
            height=36,
            corner_radius=10,
            fg_color=BG_CARD,
            hover_color=BG_ELEVATED_HOVER,
            border_color=BORDER_STRONG,
            border_width=1,
            command=self._open_break_bar_settings_popup
        )
        self.break_bar_settings_btn.grid(row=0, column=3, rowspan=2, padx=(6, 14), pady=8, sticky="e")

    def _update_nav_tab_styles(self):
        for t_name, btn in self._nav_buttons.items():
            if t_name == self.current_tab:
                btn.configure(
                    fg_color=ACCENT_WHITE,
                    hover_color="#e4e4e7",
                    text_color=BG_CANVAS
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=BG_ELEVATED,
                    text_color=TEXT_SECONDARY
                )

    # ==================================================================
    # 📊 DERS SÜRELERİM: BENTO DASHBOARD (1 KEZ OLUŞTURULUR, YERİNDE GÜNCELLENİR)
    # ==================================================================
    def _build_subject_stats_view_once(self):
        """
        Ders Sürelerim ekranındaki tüm Bento kartlarını ve ders satırlarını yalnızca 1 kez oluşturur.
        Daha sonra periyot değiştiğinde, sayaç başlatılıp durdurulduğunda veya soru eklendiğinde
        hiçbir widget silinmez (.destroy() çağrılmaz); yalnızca metin ve renkleri anında güncellenir!
        """
        if self._stats_built:
            return
        self._stats_built = True

        # --------------------------------------------------------------
        # 1. ÜST KONTROL & FİLTRE BARI (Tam Genişlik — Hiçbir Yazı Sıkışmaz)
        # --------------------------------------------------------------
        bento_ctrl = ctk.CTkFrame(
            self.stats_scroll_frame,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        bento_ctrl.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 8))
        bento_ctrl.grid_columnconfigure(1, weight=1)

        # Sol: Görüntüleme Periyodu Başlığı + Segmented Pill Butonları
        left_ctrl = ctk.CTkFrame(bento_ctrl, fg_color="transparent")
        left_ctrl.grid(row=0, column=0, sticky="w", padx=(14, 10), pady=8)

        ctk.CTkLabel(
            left_ctrl,
            text="GÖRÜNTÜLEME PERİYODU:",
            font=self._font(11, "bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left", padx=(0, 10))

        period_pills_frame = ctk.CTkFrame(
            left_ctrl,
            fg_color=BG_INPUT,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=10
        )
        period_pills_frame.pack(side="left")

        for p_idx, p_label in enumerate(PERIOD_LABELS.keys()):
            p_btn = ctk.CTkButton(
                period_pills_frame,
                text=p_label,
                font=self._font(12, "bold"),
                fg_color="transparent",
                hover_color=BG_ELEVATED,
                text_color=TEXT_SECONDARY,
                width=96,
                height=28,
                corner_radius=7,
                command=lambda pl=p_label: self._on_period_changed(pl)
            )
            p_btn.grid(row=0, column=p_idx, padx=2, pady=2)
            self._period_btn_refs[p_label] = p_btn

        # Sağ: Kaynak Siteler Menüsü Kısayolu (345 / Bilgi Sarmal / Özel Siteler artık Kaynak Siteler menüsünde)
        right_ctrl = ctk.CTkFrame(bento_ctrl, fg_color="transparent")
        right_ctrl.grid(row=0, column=2, sticky="e", padx=(10, 14), pady=8)

        ctk.CTkButton(
            right_ctrl,
            text="🌐 Video Kaynak Siteleri & Branş Ayarları",
            font=self._font(12, "bold"),
            fg_color=BG_ELEVATED,
            hover_color=BG_ELEVATED_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=BORDER_DEFAULT,
            border_width=1,
            height=28,
            corner_radius=8,
            command=lambda: self._on_tab_changed("🌐 Kaynak Siteler")
        ).pack(side="left")

        # --------------------------------------------------------------
        # 2. GENİŞ BENTO HERO KARTLARI (2 Eşit Geniş Sütun — ~515px Genişlik)
        # --------------------------------------------------------------
        bento_top = ctk.CTkFrame(self.stats_scroll_frame, fg_color="transparent")
        bento_top.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 10))
        bento_top.grid_columnconfigure(0, weight=1, uniform="bento_hero")
        bento_top.grid_columnconfigure(1, weight=1, uniform="bento_hero")

        # Bento 1: Toplam Çalışma Süresi (Geniş Sol Hero Kartı)
        bento_time = ctk.CTkFrame(
            bento_top,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        bento_time.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._bento_time_title = ctk.CTkLabel(
            bento_time,
            text="TOPLAM ÇALIŞMA SÜRESİ  •  BUGÜN",
            font=self._font(12, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        self._bento_time_title.pack(fill="x", padx=18, pady=(14, 2))

        self._total_study_lbl = ctk.CTkLabel(
            bento_time,
            text="0 dk 00 sn",
            font=self._font(26, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        )
        self._total_study_lbl.pack(fill="x", padx=18, pady=(0, 2))

        self._bento_time_sub = ctk.CTkLabel(
            bento_time,
            text="Tüm zamanlar toplamı: 0 dk 00 sn",
            font=self._font(12, "bold"),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        self._bento_time_sub.pack(fill="x", padx=18, pady=(0, 14))

        # Bento 2: Toplam Çözülen Soru & Rütbe (Geniş Sağ Hero Kartı)
        self._bento_q_frame = ctk.CTkFrame(
            bento_top,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        self._bento_q_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._bento_q_title = ctk.CTkLabel(
            self._bento_q_frame,
            text="ÇÖZÜLEN SORU (BUGÜN)  •  RÜTBE: BAŞLANGIÇ",
            font=self._font(12, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        self._bento_q_title.pack(fill="x", padx=18, pady=(14, 2))

        self._total_questions_lbl = ctk.CTkLabel(
            self._bento_q_frame,
            text="0 SORU",
            font=self._font(26, "bold"),
            text_color=ACCENT_EMERALD_TEXT,
            anchor="w"
        )
        self._total_questions_lbl.pack(fill="x", padx=18, pady=(0, 2))

        self._bento_q_sub = ctk.CTkLabel(
            self._bento_q_frame,
            text="Hedef: 10 Soru (10 kaldı)",
            font=self._font(12, "bold"),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        self._bento_q_sub.pack(fill="x", padx=18, pady=(0, 14))

        # --------------------------------------------------------------
        # 3. DERS KARTLARI (YERİNDE GÜNCELLENEN KARTLAR)
        # --------------------------------------------------------------
        for idx, subj in enumerate(SUBJECT_DEFINITIONS):
            sid = subj["id"]
            s_color = subj["color"]

            card = ctk.CTkFrame(
                self.stats_scroll_frame,
                fg_color=BG_CARD,
                border_color=BORDER_SUBTLE,
                border_width=1,
                corner_radius=14
            )
            card.grid(row=idx + 2, column=0, columnspan=2, sticky="ew", padx=4, pady=5)
            card.grid_columnconfigure(0, weight=1)

            # Üst Satır: Özel Vektör Ders Rozeti + Ders Adı + Dev Soru Rozeti + Süre + Manuel Başlat/Durdur
            header_row = ctk.CTkFrame(card, fg_color="transparent")
            header_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
            header_row.grid_columnconfigure(1, weight=1)

            badge_img = self._get_subject_badge_icon(sid, s_color)
            ctk.CTkLabel(
                header_row,
                text="",
                image=badge_img,
                width=44
            ).grid(row=0, column=0, padx=(0, 12))

            title_block = ctk.CTkFrame(header_row, fg_color="transparent")
            title_block.grid(row=0, column=1, sticky="w")

            name_line = ctk.CTkFrame(title_block, fg_color="transparent")
            name_line.pack(anchor="w")

            ctk.CTkLabel(
                name_line,
                text=subj["name"],
                font=self._font(16, "bold"),
                text_color=TEXT_PRIMARY
            ).pack(side="left")

            pct_badge = ctk.CTkLabel(
                name_line,
                text="  %0",
                font=self._font(12, "bold"),
                text_color=TEXT_MUTED
            )
            pct_badge.pack(side="left", padx=(4, 0))

            live_tag = ctk.CTkLabel(
                name_line,
                text="",
                font=self._font(11, "bold"),
                text_color=ACCENT_EMERALD_TEXT
            )
            live_tag.pack(side="left", padx=(8, 0))

            # Sağ Üstte Gözüne Çarpan Dev Soru & Rütbe Kapsülü
            q_header_pill = ctk.CTkFrame(
                header_row,
                fg_color=BG_INPUT,
                border_color=BORDER_DEFAULT,
                border_width=1,
                corner_radius=10
            )
            q_header_pill.grid(row=0, column=2, sticky="e", padx=(8, 10))

            q_header_lbl = ctk.CTkLabel(
                q_header_pill,
                text="Başlangıç  •  0 SORU",
                font=self._font(14, "bold"),
                text_color=TEXT_SECONDARY
            )
            q_header_lbl.pack(padx=12, pady=4)

            dur_lbl = ctk.CTkLabel(
                header_row,
                text="0 dk 00 sn",
                font=self._font(15, "bold"),
                text_color=s_color,
                anchor="e"
            )
            dur_lbl.grid(row=0, column=3, sticky="e", padx=(4, 14))

            man_btn = ctk.CTkButton(
                header_row,
                text="Manuel Çalışma Başlat",
                font=self._font(12, "bold"),
                fg_color=BG_ELEVATED,
                hover_color=BG_ELEVATED_HOVER,
                text_color=TEXT_PRIMARY,
                border_color=BORDER_DEFAULT,
                border_width=1,
                width=175,
                height=34,
                corner_radius=10,
                command=lambda s_id=sid: self._on_toggle_manual_study(s_id)
            )
            man_btn.grid(row=0, column=4, sticky="e")

            # Orta Satır: İnce Modern İlerleme Çubuğu
            bar = ctk.CTkProgressBar(
                card,
                height=5,
                fg_color=BG_INPUT,
                progress_color=s_color,
                corner_radius=3
            )
            bar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
            bar.set(0.0)

            # Alt Satır: Sisteme Gömülü Dev Çözülen Soru Sayacı + "Soru Çözmedim" + Kümülatif Ekleme
            q_row = ctk.CTkFrame(
                card,
                fg_color=BG_INPUT,
                border_color=BORDER_SUBTLE,
                border_width=1,
                corner_radius=12
            )
            q_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
            q_row.grid_columnconfigure(1, weight=1)

            # Sol: Büyük Vurgulu Çözülen Soru Kutusu
            q_big_pill = ctk.CTkFrame(
                q_row,
                fg_color=BG_SURFACE,
                border_color=BORDER_DEFAULT,
                border_width=1,
                corner_radius=9
            )
            q_big_pill.grid(row=0, column=0, sticky="w", padx=(10, 10), pady=7)

            q_big_num_lbl = ctk.CTkLabel(
                q_big_pill,
                text="0 SORU ÇÖZÜLDÜ",
                font=self._font(15, "bold"),
                text_color=TEXT_SECONDARY
            )
            q_big_num_lbl.pack(padx=12, pady=4)

            # Orta: Tek Satır Hedef & Durum Bilgisi (İkinci bir etiket olmadığı için ASLA çakışmaz)
            q_lbl = ctk.CTkLabel(
                q_row,
                text="",
                font=self._font(12, "bold"),
                text_color=TEXT_SECONDARY,
                anchor="w"
            )
            q_lbl.grid(row=0, column=1, sticky="w", padx=(2, 10), pady=7)

            q_entry = ctk.CTkEntry(
                q_row,
                placeholder_text="Soru sayısı",
                width=96,
                height=30,
                font=self._font(12, "bold"),
                fg_color=BG_SURFACE,
                text_color=TEXT_PRIMARY,
                placeholder_text_color=TEXT_MUTED,
                border_color=BORDER_DEFAULT,
                border_width=1,
                corner_radius=8,
                justify="center"
            )
            q_entry.grid(row=0, column=2, sticky="e", padx=(0, 6), pady=7)
            q_entry.bind(
                "<Return>",
                lambda _e, s_id=sid, ent=q_entry: self._on_add_questions_submitted(s_id, ent)
            )

            add_q_btn = ctk.CTkButton(
                q_row,
                text="+ Üzerine Ekle",
                font=self._font(12, "bold"),
                fg_color="#27272a",
                hover_color="#3f3f46",
                text_color=TEXT_PRIMARY,
                border_color="#3f3f46",
                border_width=1,
                width=114,
                height=30,
                corner_radius=8,
                command=lambda s_id=sid, ent=q_entry: self._on_add_questions_submitted(s_id, ent)
            )
            add_q_btn.grid(row=0, column=3, sticky="e", padx=(0, 6), pady=7)

            no_q_btn = ctk.CTkButton(
                q_row,
                text="Soru Çözmedim",
                font=self._font(11, "bold"),
                fg_color=BG_ELEVATED,
                hover_color=BG_ELEVATED_HOVER,
                text_color=TEXT_SECONDARY,
                width=108,
                height=30,
                corner_radius=8,
                command=lambda s_id=sid, ent=q_entry: self._on_no_questions_clicked(s_id, ent)
            )
            no_q_btn.grid(row=0, column=4, sticky="e", padx=(0, 10), pady=7)

            self._subject_ui_refs[sid] = {
                "card": card,
                "dur_lbl": dur_lbl,
                "pct_badge": pct_badge,
                "live_tag": live_tag,
                "q_header_pill": q_header_pill,
                "q_header_lbl": q_header_lbl,
                "man_btn": man_btn,
                "bar": bar,
                "q_row": q_row,
                "q_big_pill": q_big_pill,
                "q_big_num_lbl": q_big_num_lbl,
                "q_lbl": q_lbl,
                "q_entry": q_entry,
                "add_q_btn": add_q_btn,
                "no_q_btn": no_q_btn,
                "color": s_color,
                "last_state_sig": None,
            }

    def _sync_subject_stats_view(self, focus_stopped_entry: bool = False):
        """
        Ders Sürelerim ekranındaki tüm verileri HİÇBİR WİDGET SİLMEDEN (Sıfır F5 titremesiyle)
        yerinde (in-place) günceller.
        """
        if not self._stats_built:
            self._build_subject_stats_view_once()

        period_key = PERIOD_LABELS.get(self.current_stats_period_label, "today")
        subj_secs, subj_questions = self.engine.get_stats_for_period(period_key)
        all_secs, all_questions = self.engine.get_stats_for_period("all")

        with self.engine.lock:
            pref_subj = self.engine.preferred_solution_subject
            man_active = self.engine.manual_study_active
            man_subj = self.engine.manual_study_subject_id
            just_stopped_subj = self.engine.last_stopped_manual_subject_id
            just_stopped_ts = self.engine.last_stopped_manual_ts
            last_session_map = dict(self.engine.subject_last_session_status)

        # Periyot butonlarının stilini güncelle
        for p_label, p_btn in self._period_btn_refs.items():
            if p_label == self.current_stats_period_label:
                p_btn.configure(fg_color=ACCENT_WHITE, hover_color="#e4e4e7", text_color=BG_CANVAS)
            else:
                p_btn.configure(fg_color="transparent", hover_color=BG_ELEVATED, text_color=TEXT_SECONDARY)

        # Bento Hero Kartlarını Sadece Değer Değiştiğinde Güncelle (Sıfır CPU / Sıfır Kasma)
        total_period_sec = sum(subj_secs.values())
        total_all_sec = sum(all_secs.values())
        total_period_q = sum(subj_questions.values())
        total_all_q = sum(all_questions.values())

        bento_sig = (period_key, int(total_period_sec), int(total_all_sec), total_period_q, total_all_q)
        if self._last_bento_header_sig != bento_sig:
            self._last_bento_header_sig = bento_sig
            p_upper = self.current_stats_period_label.upper()
            self._bento_time_title.configure(text=f"TOPLAM ÇALIŞMA SÜRESİ  •  {p_upper}")
            self._total_study_lbl.configure(text=format_duration_tr(total_period_sec))
            if period_key == "all":
                self._bento_time_sub.configure(text="Tüm derslerin kalıcı birikimli toplamı")
            else:
                self._bento_time_sub.configure(text=f"Tüm zamanlar toplamı: {format_duration_tr(total_all_sec)}")

            # Üst Bento Soru Kartını Genel Rütbe Algoritmasına Göre Renklendir
            global_rank = get_question_rank_tier(max(total_period_q, total_all_q))
            self._bento_q_title.configure(
                text=f"ÇÖZÜLEN SORU ({p_upper})  •  RÜTBE: {global_rank['title'].upper()}",
                text_color=global_rank["text"] if total_all_q > 0 else TEXT_SECONDARY
            )
            self._total_questions_lbl.configure(
                text=f"{total_period_q:,} SORU".replace(",", "."),
                text_color=global_rank["text"] if total_all_q > 0 else ACCENT_EMERALD_TEXT
            )
            if total_all_q > 0:
                self._bento_q_frame.configure(
                    fg_color=global_rank["card_bg"],
                    border_color=global_rank["border"],
                    border_width=2
                )
            else:
                self._bento_q_frame.configure(fg_color=BG_SURFACE, border_color=BORDER_SUBTLE, border_width=1)

            if period_key == "all":
                self._bento_q_sub.configure(
                    text=global_rank["next_info"],
                    text_color=global_rank["text"] if total_all_q > 0 else TEXT_MUTED
                )
            else:
                self._bento_q_sub.configure(
                    text=f"Genel Toplam: {total_all_q:,} Soru   •   {global_rank['next_info']}".replace(",", "."),
                    text_color=global_rank["text"] if total_all_q > 0 else TEXT_MUTED
                )

        now_ts = time.time()
        entry_to_focus = None

        for sid, refs in self._subject_ui_refs.items():
            sec = subj_secs.get(sid, 0.0)
            q_cnt = subj_questions.get(sid, 0)
            q_all_cnt = all_questions.get(sid, 0)
            rank_q_val = max(q_cnt, q_all_cnt)
            rank_info = get_question_rank_tier(rank_q_val)

            ratio = (sec / total_period_sec) if total_period_sec > 0 else 0.0
            pct = int(round(ratio * 100))
            last_note = last_session_map.get(sid, "")

            is_running = bool(man_active and man_subj == sid)
            is_just_stopped = bool(
                not is_running
                and just_stopped_subj == sid
                and (now_ts - just_stopped_ts) < 600.0
            )

            # Süre & ilerleme çubuğu yalnızca tam saniye veya yüzde değiştiğinde güncellenir
            time_sig = (int(sec), pct)
            if refs.get("last_time_sig") != time_sig:
                refs["last_time_sig"] = time_sig
                refs["dur_lbl"].configure(text=format_duration_tr(sec))
                refs["pct_badge"].configure(text=f"  %{pct}")
                refs["bar"].set(min(1.0, max(0.0, ratio)))

            # Büyük soru rozeti, rütbe adı ve sonraki rütbe hedefini oluştur
            big_num_str = f"{q_cnt:,} SORU ÇÖZÜLDÜ".replace(",", ".")
            if rank_q_val > 0:
                header_q_str = f"★ {rank_info['title']}  •  {q_cnt:,} SORU".replace(",", ".")
            else:
                header_q_str = "Başlangıç  •  0 SORU"

            if is_just_stopped:
                detail_str = "Çalışma tamamlandı  •  Çözdüğün soru sayısını sağdaki kutuya yaz:"
            else:
                extra_parts = [rank_info["next_info"]]
                if period_key != "all" and q_all_cnt != q_cnt:
                    extra_parts.append(f"Toplam: {q_all_cnt:,} Soru".replace(",", "."))
                if last_note == "no_questions":
                    extra_parts.append("Son: Konu (0 soru)")
                elif last_note.startswith("+"):
                    extra_parts.append(f"Son: {last_note} Soru")
                detail_str = "   •   ".join(extra_parts)

            # Yalnızca kartın görsel durumu değiştiyse renk/buton özelliklerini güncelle (Sıfır titreme)
            state_sig = (is_running, is_just_stopped, big_num_str, header_q_str, detail_str, rank_info["tier_index"], last_note)
            if refs["last_state_sig"] != state_sig:
                refs["last_state_sig"] = state_sig

                refs["q_header_lbl"].configure(text=header_q_str)
                refs["q_big_num_lbl"].configure(text=big_num_str)
                refs["q_lbl"].configure(text=detail_str)

                # Soru kapsüllerini, alt soru barını ve + Üzerine Ekle butonunu YALNIZCA Rütbe (Tier) rengine boya!
                if rank_q_val > 0:
                    refs["q_header_pill"].configure(
                        fg_color=rank_info["pill_bg"],
                        border_color=rank_info["border"],
                        border_width=2
                    )
                    refs["q_header_lbl"].configure(text_color=rank_info["text"])
                    refs["q_big_pill"].configure(
                        fg_color=rank_info["pill_bg"],
                        border_color=rank_info["border"],
                        border_width=2
                    )
                    refs["q_big_num_lbl"].configure(text_color=rank_info["text"])
                    refs["add_q_btn"].configure(
                        fg_color=rank_info["pill_bg"],
                        hover_color=rank_info["card_bg"],
                        text_color=rank_info["text"],
                        border_color=rank_info["border"],
                        border_width=1
                    )
                else:
                    refs["q_header_pill"].configure(fg_color=BG_INPUT, border_color=BORDER_DEFAULT, border_width=1)
                    refs["q_header_lbl"].configure(text_color=TEXT_MUTED)
                    refs["q_big_pill"].configure(fg_color=BG_SURFACE, border_color=BORDER_DEFAULT, border_width=1)
                    refs["q_big_num_lbl"].configure(text_color=TEXT_SECONDARY)
                    refs["add_q_btn"].configure(
                        fg_color="#27272a",
                        hover_color="#3f3f46",
                        text_color=TEXT_PRIMARY,
                        border_color="#3f3f46",
                        border_width=1
                    )

                # Kartın ana çerçevesini ve soru satırı çerçevesini Rütbe (Tier) veya Aktif Çalışma durumuna göre boya
                if is_running:
                    refs["card"].configure(fg_color="#11221c", border_color=ACCENT_EMERALD, border_width=2)
                    refs["live_tag"].configure(text="● ÇALIŞILIYOR", text_color=ACCENT_EMERALD_TEXT)
                    refs["man_btn"].configure(
                        text="Sayacı Durdur",
                        fg_color=ACCENT_EMERALD,
                        hover_color="#059669",
                        text_color="#ffffff",
                        border_width=0
                    )
                    refs["q_row"].configure(
                        fg_color=rank_info["row_bg"] if rank_q_val > 0 else BG_INPUT,
                        border_color=rank_info["border"] if rank_q_val > 0 else BORDER_SUBTLE,
                        border_width=2 if rank_q_val > 0 else 1
                    )
                    refs["q_lbl"].configure(text_color=rank_info["text"] if rank_q_val > 0 else TEXT_SECONDARY)
                    refs["q_entry"].configure(border_color=rank_info["border"] if rank_q_val > 0 else BORDER_DEFAULT)
                elif is_just_stopped:
                    refs["card"].configure(fg_color="#211b11", border_color=ACCENT_AMBER, border_width=2)
                    refs["live_tag"].configure(text="● SORU GİRİŞİ BEKLENİYOR", text_color=ACCENT_AMBER)
                    refs["man_btn"].configure(
                        text="Manuel Çalışma Başlat",
                        fg_color=BG_ELEVATED,
                        hover_color=BG_ELEVATED_HOVER,
                        text_color=TEXT_PRIMARY,
                        border_color=BORDER_DEFAULT,
                        border_width=1
                    )
                    refs["q_row"].configure(fg_color="#1c160c", border_color=ACCENT_AMBER, border_width=2)
                    refs["q_lbl"].configure(text_color=ACCENT_AMBER)
                    refs["q_entry"].configure(border_color=ACCENT_AMBER)
                    entry_to_focus = refs["q_entry"]
                else:
                    refs["card"].configure(
                        fg_color=rank_info["card_bg"] if rank_q_val > 0 else BG_CARD,
                        border_color=rank_info["border"] if rank_q_val > 0 else BORDER_SUBTLE,
                        border_width=2 if rank_q_val > 0 else 1
                    )
                    refs["live_tag"].configure(text="", text_color=rank_info["text"])
                    refs["man_btn"].configure(
                        text="Manuel Çalışma Başlat",
                        fg_color=BG_ELEVATED,
                        hover_color=BG_ELEVATED_HOVER,
                        text_color=TEXT_PRIMARY,
                        border_color=BORDER_DEFAULT,
                        border_width=1
                    )
                    refs["q_row"].configure(
                        fg_color=rank_info["row_bg"] if rank_q_val > 0 else BG_INPUT,
                        border_color=rank_info["border"] if rank_q_val > 0 else BORDER_SUBTLE,
                        border_width=2 if rank_q_val > 0 else 1
                    )
                    refs["q_lbl"].configure(text_color=rank_info["text"] if rank_q_val > 0 else TEXT_SECONDARY)
                    refs["q_entry"].configure(border_color=rank_info["border"] if rank_q_val > 0 else BORDER_DEFAULT)

        if focus_stopped_entry and entry_to_focus is not None:
            self.after(60, lambda: entry_to_focus.focus_set() if entry_to_focus.winfo_exists() else None)

    def _on_period_changed(self, selected_label: str):
        if self.current_stats_period_label == selected_label:
            return
        self.current_stats_period_label = selected_label
        self._sync_subject_stats_view(focus_stopped_entry=False)

    def _on_add_questions_submitted(self, subject_id: str, entry_widget: ctk.CTkEntry):
        raw = entry_widget.get().strip()
        if not raw:
            self.feedback_label.configure(
                text="Lütfen eklemek istediğiniz soru sayısını yazın (Soru çözmediyseniz '0' yazabilir veya 'Soru Çözmedim' butonuna basabilirsiniz).",
                text_color=ACCENT_AMBER
            )
            return

        cleaned = raw.lstrip("+").strip()
        if not cleaned.isdigit():
            self.feedback_label.configure(
                text="Lütfen geçerli bir sayı girin (Örn: 10 veya soru çözmediyseniz 0).",
                text_color=ACCENT_ROSE
            )
            return

        count = int(cleaned)
        with self.engine.lock:
            prev_total = int(self.engine.subject_questions.get(subject_id, 0))
        prev_rank = get_question_rank_tier(prev_total)

        new_total = self.engine.add_solved_questions(subject_id, count)
        new_rank = get_question_rank_tier(new_total)
        self._ui_dirty = False
        subj_info = get_subject_info(subject_id)
        entry_widget.delete(0, "end")

        if count == 0:
            self.feedback_label.configure(
                text=f"📖 {subj_info['name']}: Bu periyotta soru çözülmedi (Konu çalışması) olarak kaydedildi. Kayıtlı toplam: {new_total} Soru.",
                text_color=ACCENT_CYAN
            )
        elif new_rank["tier_index"] > prev_rank["tier_index"]:
            self.feedback_label.configure(
                text=f"🏆 RÜTBE ATLADIN! {subj_info['name']} dersi [{new_rank['title']}] rütbesine yükseldi! (+{count} soru • Toplam: {new_total} Soru • {new_rank['next_info']})",
                text_color=new_rank["text"]
            )
        else:
            self.feedback_label.configure(
                text=f"✅ {subj_info['name']}: +{count} soru üzerine eklendi! Toplam: {new_total} Soru ({new_rank['title']} • {new_rank['next_info']}).",
                text_color=new_rank["text"]
            )
        self._sync_subject_stats_view(focus_stopped_entry=False)

    def _on_no_questions_clicked(self, subject_id: str, entry_widget: ctk.CTkEntry):
        """Kullanıcı 'Soru Çözmedim' butonuna bastığında 0 soru (konu çalışması) olarak kaydeder."""
        new_total = self.engine.add_solved_questions(subject_id, 0)
        self._ui_dirty = False
        subj_info = get_subject_info(subject_id)
        entry_widget.delete(0, "end")
        self.feedback_label.configure(
            text=f"📖 {subj_info['name']}: Bu periyotta soru çözülmedi (Konu çalışması) olarak işaretlendi. Kayıtlı toplam: {new_total} Soru.",
            text_color=ACCENT_CYAN
        )
        self._sync_subject_stats_view(focus_stopped_entry=False)

    def _on_toggle_manual_study(self, subject_id: str):
        subj_info = get_subject_info(subject_id)
        started = self.engine.toggle_manual_study(subject_id)
        self._ui_dirty = False
        if started:
            self.feedback_label.configure(
                text=f"▶️ {subj_info['name']} için manuel çalışma sayacı başlatıldı! Hem ders sürenize hem 2 saatlik mola barajına işliyor.",
                text_color=ACCENT_EMERALD_TEXT
            )
            self._sync_subject_stats_view(focus_stopped_entry=False)
        else:
            self.feedback_label.configure(
                text=f"⏸️ {subj_info['name']} çalışması tamamlandı! Bu periyotta kaç soru çözdüğünü aşağıya yazabilir veya 'Soru Çözmedim' diyebilirsin.",
                text_color=ACCENT_AMBER
            )
            self._sync_subject_stats_view(focus_stopped_entry=True)

    def _on_stop_manual_from_bottom(self):
        stopped_subj_id = self.engine.manual_study_subject_id
        self.engine.stop_manual_study()
        self._ui_dirty = False
        if stopped_subj_id:
            subj_info = get_subject_info(stopped_subj_id)
            self.feedback_label.configure(
                text=f"⏸️ {subj_info['name']} çalışması tamamlandı! Kaç soru çözdüğünü ilgili dersin altına ekleyebilir veya 'Soru Çözmedim' seçebilirsin.",
                text_color=ACCENT_AMBER
            )
        else:
            self.feedback_label.configure(
                text="⏸️ Manuel ders çalışma sayacı durduruldu.",
                text_color=ACCENT_AMBER
            )
        if self.current_tab != "📊 Ders Sürelerim":
            self.current_tab = "📊 Ders Sürelerim"
            self._update_nav_tab_styles()
        self._switch_active_view(force_rebuild=False, focus_stopped_entry=True)

    # ==================================================================
    # 🌐 KAYNAK SİTELER: DERS VİDEO KAYNAKLARI YÖNETİMİ
    # ==================================================================
    def _build_sources_view_once(self):
        if self._sources_built:
            return
        self._sources_built = True

        self._cat_label_to_id = {
            (opt["label"] if isinstance(opt, dict) else opt[0]): (opt["id"] if isinstance(opt, dict) else opt[1])
            for opt in SOURCE_CATEGORY_OPTIONS
        }
        self._cat_id_to_label = {sid: label for label, sid in self._cat_label_to_id.items()}

        # 1. ÜST KART: YENİ DERS VİDEO KAYNAK SİTESİ EKLEME
        add_card = ctk.CTkFrame(
            self.sources_scroll_frame,
            fg_color=BG_SURFACE,
            border_color=BORDER_STRONG,
            border_width=1,
            corner_radius=14
        )
        add_card.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 10))
        add_card.grid_columnconfigure(0, weight=1)

        head_row = ctk.CTkFrame(add_card, fg_color="transparent")
        head_row.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))
        head_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            head_row,
            text="🌐 YENİ DERS VİDEO KAYNAK SİTESİ EKLE",
            font=self._font(14, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            head_row,
            text=(
                "Eklediğiniz siteden ders veya soru çözümü videosu açtığınızda (video oynarken) tıpkı YouTube, ÜçDörtBeş ve Bilgi Sarmal gibi "
                "otomatik algılanır; seçtiğiniz dersin süresine ve Mola Barajına saniyesi saniyesine işler."
            ),
            font=self._font(12),
            text_color=TEXT_SECONDARY,
            justify="left",
            anchor="w",
            wraplength=980
        ).grid(row=1, column=0, sticky="ew", pady=(3, 0))

        form_row = ctk.CTkFrame(add_card, fg_color="transparent")
        form_row.grid(row=1, column=0, sticky="ew", padx=18, pady=(10, 6))
        form_row.grid_columnconfigure(0, weight=1)

        self.new_source_entry = ctk.CTkEntry(
            form_row,
            placeholder_text="Kaynak site adresi veya adı (Örn: 3dyayinlari.com, ozdebir.org.tr, ogmmateryal.eba.gov.tr, ertansinansahin.com)...",
            height=38,
            font=self._font(13),
            fg_color=BG_INPUT,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            border_color=BORDER_DEFAULT,
            border_width=1,
            corner_radius=10
        )
        self.new_source_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.new_source_entry.bind("<Return>", lambda _e: self._on_add_source_clicked())

        cat_wrap = ctk.CTkFrame(form_row, fg_color="transparent")
        cat_wrap.grid(row=0, column=1, padx=(0, 10))

        ctk.CTkLabel(
            cat_wrap,
            text="Kategori / Ders:",
            font=self._font(12, "bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left", padx=(0, 6))

        def _on_new_cat_preview_change(selected_label: str):
            chosen_sid = self._cat_label_to_id.get(selected_label, "soru_cozum")
            preview_desc = get_source_benefit_description({"subject_id": chosen_sid, "locked": False})
            self._new_source_preview_lbl.configure(text=f"🎯 Seçilen Kategori Etkisi:  {preview_desc}")

        self.new_source_cat_menu = ctk.CTkOptionMenu(
            cat_wrap,
            values=list(self._cat_label_to_id.keys()),
            font=self._font(12, "bold"),
            fg_color=BG_ELEVATED,
            button_color=BG_ELEVATED_HOVER,
            button_hover_color="#3f3f46",
            dropdown_fg_color=BG_CARD,
            text_color=TEXT_PRIMARY,
            width=235,
            height=38,
            corner_radius=10,
            command=_on_new_cat_preview_change
        )
        self.new_source_cat_menu.pack(side="left")
        self.new_source_cat_menu.set("Genel (Soru Çözümü / Deneme)")

        ctk.CTkButton(
            form_row,
            text="+ Kaynak Site Ekle",
            font=self._font(13, "bold"),
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            text_color="#052e16",
            width=165,
            height=38,
            corner_radius=10,
            border_width=0,
            command=self._on_add_source_clicked
        ).grid(row=0, column=2, sticky="e")

        preview_bar = ctk.CTkFrame(
            add_card,
            fg_color=BG_INPUT,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=9
        )
        preview_bar.grid(row=2, column=0, sticky="ew", padx=18, pady=(2, 14))

        init_preview = get_source_benefit_description({"subject_id": "soru_cozum", "locked": False})
        self._new_source_preview_lbl = ctk.CTkLabel(
            preview_bar,
            text=f"🎯 Seçilen Kategori Etkisi:  {init_preview}",
            font=self._font(12, "bold"),
            text_color=ACCENT_EMERALD_TEXT,
            anchor="w"
        )
        self._new_source_preview_lbl.pack(fill="x", padx=12, pady=7)

        # 2. KAYITLI KAYNAK SİTELER LİSTESİ BAŞLIĞI VE KONTEYNERİ
        list_hdr = ctk.CTkFrame(self.sources_scroll_frame, fg_color="transparent")
        list_hdr.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 6))
        list_hdr.grid_columnconfigure(0, weight=1)

        self._sources_count_lbl = ctk.CTkLabel(
            list_hdr,
            text="AKTİF DERS VİDEO KAYNAK SİTELERİ",
            font=self._font(12, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        self._sources_count_lbl.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            list_hdr,
            text="YouTube sabit sistem kaynağıdır • 345, Bilgi Sarmal ve eklediğiniz tüm sitelerin kategorisini değiştirebilir veya silebilirsiniz",
            font=self._font(11),
            text_color=TEXT_MUTED,
            anchor="e"
        ).grid(row=0, column=1, sticky="e")

        self._sources_list_frame = ctk.CTkFrame(self.sources_scroll_frame, fg_color="transparent")
        self._sources_list_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 12))
        self._sources_list_frame.grid_columnconfigure(0, weight=1)

        self._sync_sources_view()

    def _sync_sources_view(self):
        if not self._sources_built:
            self._build_sources_view_once()
            return

        for w in self._sources_list_frame.winfo_children():
            w.destroy()

        sources = self.engine.get_study_sources()
        q = self.search_query.lower().strip() if self.search_query else ""
        if q:
            sources = [
                s for s in sources
                if q in str(s.get("name", "")).lower()
                or q in str(s.get("domain", "")).lower()
                or any(q in str(tok).lower() for tok in s.get("keywords", []))
            ]

        self._sources_count_lbl.configure(
            text=f"AKTİF DERS VİDEO KAYNAK SİTELERİ  •  {len(sources)} KAYNAK TANIMLI"
        )

        for idx, src in enumerate(sources):
            src_id = src.get("id", f"src_{idx}")
            src_name = src.get("name", src_id)
            src_domain = src.get("domain", "")
            src_subj = src.get("subject_id", "soru_cozum")
            is_locked = bool(src.get("locked", False))
            benefit_txt = get_source_benefit_description(src)
            badge_code = get_source_badge_code(src)

            if is_locked:
                badge_color = "#10b981"
            elif src_id == "src_ucdortbes":
                badge_color = "#f59e0b"
            elif src_id == "src_bilgisarmal":
                badge_color = "#e4e4e7"
            else:
                subj_info = get_subject_info(src_subj if src_subj != "otomatik" else "genel_ders")
                badge_color = subj_info.get("color", "#10b981")

            card = ctk.CTkFrame(
                self._sources_list_frame,
                fg_color="#141818" if is_locked else BG_CARD,
                border_color="#10b981" if is_locked else BORDER_DEFAULT,
                border_width=1,
                corner_radius=13
            )
            card.grid(row=idx, column=0, sticky="ew", pady=5)
            card.grid_columnconfigure(1, weight=1)

            # Sol Rozet
            badge_img = create_subject_badge_ctk(badge_code, badge_color)
            ctk.CTkLabel(
                card,
                text="",
                image=badge_img,
                width=46
            ).grid(row=0, column=0, padx=(14, 12), pady=12)

            # Orta Bilgi Alanı (Kaynak Adı + Domain + Ne İşe Yaradığı)
            info_col = ctk.CTkFrame(card, fg_color="transparent")
            info_col.grid(row=0, column=1, sticky="ew", pady=10, padx=(0, 10))
            info_col.grid_columnconfigure(0, weight=1)

            title_line = ctk.CTkFrame(info_col, fg_color="transparent")
            title_line.grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                title_line,
                text=src_name,
                font=self._font(14, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w"
            ).pack(side="left")

            if src_domain:
                dom_pill = ctk.CTkFrame(
                    title_line,
                    fg_color=BG_INPUT,
                    border_color=BORDER_SUBTLE,
                    border_width=1,
                    corner_radius=7
                )
                dom_pill.pack(side="left", padx=(8, 0))
                ctk.CTkLabel(
                    dom_pill,
                    text=src_domain,
                    font=self._font(11, "bold"),
                    text_color=TEXT_SECONDARY
                ).pack(padx=8, pady=2)

            benefit_lbl = ctk.CTkLabel(
                info_col,
                text=f"🎯 Ne İşe Yarar:  {benefit_txt}",
                font=self._font(12, "bold"),
                text_color=ACCENT_EMERALD_TEXT if is_locked else "#e4e4e7",
                anchor="w",
                justify="left",
                wraplength=610
            )
            benefit_lbl.grid(row=1, column=0, sticky="w", pady=(4, 0))

            # Sağ Aksiyon Alanı
            right_col = ctk.CTkFrame(card, fg_color="transparent")
            right_col.grid(row=0, column=2, sticky="e", padx=(6, 14), pady=10)

            if is_locked:
                locked_pill = ctk.CTkFrame(
                    right_col,
                    fg_color="#0d261e",
                    border_color="#10b981",
                    border_width=1,
                    corner_radius=9
                )
                locked_pill.pack(side="right")
                ctk.CTkLabel(
                    locked_pill,
                    text="🔒 Sabit Sistem Kaynağı (Silinemez / Değiştirilemez)",
                    font=self._font(11, "bold"),
                    text_color=ACCENT_EMERALD_TEXT
                ).pack(padx=12, pady=6)
            else:
                ctk.CTkLabel(
                    right_col,
                    text="Kategori:",
                    font=self._font(11, "bold"),
                    text_color=TEXT_SECONDARY
                ).pack(side="left", padx=(0, 6))

                cur_label = get_source_category_label(src_subj)
                cat_menu = ctk.CTkOptionMenu(
                    right_col,
                    values=list(self._cat_label_to_id.keys()),
                    font=self._font(12, "bold"),
                    fg_color=BG_ELEVATED,
                    button_color=BG_ELEVATED_HOVER,
                    button_hover_color="#3f3f46",
                    dropdown_fg_color=BG_CARD,
                    text_color=TEXT_PRIMARY,
                    width=225,
                    height=32,
                    corner_radius=8,
                    command=lambda chosen_lbl, s_id=src_id: self._on_source_category_changed(s_id, chosen_lbl)
                )
                cat_menu.pack(side="left", padx=(0, 8))
                cat_menu.set(cur_label)

                ctk.CTkButton(
                    right_col,
                    text="Kaynağı Sil",
                    font=self._font(12, "bold"),
                    fg_color="#2a1218",
                    hover_color=ACCENT_ROSE,
                    text_color="#fda4af",
                    width=96,
                    height=32,
                    corner_radius=8,
                    border_width=0,
                    command=lambda s_id=src_id: self._on_remove_source_clicked(s_id)
                ).pack(side="left")

    def _on_add_source_clicked(self):
        raw_url = self.new_source_entry.get().strip()
        selected_label = self.new_source_cat_menu.get()
        chosen_sid = self._cat_label_to_id.get(selected_label, "soru_cozum")

        src_obj, msg = self.engine.add_study_source(raw_url, chosen_sid)
        self._ui_dirty = False
        if src_obj:
            self.new_source_entry.delete(0, "end")
            self.feedback_label.configure(text=msg, text_color=ACCENT_EMERALD_TEXT)
            self._sync_sources_view()
        else:
            self.feedback_label.configure(text=msg, text_color=ACCENT_ROSE)

    def _on_source_category_changed(self, source_id: str, selected_label: str):
        chosen_sid = self._cat_label_to_id.get(selected_label, "soru_cozum")
        ok, msg = self.engine.update_study_source_category(source_id, chosen_sid)
        self._ui_dirty = False
        self.feedback_label.configure(
            text=msg,
            text_color=ACCENT_EMERALD_TEXT if ok else ACCENT_ROSE
        )
        self._sync_sources_view()

    def _on_remove_source_clicked(self, source_id: str):
        ok, msg = self.engine.remove_study_source(source_id)
        self._ui_dirty = False
        self.feedback_label.configure(
            text=msg,
            text_color=ACCENT_AMBER if ok else ACCENT_ROSE
        )
        self._sync_sources_view()

    # ==================================================================
    # GÖRÜNÜM GEÇİŞLERİ VE LİSTE YÖNETİMİ (SIFIR TİTREME / IN-PLACE)
    # ==================================================================
    def _switch_active_view(self, force_rebuild: bool = False, focus_stopped_entry: bool = False):
        if self.current_tab == "📊 Ders Sürelerim":
            self.items_scroll_frame.grid_remove()
            self.sources_scroll_frame.grid_remove()
            self.stats_scroll_frame.grid(row=0, column=0, sticky="nsew")
            self._sync_subject_stats_view(focus_stopped_entry=focus_stopped_entry)
        elif self.current_tab == "🌐 Kaynak Siteler":
            self.items_scroll_frame.grid_remove()
            self.stats_scroll_frame.grid_remove()
            self.sources_scroll_frame.grid(row=0, column=0, sticky="nsew")
            self._sync_sources_view()
        else:
            self.stats_scroll_frame.grid_remove()
            self.sources_scroll_frame.grid_remove()
            self.items_scroll_frame.grid(row=0, column=0, sticky="nsew")
            self._refresh_items_view(force_rebuild=force_rebuild)

    def _refresh_list(self):
        self._switch_active_view(force_rebuild=False)

    def _get_filtered_items_for_current_tab(self) -> list:
        all_items = self.engine.get_all_items()
        filtered = []

        for item in all_items:
            if self.current_tab == "Antigravity'nin Seçtikleri":
                if not item.get("antigravity_pick"):
                    continue
            else:
                if item.get("antigravity_pick"):
                    continue
                if self.current_tab in ("Uygulamalarım", "Bilgisayarımdaki Uygulamalar"):
                    if not item.get("is_pc_app"):
                        continue
                elif self.current_tab == "Web Siteleri":
                    if item.get("item_type") not in ("site", "both"):
                        continue
                elif self.current_tab in ("Kilitli Olanlar", "Kapalı Olanlar"):
                    if not item.get("blocked"):
                        continue

            if self.search_query:
                q = self.search_query.lower()
                if (
                    q not in item["name"].lower()
                    and q not in item.get("category", "").lower()
                    and not any(q in d.lower() for d in item.get("domains", []))
                ):
                    continue

            filtered.append(item)

        if self.current_tab != "Antigravity'nin Seçtikleri":
            filtered.sort(key=lambda x: (not x.get("blocked", False), x["name"].lower()))
        return filtered

    def _refresh_items_view(self, force_rebuild: bool = False):
        if self.current_tab == "Şu An Açık":
            self._rendered_items_signature = None
            self._item_card_refs.clear()
            for w in self.items_scroll_frame.winfo_children():
                w.destroy()
            self._render_running_apps()
            return

        filtered = self._get_filtered_items_for_current_tab()
        item_ids_tuple = tuple(x["id"] for x in filtered)
        new_sig = (self.current_tab, self.search_query, item_ids_tuple)

        # Eğer görünür kartların listesi değişmediyse (ör. bir öğeye 'Engelle' basıldıysa),
        # hiçbir kartı silmeden (Sıfır F5 titremesi) sadece kartların durumunu yerinde güncelle!
        if not force_rebuild and self._rendered_items_signature == new_sig and self._item_card_refs:
            self._sync_existing_item_cards(filtered)
            return

        self._rendered_items_signature = new_sig
        self._item_card_refs.clear()
        for w in self.items_scroll_frame.winfo_children():
            w.destroy()

        row_offset = 0
        if self.current_tab == "Antigravity'nin Seçtikleri":
            total_domains = sum(len(x.get("domains", [])) for x in filtered)
            ag_banner = ctk.CTkFrame(
                self.items_scroll_frame,
                fg_color=BG_SURFACE,
                border_color=BORDER_DEFAULT,
                border_width=1,
                corner_radius=14
            )
            ag_banner.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=(4, 10))
            cd_now = self.engine.get_tyt_countdown()
            target_dt_str = cd_now.get("unlock_date_str", "18 Haziran 2027")
            t_title = cd_now.get("target_title", "YKS 2027")
            ctk.CTkLabel(
                ag_banner,
                text=(
                    f"Antigravity Koruma Paketi  •  {len(filtered)} Kategori ({total_domains} Alan Adı Kilitli)  •  Hedef: {t_title}\n"
                    f"Sosyal Medya, Reels, Yayın, Dizi/Film, Anime, Web Oyunları, Alışveriş ve AI Sohbet siteleri "
                    f"{target_dt_str} tarihine kadar koruma altında."
                ),
                font=self._font(12, "bold"),
                text_color=TEXT_SECONDARY,
                justify="left",
                anchor="w"
            ).pack(fill="x", padx=16, pady=12)
            row_offset = 1

        if not filtered:
            empty_msg = (
                "Şu an kapalı olan hiçbir uygulama veya site yok."
                if self.current_tab == "Kapalı Olanlar"
                else "Aramanıza uygun öğe bulunamadı."
            )
            ctk.CTkLabel(
                self.items_scroll_frame,
                text=empty_msg,
                font=self._font(13),
                text_color=TEXT_MUTED,
                pady=40
            ).grid(row=row_offset, column=0, columnspan=2)
            return

        for idx, item in enumerate(filtered):
            r = (idx // 2) + row_offset
            c = idx % 2
            self._create_icon_card(r, c, item)

    def _sync_existing_item_cards(self, items_list: list):
        """Kartları yeniden yaratmadan (F5 titremesi olmadan) kilit durumlarını yerinde günceller."""
        tyt_unlocked = self.engine.is_tyt_unlocked()
        for item in items_list:
            iid = item["id"]
            ref = self._item_card_refs.get(iid)
            if not ref:
                continue
            blocked = bool(item.get("blocked"))
            if ref["blocked"] == blocked and ref["tyt_unlocked"] == tyt_unlocked:
                continue
            ref["blocked"] = blocked
            ref["tyt_unlocked"] = tyt_unlocked

            bg_color = "#1c1216" if blocked else BG_CARD
            border_color = "#4c1d29" if blocked else BORDER_SUBTLE
            ref["card"].configure(fg_color=bg_color, border_color=border_color)

            if ref.get("sub_lbl") is not None:
                ref["sub_lbl"].configure(text_color="#fb7185" if blocked else TEXT_SECONDARY)

            btn = ref["btn"]
            if blocked:
                if tyt_unlocked:
                    btn.configure(
                        text="Kilidi Aç",
                        fg_color=ACCENT_EMERALD,
                        hover_color="#059669",
                        text_color="#ffffff",
                        state="normal",
                        command=lambda i_id=iid: self._unlock_item_after_tyt(i_id)
                    )
                else:
                    btn.configure(
                        text="Kilitli",
                        fg_color="#33141c",
                        text_color="#fb7185",
                        text_color_disabled="#fb7185",
                        state="disabled"
                    )
            else:
                btn.configure(
                    text="Engelle",
                    fg_color=BG_ELEVATED,
                    hover_color=ACCENT_ROSE,
                    text_color=TEXT_PRIMARY,
                    state="normal",
                    command=lambda i_id=iid: self._lock_item_strictly(i_id)
                )

    def _create_icon_card(self, row: int, col: int, item: dict):
        iid = item["id"]
        blocked = bool(item.get("blocked"))
        tyt_unlocked = self.engine.is_tyt_unlocked()
        bg_color = "#1c1216" if blocked else BG_CARD
        border_color = "#4c1d29" if blocked else BORDER_SUBTLE

        card = ctk.CTkFrame(
            self.items_scroll_frame,
            fg_color=bg_color,
            border_color=border_color,
            border_width=1,
            corner_radius=12,
            height=58
        )
        card.grid(row=row, column=col, sticky="ew", padx=5, pady=4)
        card.grid_columnconfigure(1, weight=1)

        ctk_img = self._get_ctk_icon(item.get("icon_png", ""))
        if ctk_img:
            ctk.CTkLabel(card, text="", image=ctk_img, width=30).grid(row=0, column=0, padx=(12, 8), pady=10)
        else:
            ctk.CTkLabel(card, text="●", font=self._font(16, "bold"), text_color=ACCENT_INDIGO, width=30).grid(
                row=0, column=0, padx=(12, 8), pady=10
            )

        raw_name = item["name"]
        sub_lbl = None
        if item.get("antigravity_pick"):
            if "(" in raw_name and raw_name.endswith(")"):
                main_title, paren_part = raw_name.split("(", 1)
                main_title = main_title.strip()
                examples_str = paren_part[:-1].strip()
            else:
                main_title = raw_name
                examples_str = item.get("category", "Dopamin Tuzağı")
            txt_frame = ctk.CTkFrame(card, fg_color="transparent")
            txt_frame.grid(row=0, column=1, sticky="ew", pady=7)
            ctk.CTkLabel(
                txt_frame,
                text=main_title,
                font=self._font(13, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w"
            ).pack(anchor="w")
            dom_cnt = len(item.get("domains", []))
            sub_lbl = ctk.CTkLabel(
                txt_frame,
                text=f"{examples_str} • {dom_cnt} alan adı kilitli",
                font=self._font(11),
                text_color="#fb7185" if blocked else TEXT_SECONDARY,
                anchor="w"
            )
            sub_lbl.pack(anchor="w")
        else:
            ctk.CTkLabel(
                card,
                text=raw_name,
                font=self._font(13, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w"
            ).grid(row=0, column=1, sticky="w", pady=10)

        if blocked:
            if tyt_unlocked:
                btn = ctk.CTkButton(
                    card,
                    text="Kilidi Aç",
                    font=self._font(12, "bold"),
                    fg_color=ACCENT_EMERALD,
                    hover_color="#059669",
                    text_color="#ffffff",
                    width=96,
                    height=30,
                    corner_radius=9,
                    command=lambda i_id=iid: self._unlock_item_after_tyt(i_id)
                )
            else:
                btn = ctk.CTkButton(
                    card,
                    text="Kilitli",
                    font=self._font(12, "bold"),
                    fg_color="#33141c",
                    text_color="#fb7185",
                    text_color_disabled="#fb7185",
                    state="disabled",
                    width=96,
                    height=30,
                    corner_radius=9
                )
        else:
            btn = ctk.CTkButton(
                card,
                text="Engelle",
                font=self._font(12, "bold"),
                fg_color=BG_ELEVATED,
                hover_color=ACCENT_ROSE,
                text_color=TEXT_PRIMARY,
                width=92,
                height=30,
                corner_radius=9,
                command=lambda i_id=iid: self._lock_item_strictly(i_id)
            )
        btn.grid(row=0, column=2, padx=12, pady=10)

        self._item_card_refs[iid] = {
            "card": card,
            "btn": btn,
            "sub_lbl": sub_lbl,
            "blocked": blocked,
            "tyt_unlocked": tyt_unlocked,
        }

    def _render_running_apps(self):
        running = self.engine.get_running_user_apps()
        if self.search_query:
            q = self.search_query.lower()
            running = [a for a in running if q in a["display_name"].lower() or q in a["exe_name"].lower()]

        if not running:
            ctk.CTkLabel(
                self.items_scroll_frame,
                text="Görev çubuğu veya gizli simgelerde açık uygulama bulunamadı.",
                font=self._font(13),
                text_color=TEXT_MUTED,
                pady=30
            ).grid(row=0, column=0, columnspan=2)
            return

        for idx, app in enumerate(running):
            r = idx // 2
            c = idx % 2
            card = ctk.CTkFrame(
                self.items_scroll_frame,
                fg_color=BG_CARD,
                border_color=BORDER_SUBTLE,
                border_width=1,
                corner_radius=12
            )
            card.grid(row=r, column=c, sticky="ew", padx=5, pady=4)
            card.grid_columnconfigure(1, weight=1)

            ctk_img = self._get_ctk_icon(app.get("icon_png", ""))
            if ctk_img:
                ctk.CTkLabel(card, text="", image=ctk_img, width=30).grid(row=0, column=0, padx=(12, 8), pady=10)

            src = app.get("source", "Görev Çubuğu")
            ctk.CTkLabel(
                card,
                text=f"{app['display_name']} ({src})",
                font=self._font(13, "bold"),
                text_color=TEXT_PRIMARY,
                anchor="w"
            ).grid(row=0, column=1, sticky="w", pady=10)

            ctk.CTkButton(
                card,
                text="Engelle",
                font=self._font(12, "bold"),
                fg_color=BG_ELEVATED,
                hover_color=ACCENT_ROSE,
                text_color=TEXT_PRIMARY,
                width=92,
                height=30,
                corner_radius=9,
                command=lambda exe=app["exe_name"]: self._block_running_exe(exe)
            ).grid(row=0, column=2, padx=12, pady=10)

    # ==================================================================
    # HAFTADA 1 KEZ 30 DAKİKALIK ACİL DURUM BUTONU ONAY PENCERESİ
    # ==================================================================
    def _on_emergency_button_clicked(self):
        em_status = self.engine.get_emergency_status()
        if em_status["active"]:
            rem = em_status["rem_active_sec"]
            m, s = divmod(rem, 60)
            self.feedback_label.configure(
                text=f"Acil Durum Modu şu an aktif! Kalan süre: {m:02d} dk {s:02d} sn.",
                text_color=ACCENT_AMBER
            )
            return

        if not em_status["can_use"]:
            rem = em_status["cooldown_rem_sec"]
            days = rem // 86400
            hrs = (rem % 86400) // 3600
            mins = (rem % 3600) // 60
            self.feedback_label.configure(
                text=f"Haftalık Acil Durum hakkınızı kullandınız. Yeni hak için kalan süre: {days} gün {hrs} saat {mins} dk.",
                text_color=ACCENT_ROSE
            )
            return

        blocked = self.engine.get_blocked_items()
        if not blocked:
            self.feedback_label.configure(
                text="Şu an kilitli hiçbir uygulama veya site yok. Haftalık Acil Durum hakkınız harcanmadı.",
                text_color=ACCENT_CYAN
            )
            return

        if self.emergency_confirm_win is not None and self.emergency_confirm_win.winfo_exists():
            self.emergency_confirm_win.lift()
            self.emergency_confirm_win.focus_force()
            return

        win = ctk.CTkToplevel(self)
        win.title("Acil Durum Modu Onayı")
        win.geometry("490x275")
        win.resizable(False, False)
        win.configure(fg_color=BG_CANVAS)
        win.attributes("-topmost", True)
        win.after(50, lambda: apply_windows_dark_titlebar(win))

        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - 490) // 2
        y = (sh - 275) // 2
        win.geometry(f"490x275+{x}+{y}")
        self.emergency_confirm_win = win

        box = ctk.CTkFrame(
            win,
            fg_color=BG_SURFACE,
            border_color=BORDER_DEFAULT,
            border_width=1,
            corner_radius=16
        )
        box.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            box,
            text="Haftalık Acil Durum Hakkı (30 Dakika)",
            font=self._font(17, "bold"),
            text_color=ACCENT_ROSE
        ).pack(padx=16, pady=(18, 8))

        ctk.CTkLabel(
            box,
            text=(
                "Bu özelliği yalnızca HAFTADA 1 KEZ kullanabilirsiniz.\n\n"
                "Onayladığınızda tüm kilitli uygulama ve siteler 30 dakikalığına açılacak,\n"
                "süre sonunda ise otomatik olarak tekrar kilitlenecektir."
            ),
            font=self._font(12),
            text_color=TEXT_SECONDARY,
            justify="center"
        ).pack(padx=16, pady=(0, 18))

        btn_row = ctk.CTkFrame(box, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row,
            text="Evet, 30 Dk Aç",
            font=self._font(13, "bold"),
            fg_color=ACCENT_ROSE,
            hover_color=ACCENT_ROSE_DARK,
            text_color="#ffffff",
            height=38,
            corner_radius=10,
            command=self._confirm_emergency_unlock
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Vazgeç",
            font=self._font(13, "bold"),
            fg_color=BG_ELEVATED,
            hover_color=BG_ELEVATED_HOVER,
            text_color=TEXT_PRIMARY,
            height=38,
            corner_radius=10,
            command=win.destroy
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _confirm_emergency_unlock(self):
        if self.emergency_confirm_win is not None and self.emergency_confirm_win.winfo_exists():
            self.emergency_confirm_win.destroy()
        self.emergency_confirm_win = None

        ok, msg = self.engine.trigger_emergency_unlock()
        self._ui_dirty = False
        self.feedback_label.configure(
            text=msg,
            text_color=ACCENT_AMBER if ok else ACCENT_ROSE
        )
        self._switch_active_view(force_rebuild=False)
        self._refresh_status()

    # ==================================================================
    # 2 SAAT DERS SONRASI 10 DAKİKA MOLA ÖDÜL POP-UP PENCERESİ
    # ==================================================================
    def _force_window_on_top(self, win: ctk.CTkToplevel, width: int, height: int, break_fullscreen: bool = False):
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = max(0, (sw - width) // 2)
            y = max(0, (sh - height) // 2)

            fg_hwnd = user32.GetForegroundWindow()
            if break_fullscreen and fg_hwnd:
                rect = ctypes.wintypes.RECT()
                if user32.GetWindowRect(fg_hwnd, ctypes.byref(rect)):
                    w_rect = rect.right - rect.left
                    h_rect = rect.bottom - rect.top
                    if w_rect >= sw and h_rect >= sh:
                        user32.keybd_event(0x1B, 0x01, 0, 0)
                        user32.keybd_event(0x1B, 0x01, 0x0002, 0)

            win.deiconify()
            win.attributes("-topmost", True)
            win.lift()
            win.update_idletasks()

            hwnd = user32.GetParent(win.winfo_id()) or win.winfo_id()
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
            cur_thread = kernel32.GetCurrentThreadId()
            attached = False
            if fg_thread and fg_thread != cur_thread:
                attached = bool(user32.AttachThreadInput(fg_thread, cur_thread, True))
            try:
                user32.ShowWindow(hwnd, 9)
                user32.SetWindowPos(hwnd, -1, x, y, width, height, 0x0040)
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
            finally:
                if attached:
                    user32.AttachThreadInput(fg_thread, cur_thread, False)

            win.focus_force()
        except Exception:
            pass

    def _open_break_bar_settings_popup(self):
        """Mola Barajının en sağındaki ayar simgesine basıldığında açılan Mola Barajı Ayarları Pop-up'ı."""
        if self.break_settings_win is not None and self.break_settings_win.winfo_exists():
            try:
                self.break_settings_win.lift()
                self.break_settings_win.focus_force()
            except Exception:
                pass
            return

        with self.engine.lock:
            cur_goal = int(self.engine.study_goal_seconds)
            cur_break = int(self.engine.reward_break_minutes)

        pop_w, pop_h = 660, 515
        win = ctk.CTkToplevel(self)
        win.title("Mola Barajı Ayarları")
        win.geometry(f"{pop_w}x{pop_h}")
        win.resizable(False, False)
        win.configure(fg_color=BG_CANVAS)
        win.attributes("-topmost", True)

        def _style_popup_win():
            if not win.winfo_exists():
                return
            apply_windows_dark_titlebar(win)
            ico_p = os.path.join(BASE_DIR, "odak_icon.ico")
            if os.path.exists(ico_p):
                try:
                    win.iconbitmap(ico_p)
                except Exception:
                    pass

        win.after(50, _style_popup_win)
        win.after(230, _style_popup_win)

        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - pop_w) // 2
        y = (sh - pop_h) // 2
        win.geometry(f"{pop_w}x{pop_h}+{x}+{y}")

        self.break_settings_win = win

        selected_state = {
            "goal_sec": cur_goal,
            "break_min": cur_break,
        }
        goal_btns = {}
        break_btns = {}

        # Başlık Kartı
        hdr = ctk.CTkFrame(
            win,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        hdr.pack(fill="x", padx=22, pady=(18, 12))

        title_row = ctk.CTkFrame(hdr, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            title_row,
            text="",
            image=self._gear_ctk_img,
            width=24
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            title_row,
            text="Mola Barajı Ayarları",
            font=self._font(18, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            hdr,
            text="Hedef süreyi değiştirdiğinde baraj sıfırlanmaz; mevcut ilerlemen yeni süreye adaletli oranda aktarılır.",
            font=self._font(12),
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=580
        ).pack(fill="x", padx=16, pady=(0, 12))

        # 1. Ders Çalışma Süresi Seçenekleri
        goal_card = ctk.CTkFrame(
            win,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        goal_card.pack(fill="x", padx=22, pady=(0, 12))

        ctk.CTkLabel(
            goal_card,
            text="DERS ÇALIŞMA SÜRESİ SEÇENEKLERİ (MOLA BARAJI HEDEFİ)",
            font=self._font(11, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x", padx=16, pady=(12, 8))

        goal_btn_row = ctk.CTkFrame(goal_card, fg_color="transparent")
        goal_btn_row.pack(fill="x", padx=12, pady=(0, 14))
        for idx in range(len(STUDY_GOAL_OPTIONS)):
            goal_btn_row.grid_columnconfigure(idx, weight=1)

        # 2. Mola Süresi Seçenekleri
        break_card = ctk.CTkFrame(
            win,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        break_card.pack(fill="x", padx=22, pady=(0, 12))

        ctk.CTkLabel(
            break_card,
            text="MOLA SÜRESİ SEÇENEKLERİ (ÖDÜL MOLASI)",
            font=self._font(11, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x", padx=16, pady=(12, 8))

        break_btn_row = ctk.CTkFrame(break_card, fg_color="transparent")
        break_btn_row.pack(fill="x", padx=12, pady=(0, 14))
        for idx in range(len(REWARD_BREAK_OPTIONS)):
            break_btn_row.grid_columnconfigure(idx, weight=1)

        # Adaletli Ölçekleme Canlı Bilgi Bandı (İki satırlı, taşmayan net yapı)
        scale_info_frame = ctk.CTkFrame(
            win,
            fg_color=BG_CARD,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=12
        )
        scale_info_frame.pack(fill="x", padx=22, pady=(0, 16))

        scale_title_lbl = ctk.CTkLabel(
            scale_info_frame,
            text="",
            font=self._font(12, "bold"),
            text_color=ACCENT_EMERALD_TEXT,
            anchor="w",
            justify="left"
        )
        scale_title_lbl.pack(fill="x", padx=16, pady=(10, 2))

        scale_detail_lbl = ctk.CTkLabel(
            scale_info_frame,
            text="",
            font=self._font(12),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left"
        )
        scale_detail_lbl.pack(fill="x", padx=16, pady=(0, 10))

        def _fmt_hms(sec_val: float) -> str:
            s_int = max(0, int(round(sec_val)))
            h, rem = divmod(s_int, 3600)
            m, s = divmod(rem, 60)
            if h > 0:
                return f"{h:02d}s {m:02d}dk {s:02d}sn"
            return f"{m:02d}dk {s:02d}sn"

        def _refresh_selection_ui():
            sel_g = selected_state["goal_sec"]
            sel_b = selected_state["break_min"]

            for g_sec, btn in goal_btns.items():
                if g_sec == sel_g:
                    btn.configure(
                        fg_color=ACCENT_EMERALD,
                        hover_color="#059669",
                        text_color="#ffffff"
                    )
                else:
                    btn.configure(
                        fg_color=BG_ELEVATED,
                        hover_color=BG_ELEVATED_HOVER,
                        text_color=TEXT_PRIMARY
                    )

            for b_min, btn in break_btns.items():
                if b_min == sel_b:
                    btn.configure(
                        fg_color=ACCENT_WHITE,
                        hover_color="#e4e4e7",
                        text_color=BG_CANVAS
                    )
                else:
                    btn.configure(
                        fg_color=BG_ELEVATED,
                        hover_color=BG_ELEVATED_HOVER,
                        text_color=TEXT_PRIMARY
                    )

            with self.engine.lock:
                live_old_goal = max(1, int(self.engine.study_goal_seconds))
                live_watched = float(self.engine.study_watched_seconds)

            ratio = min(1.0, max(0.0, live_watched / float(live_old_goal)))
            scaled_watched = live_watched * (float(sel_g) / float(live_old_goal))
            pct_str = f"%{ratio * 100:.1f}"

            if sel_g == live_old_goal:
                scale_title_lbl.configure(
                    text=f"● Adaletli Baraj Korunuyor ({pct_str} Dolu)",
                    text_color=ACCENT_EMERALD_TEXT
                )
                scale_detail_lbl.configure(
                    text=f"Mevcut İlerleme: {_fmt_hms(live_watched)} / {format_goal_bar_target(sel_g)}   •   Seçili Ödül Molası: {sel_b} Dakika"
                )
            else:
                scale_title_lbl.configure(
                    text=f"● Adaletli Oran Hesabı ({pct_str} İlerleme Oranı Aynen Korunur)",
                    text_color=ACCENT_EMERALD_TEXT
                )
                scale_detail_lbl.configure(
                    text=(
                        f"Eski: {_fmt_hms(live_watched)} ({format_goal_bar_target(live_old_goal)})   ➔   "
                        f"Yeni: {_fmt_hms(scaled_watched)} ({format_goal_bar_target(sel_g)})   •   Mola: {sel_b} Dakika"
                    )
                )

        def _select_goal(g_sec: int):
            selected_state["goal_sec"] = g_sec
            _refresh_selection_ui()

        def _select_break(b_min: int):
            selected_state["break_min"] = b_min
            _refresh_selection_ui()

        for idx, opt in enumerate(STUDY_GOAL_OPTIONS):
            g_sec = int(opt["seconds"])
            b = ctk.CTkButton(
                goal_btn_row,
                text=opt["label"],
                font=self._font(13, "bold"),
                width=90,
                height=40,
                corner_radius=10,
                border_width=0,
                command=lambda gs=g_sec: _select_goal(gs)
            )
            b.grid(row=0, column=idx, sticky="ew", padx=5, pady=2)
            goal_btns[g_sec] = b

        for idx, opt in enumerate(REWARD_BREAK_OPTIONS):
            b_min = int(opt["minutes"])
            b = ctk.CTkButton(
                break_btn_row,
                text=opt["label"],
                font=self._font(13, "bold"),
                width=110,
                height=40,
                corner_radius=10,
                border_width=0,
                command=lambda bm=b_min: _select_break(bm)
            )
            b.grid(row=0, column=idx, sticky="ew", padx=5, pady=2)
            break_btns[b_min] = b

        _refresh_selection_ui()

        # Alt Aksiyon Butonları
        btn_bar = ctk.CTkFrame(win, fg_color="transparent")
        btn_bar.pack(fill="x", padx=22, pady=(0, 20))
        btn_bar.grid_columnconfigure(0, weight=1)
        btn_bar.grid_columnconfigure(1, weight=2)

        def _on_cancel():
            if win.winfo_exists():
                win.destroy()
            self.break_settings_win = None

        def _on_save():
            try:
                res = self.engine.update_break_bar_settings(
                    selected_state["goal_sec"],
                    selected_state["break_min"]
                )
                self._last_bottom_sig = None
                goal_lbl = format_goal_short_tr(res.get("new_goal_sec", selected_state["goal_sec"]))
                brk_min = res.get("break_minutes", selected_state["break_min"])
                scaled_str = _fmt_hms(res.get("new_watched_sec", 0.0))
                self.feedback_label.configure(
                    text=(
                        f"⚙ Mola Barajı güncellendi: Hedef {goal_lbl}, Mola {brk_min} Dakika "
                        f"(İlerleme sıfırlanmadı, adaletli karşılığı: {scaled_str})."
                    ),
                    text_color=ACCENT_EMERALD_TEXT
                )
            finally:
                self.break_settings_win = None
                try:
                    if win.winfo_exists():
                        win.withdraw()
                        win.destroy()
                except Exception:
                    pass

            # Eğer ödül seçim pop-up'ı o anda açıksa metinlerini yeni mola süresine göre tazele
            if self.reward_popup_win is not None and self.reward_popup_win.winfo_exists():
                try:
                    self.reward_popup_win.destroy()
                except Exception:
                    pass
                self.reward_popup_win = None
                if self.engine.reward_available:
                    self._show_reward_popup()

        ctk.CTkButton(
            btn_bar,
            text="Vazgeç",
            font=self._font(13, "bold"),
            fg_color=BG_ELEVATED,
            hover_color=BG_ELEVATED_HOVER,
            text_color=TEXT_PRIMARY,
            height=42,
            corner_radius=10,
            command=_on_cancel
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            btn_bar,
            text="Ayarları Kaydet ve Uygula",
            font=self._font(13, "bold"),
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            text_color="#ffffff",
            height=42,
            corner_radius=10,
            command=_on_save
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _open_custom_lock_chooser_popup(self):
        """Sağ üstteki sayaç rozetine veya sol üstteki hedef rozetine tıklandığında açılan Custom Lock Chooser."""
        if self.custom_lock_win is not None and self.custom_lock_win.winfo_exists():
            try:
                self.custom_lock_win.lift()
                self.custom_lock_win.focus_force()
            except Exception:
                pass
            return

        cd = self.engine.get_tyt_countdown()
        presets = get_lock_target_presets()
        preset_map = {p["title"]: p for p in presets}

        win_w, win_h = 680, 560
        win = ctk.CTkToplevel(self)
        win.title("Özel Kilit Hedefi & Tarih Seçici (Custom Lock Chooser)")
        win.geometry(f"{win_w}x{win_h}")
        win.resizable(False, False)
        win.configure(fg_color=BG_CANVAS)
        win.attributes("-topmost", True)
        self.custom_lock_win = win

        def _on_close():
            try:
                if win.winfo_exists():
                    win.destroy()
            except Exception:
                pass
            self.custom_lock_win = None

        win.protocol("WM_DELETE_WINDOW", _on_close)
        win.after(40, lambda: apply_windows_dark_titlebar(win))
        win.after(80, lambda: self._force_window_on_top(win, win_w, win_h, break_fullscreen=False))

        # 1. ÜST BAŞLIK & KATI KORUMA BİLGİ BARI
        hdr = ctk.CTkFrame(
            win,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        hdr.pack(fill="x", padx=20, pady=(18, 10))

        ctk.CTkLabel(
            hdr,
            text="🔒 Özel Kilit Hedefi & Sınav Tarih Seçici (Custom Lock Chooser)",
            font=self._font(16, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x", padx=16, pady=(12, 3))

        is_strict_locked = bool(cd.get("committed", True) and not cd.get("unlocked", False))
        strict_msg = (
            f"🛡 Katı Koruma Aktif: Mevcut kilit tarihi ({cd['unlock_date_str']}) dolmadan bitiş tarihini erkene çekemezsiniz. "
            f"Tarihi daha ileri bir sınava/hedefe uzatabilir, hedef adını değiştirebilir veya mevcut süre bittiğinde yeni bir kilit başlatabilirsiniz."
            if is_strict_locked
            else "✨ Yeni Kilit Hedefi Seçime Açık: Hazır sınav/kamp şablonlarından birini seçebilir veya kendi özel hedef adınızı ve bitiş tarihinizi belirleyebilirsiniz."
        )
        ctk.CTkLabel(
            hdr,
            text=strict_msg,
            font=self._font(11),
            text_color=ACCENT_AMBER if is_strict_locked else ACCENT_EMERALD_TEXT,
            anchor="w",
            justify="left",
            wraplength=610
        ).pack(fill="x", padx=16, pady=(0, 12))

        # 2. HAZIR SINAV / HEDEF ŞABLONU SEÇİCİ KARTI
        preset_card = ctk.CTkFrame(
            win,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        preset_card.pack(fill="x", padx=20, pady=(0, 10))

        p_row = ctk.CTkFrame(preset_card, fg_color="transparent")
        p_row.pack(fill="x", padx=16, pady=12)
        p_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            p_row,
            text="HAZIR SINAV / KAMP ŞABLONU:",
            font=self._font(12, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))

        preset_menu = ctk.CTkOptionMenu(
            p_row,
            values=list(preset_map.keys()),
            font=self._font(13, "bold"),
            fg_color=BG_ELEVATED,
            button_color=BG_ELEVATED_HOVER,
            button_hover_color="#3f3f46",
            dropdown_fg_color=BG_CARD,
            text_color=TEXT_PRIMARY,
            height=36,
            corner_radius=10
        )
        preset_menu.grid(row=0, column=1, sticky="ew")

        # 3. ÖZEL HEDEF İSMİ VE TARİH / SAAT (GÜN / AY / YIL) SEÇİCİ KARTI
        custom_card = ctk.CTkFrame(
            win,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        custom_card.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            custom_card,
            text="HEDEF İSMİ, ROZETİ VE KİLİT AÇILIŞ TARİHİ",
            font=self._font(12, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x", padx=16, pady=(12, 8))

        fields_row = ctk.CTkFrame(custom_card, fg_color="transparent")
        fields_row.pack(fill="x", padx=16, pady=(0, 10))
        fields_row.grid_columnconfigure(0, weight=3)
        fields_row.grid_columnconfigure(1, weight=2)
        fields_row.grid_columnconfigure(2, weight=1)

        # Hedef Adı
        col_title = ctk.CTkFrame(fields_row, fg_color="transparent")
        col_title.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(col_title, text="Hedef / Sınav Adı:", font=self._font(11, "bold"), text_color=TEXT_MUTED).pack(anchor="w")
        title_entry = ctk.CTkEntry(
            col_title,
            height=36,
            font=self._font(13, "bold"),
            fg_color=BG_INPUT,
            text_color=TEXT_PRIMARY,
            border_color=BORDER_DEFAULT,
            border_width=1,
            corner_radius=9
        )
        title_entry.pack(fill="x", pady=(3, 0))
        title_entry.insert(0, cd.get("target_title", "YKS 2027 (TYT / AYT)"))

        # Sayaç Başlığı
        col_pref = ctk.CTkFrame(fields_row, fg_color="transparent")
        col_pref.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkLabel(col_pref, text="Sayaç Etiketi (Örn: TYT Kilidi):", font=self._font(11, "bold"), text_color=TEXT_MUTED).pack(anchor="w")
        prefix_entry = ctk.CTkEntry(
            col_pref,
            height=36,
            font=self._font(13, "bold"),
            fg_color=BG_INPUT,
            text_color=TEXT_PRIMARY,
            border_color=BORDER_DEFAULT,
            border_width=1,
            corner_radius=9
        )
        prefix_entry.pack(fill="x", pady=(3, 0))
        prefix_entry.insert(0, cd.get("countdown_prefix", "TYT Kilidi"))

        # Üst Bar Rozeti
        col_badge = ctk.CTkFrame(fields_row, fg_color="transparent")
        col_badge.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(col_badge, text="Üst Rozet:", font=self._font(11, "bold"), text_color=TEXT_MUTED).pack(anchor="w")
        badge_entry = ctk.CTkEntry(
            col_badge,
            height=36,
            font=self._font(13, "bold"),
            fg_color=BG_INPUT,
            text_color=TEXT_PRIMARY,
            border_color=BORDER_DEFAULT,
            border_width=1,
            corner_radius=9
        )
        badge_entry.pack(fill="x", pady=(3, 0))
        badge_entry.insert(0, cd.get("target_badge", "YKS 2027"))

        # Gün / Ay / Yıl / Saat Seçici Satırı
        date_row = ctk.CTkFrame(custom_card, fg_color="transparent")
        date_row.pack(fill="x", padx=16, pady=(2, 14))
        for c_i in range(4):
            date_row.grid_columnconfigure(c_i, weight=1)

        day_vals = [f"{d:02d}" for d in range(1, 32)]
        month_vals = [f"{m:02d} - {TR_MONTH_NAMES[m]}" for m in range(1, 13)]
        cur_yr = datetime.now().year
        year_vals = [str(y) for y in range(cur_yr, cur_yr + 10)]
        time_vals = ["00:00", "06:00", "08:00", "09:00", "10:00", "12:00", "18:00", "20:00", "23:59"]

        def _make_date_col(parent, col_idx, lbl_text, values, init_val, pad_x):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.grid(row=0, column=col_idx, sticky="ew", padx=pad_x)
            ctk.CTkLabel(f, text=lbl_text, font=self._font(11, "bold"), text_color=TEXT_MUTED).pack(anchor="w")
            om = ctk.CTkOptionMenu(
                f,
                values=values,
                font=self._font(13, "bold"),
                fg_color=BG_ELEVATED,
                button_color=BG_ELEVATED_HOVER,
                button_hover_color="#3f3f46",
                dropdown_fg_color=BG_CARD,
                text_color=TEXT_PRIMARY,
                height=36,
                corner_radius=9
            )
            om.pack(fill="x", pady=(3, 0))
            if init_val in values:
                om.set(init_val)
            return om

        init_day = f"{int(cd.get('day', 18)):02d}"
        init_m_num = int(cd.get("month", 6))
        init_month = f"{init_m_num:02d} - {TR_MONTH_NAMES[init_m_num]}"
        init_year = str(cd.get("year", 2027))
        init_time = f"{int(cd.get('hour', 0)):02d}:{int(cd.get('minute', 0)):02d}"
        if init_time not in time_vals:
            time_vals.insert(0, init_time)

        day_menu = _make_date_col(date_row, 0, "Gün:", day_vals, init_day, (0, 6))
        month_menu = _make_date_col(date_row, 1, "Ay:", month_vals, init_month, 6)
        year_menu = _make_date_col(date_row, 2, "Yıl:", year_vals, init_year, 6)
        time_menu = _make_date_col(date_row, 3, "Saat:", time_vals, init_time, (6, 0))

        # 4. CANLI ÖNİZLEME VE DOĞRULAMA KUTUSU
        preview_card = ctk.CTkFrame(
            win,
            fg_color=BG_INPUT,
            border_color=BORDER_STRONG,
            border_width=1,
            corner_radius=12
        )
        preview_card.pack(fill="x", padx=20, pady=(0, 14))

        preview_lbl = ctk.CTkLabel(
            preview_card,
            text="",
            font=self._font(12, "bold"),
            text_color=ACCENT_EMERALD_TEXT,
            anchor="w",
            justify="left",
            wraplength=610
        )
        preview_lbl.pack(fill="x", padx=14, pady=10)

        selected_preset_state = {"id": cd.get("preset_id", "yks_2027")}

        def _build_selected_datetime():
            try:
                y = int(year_menu.get())
                m = int(month_menu.get().split("-")[0].strip())
                d = int(day_menu.get())
                hm = time_menu.get().split(":")
                hr, mn = int(hm[0]), int(hm[1])
                # Ayın son gününü aşarsa otomatik düzelt (örn. 31 Şubat -> 28/29 Şubat)
                for try_d in range(d, 27, -1):
                    try:
                        return datetime(y, m, try_d, hr, mn, 0)
                    except ValueError:
                        continue
                return datetime(y, m, 28, hr, mn, 0)
            except Exception:
                return datetime(2027, 6, 18, 0, 0, 0)

        def _refresh_preview(*_args):
            dt = _build_selected_datetime()
            now_ts = self.engine.self_defense.get_verified_timestamp()
            cur_ts = float(cd.get("unlock_timestamp", 0.0))
            new_ts = dt.timestamp()
            diff_sec = int(new_ts - now_ts)
            d_cnt = max(0, diff_sec // 86400)
            h_cnt = max(0, (diff_sec % 86400) // 3600)
            t_name = title_entry.get().strip() or "Özel Odak Hedefi"

            if diff_sec <= 60:
                preview_lbl.configure(
                    text=f"⚠️ Seçilen Tarih Geçmişte: {format_turkish_date_full(dt)} — Lütfen gelecekte bir tarih seçin.",
                    text_color=ACCENT_ROSE
                )
            elif is_strict_locked and new_ts < (cur_ts - 60):
                preview_lbl.configure(
                    text=(
                        f"⛔ Katı Koruma Engeli: Seçilen tarih ({format_turkish_date_full(dt)}) mevcut kilit tarihinden "
                        f"({cd['unlock_date_str']}) daha erken! Yalnızca mevcut tarihten ileri bir tarih seçebilirsiniz."
                    ),
                    text_color=ACCENT_ROSE
                )
            else:
                preview_lbl.configure(
                    text=(
                        f"🎯 Seçilen Hedef: {t_name}  •  Kilit Açılışı: {format_turkish_date_full(dt)}\n"
                        f"⏳ Toplam Koruma Süresi: {d_cnt} Gün {h_cnt} Saat boyunca tüm dikkat dağıtıcılar kilitli kalacak."
                    ),
                    text_color=ACCENT_EMERALD_TEXT
                )

        def _on_preset_selected(selected_title: str):
            p = preset_map.get(selected_title)
            if not p:
                return
            selected_preset_state["id"] = p["id"]
            if p["id"] != "custom":
                title_entry.delete(0, "end")
                title_entry.insert(0, p["title"])
                prefix_entry.delete(0, "end")
                prefix_entry.insert(0, p["countdown_prefix"])
                badge_entry.delete(0, "end")
                badge_entry.insert(0, p["badge"])
                day_menu.set(f"{int(p['day']):02d}")
                m_idx = int(p["month"])
                month_menu.set(f"{m_idx:02d} - {TR_MONTH_NAMES[m_idx]}")
                if str(p["year"]) in year_vals:
                    year_menu.set(str(p["year"]))
                time_menu.set(f"{int(p['hour']):02d}:{int(p['minute']):02d}")
            _refresh_preview()

        preset_menu.configure(command=_on_preset_selected)
        day_menu.configure(command=_refresh_preview)
        month_menu.configure(command=_refresh_preview)
        year_menu.configure(command=_refresh_preview)
        time_menu.configure(command=_refresh_preview)
        title_entry.bind("<KeyRelease>", _refresh_preview)

        # Mevcut şablonu seçili göster
        cur_p_id = cd.get("preset_id", "yks_2027")
        for p in presets:
            if p["id"] == cur_p_id:
                preset_menu.set(p["title"])
                break
        _refresh_preview()

        # 5. ALT KAYDET / VAZGEÇ BUTONLARI
        btn_bar = ctk.CTkFrame(win, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=(0, 18))
        btn_bar.grid_columnconfigure(0, weight=1)
        btn_bar.grid_columnconfigure(1, weight=2)

        def _on_save_lock():
            dt = _build_selected_datetime()
            t_title = title_entry.get().strip() or "Özel Odak Hedefi"
            t_prefix = prefix_entry.get().strip() or "Hedef Kilidi"
            t_badge = badge_entry.get().strip() or "ODAK"

            ok, msg = self.engine.update_lock_target(
                new_unlock_dt=dt,
                target_title=t_title,
                countdown_prefix=t_prefix,
                target_badge=t_badge,
                preset_id=selected_preset_state["id"],
            )
            if not ok:
                preview_lbl.configure(text=msg, text_color=ACCENT_ROSE)
                return

            self._last_tyt_sig = None
            self.feedback_label.configure(text=msg, text_color=ACCENT_EMERALD_TEXT)
            self._switch_active_view(force_rebuild=True)
            self._refresh_status()
            _on_close()

        ctk.CTkButton(
            btn_bar,
            text="Vazgeç",
            font=self._font(13, "bold"),
            fg_color=BG_ELEVATED,
            hover_color=BG_ELEVATED_HOVER,
            text_color=TEXT_PRIMARY,
            height=42,
            corner_radius=10,
            border_width=0,
            command=_on_close
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            btn_bar,
            text="Hedefi Kaydet ve Kilidi Uygula",
            font=self._font(13, "bold"),
            fg_color=ACCENT_EMERALD,
            hover_color="#059669",
            text_color="#052e16",
            height=42,
            corner_radius=10,
            border_width=0,
            command=_on_save_lock
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _show_reward_popup(self):
        self._switch_active_view(force_rebuild=False)
        self._refresh_status()

        if self.reward_popup_win is not None and self.reward_popup_win.winfo_exists():
            self._force_window_on_top(self.reward_popup_win, 600, 540, break_fullscreen=True)
            return

        with self.engine.lock:
            goal_sec = int(self.engine.study_goal_seconds)
            break_min = int(self.engine.reward_break_minutes)

        goal_title_tr = format_goal_short_tr(goal_sec)

        blocked_items = self.engine.get_blocked_items()
        user_picks = [it for it in blocked_items if not it.get("antigravity_pick")]
        ag_picks = [it for it in blocked_items if it.get("antigravity_pick")]

        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        pop = ctk.CTkToplevel(self)
        pop.title(f"{goal_title_tr} Ders Hedefi Tamamlandı!")
        pop.geometry("600x540")
        pop.resizable(False, False)
        pop.configure(fg_color=BG_CANVAS)
        pop.attributes("-topmost", True)
        pop.protocol("WM_DELETE_WINDOW", self._on_dismiss_reward_popup)
        pop.after(50, lambda: apply_windows_dark_titlebar(pop))

        pop.update_idletasks()
        sw = pop.winfo_screenwidth()
        sh = pop.winfo_screenheight()
        x = (sw - 600) // 2
        y = (sh - 540) // 2
        pop.geometry(f"600x540+{x}+{y}")

        self.reward_popup_win = pop

        header = ctk.CTkFrame(
            pop,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=16
        )
        header.pack(fill="x", padx=20, pady=(18, 10))

        ctk.CTkLabel(
            header,
            text=f"{goal_title_tr} Çalışma Hedefini Tamamladın!",
            font=self._font(19, "bold"),
            text_color=ACCENT_EMERALD_TEXT
        ).pack(padx=16, pady=(14, 4))

        ctk.CTkLabel(
            header,
            text=(
                f"{break_min} dakikalık ödül molası için aşağıdan istediğin bir uygulamayı veya siteyi seçebilirsin.\n"
                "Süre dolduğunda seçtiğin öğe otomatik olarak tekrar kilitlenecektir."
            ),
            font=self._font(12),
            text_color=TEXT_SECONDARY,
            justify="center"
        ).pack(padx=16, pady=(0, 14))

        popup_tab_bar = ctk.CTkFrame(pop, fg_color=BG_INPUT, corner_radius=10, border_color=BORDER_SUBTLE, border_width=1)
        popup_tab_bar.pack(fill="x", padx=20, pady=(0, 8))
        popup_tab_bar.grid_columnconfigure(0, weight=1)
        popup_tab_bar.grid_columnconfigure(1, weight=1)

        scroll = ctk.CTkScrollableFrame(
            pop,
            fg_color=BG_SURFACE,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=14
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        scroll.grid_columnconfigure(1, weight=1)

        pop_tab_btns = {}

        def _render_popup_tab(selected_tab: str):
            for k_tab, k_btn in pop_tab_btns.items():
                if k_tab == selected_tab:
                    k_btn.configure(fg_color=ACCENT_WHITE, text_color=BG_CANVAS, hover_color="#e4e4e7")
                else:
                    k_btn.configure(fg_color="transparent", text_color=TEXT_SECONDARY, hover_color=BG_ELEVATED)

            for w in scroll.winfo_children():
                w.destroy()

            target_list = user_picks if selected_tab == "Senin Seçtiklerin" else ag_picks
            if not target_list:
                empty_txt = (
                    "Kilitlediğin herhangi bir uygulama veya site bulunmuyor.\n"
                    "Üstteki 'Antigravity'nin Seçtikleri' sekmesinden seçim yapabilirsin."
                    if selected_tab == "Senin Seçtiklerin"
                    else "Antigravity'nin seçtiği kilitli bir site bulunmuyor."
                )
                ctk.CTkLabel(
                    scroll,
                    text=empty_txt,
                    font=self._font(13),
                    text_color=TEXT_SECONDARY,
                    justify="center",
                    pady=45
                ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=20)
                return

            for idx, item in enumerate(target_list):
                row_card = ctk.CTkFrame(
                    scroll,
                    fg_color=BG_CARD,
                    border_color=BORDER_SUBTLE,
                    border_width=1,
                    corner_radius=12
                )
                row_card.grid(row=idx, column=0, columnspan=2, sticky="ew", padx=6, pady=4)
                row_card.grid_columnconfigure(1, weight=1)

                ctk_img = self._get_ctk_icon(item.get("icon_png", ""))
                if ctk_img:
                    ctk.CTkLabel(row_card, text="", image=ctk_img, width=30).grid(row=0, column=0, padx=(12, 8), pady=10)
                else:
                    ctk.CTkLabel(row_card, text="●", font=self._font(16), text_color=ACCENT_INDIGO, width=30).grid(
                        row=0, column=0, padx=(12, 8), pady=10
                    )

                disp = item["name"]
                linked_ids = self.engine._find_linked_break_ids(item["id"])
                if linked_ids:
                    disp = f"{disp} (Uygulama + Site Birlikte Açılır)"
                if len(disp) > 46:
                    disp = disp[:44] + "…"

                ctk.CTkLabel(
                    row_card,
                    text=disp,
                    font=self._font(13, "bold"),
                    text_color=TEXT_PRIMARY,
                    anchor="w"
                ).grid(row=0, column=1, sticky="w", pady=10)

                ctk.CTkButton(
                    row_card,
                    text=f"{break_min} Dk Mola Başlat",
                    font=self._font(12, "bold"),
                    fg_color=ACCENT_EMERALD,
                    hover_color="#059669",
                    text_color="#ffffff",
                    width=155,
                    height=32,
                    corner_radius=10,
                    command=lambda i_id=item["id"]: self._on_claim_reward_item(i_id)
                ).grid(row=0, column=2, padx=12, pady=10)

        for col_i, tab_lbl in enumerate(["Senin Seçtiklerin", "Antigravity'nin Seçtikleri"]):
            tb = ctk.CTkButton(
                popup_tab_bar,
                text=tab_lbl,
                font=self._font(12, "bold"),
                fg_color="transparent",
                height=32,
                corner_radius=8,
                command=lambda tl=tab_lbl: _render_popup_tab(tl)
            )
            tb.grid(row=0, column=col_i, sticky="ew", padx=3, pady=3)
            pop_tab_btns[tab_lbl] = tb

        _render_popup_tab("Senin Seçtiklerin")

        ctk.CTkButton(
            pop,
            text="Molaya Gerek Yok, Sayacı Sıfırla ve Çalışmaya Devam Et",
            font=self._font(12, "bold"),
            fg_color=BG_ELEVATED,
            hover_color=BG_ELEVATED_HOVER,
            text_color=TEXT_PRIMARY,
            height=36,
            corner_radius=10,
            command=self._on_dismiss_reward_popup
        ).pack(fill="x", padx=20, pady=(0, 18))

        self._force_window_on_top(pop, 600, 540, break_fullscreen=True)
        pop.after(250, lambda: self._force_window_on_top(pop, 600, 540, break_fullscreen=False) if pop.winfo_exists() else None)
        pop.after(600, lambda: self._force_window_on_top(pop, 600, 540, break_fullscreen=False) if pop.winfo_exists() else None)

    def _on_claim_reward_item(self, item_id: str):
        item_name = self.engine.items.get(item_id, {}).get("name", item_id)
        break_min = int(getattr(self.engine, "reward_break_minutes", 10))
        self.engine.claim_reward_break(item_id)
        self._ui_dirty = False
        if self.reward_popup_win is not None and self.reward_popup_win.winfo_exists():
            self.reward_popup_win.destroy()
        self.reward_popup_win = None
        self.feedback_label.configure(
            text=f"☕ {break_min} dakikalık ödül molası başladı: '{item_name}' şu an açık. Süre bitiminde otomatik kilitlenecek.",
            text_color=ACCENT_EMERALD_TEXT
        )
        self._switch_active_view(force_rebuild=False)
        self._refresh_status()

    def _on_dismiss_reward_popup(self):
        self.engine.dismiss_reward_without_break()
        self._ui_dirty = False
        if self.reward_popup_win is not None and self.reward_popup_win.winfo_exists():
            self.reward_popup_win.destroy()
        self.reward_popup_win = None
        self._switch_active_view(force_rebuild=False)
        self._refresh_status()

    # ==================================================================
    # OLAYLAR VE CANLI GÜNCELLEMELER
    # ==================================================================
    def _on_entry_key_release(self, _event=None):
        val = self.cmd_entry.get()
        if any(ch in val for ch in "ýÝðÐþÞ"):
            cursor_pos = self.cmd_entry.index("insert")
            fixed = (
                val.replace("ý", "ı")
                .replace("Ý", "İ")
                .replace("ð", "ğ")
                .replace("Ð", "Ğ")
                .replace("þ", "ş")
                .replace("Þ", "Ş")
            )
            self.cmd_entry.delete(0, "end")
            self.cmd_entry.insert(0, fixed)
            try:
                self.cmd_entry.icursor(cursor_pos)
            except Exception:
                pass

    def _on_search_changed(self, _event=None):
        val = self.search_entry.get()
        if any(ch in val for ch in "ýÝðÐþÞ"):
            val = (
                val.replace("ý", "ı")
                .replace("Ý", "İ")
                .replace("ð", "ğ")
                .replace("Ð", "Ğ")
                .replace("þ", "ş")
                .replace("Þ", "Ş")
            )
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, val)
        new_q = val.strip()
        if new_q != self.search_query:
            self.search_query = new_q
            if self.current_tab == "🌐 Kaynak Siteler":
                self._sync_sources_view()
            elif self.current_tab != "📊 Ders Sürelerim":
                self._refresh_items_view(force_rebuild=False)

    def _execute_command(self):
        text = self.cmd_entry.get().strip()
        if not text:
            return
        res = self.parser.execute_command(text)
        self._ui_dirty = False
        self.cmd_entry.delete(0, "end")
        self.feedback_label.configure(
            text=res["message"],
            text_color=ACCENT_EMERALD_TEXT if res["success"] else ACCENT_ROSE
        )
        self._switch_active_view(force_rebuild=False)
        self._refresh_status()

    def _lock_item_strictly(self, item_id: str):
        self.engine.set_item_blocked(item_id, True)
        self._ui_dirty = False
        item = self.engine.items.get(item_id, {})
        name = item.get("name", item_id)
        cd = self.engine.get_tyt_countdown()
        self.feedback_label.configure(
            text=f"🔒 {name} TYT'den 1 gün öncesine ({cd['unlock_date_str']}) kadar kilitlendi! Kalan: {cd['formatted_short']}",
            text_color=ACCENT_ROSE
        )
        self._switch_active_view(force_rebuild=False)
        self._refresh_status()

    def _unlock_item_after_tyt(self, item_id: str):
        if not self.engine.is_tyt_unlocked():
            return
        self.engine.set_item_blocked(item_id, False)
        self._ui_dirty = False
        item = self.engine.items.get(item_id, {})
        name = item.get("name", item_id)
        self.feedback_label.configure(
            text=f"🔓 {name} kilidi kaldırıldı.",
            text_color=ACCENT_EMERALD_TEXT
        )
        self._switch_active_view(force_rebuild=False)
        self._refresh_status()

    def _block_running_exe(self, exe_name: str):
        self.engine.add_custom_item(exe_name, block_immediately=True)
        self._ui_dirty = False
        self.feedback_label.configure(text=f"🔒 {exe_name} kilitlendi ve kapatıldı.", text_color=ACCENT_ROSE)
        self._switch_active_view(force_rebuild=True)
        self._refresh_status()

    def _on_tab_changed(self, val: str):
        if self.current_tab == val:
            return
        self.current_tab = val
        self._update_nav_tab_styles()
        self._switch_active_view(force_rebuild=False)

    def _schedule_ui_refresh(self):
        self._ui_dirty = True

    def _refresh_status(self):
        blocked = self.engine.get_blocked_items()
        if not blocked:
            self.status_label.configure(text="● Her şey açık ve normal çalışıyor", text_color=ACCENT_EMERALD_TEXT)
        else:
            short_names = []
            for x in blocked[:2]:
                clean_n = x["name"].split("(")[0].strip()
                short_names.append(clean_n)
            names = ", ".join(short_names)
            if len(blocked) > 2:
                names += f" +{len(blocked) - 2}"
            self.status_label.configure(text=f"● {len(blocked)} öğe kilitli ({names})", text_color="#fb7185")

    def _tick(self):
        if getattr(self, "_pending_initial_hide", False):
            self._pending_initial_hide = False
            self._minimize_to_tray()

        if os.path.exists(SHOW_SIGNAL_FILE):
            try:
                os.remove(SHOW_SIGNAL_FILE)
            except Exception:
                pass
            self._restore_from_tray()

        if self._ui_dirty:
            self._ui_dirty = False
            self._switch_active_view(force_rebuild=False)
            self._refresh_status()
        elif self.current_tab == "📊 Ders Sürelerim":
            # Ders Sürelerim sekmesi açıksa canlı sayaçları sıfır titremeyle güncelle
            self._sync_subject_stats_view(focus_stopped_entry=False)

        # Kilit Açılış Geri Sayım Sayacını Sadece Saniye veya Hedef Değiştiğinde Güncelle
        cd = self.engine.get_tyt_countdown()
        tyt_sig = (
            cd["unlocked"],
            cd["days"],
            cd["hours"],
            cd["minutes"],
            cd["seconds"],
            cd.get("countdown_prefix", "TYT Kilidi"),
            cd.get("target_badge", "YKS 2027"),
            cd.get("unlock_date_short", "18 Haz 2027"),
        )
        if getattr(self, "_last_tyt_sig", None) != tyt_sig:
            self._last_tyt_sig = tyt_sig
            prefix_lbl = cd.get("countdown_prefix", "TYT Kilidi")
            short_dt = cd.get("unlock_date_short", "18 Haz 2027")
            badge_txt = cd.get("target_badge", "YKS 2027")
            self.header_badge_btn.configure(text=badge_txt)
            if cd["unlocked"]:
                self.tyt_info_label.configure(
                    text=f"{short_dt} • Süre Doldu (Yeni Hedef Seçmek İçin Sağ Üstteki Sayaca Tıklayın)",
                    text_color=ACCENT_EMERALD_TEXT
                )
                self.tyt_countdown_label.configure(
                    text=f"🔓 {prefix_lbl} Açıldı — Yeni Hedef Seç  ▾",
                    text_color=ACCENT_EMERALD_TEXT
                )
            else:
                self.tyt_info_label.configure(
                    text=f"Kilit Açılışı: {short_dt} • Silinemezlik Aktif",
                    text_color=TEXT_MUTED
                )
                self.tyt_countdown_label.configure(
                    text=f"🔒 {prefix_lbl}: {cd['days']:02d}G {cd['hours']:02d}S {cd['minutes']:02d}D {cd['seconds']:02d}Sn  ▾",
                    text_color=ACCENT_CYAN
                )

        # Üst Bardaki Haftalık Acil Durum Butonu Durumunu Sadece Değiştiğinde Güncelle
        em = self.engine.get_emergency_status()
        em_sig = (em["active"], em["rem_active_sec"], em["can_use"], em["cooldown_rem_sec"] // 3600)
        if getattr(self, "_last_em_sig", None) != em_sig:
            self._last_em_sig = em_sig
            if em["active"]:
                em_m, em_s = divmod(em["rem_active_sec"], 60)
                self.emergency_btn.configure(
                    text=f"Acil Durum Açık ({em_m:02d}:{em_s:02d})",
                    fg_color=ACCENT_AMBER,
                    hover_color="#d97706",
                    text_color="#09090b",
                    state="normal"
                )
            elif not em["can_use"]:
                rem_c = em["cooldown_rem_sec"]
                c_days = rem_c // 86400
                c_hrs = (rem_c % 86400) // 3600
                self.emergency_btn.configure(
                    text=f"Acil Durum ({c_days}g {c_hrs}s sonra)",
                    fg_color=BG_SURFACE,
                    text_color_disabled=TEXT_MUTED,
                    border_color=BORDER_SUBTLE,
                    state="disabled"
                )
            else:
                self.emergency_btn.configure(
                    text="Acil Durum (30 Dk)",
                    fg_color="#281117",
                    hover_color="#3b1620",
                    text_color="#fb7185",
                    border_color="#591c2b",
                    state="normal"
                )

        # Mola Barajı Ders Sayacı ve Ödül Pop-up Kontrolü
        with self.engine.lock:
            watched = int(self.engine.study_watched_seconds)
            goal = int(self.engine.study_goal_seconds)
            break_mins = int(self.engine.reward_break_minutes)
            break_dur_sec = int(self.engine.reward_break_duration_sec)
            vid_title = self.engine.current_study_video
            subj_id = self.engine.current_study_subject_id
            counting = self.engine.is_study_counting
            man_active = self.engine.manual_study_active
            man_subj = self.engine.manual_study_subject_id
            reward_ready = self.engine.reward_available
            popup_already_shown = self.engine.reward_popup_shown
            rb_id = self.engine.reward_break_item_id
            rb_end = self.engine.reward_break_end_ts

        # Alt bardaki Manuel Sayaç Durdur butonunu sadece durum değiştiğinde göster/gizle
        if getattr(self, "_last_man_btn_shown", None) != bool(man_active):
            self._last_man_btn_shown = bool(man_active)
            if man_active:
                self.bottom_manual_stop_btn.grid(row=0, column=2, padx=(0, 8), pady=(10, 4), sticky="e")
            else:
                self.bottom_manual_stop_btn.grid_forget()

        now = time.time()
        rem_break = max(0, int(rb_end - now)) if (rb_id and rb_end > now) else 0
        bottom_sig = (
            bool(rb_id and rem_break > 0),
            rem_break,
            watched,
            goal,
            break_mins,
            break_dur_sec,
            vid_title,
            subj_id,
            counting,
            man_active,
            man_subj,
            reward_ready,
        )
        if getattr(self, "_last_bottom_sig", None) != bottom_sig:
            self._last_bottom_sig = bottom_sig
            if rb_id and rem_break > 0:
                bm, bs = divmod(rem_break, 60)
                b_name = self.engine.items.get(rb_id, {}).get("name", rb_id)
                self.study_time_label.configure(
                    text=f"{break_mins} Dk Ödül Molası: {bm:02d}:{bs:02d} kaldı",
                    text_color=ACCENT_EMERALD_TEXT
                )
                self.study_video_label.configure(
                    text=f"'{b_name}' mola için açık — Süre bitince otomatik kilitlenecek",
                    text_color=ACCENT_EMERALD_TEXT
                )
                self.study_progress.set(rem_break / float(max(1, break_dur_sec)))
            else:
                hrs, rem = divmod(watched, 3600)
                mins, secs = divmod(rem, 60)
                self.study_time_label.configure(
                    text=f"Mola Barajı: {hrs:02d}s {mins:02d}dk {secs:02d}sn / {format_goal_bar_target(goal)}  •  Mola: {break_mins} Dk",
                    text_color=TEXT_PRIMARY
                )
                self.study_progress.set(min(1.0, watched / max(1, goal)))

                if reward_ready:
                    goal_short = format_goal_short_tr(goal)
                    self.study_video_label.configure(
                        text=f"{goal_short} Hedef Doldu! Tüm Sayaçlar Durduruldu — {break_mins} Dk Mola Seçimi Bekleniyor",
                        text_color=ACCENT_EMERALD_TEXT
                    )
                elif man_active and man_subj:
                    s_info = get_subject_info(man_subj)
                    self.study_video_label.configure(
                        text=f"● Manuel Sayaç İşliyor [{s_info['name']}] — Bitirdiğinde soru sayısını girebilirsin",
                        text_color=ACCENT_EMERALD_TEXT
                    )
                elif vid_title:
                    if vid_title.startswith("🚫"):
                        self.study_video_label.configure(
                            text=vid_title,
                            text_color=ACCENT_ROSE
                        )
                    else:
                        subj_info = get_subject_info(subj_id) if subj_id else None
                        subj_badge = f"[{subj_info['name']}] " if subj_info else ""
                        if counting:
                            self.study_video_label.configure(
                                text=f"● Ders Oynatılıyor {subj_badge}: {vid_title}",
                                text_color=ACCENT_EMERALD_TEXT
                            )
                        else:
                            self.study_video_label.configure(
                                text=f"⏸ Video Duraklatıldı (Sayaç Beklemede): {vid_title}",
                                text_color=ACCENT_AMBER
                            )
                else:
                    self.study_video_label.configure(
                        text="YouTube / Kaynak Siteler ders videosu veya Ders Sürelerim'den manuel sayaç bekleniyor",
                        text_color=TEXT_SECONDARY
                    )

        # Mola barajı dolduysa ve pop-up henüz gösterilmediyse ekrana çıkar!
        if reward_ready and not popup_already_shown:
            with self.engine.lock:
                self.engine.reward_popup_shown = True
            self._show_reward_popup()
        elif reward_ready and self.reward_popup_win is not None and self.reward_popup_win.winfo_exists():
            try:
                self.reward_popup_win.attributes("-topmost", True)
                self.reward_popup_win.lift()
            except Exception:
                pass

        self.after(180, self._tick)

    def _restart_as_admin(self):
        try:
            script_path = os.path.abspath(__file__)
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script_path}"', os.path.dirname(script_path), 1
            )
            self._quit_completely()
        except Exception:
            pass

    def _on_close_button_pressed(self):
        self._minimize_to_tray()

    def _minimize_to_tray(self):
        self.withdraw()
        if self.tray_icon is None:
            image = create_tray_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem("Odak Asistanı'nı Aç", self._restore_from_tray, default=True),
            )
            self.tray_icon = pystray.Icon("OdakAsistani", image, "Odak Asistanı (Katı Koruma Aktif)", menu)

            def _run_tray():
                try:
                    hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x01FF)
                    if hdesk:
                        ctypes.windll.user32.SetThreadDesktop(hdesk)
                except Exception:
                    pass
                self.tray_icon.run()

            threading.Thread(target=_run_tray, daemon=True).start()

    def _restore_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.after(
            0,
            lambda: (
                self.attributes("-alpha", 1.0),
                self.deiconify(),
                apply_windows_dark_titlebar(self),
                self.lift(),
                self.focus_force(),
                self._switch_active_view(force_rebuild=False),
                self._refresh_status(),
            ),
        )

    def _quit_completely(self):
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.engine.shutdown()
        self.destroy()


_MUTEX_HANDLE = None


def main():
    global _MUTEX_HANDLE
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.wintypes.HANDLE
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, "Local\\OdakAsistaniSingleInstanceMutex")
    last_err = kernel32.GetLastError()
    if last_err == 183:  # ERROR_ALREADY_EXISTS
        try:
            with open(SHOW_SIGNAL_FILE, "w", encoding="utf-8") as f:
                f.write("show")
        except Exception:
            pass
        return

    start_hidden = "--hidden" in sys.argv
    is_boot = ("--boot" in sys.argv) or start_hidden
    app = OdakAsistaniApp(start_hidden=start_hidden, reset_study_on_boot=is_boot)
    app.mainloop()


if __name__ == "__main__":
    main()
