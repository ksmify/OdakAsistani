# -*- coding: utf-8 -*-
"""
Odak Asistanı — GPU-Accelerated Native WebView2 Desktop Edition
Silicon Valley Obsidian UI (Linear / Raycast / Vercel Design System)
Full compatibility with BlockerEngine, StudyTracker, SelfDefenseEngine, and state.json.
"""

import base64
import calendar
import ctypes
from ctypes import wintypes
from datetime import datetime
import os
import sys
import threading
import time
import winreg
import winsound

try:
    _u32 = ctypes.windll.user32
    _hdesk = _u32.OpenDesktopW("Default", 0, False, 0x01FF)
    if _hdesk:
        _u32.SetThreadDesktop(_hdesk)
except Exception:
    pass

from PIL import Image, ImageDraw
import pystray
import webview

from blocker_engine import BlockerEngine, is_admin
from nlp_parser import CommandParser
from self_defense import get_lock_target_presets, TR_MONTH_NAMES, format_turkish_date_full
from study_tracker import (
    SUBJECT_DEFINITIONS,
    STUDY_GOAL_OPTIONS,
    REWARD_BREAK_OPTIONS,
    MAX_BREAK_MINUTES_BY_GOAL,
    SOURCE_CATEGORY_OPTIONS,
    get_subject_info,
    get_source_category_label,
    get_source_benefit_description,
    get_source_badge_code,
    format_goal_short_tr,
    format_goal_bar_target,
    clamp_break_minutes_for_goal,
)

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SHOW_SIGNAL_FILE = os.path.join(BASE_DIR, "show_window.signal")
UI_HTML_PATH = os.path.join(BASE_DIR, "ui_webview.html")

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

RANK_TIER_VISUALS = [
    ("#2e2e38", "#a1a1aa", "#18181e", "#18181e", "#0d0d11"),  # 0
    ("#b45309", "#fbbf24", "#26180a", "#19140e", "#120e0a"),  # 1
    ("#d97706", "#fbbf24", "#2e1d0a", "#1c1610", "#16110b"),  # 2
    ("#22c55e", "#4ade80", "#0d2b18", "#111e16", "#0b1610"),  # 3
    ("#10b981", "#34d399", "#092e22", "#0f201b", "#0a1713"),  # 4
    ("#eab308", "#facc15", "#2e2408", "#1d190c", "#141108"),  # 5
    ("#f97316", "#fb923c", "#331809", "#20130c", "#160d08"),  # 6
    ("#f43f5e", "#fb7185", "#331019", "#201015", "#160b0e"),  # 7
    ("#ef4444", "#f87171", "#361111", "#221010", "#170b0b"),  # 8
    ("#8b5cf6", "#a78bfa", "#241442", "#191328", "#120d1e"),  # 9
    ("#a855f7", "#c084fc", "#2d1245", "#1d1129", "#150c1f"),  # 10
    ("#d946ef", "#e879f9", "#36103b", "#221025", "#180b1b"),  # 11
    ("#ec4899", "#f472b6", "#381024", "#24101a", "#1a0b12"),  # 12
    ("#f59e0b", "#fde047", "#382a07", "#241d0b", "#1a1507"),  # 13
    ("#e4e4e7", "#ffffff", "#27272a", "#1f1f23", "#151518"),  # 14
    ("#10b981", "#6ee7b7", "#06382c", "#0c2620", "#081b16"),  # 15
]

# Tek bir ders için insansı ve motive edici soru rütbe barajları (16 Kademe: Başlangıç + Rütbe I..XV)
SUBJECT_RANK_THRESHOLDS_BY_PERIOD = {
    "today": [0, 5, 10, 20, 30, 40, 55, 70, 85, 100, 120, 140, 165, 190, 220, 250],
    "week": [0, 15, 35, 60, 90, 130, 175, 230, 290, 360, 440, 530, 630, 740, 860, 1000],
    "month": [0, 50, 120, 220, 350, 500, 700, 950, 1250, 1600, 2000, 2450, 2950, 3500, 4000, 4500],
    "all": [0, 50, 150, 300, 500, 800, 1200, 1700, 2300, 3000, 4000, 5200, 6600, 8200, 10000, 12000],
}

# Tüm derslerin toplamı (Genel Rütbe) için insansı soru rütbe barajları
GLOBAL_RANK_THRESHOLDS_BY_PERIOD = {
    "today": [0, 10, 25, 45, 70, 100, 135, 175, 220, 270, 325, 380, 440, 500, 550, 600],
    "week": [0, 40, 90, 160, 250, 360, 500, 660, 850, 1050, 1300, 1600, 1950, 2350, 2800, 3300],
    "month": [0, 120, 300, 550, 850, 1250, 1750, 2350, 3100, 4000, 5000, 6200, 7500, 9000, 10500, 12500],
    "all": [0, 100, 300, 600, 1000, 1800, 3000, 4500, 6500, 9000, 12000, 16000, 21000, 27000, 33000, 40000],
}

GLOBAL_RANK_TITLES = [
    "Başlangıç",
    "I • Kıvılcım Avcısı",
    "II • Bronz Savaşçı",
    "III • Yeşim Muhafız",
    "IV • Zümrüt Şövalye",
    "V • Altın Uzman",
    "VI • Kor Alevi",
    "VII • Mercan Üstat",
    "VIII • Kızıl Baron",
    "IX • Ametist Seçkin",
    "X • Destansı (Epic)",
    "XI • Fuşya Mareşal",
    "XII • Yakut Lordu",
    "XIII • Güneş İmparatoru",
    "XIV • Platin Efsane",
    "XV • YKS EFSANESİ",
]

SUBJECT_SPECIFIC_RANK_TITLES = {
    "matematik": [
        "Başlangıç", "I • Bir İki Üç", "II • Dört İşlem Çırağı", "III • Denklem Avcısı",
        "IV • Polinom Bükücü", "V • Fonksiyon Mimarı", "VI • Logaritma Kâşifi", "VII • Trigonometri Ustası",
        "VIII • Limit Fatihi", "IX • Türev Canavarı", "X • İntegral Dâhisi", "XI • Analiz Üstadı",
        "XII • Sayılar Teoricisi", "XIII • Gauss'un Mirasçısı", "XIV • Euler Seviyesi", "XV • Pisagor'un İkizi",
    ],
    "geometri": [
        "Başlangıç", "I • Nokta & Doğru", "II • Cetvel Çırağı", "III • Açı Avcısı",
        "IV • Üçgen Kâşifi", "V • Pisagor Takipçisi", "VI • Benzerlik Ustası", "VII • Dörtgen Mimarı",
        "VIII • Çokgen Stratejisti", "IX • Çember Kılavuzu", "X • Daire Büyücüsü", "XI • Katı Cisim Mühendisi",
        "XII • Analitik Hâkimi", "XIII • Uzay Geometri Lideri", "XIV • Altın Oran Üstadı", "XV • Öklid'in Aynası",
    ],
    "fizik": [
        "Başlangıç", "I • Statik Kıvılcım", "II • Vektör Çırağı", "III • Dinamik Gözlemcisi",
        "IV • Newton Yolcusu", "V • İtme & Momentum Ustası", "VI • Enerji Koruyucusu", "VII • Tork Dengesi",
        "VIII • Basınç & Akışkan Mimarı", "IX • Termodinamik Hâkimi", "X • Optik & Işık Kâşifi", "XI • Manyetizma Efendisi",
        "XII • Dalga Mekaniği Lideri", "XIII • Kuantum Meraklısı", "XIV • Görelilik Kuramcısı", "XV • Einstein'ın Zihni",
    ],
    "kimya": [
        "Başlangıç", "I • Beher Çırağı", "II • Madde Kaşifi", "III • Atom Modelcisi",
        "IV • Periyodik Tablo Avcısı", "V • Kimyasal Bağ Mimarı", "VI • Mol Hesaplayıcısı", "VII • Gaz Yasaları Ustası",
        "VIII • Çözelti Kimyageri", "IX • Termokimya Uzmanı", "X • Hız & Denge Cambazı", "XI • Asit-Baz Stratejisti",
        "XII • Elektrokimya Hâkimi", "XIII • Organik Molekül Lideri", "XIV • Reaksiyon Mimarı", "XV • Simyacı'nın Zirvesi",
    ],
    "biyoloji": [
        "Başlangıç", "I • Tek Hücreli", "II • Organel Çırağı", "III • Sitoplazma Gezgini",
        "IV • Membran Bekçisi", "V • Enzim Mühendisi", "VI • Mitoz & Mayoz Gözlemcisi", "VII • Kalıtım & Gen Avcısı",
        "VIII • Ekoloji Koruyucusu", "IX • Doku & Sistem Kâşifi", "X • Sinir Sistemi Hâkimi", "XI • Fotosentez Fabrikatörü",
        "XII • Hücresel Solunum Ustası", "XIII • Protein Sentezi Mimarı", "XIV • Evrimsel Biyolog", "XV • Yaşamın Kodu (DNA)",
    ],
    "turkce": [
        "Başlangıç", "I • Alfabeci", "II • Kelime Çırağı", "III • Hece & Ses Avcısı",
        "IV • Yazım Kuralları Bekçisi", "V • Noktalama Muhafızı", "VI • Paragraf Dedektifi", "VII • Anlam Ustası",
        "VIII • Dil Bilgisi Hâkimi", "IX • Cümle Analisti", "X • Nazım & Nesir Kâşifi", "XI • Divan & Halk Bilgesi",
        "XII • Tanzimat & Servetifünun Rehberi", "XIII • Cumhuriyet Edebiyatçısı", "XIV • Söz Sanatları Üstadı", "XV • Şair (Edebiyat Dehası)",
    ],
    "sosyal": [
        "Başlangıç", "I • Kronikçi", "II • Pusula Çırağı", "III • Harita Okuyucusu",
        "IV • İlk Çağ Gezgini", "V • İklim & Yer Bilimci", "VI • Selçuklu & Beylikler Kâşifi", "VII • Osmanlı Tarihçisi",
        "VIII • Nüfus & Göç Stratejisti", "IX • İnkılap Tarihi Muhafızı", "X • Coğrafya Hâkimi", "XI • Felsefi Düşünür",
        "XII • Mantık & Ahlak Bilgesi", "XIII • Medeniyetler Mimarı", "XIV • Tarihçi-Coğrafyacı Başyazar", "XV • Zaman & Mekân Bilgesi",
    ],
    "soru_cozum": [
        "Başlangıç", "I • Kalem Tutan", "II • Sayfa Çeviren", "III • Test Çırağı",
        "IV • Şık Avcısı", "V • Süre Taktisyeni", "VI • Hata Avcısı", "VII • Branş Denemecisi",
        "VIII • Net Avcısı", "IX • Genel Deneme Askeri", "X • Optik Form Ustası", "XI • Baraj Yıkan",
        "XII • Hız & Doğruluk Cambazı", "XIII • Derece Adayı", "XIV • Net Canavarı", "XV • YKS Şampiyonu",
    ],
}


def _get_thresholds_for(subject_id: str, period_key: str) -> list:
    if subject_id == "global":
        return GLOBAL_RANK_THRESHOLDS_BY_PERIOD.get(period_key, GLOBAL_RANK_THRESHOLDS_BY_PERIOD["all"])
    return SUBJECT_RANK_THRESHOLDS_BY_PERIOD.get(period_key, SUBJECT_RANK_THRESHOLDS_BY_PERIOD["all"])


def get_question_rank_tier(question_count: int, subject_id: str = "global", period_key: str = "all") -> dict:
    q = max(0, int(question_count))
    thresholds = _get_thresholds_for(subject_id, period_key)
    title_list = SUBJECT_SPECIFIC_RANK_TITLES.get(subject_id, GLOBAL_RANK_TITLES)

    tier_index = 0
    for idx, th in enumerate(thresholds):
        if q >= th:
            tier_index = idx
        else:
            break

    title = title_list[tier_index] if tier_index < len(title_list) else title_list[-1]
    border_c, text_c, pill_bg, card_bg, row_bg = RANK_TIER_VISUALS[tier_index]
    min_th = thresholds[tier_index]

    if tier_index < len(thresholds) - 1:
        next_th = thresholds[tier_index + 1]
        next_title = title_list[tier_index + 1]
        rem = max(0, next_th - q)
        span = max(1, next_th - min_th)
        tier_progress = min(1.0, max(0.0, (q - min_th) / float(span)))
        next_info_short = f"Hedef: {next_title} ({next_th:,} Soru • {rem:,} kaldı)".replace(",", ".")
        next_info_compact = f"Hedef: {next_title} ({rem:,} soru kaldı)".replace(",", ".")
    else:
        max_th = thresholds[-1]
        next_th = None
        tier_progress = 1.0
        next_info_short = f"MAKSİMUM RÜTBE ({max_th:,}+ SORU TAMAMLANDI!)".replace(",", ".")
        next_info_compact = "MAKSİMUM RÜTBE TAMAMLANDI!"

    return {
        "tier_index": tier_index,
        "min_q": min_th,
        "next_q": next_th,
        "tier_progress": tier_progress,
        "title": title,
        "border": border_c,
        "text": text_c,
        "pill_bg": pill_bg,
        "card_bg": card_bg,
        "row_bg": row_bg,
        "next_info_short": next_info_short,
        "next_info_compact": next_info_compact,
    }


def build_rank_ladder_list(q_count: int, subject_id: str, period_key: str) -> list:
    thresholds = _get_thresholds_for(subject_id, period_key)
    titles = SUBJECT_SPECIFIC_RANK_TITLES.get(subject_id, GLOBAL_RANK_TITLES)
    curr = get_question_rank_tier(q_count, subject_id=subject_id, period_key=period_key)
    curr_idx = curr["tier_index"]

    out = []
    for idx, th in enumerate(thresholds):
        t_title = titles[idx] if idx < len(titles) else titles[-1]
        border_c, text_c, pill_bg, card_bg, _ = RANK_TIER_VISUALS[idx]
        is_curr = (idx == curr_idx)
        is_unl = (q_count >= th)
        if is_curr:
            badge = "★ MEVCUT"
        elif is_unl:
            badge = "✓ TAMAMLANDI"
        else:
            rem = max(0, th - q_count)
            badge = f"{rem:,} kaldı".replace(",", ".")
        out.append({
            "title": t_title,
            "border": border_c,
            "text": text_c,
            "card_bg": "#1f2937" if (is_curr and idx == 0) else card_bg,
            "is_current": is_curr,
            "is_unlocked": is_unl,
            "status_badge": badge,
            "threshold_str": f"{th:,} Soru".replace(",", "."),
        })
    return out


def format_duration_tr(seconds: float) -> str:
    total = max(0, int(seconds))
    hrs, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs} sa {mins:02d} dk {secs:02d} sn"
    return f"{mins} dk {secs:02d} sn"


def get_monogram(title_str: str) -> str:
    clean = "".join(ch for ch in title_str.strip() if ch.isalnum() or ch == " ").strip()
    parts = [p for p in clean.split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    elif parts:
        return parts[0][:2].upper()
    return "OA"


def ensure_startup_registered():
    try:
        exe_path = os.path.join(BASE_DIR, "OdakAsistani.exe")
        if os.path.exists(exe_path):
            cmd = f'"{exe_path}" --boot'
        else:
            pythonw_exe = sys.executable
            if pythonw_exe.lower().endswith("python.exe"):
                pw = pythonw_exe[:-10] + "pythonw.exe"
                if os.path.exists(pw):
                    pythonw_exe = pw
            script_path = os.path.join(BASE_DIR, "main.py")
            cmd = f'"{pythonw_exe}" "{script_path}" --boot'
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        ) as key:
            winreg.SetValueEx(key, "OdakAsistani", 0, winreg.REG_SZ, cmd)
    except Exception:
        pass


def create_tray_icon_image() -> Image.Image:
    ico_path = os.path.join(BASE_DIR, "odak_icon.ico")
    if os.path.exists(ico_path):
        try:
            return Image.open(ico_path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
        except Exception:
            pass
    img = Image.new("RGBA", (64, 64), (18, 18, 22, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((14, 14, 50, 50), outline=(16, 185, 129, 255), width=4)
    return img


def bring_window_to_topmost(window=None, restore_tray_cb=None):
    """
    Restores Odak Asistanı if minimized or hidden in tray,
    bypasses Windows foreground locking, brings it to foreground
    and sets HWND_TOPMOST so it overlays fullscreen videos/apps,
    flashes the taskbar, and plays an alert sound.
    """
    if restore_tray_cb:
        try:
            restore_tray_cb()
        except Exception:
            pass

    if window:
        try:
            window.show()
            window.restore()
            window.on_top = True
        except Exception:
            pass

    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Odak Asistanı")
        if hwnd:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            user32.SetWindowPos.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint,
            ]

            SW_RESTORE = 9
            SW_SHOW = 5
            HWND_TOPMOST = ctypes.c_void_p(-1)
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_SHOWWINDOW = 0x0040
            FLAGS = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW

            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            else:
                user32.ShowWindow(hwnd, SW_SHOW)

            # Bypass LockSetForegroundWindow
            fg_hwnd = user32.GetForegroundWindow()
            fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
            cur_tid = kernel32.GetCurrentThreadId()

            attached = False
            if fg_tid != cur_tid and fg_tid != 0:
                attached = bool(user32.AttachThreadInput(cur_tid, fg_tid, True))

            try:
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, FLAGS)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
            finally:
                if attached:
                    user32.AttachThreadInput(cur_tid, fg_tid, False)

            if user32.GetForegroundWindow() != hwnd:
                VK_MENU = 0x12
                KEYEVENTF_KEYUP = 0x0002
                user32.keybd_event(VK_MENU, 0, 0, 0)
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, FLAGS)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

            user32.FlashWindow(hwnd, True)
    except Exception:
        pass


def release_window_topmost(window=None):
    """
    Releases the HWND_TOPMOST flag after the user picks a reward or dismisses the break modal,
    returning Odak Asistanı to normal desktop z-ordering.
    """
    if window:
        try:
            window.on_top = False
        except Exception:
            pass

    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Odak Asistanı")
        if hwnd:
            user32 = ctypes.windll.user32
            user32.SetWindowPos.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint,
            ]
            HWND_NOTOPMOST = ctypes.c_void_p(-2)
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_SHOWWINDOW = 0x0040
            user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    except Exception:
        pass


class OdakBridgeApi:
    def __init__(self, engine: BlockerEngine, parser: CommandParser):
        self._engine = engine
        self._parser = parser
        self._icon_b64_cache = {}
        self._window = None
        self._restore_tray_cb = None

    def _get_icon_data_uri(self, png_path: str) -> str:
        if not png_path or not os.path.exists(png_path):
            return ""
        if png_path in self._icon_b64_cache:
            return self._icon_b64_cache[png_path]
        try:
            with open(png_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            uri = f"data:image/png;base64,{b64}"
            self._icon_b64_cache[png_path] = uri
            return uri
        except Exception:
            return ""

    def get_live_snapshot(self, current_tab: str, current_period_label: str, search_query: str) -> dict:
        # Check show_window.signal
        if os.path.exists(SHOW_SIGNAL_FILE):
            try:
                os.remove(SHOW_SIGNAL_FILE)
            except Exception:
                pass
            bring_window_to_topmost(self._window, self._restore_tray_cb)
            if not self._engine.reward_available:
                release_window_topmost(self._window)

        cd = self._engine.get_tyt_countdown()
        em = self._engine.get_emergency_status()
        blocked = self._engine.get_blocked_items()

        if not blocked:
            status_text = "Her şey açık ve normal çalışıyor"
        else:
            first_name = blocked[0]["name"].split("(")[0].strip()
            if len(first_name) > 16:
                first_name = first_name[:15] + "…"
            if len(blocked) == 1:
                names = first_name
            elif len(blocked) == 2:
                second_name = blocked[1]["name"].split("(")[0].strip()
                if len(second_name) > 12:
                    second_name = second_name[:11] + "…"
                names = f"{first_name}, {second_name}"
            else:
                names = f"{first_name} +{len(blocked) - 1}"
            status_text = f"{len(blocked)} öğe kilitli ({names})"

        with self._engine.lock:
            watched = int(self._engine.study_watched_seconds)
            goal = int(self._engine.study_goal_seconds)
            break_mins = int(self._engine.reward_break_minutes)
            break_dur_sec = int(self._engine.reward_break_duration_sec)
            p_goal = self._engine.pending_study_goal_seconds
            p_break = self._engine.pending_reward_break_minutes
            vid_title = self._engine.current_study_video
            subj_id = self._engine.current_study_subject_id
            counting = self._engine.is_study_counting
            man_active = self._engine.manual_study_active
            man_subj = self._engine.manual_study_subject_id
            reward_ready = self._engine.reward_available
            popup_already_shown = self._engine.reward_popup_shown
            rb_id = self._engine.reward_break_item_id
            rb_end = self._engine.reward_break_end_ts

        now = time.time()
        rem_break = max(0, int(rb_end - now)) if (rb_id and rb_end > now) else 0
        is_trig_on = bool(self._engine.video_detection_enabled)

        p_str = f" • Sıradaki: {format_goal_short_tr(p_goal)} ({p_break} Dk)" if (p_goal and p_break) else ""

        if rb_id and rem_break > 0:
            bm, bs = divmod(rem_break, 60)
            b_name = self._engine.items.get(rb_id, {}).get("name", rb_id)
            dock_time_text = f"{break_mins} Dk Ödül Molası: {bm:02d}:{bs:02d} kaldı{p_str}"
            dock_video_text = f"'{b_name}' mola için açık — Süre bitince otomatik kilitlenecek"
            dock_video_color = "#34d399"
            dock_progress = rem_break / float(max(1, break_dur_sec))
        else:
            hrs, rem = divmod(watched, 3600)
            mins, secs = divmod(rem, 60)
            dock_time_text = f"Mola Barajı: {hrs:02d}s {mins:02d}dk {secs:02d}sn / {format_goal_bar_target(goal)} • Mola: {break_mins} Dk{p_str}"
            dock_progress = min(1.0, watched / float(max(1, goal)))

            if reward_ready:
                goal_short = format_goal_short_tr(goal)
                dock_video_text = f"{goal_short} Hedef Doldu! Tüm Sayaçlar Durduruldu — {break_mins} Dk Mola Seçimi Bekleniyor"
                dock_video_color = "#34d399"
            elif man_active and man_subj:
                s_info = get_subject_info(man_subj)
                dock_video_text = f"● Manuel Sayaç İşliyor [{s_info['name']}] — Bitirdiğinde soru sayısını girebilirsin"
                dock_video_color = "#34d399"
            elif vid_title:
                vid_disp = (vid_title[:62] + "…") if len(vid_title) > 63 else vid_title
                if vid_title.startswith("🚫"):
                    dock_video_text = vid_disp
                    dock_video_color = "#fb7185"
                else:
                    subj_info = get_subject_info(subj_id) if subj_id else None
                    subj_badge = f"[{subj_info['name']}] " if subj_info else ""
                    if counting:
                        dock_video_text = f"● Ders Oynatılıyor {subj_badge}: {vid_disp}"
                        dock_video_color = "#34d399"
                    else:
                        dock_video_text = f"⏸ Video Duraklatıldı (Sayaç Beklemede): {vid_disp}"
                        dock_video_color = "#f59e0b"
            else:
                if not is_trig_on:
                    dock_video_text = "⏸ Video algılama tetikleyicisi kapalı — Açmak için sağdaki butona basabilirsiniz"
                    dock_video_color = "#f59e0b"
                else:
                    dock_video_text = "YouTube / Kaynak Siteler ders videosu veya Ders Sürelerim'den manuel sayaç bekleniyor"
                    dock_video_color = "#a1a1aa"

        auto_open_reward = False
        if reward_ready and not popup_already_shown:
            with self._engine.lock:
                self._engine.reward_popup_shown = True
            auto_open_reward = True
            bring_window_to_topmost(self._window, self._restore_tray_cb)
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

        out = {
            "tab": current_tab,
            "blocked_count": len(blocked),
            "status_text": status_text,
            "countdown": cd,
            "emergency": em,
            "dock": {
                "time_text": dock_time_text,
                "video_text": dock_video_text,
                "video_color": dock_video_color,
                "progress": dock_progress,
                "manual_active": bool(man_active),
                "video_trigger_on": is_trig_on,
            },
            "AutoOpenRewardPopup": auto_open_reward,
            "reward_ready": bool(reward_ready),
            "daily_goal": self._engine.get_daily_goal_summary(),
            "daily_goal_should_prompt": bool(self._engine.should_show_daily_goal_modal()),
            "items": None,
            "stats": None,
            "sources": None,
            "running_apps": None,
        }

        if current_tab == "Ders Sürelerim":
            out["stats"] = self._build_stats_payload(current_period_label, goal, vid_title, subj_id, counting, man_active, man_subj)
        elif current_tab == "Kaynak Siteler":
            out["sources"] = self._build_sources_payload(search_query)
        elif current_tab == "Şu An Açık":
            out["running_apps"] = self._build_running_payload(search_query)
        else:
            out["items"] = self._build_items_payload(current_tab, search_query, cd)

        return out

    def _build_items_payload(self, tab: str, search_query: str, cd: dict) -> list:
        all_items = self._engine.get_all_items()
        q = (search_query or "").strip().lower()
        filtered = []

        for item in all_items:
            is_asistan_pick = bool(item.get("antigravity_pick") or item.get("asistan_pick"))
            if tab == "Asistan'ın Seçtikleri":
                if not is_asistan_pick:
                    continue
            else:
                if is_asistan_pick:
                    continue
                if tab == "Uygulamalarım" and not item.get("is_pc_app"):
                    continue
                elif tab == "Web Siteleri" and item.get("item_type") not in ("site", "both"):
                    continue
                elif tab == "Kapalı Olanlar" and not item.get("blocked"):
                    continue

            if q:
                if (
                    q not in item["name"].lower()
                    and q not in item.get("category", "").lower()
                    and not any(q in d.lower() for d in item.get("domains", []))
                ):
                    continue

            name_raw = item["name"]
            main_title = name_raw.split("(")[0].strip() if "(" in name_raw else name_raw
            blocked = bool(item.get("blocked"))
            sub_txt = f"Kilitli ({cd['unlock_date_short']} / {cd['formatted_short']})" if blocked else f"{item.get('category', 'Genel')} • Şu an açık"

            filtered.append({
                "id": item["id"],
                "name": main_title,
                "category": item.get("category", "Genel"),
                "blocked": blocked,
                "sub_text": sub_txt,
                "icon_data_uri": self._get_icon_data_uri(item.get("icon_png", "")),
                "monogram": get_monogram(main_title),
            })

        if tab != "Asistan'ın Seçtikleri":
            filtered.sort(key=lambda x: (not x["blocked"], x["name"].lower()))
        return filtered

    def _build_running_payload(self, search_query: str) -> list:
        running = self._engine.get_running_user_apps()
        q = (search_query or "").strip().lower()
        out = []
        for a in running:
            disp = a.get("display_name") or a.get("title") or a["exe_name"]
            if q and q not in a["exe_name"].lower() and q not in disp.lower():
                continue
            out.append({
                "exe_name": a["exe_name"],
                "title": disp,
                "source": a.get("source", "Görev Çubuğu"),
                "icon_data_uri": self._get_icon_data_uri(a.get("icon_png", "")),
                "monogram": get_monogram(disp),
            })
        return out

    def _build_stats_payload(self, period_label: str, goal: int, vid_title: str, active_vid_subj: str, counting: bool, man_active: bool, man_subj: str) -> dict:
        period_key = PERIOD_LABELS.get(period_label, "today")
        subj_times, subj_questions = self._engine.get_stats_for_period(period_key)
        total_sec = sum(subj_times.values())
        total_q = sum(subj_questions.values())

        best_subj_id, best_sec = None, 0.0
        for sid, sec in subj_times.items():
            if sec > best_sec:
                best_sec = sec
                best_subj_id = sid

        if best_subj_id and best_sec > 0:
            bs_info = get_subject_info(best_subj_id)
            share_pct = int(round((best_sec / max(1.0, total_sec)) * 100))
            top_name = bs_info["name"]
            top_sub = f"{format_duration_tr(best_sec)} (Toplam sürenin %{share_pct}'i)"
        else:
            top_name = "Henüz Kayıt Yok"
            top_sub = "Video izlediğinizde veya sayaç açtığınızda işlenir"

        global_rank = get_question_rank_tier(total_q, subject_id="global", period_key=period_key)
        max_s = max(1.0, max(subj_times.values(), default=1.0))

        subjects_out = []
        for s_def in SUBJECT_DEFINITIONS:
            sid = s_def["id"]
            s_sec = float(subj_times.get(sid, 0.0))
            q_cnt = int(subj_questions.get(sid, 0))
            is_vid_here = bool(counting and active_vid_subj == sid and not man_active)
            is_man_here = bool(man_active and man_subj == sid)
            s_rank = get_question_rank_tier(q_cnt, subject_id=sid, period_key=period_key)

            if is_man_here:
                st_txt = "● Manuel Sayaç İşliyor (Mola barajına dahil)"
                st_col = "#f59e0b"
            elif is_vid_here:
                st_txt = f"● Video Algılandı: {(vid_title or '')[:36]}"
                st_col = "#34d399"
            else:
                st_txt = s_rank["next_info_compact"]
                st_col = s_rank["text"] if q_cnt > 0 else "#71717a"

            subjects_out.append({
                "id": sid,
                "code": SUBJECT_BADGE_CODES.get(sid, sid[:3].upper()),
                "name": s_def["name"],
                "color": s_def["color"],
                "badge_bg": "#14141c",
                "time_seconds": s_sec,
                "time_str": format_duration_tr(s_sec),
                "questions": q_cnt,
                "share_ratio": min(1.0, s_sec / max_s) if s_sec > 0 else 0.0,
                "is_active": is_man_here or is_vid_here,
                "is_manual_active": is_man_here,
                "needs_question_input": bool(self._engine.last_stopped_manual_subject_id == sid),
                "status_text": st_txt,
                "status_color": st_col,
                "rank": s_rank,
                "ladder": build_rank_ladder_list(q_cnt, sid, period_key),
            })

        return {
            "total_time_str": format_duration_tr(total_sec),
            "time_progress": min(1.0, total_sec / float(max(1, goal))),
            "time_sub": f"Mola Barajı Hedefi: {format_goal_bar_target(goal)}",
            "total_q_str": f"{total_q:,} Soru".replace(",", "."),
            "global_rank": global_rank,
            "global_ladder": build_rank_ladder_list(total_q, "global", period_key),
            "top_subject_name": top_name,
            "top_subject_sub": top_sub,
            "subjects": subjects_out,
        }

    def _build_sources_payload(self, search_query: str) -> dict:
        sources = self._engine.get_study_sources()
        ranking = self._engine.get_source_study_ranking()
        total_sec = sum(float(x.get("total_seconds", 0.0)) for x in ranking)
        q = (search_query or "").strip().lower()

        cats = [
            {"id": (o["id"] if isinstance(o, dict) else o[1]), "label": (o["label"] if isinstance(o, dict) else o[0])}
            for o in SOURCE_CATEGORY_OPTIONS
        ]

        rows = []
        for item in ranking:
            sec = float(item.get("total_seconds", 0.0))
            pct = int(round(float(item.get("overall_percent", 0.0))))
            rows.append({
                "name": item.get("name", ""),
                "domain": item.get("badge", ""),
                "seconds": sec,
                "time_str": format_duration_tr(sec),
                "pct": pct,
                "is_youtube": item.get("id") == "youtube_default",
            })

        src_list = []
        for s in sources:
            if q and q not in s.get("name", "").lower() and q not in s.get("domain", "").lower():
                continue
            src_list.append({
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "domain": s.get("domain", ""),
                "subject_id": s.get("subject_id", "soru_cozum"),
                "locked": bool(s.get("locked", False)),
                "badge": get_source_badge_code(s),
                "benefit": get_source_benefit_description(s),
            })

        return {
            "categories": cats,
            "summary_text": f"Toplam Kaynak Video Süresi: {format_duration_tr(total_sec)} ({len(ranking)} kaynak)",
            "stats_rows": rows,
            "list": src_list,
        }

    def execute_command(self, text: str) -> dict:
        return self._parser.execute_command(text)

    def lock_item(self, item_id: str) -> dict:
        self._engine.set_item_blocked(item_id, True)
        item = self._engine.items.get(item_id, {})
        name = item.get("name", item_id)
        cd = self._engine.get_tyt_countdown()
        return {"ok": True, "message": f"{name} hedef tarihe ({cd['unlock_date_str']}) kadar kilitlendi!"}

    def unlock_item(self, item_id: str) -> dict:
        if not self._engine.is_tyt_unlocked():
            return {"ok": False, "message": "Kilit süresi henüz dolmadı!"}
        self._engine.set_item_blocked(item_id, False)
        item = self._engine.items.get(item_id, {})
        return {"ok": True, "message": f"{item.get('name', item_id)} kilidi kaldırıldı."}

    def block_running_exe(self, exe_name: str) -> dict:
        self._engine.add_custom_item(exe_name, block_immediately=True)
        return {"ok": True, "message": f"{exe_name} kilitlendi ve kapatıldı."}

    def toggle_manual_study(self, subject_id: str) -> dict:
        subj_info = get_subject_info(subject_id)
        started = self._engine.toggle_manual_study(subject_id)
        if started:
            return {"started": True, "message": f"{subj_info['name']} için manuel çalışma sayacı başlatıldı!"}
        return {"started": False, "message": f"{subj_info['name']} çalışması tamamlandı! Soru sayısını girebilirsiniz."}

    def stop_manual_study(self) -> dict:
        stopped_subj_id = self._engine.manual_study_subject_id
        self._engine.stop_manual_study()
        if stopped_subj_id:
            s_info = get_subject_info(stopped_subj_id)
            return {"ok": True, "message": f"{s_info['name']} çalışması tamamlandı! Soru sayısını girebilirsiniz."}
        return {"ok": True, "message": "Manuel çalışma sayacı durduruldu."}

    def add_questions(self, subject_id: str, raw_val: str, period_label: str) -> dict:
        cleaned = str(raw_val).lstrip("+").strip()
        if not cleaned.isdigit():
            return {"ok": False, "message": "Lütfen geçerli bir sayı girin.", "color": "#fb7185"}
        count = int(cleaned)
        period_key = PERIOD_LABELS.get(period_label, "today")
        _, prev_subj_q = self._engine.get_stats_for_period(period_key)
        prev_q = int(prev_subj_q.get(subject_id, 0))
        prev_rank = get_question_rank_tier(prev_q, subject_id=subject_id, period_key=period_key)

        new_total = self._engine.add_solved_questions(subject_id, count)
        with self._engine.lock:
            if self._engine.last_stopped_manual_subject_id == subject_id:
                self._engine.last_stopped_manual_subject_id = ""
        _, new_subj_q = self._engine.get_stats_for_period(period_key)
        new_q = int(new_subj_q.get(subject_id, 0))
        new_rank = get_question_rank_tier(new_q, subject_id=subject_id, period_key=period_key)
        subj_info = get_subject_info(subject_id)

        if count == 0:
            return {
                "ok": True,
                "message": f"{subj_info['name']}: Soru çözülmedi (Konu çalışması) olarak kaydedildi. Toplam: {new_total} Soru.",
                "color": "#a1a1aa",
            }
        if new_rank["tier_index"] > prev_rank["tier_index"]:
            return {
                "ok": True,
                "message": f"RÜTBE ATLADIN! {subj_info['name']} dersi [{new_rank['title']}] rütbesine yükseldi! (+{count} soru)",
                "color": new_rank["text"],
            }
        return {
            "ok": True,
            "message": f"{subj_info['name']}: +{count} soru eklendi! ({new_rank['title']} • {new_rank['next_info_compact']})",
            "color": new_rank["text"],
        }

    def add_study_source(self, raw_url: str, subject_id: str) -> dict:
        src_obj, msg = self._engine.add_study_source(raw_url, subject_id)
        return {"ok": bool(src_obj), "message": msg}

    def update_study_source_category(self, source_id: str, subject_id: str) -> dict:
        ok, msg = self._engine.update_study_source_category(source_id, subject_id)
        return {"ok": ok, "message": msg}

    def remove_study_source(self, source_id: str) -> dict:
        ok, msg = self._engine.remove_study_source(source_id)
        return {"ok": ok, "message": msg}

    def trigger_emergency_unlock(self) -> dict:
        ok, msg = self._engine.trigger_emergency_unlock()
        return {"ok": ok, "message": msg}

    def toggle_video_trigger(self) -> dict:
        new_state = self._engine.toggle_video_detection()
        msg = (
            "Video algılama tetikleyicisi açıldı. Ders videoları otomatik algılanacak."
            if new_state
            else "Video algılama tetikleyicisi kapatıldı. Ders videoları sayacı tetiklemeyecek."
        )
        return {"enabled": new_state, "message": msg}

    def get_break_settings_data(self) -> dict:
        with self._engine.lock:
            cur_goal = int(self._engine.study_goal_seconds)
            cur_break = clamp_break_minutes_for_goal(cur_goal, int(self._engine.reward_break_minutes))
            watched = float(self._engine.study_watched_seconds)
            now = time.time()
            in_break = bool(self._engine.reward_break_item_id and now < self._engine.reward_break_end_ts)
            is_cycle_active = (watched > 0.0) or bool(self._engine.reward_available) or in_break

            p_goal = self._engine.pending_study_goal_seconds
            p_break = self._engine.pending_reward_break_minutes
            has_pending = bool(p_goal and p_break)

        return {
            "cur_goal": cur_goal,
            "cur_break": cur_break,
            "cur_goal_str": format_goal_short_tr(cur_goal),
            "watched": watched,
            "is_cycle_active": is_cycle_active,
            "has_pending": has_pending,
            "pending_goal": p_goal,
            "pending_break": p_break,
            "pending_goal_str": format_goal_short_tr(p_goal) if p_goal else "",
            "goal_options": STUDY_GOAL_OPTIONS,
            "break_options": REWARD_BREAK_OPTIONS,
            "max_break_by_goal": {str(k): v for k, v in MAX_BREAK_MINUTES_BY_GOAL.items()},
        }

    def cancel_pending_break_settings(self) -> dict:
        self._engine.cancel_pending_break_settings()
        return {"ok": True, "message": "Sıradaki mola barajı hedefi iptal edildi."}

    def save_break_settings(self, goal_sec: int, break_min: int) -> dict:
        clamped_break = clamp_break_minutes_for_goal(int(goal_sec), int(break_min))
        res = self._engine.update_break_bar_settings(int(goal_sec), int(clamped_break))
        if res.get("queued", False):
            goal_lbl = format_goal_short_tr(res.get("pending_goal_sec", goal_sec))
            brk_min = res.get("pending_break_minutes", clamped_break)
            return {
                "ok": True,
                "queued": True,
                "message": f"Sıradaki ders-mola aralığı: {goal_lbl} - {brk_min} Dakika olarak sıraya alındı! Mevcut mola ders aralığı bittikten sonra aktifleşecek.",
            }
        else:
            goal_lbl = format_goal_short_tr(res.get("new_goal_sec", goal_sec))
            brk_min = res.get("break_minutes", clamped_break)
            return {"ok": True, "queued": False, "message": f"Mola Barajı güncellendi: Hedef {goal_lbl}, Mola {brk_min} Dakika."}

    def get_daily_goal_data(self) -> dict:
        return self._engine.get_daily_goal_summary()

    def set_daily_goal(self, goal_count: int) -> dict:
        try:
            val = int(goal_count)
        except Exception:
            val = 30
        return self._engine.set_daily_question_goal(val)

    def skip_daily_goal(self) -> dict:
        return self._engine.skip_daily_question_goal()

    def get_lock_modal_data(self) -> dict:
        cd = self._engine.get_tyt_countdown()
        presets = get_lock_target_presets()
        is_strict = bool(cd.get("committed", True) and not cd.get("unlocked", False))
        strict_msg = (
            f"Katı Koruma Aktif: Mevcut kilit tarihi ({cd['unlock_date_str']}) dolmadan bitiş tarihini erkene çekemezsiniz. Tarihi yalnızca ileriye uzatabilirsiniz."
            if is_strict
            else "Yeni Kilit Hedefi Seçime Açık: Hazır sınav şablonlarından birini veya özel tarihinizi belirleyebilirsiniz."
        )
        cur_yr = datetime.now().year
        return {
            "cd": cd,
            "presets": presets,
            "strict_msg": strict_msg,
            "months": [{"num": m, "label": f"{m:02d} - {TR_MONTH_NAMES[m]}"} for m in range(1, 13)],
            "years": [y for y in range(cur_yr, cur_yr + 10)],
        }

    def _parse_lock_payload_dt(self, payload: dict) -> datetime:
        y = int(payload.get("year", 2027))
        m = int(payload.get("month", 6))
        d = int(payload.get("day", 18))
        hm = str(payload.get("time", "00:00")).split(":")
        hr, mn = int(hm[0]), int(hm[1])
        max_d = calendar.monthrange(y, m)[1]
        return datetime(y, m, min(d, max_d), hr, mn, 0)

    def preview_lock_target(self, payload: dict) -> dict:
        dt = self._parse_lock_payload_dt(payload)
        cd = self._engine.get_tyt_countdown()
        is_strict = bool(cd.get("committed", True) and not cd.get("unlocked", False))
        now_ts = self._engine.self_defense.get_verified_timestamp()
        cur_ts = float(cd.get("unlock_timestamp", 0.0))
        new_ts = dt.timestamp()
        diff_sec = int(new_ts - now_ts)
        d_cnt = max(0, diff_sec // 86400)
        h_cnt = max(0, (diff_sec % 86400) // 3600)
        t_name = str(payload.get("title", "")).strip() or "Özel Odak Hedefi"

        if diff_sec <= 60:
            return {"ok": False, "text": f"Seçilen Tarih Geçmişte: {format_turkish_date_full(dt)} — Lütfen gelecekte bir tarih seçin."}
        if is_strict and new_ts < (cur_ts - 60):
            return {"ok": False, "text": f"Katı Koruma Engeli: Seçilen tarih ({format_turkish_date_full(dt)}) mevcut kilit tarihinden ({cd['unlock_date_str']}) daha erken!"}
        return {"ok": True, "text": f"Seçilen Hedef: {t_name} • Kilit Açılışı: {format_turkish_date_full(dt)} ({d_cnt} Gün {h_cnt} Saat koruma)"}

    def save_lock_target(self, payload: dict) -> dict:
        dt = self._parse_lock_payload_dt(payload)
        ok, msg = self._engine.update_lock_target(
            new_unlock_dt=dt,
            target_title=str(payload.get("title", "")).strip() or "Özel Odak Hedefi",
            countdown_prefix=str(payload.get("prefix", "")).strip() or "Hedef Kilidi",
            target_badge=str(payload.get("badge", "")).strip() or "ODAK",
            preset_id=str(payload.get("preset_id", "yks_2027")),
        )
        return {"ok": ok, "message": msg}

    def get_reward_modal_data(self) -> dict:
        with self._engine.lock:
            goal_sec = int(self._engine.study_goal_seconds)
            break_min = int(self._engine.reward_break_minutes)
        blocked_items = self._engine.get_blocked_items()
        user_picks, ag_picks = [], []
        for it in blocked_items:
            entry = {
                "id": it["id"],
                "name": it["name"],
                "icon_data_uri": self._get_icon_data_uri(it.get("icon_png", "")),
                "monogram": get_monogram(it["name"]),
            }
            if it.get("antigravity_pick") or it.get("asistan_pick"):
                ag_picks.append(entry)
            else:
                user_picks.append(entry)
        return {
            "goal_title": format_goal_short_tr(goal_sec),
            "break_min": break_min,
            "user_picks": user_picks,
            "ag_picks": ag_picks,
        }

    def claim_reward_item(self, item_id: str) -> dict:
        release_window_topmost(self._window)
        item_name = self._engine.items.get(item_id, {}).get("name", item_id)
        break_min = int(getattr(self._engine, "reward_break_minutes", 10))
        self._engine.claim_reward_break(item_id)
        return {"ok": True, "message": f"{break_min} dakikalık ödül molası başladı: '{item_name}' şu an açık."}

    def dismiss_reward(self) -> dict:
        release_window_topmost(self._window)
        self._engine.dismiss_reward_without_break()
        return {"ok": True}


def apply_dark_titlebar_and_icon():
    """Finds the Odak Asistanı native window handle and applies Windows 11 Obsidian dark titlebar + icon."""
    icon_path = os.path.join(BASE_DIR, "odak_icon.ico")
    for _ in range(30):
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, "Odak Asistanı")
            if hwnd:
                dwmapi = ctypes.windll.dwmapi
                dark_mode = ctypes.c_int(1)
                dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
                dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
                border_color = ctypes.c_int(0x002A2222)
                dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), ctypes.sizeof(border_color))
                caption_color = ctypes.c_int(0x000B0909)
                dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))

                if os.path.exists(icon_path):
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x00000010
                    WM_SETICON = 0x0080
                    GCLP_HICON = -14
                    GCLP_HICONSM = -34
                    hicon_big = ctypes.windll.user32.LoadImageW(0, icon_path, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                    hicon_small = ctypes.windll.user32.LoadImageW(0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    if hicon_big:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, hicon_big)
                        try:
                            ctypes.windll.user32.SetClassLongPtrW(hwnd, GCLP_HICON, hicon_big)
                        except Exception:
                            pass
                    if hicon_small:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, hicon_small)
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 2, hicon_small)
                        try:
                            ctypes.windll.user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, hicon_small)
                        except Exception:
                            pass
                break
        except Exception:
            pass
        time.sleep(0.3)


_MUTEX_HANDLE = None


def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OdakAsistani.FocusApp.2.0")
        ctypes.windll.kernel32.SetConsoleTitleW("Odak Asistanı")
    except Exception:
        pass

    global _MUTEX_HANDLE
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.wintypes.HANDLE
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, "Local\\OdakAsistaniSingleInstanceMutex")
    if kernel32.GetLastError() == 183:
        try:
            with open(SHOW_SIGNAL_FILE, "w", encoding="utf-8") as f:
                f.write("show")
        except Exception:
            pass
        return

    ensure_startup_registered()
    start_hidden = "--hidden" in sys.argv
    is_boot = ("--boot" in sys.argv) or start_hidden

    engine = BlockerEngine(on_state_change=lambda: None, reset_study_on_boot=is_boot)
    parser = CommandParser(engine)
    api = OdakBridgeApi(engine, parser)

    win = webview.create_window(
        "Odak Asistanı",
        url=UI_HTML_PATH,
        js_api=api,
        width=1180,
        height=820,
        min_size=(960, 660),
        background_color="#09090b",
        hidden=start_hidden,
    )
    api._window = win

    tray_holder = {"icon": None}

    def restore_from_tray(icon=None, item=None):
        if tray_holder["icon"]:
            try:
                tray_holder["icon"].stop()
            except Exception:
                pass
            tray_holder["icon"] = None
        try:
            win.show()
            win.restore()
        except Exception:
            pass
        bring_window_to_topmost(win)
        if not engine.reward_available:
            release_window_topmost(win)

    api._restore_tray_cb = restore_from_tray

    def on_closing():
        release_window_topmost(win)
        # Minimize to system tray instead of killing protection
        try:
            win.hide()
            if tray_holder["icon"] is None:
                image = create_tray_icon_image()
                menu = pystray.Menu(
                    pystray.MenuItem("Odak Asistanı'nı Aç", restore_from_tray, default=True),
                )
                t_icon = pystray.Icon("OdakAsistani", image, "Odak Asistanı (Katı Koruma Aktif)", menu)
                tray_holder["icon"] = t_icon
                threading.Thread(target=t_icon.run, daemon=True).start()
            return False
        except Exception:
            return False

    win.events.closing += on_closing
    threading.Thread(target=apply_dark_titlebar_and_icon, daemon=True).start()
    webview.start(debug=False)


if __name__ == "__main__":
    main()

