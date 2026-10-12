# -*- coding: utf-8 -*-
"""
Odak Asistanı - Engelleme Motoru (Blocker Engine)
Sadece kullanıcının "kapat / engelle" emri verdiği uygulama ve web sitelerini engeller;
diğer tüm uygulama ve sitelerin normal şekilde çalışmasını garanti eder.
"""

import ctypes
from ctypes import wintypes
import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta
import psutil

from presets import DEFAULT_ITEMS, ANTIGRAVITY_SITE_PICKS, ALL_PRESET_ITEMS, SAFE_SYSTEM_PROCESSES, BROWSER_PROCESSES
from pc_scanner import scan_installed_pc_apps, generate_badge_icon, extract_icon_to_cache
from study_tracker import (
    STUDY_GOAL_SECONDS,
    REWARD_BREAK_MINUTES,
    ALLOWED_STUDY_GOAL_SECONDS,
    ALLOWED_REWARD_BREAK_MINUTES,
    SUBJECT_DEFINITIONS,
    DEFAULT_STUDY_SOURCES,
    SOURCE_CATEGORY_OPTIONS,
    AudioPeakDetector,
    BrowserMediaSessionMonitor,
    find_active_study_video,
    get_cached_process_name,
    detect_subject_id,
    get_subject_info,
    is_solution_site_title,
    format_goal_short_tr,
    set_dynamic_study_sources,
    build_custom_study_source,
    get_source_category_label,
)
from self_defense import SelfDefenseManager

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
MARKER_START = "# >>> ODAK ASISTANI ENGEL BASLANGIC >>>"
MARKER_END = "# <<< ODAK ASISTANI ENGEL BITIS <<<"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

BADGE_COLORS = {
    "youtube": ("Y", "#dc2626"),
    "discord": ("D", "#5865f2"),
    "instagram": ("I", "#e1306c"),
    "bluestacks": ("B", "#2563eb"),
    "whatsapp": ("W", "#16a34a"),
    "twitter": ("X", "#0284c7"),
    "tiktok": ("T", "#db2777"),
    "steam": ("S", "#1e3a8a"),
    "roblox": ("R", "#dc2626"),
    "valorant": ("V", "#ef4444"),
    "lol": ("L", "#ca8a04"),
    "epicgames": ("E", "#334155"),
    "osu": ("O", "#ec4899"),
    "minecraft": ("M", "#15803d"),
    "telegram": ("T", "#0284c7"),
    "twitch": ("T", "#9333ea"),
    "kick": ("K", "#16a34a"),
    "netflix": ("N", "#b91c1c"),
    "spotify": ("S", "#16a34a"),
    "capcut": ("C", "#0f172a"),
    "reddit": ("R", "#ea580c"),
    "eksisozluk": ("E", "#65a30d"),
    "facebook": ("F", "#1d4ed8"),
}


def is_admin() -> bool:
    """Uygulamanın Yönetici (Administrator) yetkisiyle çalışıp çalışmadığını kontrol eder."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


_thread_desktop_attached = threading.local()


def attach_to_default_desktop():
    """Arka plan iş parçacığının aktif kullanıcı masaüstünü (Default) görmesini garanti eder."""
    if getattr(_thread_desktop_attached, "done", False):
        return
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            _thread_desktop_attached.done = True
    except Exception:
        pass


def get_foreground_window_info():
    """Aktif (ön plandaki) pencerenin başlığını, PID'sini ve süreç adını sıfır CPU yüküyle döndürür."""
    try:
        attach_to_default_desktop()
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, None, ""

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_pid = pid.value
        proc_name = get_cached_process_name(proc_pid) if proc_pid else ""

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return hwnd, proc_name, ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or ""

        return hwnd, proc_name, title
    except Exception:
        return None, None, ""


def send_ctrl_w():
    """
    Aktif tarayıcı sekmesini anında kapatmak için basılı tutulan Shift/Alt tuşlarını
    bıraktırıp donanımsal tarama koduyla (scan code) Ctrl+W gönderir.
    """
    try:
        attach_to_default_desktop()
        user32 = ctypes.windll.user32
        VK_SHIFT = 0x10
        VK_LSHIFT = 0xA0
        VK_RSHIFT = 0xA1
        VK_MENU = 0x12
        VK_LMENU = 0xA4
        VK_RMENU = 0xA5
        VK_CONTROL = 0x11
        VK_W = 0x57
        KEYEVENTF_KEYUP = 0x0002

        # Kullanıcı sohbette yazarken Shift veya Alt basılıysa önce onları bırak
        for mod_vk in (VK_SHIFT, VK_LSHIFT, VK_RSHIFT, VK_MENU, VK_LMENU, VK_RMENU):
            user32.keybd_event(mod_vk, 0, KEYEVENTF_KEYUP, 0)

        sc_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
        sc_w = user32.MapVirtualKeyW(VK_W, 0)

        user32.keybd_event(VK_CONTROL, sc_ctrl, 0, 0)
        user32.keybd_event(VK_W, sc_w, 0, 0)
        time.sleep(0.025)
        user32.keybd_event(VK_W, sc_w, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, sc_ctrl, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


EMERGENCY_DURATION_SECONDS = 30 * 60          # 30 dakika (1800 sn)
EMERGENCY_COOLDOWN_SECONDS = 7 * 24 * 3600    # Haftada 1 kez (7 gün = 604800 sn)


class BlockerEngine:
    def __init__(self, on_state_change=None, on_log_event=None, reset_study_on_boot: bool = False):
        self.lock = threading.RLock()
        self.on_state_change = on_state_change
        self.on_log_event = on_log_event
        self.reset_study_on_boot = reset_study_on_boot

        self.items = {}
        self.settings = {
            "enable_process_blocker": True,
            "enable_hosts_blocker": True,
            "enable_tab_closer": True,
            "unblock_all_on_timer_end": False,
            "clean_hosts_on_exit": False,
        }
        self.stats = {
            "blocked_attempts": 0,
            "commands_executed": 0,
        }
        self.logs = []

        # Genel Pomodoro / Odak Sayacı
        self.timer_active = False
        self.timer_end_ts = 0.0
        self.timer_total_seconds = 0

        # Akıllı YouTube & Soru Çözüm (345 / Bilgi Sarmal) + Manuel Test Çözüm Ders Takibi
        self.study_watched_seconds = 0.0
        self.study_goal_seconds = STUDY_GOAL_SECONDS
        self.reward_break_minutes = REWARD_BREAK_MINUTES
        self.reward_break_duration_sec = REWARD_BREAK_MINUTES * 60
        self.current_study_video = ""
        self.current_study_subject_id = ""
        self.is_study_counting = False
        self.manual_study_active = False
        self.manual_study_subject_id = ""
        self.last_stopped_manual_subject_id = ""
        self.last_stopped_manual_ts = 0.0
        self.reward_available = False
        self.reward_popup_shown = False
        self.reward_break_item_id = None
        self.reward_break_related_ids = []
        self.reward_break_end_ts = 0.0
        self.subject_seconds = {s["id"]: 0.0 for s in SUBJECT_DEFINITIONS}
        self.subject_questions = {s["id"]: 0 for s in SUBJECT_DEFINITIONS}
        self.subject_last_session_status = {}
        self.daily_history = {}
        self.preferred_solution_subject = "otomatik"
        self.study_sources = [dict(s) for s in DEFAULT_STUDY_SOURCES]
        set_dynamic_study_sources(self.study_sources)
        self.last_heartbeat_ts = time.time()

        # Haftada 1 Kez Kullanılabilen 30 Dakikalık Acil Durum Butonu
        self.emergency_active = False
        self.emergency_end_ts = 0.0
        self.emergency_last_used_ts = 0.0
        self.emergency_saved_blocked_ids = []
        self.tyt_auto_unlocked = False
        self.lock_target_committed = False

        self._audio_detector = None
        self._media_monitor = None
        self._last_audio_ts = 0.0
        self._last_user_pause_input_ts = 0.0
        self._manual_pause_latched = False
        self._last_proc_enforce_ts = 0.0
        self._last_loop_ts = time.time()
        self._last_study_save_ts = time.time()
        self._last_heartbeat_save_ts = time.time()

        self._running = True
        self._last_tab_close_ts = 0.0
        self._last_hosts_signature = None

        self.self_defense = SelfDefenseManager()

        self._load_state()
        self.save_state()
        # Başlangıçta hosts dosyasını mevcut duruma senkronize et
        self.sync_hosts_file()

        # Arka plan koruma iş parçacığını başlat
        self._worker_thread = threading.Thread(target=self._enforcement_loop, daemon=True)
        self._worker_thread.start()

    # ------------------------------------------------------------------
    # DURUM YÖNETİMİ (STATE)
    # ------------------------------------------------------------------
    def _load_state(self):
        with self.lock:
            preset_ids = {p["id"] for p in ALL_PRESET_ITEMS}
            # 1. Önce varsayılan öğeleri ve Antigravity'nin Seçtikleri siteleri yükle
            for preset in ALL_PRESET_ITEMS:
                item_copy = dict(preset)
                is_ag_pick = bool(preset.get("antigravity_pick", False))
                item_copy["antigravity_pick"] = is_ag_pick
                item_copy["blocked"] = bool(preset.get("default_blocked", False))
                item_copy["until_ts"] = 0.0
                item_copy["is_custom"] = False
                item_copy["is_pc_app"] = False if is_ag_pick else (item_copy.get("item_type") in ("app", "both"))
                if is_ag_pick:
                    item_copy["exe_names"] = []
                    item_copy["item_type"] = "site"
                else:
                    item_copy["domains"] = list(preset.get("domains", []))
                    item_copy["exe_names"] = list(preset.get("exe_names", []))
                    item_copy["tab_keywords"] = list(preset.get("tab_keywords", []))
                b_char = preset.get("badge_char") or BADGE_COLORS.get(item_copy["id"], (item_copy["name"][0].upper(), "#2563eb"))[0]
                b_col = preset.get("badge_color") or BADGE_COLORS.get(item_copy["id"], (item_copy["name"][0].upper(), "#2563eb"))[1]
                item_copy["icon_png"] = generate_badge_icon(item_copy["id"], b_char, b_col)
                self.items[item_copy["id"]] = item_copy

            # 2. Bilgisayardaki tüm kurulu uygulama ve oyunları (gerçek ikonlarıyla) yükle
            self._merge_scanned_pc_apps(force_rescan=False)

            # 3. Kayıtlı durumu (state.json) geri yükle
            if os.path.exists(STATE_FILE):
                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    saved_items = data.get("items", {})
                    for item_id, s_item in saved_items.items():
                        if item_id in self.items:
                            is_ag = bool(self.items[item_id].get("antigravity_pick", False))
                            if not is_ag:
                                self.items[item_id]["blocked"] = bool(s_item.get("blocked", False))
                            self.items[item_id]["until_ts"] = float(s_item.get("until_ts", 0.0))
                            # Yalnızca site/both türündeki öğelerin domain/sekme anahtar kelimelerini koru
                            if item_id not in preset_ids and self.items[item_id].get("item_type") in ("site", "both"):
                                for d in s_item.get("domains", []):
                                    if d not in self.items[item_id]["domains"]:
                                        self.items[item_id]["domains"].append(d)
                                for tk_kw in s_item.get("tab_keywords", []):
                                    if tk_kw not in self.items[item_id]["tab_keywords"]:
                                        self.items[item_id]["tab_keywords"].append(tk_kw)
                            if not is_ag:
                                for e in s_item.get("exe_names", []):
                                    if e not in self.items[item_id]["exe_names"]:
                                        self.items[item_id]["exe_names"].append(e)
                        elif s_item.get("is_custom"):
                            if not s_item.get("icon_png") or not os.path.exists(s_item.get("icon_png", "")):
                                ch = (s_item.get("name") or "?")[0].upper()
                                s_item["icon_png"] = generate_badge_icon(item_id, ch, "#475569")
                            self.items[item_id] = s_item

                    # YouTube sabit ders kaynağıdır: Alan adının tamamı asla engellenemez
                    self.items.pop("youtube", None)
                    for it in list(self.items.values()):
                        if it.get("domains"):
                            it["domains"] = [
                                d for d in it["domains"]
                                if d.strip().lower() not in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be")
                            ]
                        if it.get("id") == "youtube" or it.get("name", "").lower() == "youtube":
                            it["blocked"] = False

                    if "settings" in data:
                        self.settings.update(data["settings"])
                    if "stats" in data:
                        self.stats.update(data["stats"])
                    if "timer" in data:
                        t_info = data["timer"]
                        end_ts = float(t_info.get("timer_end_ts", 0.0))
                        if t_info.get("timer_active") and end_ts > time.time():
                            self.timer_active = True
                            self.timer_end_ts = end_ts
                            self.timer_total_seconds = int(t_info.get("timer_total_seconds", 0))

                    if "emergency" in data:
                        em = data["emergency"]
                        self.emergency_last_used_ts = float(em.get("emergency_last_used_ts", 0.0))
                        em_active = bool(em.get("emergency_active", False))
                        em_end = float(em.get("emergency_end_ts", 0.0))
                        em_saved = list(em.get("emergency_saved_blocked_ids", []))
                        self.emergency_saved_blocked_ids = em_saved
                        if em_active:
                            if em_end > time.time():
                                self.emergency_active = True
                                self.emergency_end_ts = em_end
                            else:
                                # Bilgisayar kapalıyken 30 dk Acil Durum süresi dolmuşsa hepsini tekrar kilitle!
                                self.emergency_active = False
                                self.emergency_end_ts = 0.0
                                for bid in em_saved:
                                    if bid in self.items:
                                        self.items[bid]["blocked"] = True
                                        self.items[bid]["until_ts"] = 0.0

                    if "study" in data:
                        st = data["study"]
                        # Ders Sürelerim istatistikleri bilgisayar kapatılsa bile ASLA sıfırlanmaz, korunur!
                        self.preferred_solution_subject = str(st.get("preferred_solution_subject", "otomatik"))
                        saved_subj = st.get("subject_seconds", {})
                        if isinstance(saved_subj, dict):
                            for k, v in saved_subj.items():
                                if k in self.subject_seconds:
                                    self.subject_seconds[k] = max(0.0, float(v))

                        saved_q = st.get("subject_questions", {})
                        if isinstance(saved_q, dict):
                            for k, v in saved_q.items():
                                if k in self.subject_questions:
                                    try:
                                        self.subject_questions[k] = max(0, int(v))
                                    except Exception:
                                        pass

                        saved_last_st = st.get("subject_last_session_status", {})
                        if isinstance(saved_last_st, dict):
                            self.subject_last_session_status = {str(k): str(v) for k, v in saved_last_st.items()}

                        saved_hist = st.get("daily_history", {})
                        if isinstance(saved_hist, dict):
                            cleaned_hist = {}
                            for day_key, day_val in saved_hist.items():
                                if isinstance(day_key, str) and isinstance(day_val, dict):
                                    sec_map = {s["id"]: 0.0 for s in SUBJECT_DEFINITIONS}
                                    q_map = {s["id"]: 0 for s in SUBJECT_DEFINITIONS}
                                    raw_sec = day_val.get("seconds", {})
                                    raw_q = day_val.get("questions", {})
                                    if isinstance(raw_sec, dict):
                                        for sk, sv in raw_sec.items():
                                            if sk in sec_map:
                                                try:
                                                    sec_map[sk] = max(0.0, float(sv))
                                                except Exception:
                                                    pass
                                    if isinstance(raw_q, dict):
                                        for qk, qv in raw_q.items():
                                            if qk in q_map:
                                                try:
                                                    q_map[qk] = max(0, int(qv))
                                                except Exception:
                                                    pass
                                    cleaned_hist[day_key] = {"seconds": sec_map, "questions": q_map}
                            self.daily_history = cleaned_hist

                        # Eğer daha önce daily_history yoksa ama mevcut ders süreleri/soruları varsa
                        # bugünün tarihine aktar ki Bugün / Bu Hafta / Bu Ay görünümleri sıfır görünmesin!
                        if not self.daily_history and (
                            any(v > 0 for v in self.subject_seconds.values())
                            or any(v > 0 for v in self.subject_questions.values())
                        ):
                            today_key = datetime.now().strftime("%Y-%m-%d")
                            self.daily_history[today_key] = {
                                "seconds": {k: float(v) for k, v in self.subject_seconds.items()},
                                "questions": {k: int(v) for k, v in self.subject_questions.items()},
                            }

                        # Mola barajı hedef süresi (40 DK / 45 DK / 1 SAAT / 2 SAAT / 3 SAAT) ve mola süresi (5 / 10 / 20 / 30 DK)
                        try:
                            saved_goal = int(st.get("study_goal_seconds", STUDY_GOAL_SECONDS))
                            if saved_goal in ALLOWED_STUDY_GOAL_SECONDS:
                                self.study_goal_seconds = saved_goal
                        except Exception:
                            pass

                        try:
                            saved_break_min = int(st.get("reward_break_minutes", REWARD_BREAK_MINUTES))
                            if saved_break_min in ALLOWED_REWARD_BREAK_MINUTES:
                                self.reward_break_minutes = saved_break_min
                        except Exception:
                            pass

                        try:
                            self.reward_break_duration_sec = max(
                                60, int(st.get("reward_break_duration_sec", self.reward_break_minutes * 60))
                            )
                        except Exception:
                            self.reward_break_duration_sec = self.reward_break_minutes * 60

                        # Kaynak Siteler listesini yükle (yoksa varsayılan YouTube + 345 + Bilgi Sarmal ile başlat)
                        saved_sources = st.get("study_sources")
                        if isinstance(saved_sources, list) and len(saved_sources) > 0:
                            loaded_src = []
                            has_yt = False
                            for s_obj in saved_sources:
                                if not isinstance(s_obj, dict) or not s_obj.get("id"):
                                    continue
                                cp = dict(s_obj)
                                if cp["id"] == "src_youtube":
                                    cp["locked"] = True
                                    cp["subject_id"] = "otomatik"
                                    has_yt = True
                                loaded_src.append(cp)
                            if not has_yt:
                                loaded_src.insert(0, dict(DEFAULT_STUDY_SOURCES[0]))
                            self.study_sources = loaded_src
                        else:
                            init_subj = (
                                self.preferred_solution_subject
                                if (self.preferred_solution_subject and self.preferred_solution_subject != "otomatik")
                                else "soru_cozum"
                            )
                            self.study_sources = []
                            for def_s in DEFAULT_STUDY_SOURCES:
                                cp = dict(def_s)
                                if not cp.get("locked"):
                                    cp["subject_id"] = init_subj
                                self.study_sources.append(cp)
                        set_dynamic_study_sources(self.study_sources)

                        # Bilgisayar kapatılıp yeniden açılmış mı kontrol et
                        # (Windows Hızlı Başlatma / Kapatma / Uyku durumu dahil: son kalp atışından beri > 5 dk geçtiyse
                        # veya boot_time değiştiyse veya --boot ile açıldıysa mola barajı sayacını sıfırla!)
                        now_ts = time.time()
                        current_boot = int(psutil.boot_time())
                        saved_boot = int(st.get("boot_time", 0))
                        saved_hb = float(st.get("last_heartbeat_ts", 0.0))

                        pc_was_shut_down = (
                            self.reset_study_on_boot
                            or (saved_boot > 0 and abs(current_boot - saved_boot) > 15)
                            or saved_hb <= 0.0
                            or (now_ts - saved_hb) > 300.0
                        )

                        if pc_was_shut_down:
                            # Bilgisayar kapatılıp açıldığında ödül mola sayacı sıfırlanır
                            self.study_watched_seconds = 0.0
                            self.reward_available = False
                            self.reward_popup_shown = False
                            self.manual_study_active = False
                            self.manual_study_subject_id = ""
                        else:
                            self.study_watched_seconds = min(
                                float(self.study_goal_seconds),
                                max(0.0, float(st.get("study_watched_seconds", 0.0)))
                            )
                            self.reward_available = bool(st.get("reward_available", False))
                            self.manual_study_active = bool(st.get("manual_study_active", False))
                            self.manual_study_subject_id = str(st.get("manual_study_subject_id", ""))

                        rb_id = st.get("reward_break_item_id")
                        rb_rel = list(st.get("reward_break_related_ids", []))
                        rb_end = float(st.get("reward_break_end_ts", 0.0))
                        if rb_id and rb_id in self.items:
                            if not pc_was_shut_down and rb_end > now_ts:
                                self.reward_break_item_id = rb_id
                                self.reward_break_related_ids = [rid for rid in rb_rel if rid in self.items]
                                self.reward_break_end_ts = rb_end
                            else:
                                # Bilgisayar kapalıyken veya mola süresi dolmuşsa tekrar kilitle!
                                self.items[rb_id]["blocked"] = True
                                self.items[rb_id]["until_ts"] = 0.0
                                for rid in rb_rel:
                                    if rid in self.items:
                                        self.items[rid]["blocked"] = True
                                        self.items[rid]["until_ts"] = 0.0

                    if "lock_target" in data and isinstance(data["lock_target"], dict):
                        lt = data["lock_target"]
                        self.lock_target_committed = bool(lt.get("committed", True))
                        self.self_defense.configure_lock_target(
                            unlock_ts=float(lt.get("unlock_timestamp", self.self_defense.unlock_timestamp)),
                            target_title=str(lt.get("target_title", "YKS 2027 (TYT / AYT)")),
                            countdown_prefix=str(lt.get("countdown_prefix", "TYT Kilidi")),
                            target_badge=str(lt.get("target_badge", "YKS 2027")),
                            preset_id=str(lt.get("preset_id", "yks_2027")),
                        )
                    else:
                        # Mevcut state.json varsa Katı Koruma (18 Haziran 2027) zaten aktiftir
                        self.lock_target_committed = True

                    self.tyt_auto_unlocked = bool(data.get("tyt_auto_unlocked", False))
                    if self.self_defense.is_unlock_date_reached():
                        if not self.tyt_auto_unlocked:
                            self.tyt_auto_unlocked = True
                            for item in self.items.values():
                                item["blocked"] = False
                                item["until_ts"] = 0.0
                            self.self_defense.release_all_protections()
                    else:
                        # Hedef kilit tarihine kadar Antigravity'nin seçtiği
                        # tüm dopamin tuzağı siteleri (mola veya acil durum aktif değilse) kilitli tut!
                        active_break_ids = {self.reward_break_item_id} | set(self.reward_break_related_ids)
                        for item_id, item in self.items.items():
                            if item.get("antigravity_pick"):
                                item["exe_names"] = []
                                item["is_pc_app"] = False
                                item["item_type"] = "site"
                                if not self.emergency_active and item_id not in active_break_ids:
                                    item["blocked"] = True
                except Exception as e:
                    self.add_log(f"⚠️ Durum dosyası okunurken hata oluştu: {e}")

    def _merge_scanned_pc_apps(self, force_rescan: bool = False):
        """Taranan bilgisayar uygulamalarını ve gerçek ikonlarını mevcut listeyle birleştirir."""
        pc_apps = scan_installed_pc_apps(force_rescan=force_rescan)
        with self.lock:
            for papp in pc_apps:
                pname_low = papp["name"].lower()
                pname_clean = re.sub(r"[®™©]", "", pname_low).strip()
                p_exes_low = {e.lower() for e in papp.get("exe_names", [])}
                matched_existing_id = None

                # Antigravity'nin seçtiği web sitelerine ASLA masaüstü uygulaması (.exe) bağlama!
                for ex_id, ex_item in self.items.items():
                    if ex_item.get("antigravity_pick"):
                        continue
                    ex_aliases = {a.lower() for a in ex_item.get("aliases", [])}
                    if (
                        ex_item["name"].lower() == pname_low
                        or pname_low == ex_id
                        or pname_clean in ex_aliases
                    ):
                        matched_existing_id = ex_id
                        break

                if matched_existing_id:
                    target_item = self.items[matched_existing_id]
                    target_item["is_pc_app"] = True
                    if papp.get("icon_png") and os.path.exists(papp["icon_png"]):
                        target_item["icon_png"] = papp["icon_png"]
                    for e in papp.get("exe_names", []):
                        if e not in target_item["exe_names"]:
                            target_item["exe_names"].append(e)
                else:
                    pid = papp["id"]
                    prev_blocked = self.items.get(pid, {}).get("blocked", False)
                    prev_until = self.items.get(pid, {}).get("until_ts", 0.0)
                    icon_png = papp.get("icon_png") or ""
                    if not icon_png or not os.path.exists(icon_png):
                        icon_png = generate_badge_icon(pid, papp["name"][0].upper(), "#3b82f6")
                    self.items[pid] = {
                        "id": pid,
                        "name": papp["name"],
                        "icon": "💻",
                        "icon_png": icon_png,
                        "category": "Bilgisayar Uygulaması",
                        "item_type": "app",
                        "is_pc_app": True,
                        "domains": [],
                        "exe_names": papp.get("exe_names", []),
                        "tab_keywords": [],
                        "aliases": [pname_low] + [e.lower().replace(".exe", "") for e in papp.get("exe_names", [])],
                        "blocked": prev_blocked,
                        "until_ts": prev_until,
                        "is_custom": False,
                    }

    def rescan_pc_apps(self):
        self._merge_scanned_pc_apps(force_rescan=True)
        self._notify_change()

    def save_state(self):
        with self.lock:
            try:
                self.last_heartbeat_ts = time.time()
                data = {
                    "items": self.items,
                    "settings": self.settings,
                    "stats": self.stats,
                    "tyt_auto_unlocked": self.tyt_auto_unlocked,
                    "lock_target": {
                        "preset_id": self.self_defense.target_preset_id,
                        "target_title": self.self_defense.target_title,
                        "countdown_prefix": self.self_defense.countdown_prefix,
                        "target_badge": self.self_defense.target_badge,
                        "unlock_timestamp": self.self_defense.unlock_timestamp,
                        "committed": self.lock_target_committed,
                    },
                    "timer": {
                        "timer_active": self.timer_active,
                        "timer_end_ts": self.timer_end_ts,
                        "timer_total_seconds": self.timer_total_seconds,
                    },
                    "emergency": {
                        "emergency_active": self.emergency_active,
                        "emergency_end_ts": self.emergency_end_ts,
                        "emergency_last_used_ts": self.emergency_last_used_ts,
                        "emergency_saved_blocked_ids": self.emergency_saved_blocked_ids,
                    },
                    "study": {
                        "boot_time": int(psutil.boot_time()),
                        "last_heartbeat_ts": self.last_heartbeat_ts,
                        "study_goal_seconds": self.study_goal_seconds,
                        "reward_break_minutes": self.reward_break_minutes,
                        "reward_break_duration_sec": self.reward_break_duration_sec,
                        "study_watched_seconds": self.study_watched_seconds,
                        "reward_available": self.reward_available,
                        "reward_break_item_id": self.reward_break_item_id,
                        "reward_break_related_ids": self.reward_break_related_ids,
                        "reward_break_end_ts": self.reward_break_end_ts,
                        "manual_study_active": self.manual_study_active,
                        "manual_study_subject_id": self.manual_study_subject_id,
                        "subject_seconds": self.subject_seconds,
                        "subject_questions": self.subject_questions,
                        "subject_last_session_status": self.subject_last_session_status,
                        "daily_history": self.daily_history,
                        "preferred_solution_subject": self.preferred_solution_subject,
                        "study_sources": self.study_sources,
                    }
                }
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def add_log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        with self.lock:
            self.logs.insert(0, entry)
            if len(self.logs) > 150:
                self.logs = self.logs[:150]
        if self.on_log_event:
            try:
                self.on_log_event(entry)
            except Exception:
                pass

    def _notify_change(self):
        self.save_state()
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # ÖĞE EKLEME / AÇMA / KAPATMA İŞLEMLERİ
    # ------------------------------------------------------------------
    def get_all_items(self):
        with self.lock:
            return [dict(v) for v in self.items.values()]

    def get_blocked_items(self):
        with self.lock:
            return [dict(v) for v in self.items.values() if v.get("blocked")]

    def set_item_blocked(self, item_id: str, blocked: bool, duration_minutes: int = 0, silent: bool = False) -> bool:
        if item_id == "youtube" and blocked:
            self.add_log("⚠️ YouTube sabit ders kaynağıdır; alan adı kapatılamaz. Belli bir bölüm için youtube.com/shorts veya youtube.com/playables kullanın.")
            return False

        with self.lock:
            if item_id not in self.items:
                return False
            item = self.items[item_id]
            item["blocked"] = bool(blocked)
            if blocked and duration_minutes > 0:
                item["until_ts"] = time.time() + (duration_minutes * 60)
            else:
                item["until_ts"] = 0.0

            name = item["name"]
            if not silent:
                if blocked:
                    if duration_minutes > 0:
                        self.add_log(f"🔒 {name} {duration_minutes} dakika boyunca kapatıldı/engellendi.")
                    else:
                        self.add_log(f"🔒 {name} kapatıldı ve engellendi.")
                else:
                    self.add_log(f"🔓 {name} engeli kaldırıldı (Normal çalışmaya açık).")

        self.sync_hosts_file()
        if blocked:
            self.enforce_processes_once()
            self.enforce_browser_tabs_once()
        self._notify_change()
        return True

    def set_multiple_blocked(self, item_ids: list, blocked: bool, duration_minutes: int = 0):
        changed_names = []
        with self.lock:
            for item_id in item_ids:
                if item_id == "youtube" and blocked:
                    continue
                if item_id in self.items:
                    self.items[item_id]["blocked"] = bool(blocked)
                    if blocked and duration_minutes > 0:
                        self.items[item_id]["until_ts"] = time.time() + (duration_minutes * 60)
                    else:
                        self.items[item_id]["until_ts"] = 0.0
                    changed_names.append(self.items[item_id]["name"])

        if changed_names:
            joined = ", ".join(changed_names)
            if blocked:
                if duration_minutes > 0:
                    self.add_log(f"🔒 Kapatıldı ({duration_minutes} dk): {joined}")
                else:
                    self.add_log(f"🔒 Kapatıldı ve engellendi: {joined}")
            else:
                self.add_log(f"🔓 Engeli kaldırıldı (Açıldı): {joined}")

        self.sync_hosts_file()
        if blocked:
            self.enforce_processes_once()
            self.enforce_browser_tabs_once()
        self._notify_change()
        return changed_names

    def unblock_all(self):
        with self.lock:
            count = 0
            for item in self.items.values():
                if item.get("blocked"):
                    item["blocked"] = False
                    item["until_ts"] = 0.0
                    count += 1
            self.timer_active = False
            self.timer_end_ts = 0.0

        self.sync_hosts_file(force_clean=True)
        self.add_log(f"✅ Tüm engeller kaldırıldı ({count} öğe serbest bırakıldı). Her şey normal modda.")
        self._notify_change()
        return count

    def add_custom_item(self, raw_target: str, category: str = "Özel Eklenen", block_immediately: bool = True, duration_minutes: int = 0):
        """
        Kullanıcının girdiği özel bir siteyi (örn: sahibinden.com) veya
        uygulamayı (örn: obs64.exe veya Notepad) listeye ekler.
        """
        target = raw_target.strip()
        if not target:
            return None, "Boş hedef eklendi."

        lower_t = target.lower()

        # Güvenli sistem süreci kontrolü
        if lower_t in SAFE_SYSTEM_PROCESSES or f"{lower_t}.exe" in SAFE_SYSTEM_PROCESSES:
            return None, f"⚠️ '{target}' kritik bir Windows sistem sürecidir ve güvenlik nedeniyle engellenemez!"

        # Zaten var mı kontrol et
        with self.lock:
            for existing_id, item in self.items.items():
                if lower_t == existing_id or lower_t == item["name"].lower():
                    self.set_item_blocked(existing_id, block_immediately, duration_minutes)
                    return item, f"'{item['name']}' güncellendi."
                if lower_t in [d.lower() for d in item.get("domains", [])] or lower_t in [e.lower() for e in item.get("exe_names", [])]:
                    self.set_item_blocked(existing_id, block_immediately, duration_minutes)
                    return item, f"'{item['name']}' güncellendi."

        # Uygulama mı yoksa web sitesi mi tespit et
        is_exe = lower_t.endswith(".exe")
        is_domain = ("." in lower_t and not is_exe) or lower_t.startswith("http")

        clean_id = re.sub(r"[^a-z0-9_]", "", lower_t.replace(".", "_"))
        if not clean_id:
            clean_id = f"custom_{int(time.time())}"

        if is_domain:
            # URL'yi şema / www / sorgu / port parçalarından ayıkla; yol (path) kısmını KORU
            url_body = re.sub(r"^[a-z]+://", "", lower_t).lstrip("/").split("#")[0].strip()
            host_raw = url_body.split("/")[0]
            domain = host_raw.split("?")[0].split(":")[0].strip()
            if domain.startswith("www."):
                domain = domain[4:]
            path_part = url_body[len(host_raw):].split("?")[0].strip("/").strip()

            if path_part:
                # Yalnızca belirli bir sayfa/bölüm (örn. youtube.com/playables, youtube.com/shorts):
                # Alan adının TAMAMI ASLA engellenmez (hosts'a yazılmaz); yalnızca o adresteki sekme kapatılır.
                url_rule = f"{domain}/{path_part}"
                path_tokens = [
                    t for t in re.split(r"[/\-_.]+", path_part)
                    if len(t) >= 3 and not t.isdigit()
                ]
                brand = domain.split(".")[0]
                item_id = "url_" + re.sub(
                    r"[^a-z0-9_]", "", url_rule.replace(".", "_").replace("/", "_").replace("-", "_")
                )
                badge_ch = (path_tokens[0][0] if path_tokens else domain[0]).upper()
                new_item = {
                    "id": item_id,
                    "name": url_rule,
                    "icon": "🌐",
                    "icon_png": generate_badge_icon(item_id, badge_ch, "#0284c7"),
                    "category": category,
                    "item_type": "site",
                    "is_pc_app": False,
                    "domains": [],
                    "url_rules": [url_rule],
                    # Sekme başlığında hem bölüm adı hem site adı birlikte geçmeli (örn. "playables" + "youtube")
                    "title_all_keywords": (
                        ([path_tokens + [brand]] if path_tokens else [])
                        + ([["playables", "youtube"], ["oyunlar", "youtube"], ["mini", "oyunlar", "youtube"], ["mini", "oyun", "youtube"]] if "playables" in path_part else [])
                        + ([["shorts", "youtube"], ["#shorts", "youtube"]] if "shorts" in path_part else [])
                    ),
                    "exe_names": [],
                    "tab_keywords": [],
                    "aliases": [url_rule],
                    "blocked": block_immediately,
                    "until_ts": (time.time() + duration_minutes * 60) if (block_immediately and duration_minutes > 0) else 0.0,
                    "is_custom": True,
                }
                with self.lock:
                    self.items[new_item["id"]] = new_item
                if block_immediately:
                    self.add_log(f"➕ Yalnızca '{url_rule}' sayfası engellendi (sitenin geri kalanı açık).")
                    self.enforce_browser_tabs_once()
                else:
                    self.add_log(f"➕ Sayfa kuralı listeye eklendi (Açık): {url_rule}")
                self._notify_change()
                return new_item, f"'{url_rule}' sayfası engellendi; {domain} sitesinin geri kalanı açık kalacak."

            # YouTube sabit ders kaynağıdır: alan adının tamamı özel komutla kapatılamaz
            if domain in ("youtube.com", "m.youtube.com", "youtu.be"):
                return None, (
                    "⚠️ YouTube sabit ders kaynağı olduğu için tamamı kapatılamaz. "
                    "Belirli bir bölümü kapatmak için yolunu yazın (örn: youtube.com/shorts veya youtube.com/playables)."
                )

            domains = [domain, f"www.{domain}", f"m.{domain}"]
            base_keyword = domain.split(".")[0]
            item_id = f"site_{clean_id}"
            new_item = {
                "id": item_id,
                "name": domain,
                "icon": "🌐",
                "icon_png": generate_badge_icon(item_id, domain[0].upper(), "#0284c7"),
                "category": category,
                "item_type": "site",
                "is_pc_app": False,
                "domains": domains,
                "exe_names": [],
                "tab_keywords": [domain, base_keyword] if len(base_keyword) >= 4 else [domain],
                "aliases": [domain, base_keyword],
                "blocked": block_immediately,
                "until_ts": (time.time() + duration_minutes * 60) if (block_immediately and duration_minutes > 0) else 0.0,
                "is_custom": True,
            }
        else:
            # Uygulama (.exe)
            exe_name = target if target.lower().endswith(".exe") else f"{target}.exe"
            if exe_name.lower() in SAFE_SYSTEM_PROCESSES:
                return None, f"⚠️ '{exe_name}' kritik bir sistem sürecidir, engellenemez."
            display_name = target[:-4] if target.lower().endswith(".exe") else target
            item_id = f"app_{clean_id}"
            new_item = {
                "id": item_id,
                "name": display_name,
                "icon": "💻",
                "icon_png": generate_badge_icon(item_id, display_name[0].upper(), "#4f46e5"),
                "category": category,
                "item_type": "app",
                "is_pc_app": True,
                "domains": [],
                "exe_names": [exe_name],
                "tab_keywords": [],
                "aliases": [display_name.lower(), exe_name.lower()],
                "blocked": block_immediately,
                "until_ts": (time.time() + duration_minutes * 60) if (block_immediately and duration_minutes > 0) else 0.0,
                "is_custom": True,
            }

        with self.lock:
            self.items[new_item["id"]] = new_item

        if block_immediately:
            self.add_log(f"➕ Yeni öğe eklendi ve kapatıldı: {new_item['name']}")
            self.sync_hosts_file()
            self.enforce_processes_once()
            self.enforce_browser_tabs_once()
        else:
            self.add_log(f"➕ Yeni öğe listeye eklendi (Açık): {new_item['name']}")

        self._notify_change()
        return new_item, f"'{new_item['name']}' başarıyla eklendi."

    def remove_custom_item(self, item_id: str):
        with self.lock:
            if item_id in self.items and self.items[item_id].get("is_custom"):
                name = self.items[item_id]["name"]
                del self.items[item_id]
                self.add_log(f"🗑️ Özel öğe listeden silindi: {name}")
                self.sync_hosts_file()
                self._notify_change()
                return True
        return False

    # ------------------------------------------------------------------
    # ZAMANLAYICI (POMODORO / SÜRELİ ODAK)
    # ------------------------------------------------------------------
    def start_timer(self, minutes: int):
        if minutes <= 0:
            return
        with self.lock:
            self.timer_total_seconds = minutes * 60
            self.timer_end_ts = time.time() + self.timer_total_seconds
            self.timer_active = True
        self.add_log(f"⏱️ {minutes} dakikalık odak sayacı başlatıldı.")
        self._notify_change()

    def stop_timer(self):
        with self.lock:
            self.timer_active = False
            self.timer_end_ts = 0.0
        self.add_log("⏹️ Odak sayacı durduruldu.")
        self._notify_change()

    def get_timer_remaining(self):
        with self.lock:
            if not self.timer_active:
                return 0, 0
            rem = max(0, int(self.timer_end_ts - time.time()))
            return rem, self.timer_total_seconds

    # ------------------------------------------------------------------
    # ÖDÜL MOLASI EŞLEŞEN (ÇAPRAZ MENÜ) ÖĞE VE İSTİSNA YÖNETİMİ
    # ------------------------------------------------------------------
    def _find_linked_break_ids(self, item_id: str) -> list:
        """
        Kullanıcı ödül molasında 'Senin Seçtiklerin' veya 'Antigravity'nin Seçtikleri'nden
        bir öğe seçtiğinde (örneğin Instagram Lite <-> Instagram (Reels & DM), osu! <-> osu!,
        Chai <-> Character.AI/Chai, Rocket League <-> Epic Games & Rocket League),
        diğer menüde veya listede aynı platforma ait kilitli ikiz öğeleri otomatik bulur.
        Böylece ödül molasında Instagram seçildiğinde diğer menüdeki Instagram kilidi
        yüzünden açılmama sorunu %100 önlenir!
        """
        target = self.items.get(item_id)
        if not target:
            return []

        generic_words = {
            "uygulama", "site", "web", "oyun", "oyunları", "siteleri", "platform",
            "platformları", "paketi", "paket", "video", "canlı", "yayın", "sohbet",
            "mesajlaşma", "sosyal", "medya", "reels", "dm", "tuzağı", "kısa",
            "tarayıcı", "hızlı", "forum", "sözlük", "dizi", "film", "lite", "app",
            "launcher", "player", "client", "studio", "pc"
        }
        shared_emulators = {"hd-player.exe", "hd-multiinstancemanager.exe", "bluestacksweb.exe", "bluestacks x.exe", "bluestacks.exe", "bstksvc.exe", "bluestacksservices.exe"}

        def _extract_brands(it: dict) -> set:
            raw = " ".join([it.get("id", ""), it.get("name", "")] + list(it.get("aliases", []))).lower()
            raw = re.sub(r"^pc_", "", raw)
            tokens = set(re.findall(r"[a-z0-9ğüşıöç]{3,}", raw))
            # Özel birleşik isimler (örn. instagramlite -> instagram)
            expanded = set()
            for tok in tokens:
                if tok in generic_words:
                    continue
                expanded.add(tok)
                for known in ("instagram", "tiktok", "twitter", "discord", "whatsapp", "telegram", "twitch", "netflix", "roblox", "steam", "valorant", "rocket", "minecraft", "craftrise", "spotify", "capcut"):
                    if known in tok:
                        expanded.add(known)
            return expanded

        target_brands = _extract_brands(target)
        target_domains = {d.lower().strip() for d in target.get("domains", []) if d}
        target_exes = {e.lower().strip() for e in target.get("exe_names", []) if e and e.lower().strip() not in shared_emulators}

        linked = []
        for other_id, other in self.items.items():
            if other_id == item_id or not other.get("blocked"):
                continue
            other_brands = _extract_brands(other)
            other_domains = {d.lower().strip() for d in other.get("domains", []) if d}
            other_exes = {e.lower().strip() for e in other.get("exe_names", []) if e and e.lower().strip() not in shared_emulators}

            if (
                (target_brands and other_brands and (target_brands & other_brands))
                or (target_domains and other_domains and (target_domains & other_domains))
                or (target_exes and other_exes and (target_exes & other_exes))
            ):
                linked.append(other_id)

        return linked

    def _get_active_break_exemptions(self) -> tuple:
        """
        10 dakikalık ödül molası aktifken, seçilen öğenin (ve ikizlerinin) çalıştırdığı
        .exe süreçlerini, alan adlarını ve sekme anahtar kelimelerini döndürür.
        Böylece başka bir kilitli öğe aynı emülatörü (örn. HD-Player.exe) veya
        aynı alan adını (örn. instagram.com) paylaşsa bile mola süresince engelleyemez!
        """
        now = time.time()
        if not self.reward_break_item_id or now >= self.reward_break_end_ts:
            return set(), set(), set()

        active_ids = [self.reward_break_item_id] + list(self.reward_break_related_ids)
        exempt_domains = set()
        exempt_exes = set()
        exempt_keywords = set()

        for aid in active_ids:
            it = self.items.get(aid)
            if not it:
                continue
            for d in it.get("domains", []):
                if d:
                    d_low = d.strip().lower()
                    exempt_domains.add(d_low)
                    base = d_low.replace("www.", "").split(".")[0]
                    if len(base) >= 4:
                        exempt_keywords.add(base)
            for e in it.get("exe_names", []):
                if e:
                    exempt_exes.add(e.strip().lower())
            for kw in it.get("tab_keywords", []):
                if kw:
                    exempt_keywords.add(kw.strip().lower())

        return exempt_domains, exempt_exes, exempt_keywords

    # ------------------------------------------------------------------
    # WINDOWS HOSTS DOSYASI İLE SİTE ENGELLEME
    # ------------------------------------------------------------------
    def sync_hosts_file(self, force_clean: bool = False) -> bool:
        """
        Aktif engelli siteleri Windows hosts dosyasına yazar.
        Engeli kaldırılan siteleri anında hosts dosyasından siler ve DNS önbelleğini temizler.
        """
        with self.lock:
            exempt_domains, _, _ = self._get_active_break_exemptions()
            domains_to_block = []
            if not force_clean and self.settings.get("enable_hosts_blocker", True):
                for item in self.items.values():
                    if item.get("blocked"):
                        for d in item.get("domains", []):
                            d_clean = d.strip().lower()
                            # YouTube sabit ders kaynağıdır: Alan adı asla hosts dosyasına yazılamaz!
                            if d_clean in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"):
                                continue
                            if d_clean and d_clean not in exempt_domains and d_clean not in domains_to_block:
                                domains_to_block.append(d_clean)

            signature = tuple(sorted(domains_to_block))
            if signature == self._last_hosts_signature and not force_clean:
                return True

        if not is_admin():
            # Yönetici yetkisi yoksa sekme kapatıcı (Tab Guard) devreye girer
            return False

        try:
            content = ""
            if os.path.exists(HOSTS_PATH):
                with open(HOSTS_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

            # Eski ODAK ASISTANI bloğunu temizle
            pattern = re.compile(
                re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END) + r"\r?\n?",
                re.DOTALL
            )
            cleaned_content = pattern.sub("", content).rstrip()

            if domains_to_block:
                block_lines = [MARKER_START]
                for domain in domains_to_block:
                    block_lines.append(f"0.0.0.0 {domain}")
                    block_lines.append(f"::0 {domain}")
                block_lines.append(MARKER_END)
                new_section = "\n".join(block_lines)
                final_content = f"{cleaned_content}\n\n{new_section}\n"
            else:
                final_content = f"{cleaned_content}\n"

            with open(HOSTS_PATH, "w", encoding="utf-8") as f:
                f.write(final_content)

            # DNS önbelleğini sessizce temizle
            subprocess.run(
                ["ipconfig", "/flushdns"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            with self.lock:
                self._last_hosts_signature = signature
            return True
        except Exception as e:
            self.add_log(f"⚠️ Hosts dosyası güncellenemedi: {e}")
            return False

    # ------------------------------------------------------------------
    # UYGULAMA (.EXE) VE TARAYICI SEKMESİ KAPATMA MOTORU
    # ------------------------------------------------------------------
    def enforce_processes_once(self):
        """
        Engelli olan masaüstü uygulamaları ve oyunları çalışıyorsa gözünün yaşına bakmadan
        anında (oyunun/sohbetin tam ortasında bile) zorla kapatır.
        """
        with self.lock:
            if not self.settings.get("enable_process_blocker", True):
                return
            _, exempt_exes, _ = self._get_active_break_exemptions()
            blocked_exe_map = {}
            for item in self.items.values():
                if item.get("blocked"):
                    for exe in item.get("exe_names", []):
                        exe_lower = exe.lower().strip()
                        if exe_lower and exe_lower not in SAFE_SYSTEM_PROCESSES and exe_lower not in exempt_exes:
                            blocked_exe_map[exe_lower] = item["name"]

        if not blocked_exe_map:
            return

        my_pid = os.getpid()
        killed_any = False

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pid = proc.info["pid"]
                if pid == my_pid or pid <= 4:
                    continue
                pname = (proc.info["name"] or "").lower()
                if not pname or pname in SAFE_SYSTEM_PROCESSES:
                    continue

                if pname in blocked_exe_map:
                    friendly_name = blocked_exe_map[pname]
                    raw_name = proc.info["name"]
                    try:
                        # Oyunun/uygulamanın ortasında anında zorla sonlandır (Graceful kapanmayı bekleme!)
                        proc.kill()
                        killed_any = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        try:
                            subprocess.Popen(
                                ["taskkill", "/F", "/T", "/IM", raw_name],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                creationflags=0x08000000
                            )
                            killed_any = True
                        except Exception:
                            pass
                    if killed_any:
                        with self.lock:
                            self.stats["blocked_attempts"] += 1
                        self.add_log(f"🛡️ {friendly_name} ({raw_name}) anında zorla kapatıldı!")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed_any:
            self._notify_change()

    def _tab_matches_blocked_rules(self, window_title: str, current_url: str, blocked_tab_rules: list, specific_url_rules: list):
        """
        Pencere başlığı ve (varsa) sekme URL'si üzerinden engelli kurallarla eşleşme yapar.
        Eşleşirse engelli öğenin adını döner, eşleşmezse None döner.
        """
        title_lower = (window_title or "").lower().strip()
        url_lower = (current_url or "").lower().strip()
        url_clean = re.sub(r"^[a-z]+://", "", url_lower).lstrip("/").split("?")[0].split("#")[0].strip()
        if url_clean.startswith("www."):
            url_clean = url_clean[4:]

        clean_title = re.sub(
            r"\s*[-—]\s*(google chrome|microsoft​? edge|brave|opera.*|mozilla firefox|vivaldi|arc).*$",
            "",
            title_lower
        ).strip()

        # 1. Öncelik: Belirli sayfa / alt yol (URL) kuralları
        for item_name, url_rules, title_all_kw in specific_url_rules:
            # A) URL kontrolü (Adres çubuğundan gelen doğrudan URL eşleşmesi)
            if url_clean:
                for ur in url_rules:
                    ur_clean = re.sub(r"^[a-z]+://", "", ur.lower()).lstrip("/").split("?")[0].strip()
                    if ur_clean.startswith("www."):
                        ur_clean = ur_clean[4:]
                    if ur_clean and (ur_clean in url_clean or url_clean.startswith(ur_clean)):
                        return item_name

            # B) Başlıkta URL kuralının kendisi geçiyor mu?
            for ur in url_rules:
                ur_clean = re.sub(r"^[a-z]+://", "", ur.lower()).lstrip("/").split("?")[0].strip()
                if ur_clean and ur_clean in title_lower:
                    return item_name

            # C) Başlık çoklu anahtar kelime kontrolü (örn. Hem 'playables' hem 'youtube' başlıkta var mı?)
            for token_group in title_all_kw:
                if token_group and all(t.lower() in title_lower for t in token_group):
                    return item_name

        # 2. Standart site kuralları (Tüm alan adı engelliyse)
        for item_name, keywords in blocked_tab_rules:
            for kw in keywords:
                if len(kw) <= 3:
                    if re.search(rf"\b{re.escape(kw)}\b", clean_title):
                        return item_name
                else:
                    if kw in clean_title:
                        return item_name
        return None

    def _title_matches_blocked_rules(self, window_title: str, blocked_tab_rules: list):
        return self._tab_matches_blocked_rules(window_title, "", blocked_tab_rules, [])

    def enforce_browser_tabs_once(self, force_all_windows: bool = False):
        """
        Tarayıcıda engelli bir web sitesinin (örn. Instagram DM sohbeti, YouTube playables vb.) sekmesi açıksa,
        yalnızca o sekmeyi Ctrl+W ile anında kapatır.
        """
        with self.lock:
            if not self.settings.get("enable_tab_closer", True):
                return
            if not force_all_windows and (time.time() - self._last_tab_close_ts < 0.35):
                return

            _, _, exempt_keywords = self._get_active_break_exemptions()
            blocked_tab_rules = []
            specific_url_rules = []
            for item in self.items.values():
                if item.get("blocked") and item.get("item_type") in ("site", "both"):
                    # 1. URL kuralları (yalnızca belirli bir sayfa/yol engellenmişse)
                    url_rules = item.get("url_rules", [])
                    title_all_kw = item.get("title_all_keywords", [])
                    if url_rules or title_all_kw:
                        specific_url_rules.append((item["name"], url_rules, title_all_kw))
                        # url_rules varsa alan adının tamamını kapatmaz
                        continue

                    # 2. Standart tüm site kuralları
                    keywords = [k.lower() for k in item.get("tab_keywords", []) if k and k.lower() not in exempt_keywords]
                    for d in item.get("domains", []):
                        base = d.lower().replace("www.", "").split(".")[0]
                        if len(base) >= 4 and base not in keywords and base not in exempt_keywords:
                            keywords.append(base)
                    if keywords:
                        blocked_tab_rules.append((item["name"], keywords))

        if not blocked_tab_rules and not specific_url_rules:
            return

        # 1. Ön plandaki pencereyi kontrol et
        hwnd, proc_name, window_title = get_foreground_window_info()
        if proc_name and proc_name in BROWSER_PROCESSES and window_title:
            current_url = ""
            try:
                from study_tracker import _ACTIVE_BROWSER_URLS
                current_url = _ACTIVE_BROWSER_URLS.get(int(hwnd), "")
            except Exception:
                pass
            matched_name = self._tab_matches_blocked_rules(window_title, current_url, blocked_tab_rules, specific_url_rules)
            if matched_name:
                with self.lock:
                    self._last_tab_close_ts = time.time()
                    self.stats["blocked_attempts"] += 1
                send_ctrl_w()
                self.add_log(f"🌐 Tarayıcıda açık '{matched_name}' sekmesi anında yüzünüze kapatıldı!")
                self._notify_change()
                return

        # 2. Mola veya Acil Durum bittiği anda arka planda/yan ekranda görünür olan tarayıcı pencerelerini de tara
        if force_all_windows:
            try:
                attach_to_default_desktop()
                user32 = ctypes.windll.user32
                WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                targets = []

                def _cb(w_hwnd, _lparam):
                    try:
                        if not user32.IsWindowVisible(w_hwnd):
                            return True
                        length = user32.GetWindowTextLengthW(w_hwnd)
                        if length == 0:
                            return True
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(w_hwnd, buf, length + 1)
                        w_title = buf.value or ""
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(w_hwnd, ctypes.byref(pid))
                        if not pid.value:
                            return True
                        pname = psutil.Process(pid.value).name().lower()
                        if pname in BROWSER_PROCESSES:
                            cur_url = ""
                            try:
                                from study_tracker import _ACTIVE_BROWSER_URLS
                                cur_url = _ACTIVE_BROWSER_URLS.get(int(w_hwnd), "")
                            except Exception:
                                pass
                            m_name = self._tab_matches_blocked_rules(w_title, cur_url, blocked_tab_rules, specific_url_rules)
                            if m_name:
                                targets.append((w_hwnd, m_name))
                    except Exception:
                        pass
                    return True

                user32.EnumWindows(WNDENUMPROC(_cb), 0)
                for t_hwnd, m_name in targets:
                    try:
                        if user32.IsIconic(t_hwnd):
                            user32.ShowWindow(t_hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(t_hwnd)
                        time.sleep(0.06)
                        send_ctrl_w()
                        with self.lock:
                            self._last_tab_close_ts = time.time()
                            self.stats["blocked_attempts"] += 1
                        self.add_log(f"🌐 Mola bitti: Açık '{m_name}' sekmesi anında kapatıldı!")
                    except Exception:
                        pass
            except Exception:
                pass

    def update_break_bar_settings(self, new_goal_seconds: int, new_break_minutes: int) -> dict:
        """
        Mola barajı ders çalışma hedefini (40 DK / 45 DK / 1 SAAT / 2 SAAT / 3 SAAT) ve
        ödül mola süresini (5 DK / 10 DK / 20 DK / 30 DK) günceller.
        - Yeni hedefe geçildiğinde mevcut baraj ilerlemesini SIFIRLAMAZ;
          eski sürenin yeni süreye oranına göre (örn. 3 Saat=180 dk -> 45 dk geçişinde 4'e bölerek)
          adaletli ve orantısal olarak ölçekler!
        """
        new_goal = int(new_goal_seconds)
        new_break = int(new_break_minutes)
        if new_goal not in ALLOWED_STUDY_GOAL_SECONDS:
            new_goal = STUDY_GOAL_SECONDS
        if new_break not in ALLOWED_REWARD_BREAK_MINUTES:
            new_break = REWARD_BREAK_MINUTES

        with self.lock:
            old_goal = int(max(1, self.study_goal_seconds))
            old_watched = float(self.study_watched_seconds)
            scale_factor = float(new_goal) / float(old_goal)
            new_watched = min(float(new_goal), max(0.0, old_watched * scale_factor))

            self.study_goal_seconds = new_goal
            self.study_watched_seconds = new_watched
            self.reward_break_minutes = new_break
            if not self.reward_break_item_id or time.time() >= self.reward_break_end_ts:
                self.reward_break_duration_sec = new_break * 60

            old_goal_lbl = format_goal_short_tr(old_goal)
            new_goal_lbl = format_goal_short_tr(new_goal)

        self.add_log(
            f"⚙️ Mola Barajı Güncellendi: Hedef {old_goal_lbl} → {new_goal_lbl} | Mola: {new_break} Dk "
            f"(Baraj ilerlemesi adaletli ölçekle korundu)."
        )
        self._notify_change()
        return {
            "old_goal_sec": old_goal,
            "new_goal_sec": new_goal,
            "old_watched_sec": old_watched,
            "new_watched_sec": new_watched,
            "scale_factor": scale_factor,
            "break_minutes": new_break,
        }

    def claim_reward_break(self, item_id: str) -> bool:
        """
        Ders izleme hedefi dolduğunda kullanıcının seçtiği YALNIZCA BİR
        uygulamanın veya sitenin (ve varsa diğer menüdeki ikizinin, örn. Instagram Lite <-> Instagram Web)
        kilidini seçili mola süresi (5 / 10 / 20 / 30 dk) boyunca kaldırır.
        Süre sonunda otomatik olarak hepsini tekrar kilitler.
        """
        with self.lock:
            if item_id not in self.items:
                return False
            linked_ids = self._find_linked_break_ids(item_id)
            self.items[item_id]["blocked"] = False
            self.items[item_id]["until_ts"] = 0.0
            for lid in linked_ids:
                if lid in self.items:
                    self.items[lid]["blocked"] = False
                    self.items[lid]["until_ts"] = 0.0

            break_mins = int(self.reward_break_minutes)
            self.reward_break_duration_sec = break_mins * 60
            self.reward_break_item_id = item_id
            self.reward_break_related_ids = linked_ids
            self.reward_break_end_ts = time.time() + self.reward_break_duration_sec
            self.study_watched_seconds = 0.0
            self.reward_available = False
            self.reward_popup_shown = False
            name = self.items[item_id]["name"]
            if linked_ids:
                linked_names = ", ".join(self.items[lid]["name"] for lid in linked_ids if lid in self.items)
                name = f"{name} (+ {linked_names})"

        self.sync_hosts_file()
        self.add_log(f"🎉 Ödül Molası Başladı: {name} {break_mins} dakikalığına açıldı!")
        self._notify_change()
        return True

    def dismiss_reward_without_break(self):
        """Kullanıcı mola kullanmadan çalışmaya devam etmek isterse sayacı sıfırlar."""
        with self.lock:
            self.study_watched_seconds = 0.0
            self.reward_available = False
            self.reward_popup_shown = False
        self._notify_change()

    def get_emergency_status(self) -> dict:
        now = time.time()
        with self.lock:
            active = bool(self.emergency_active and self.emergency_end_ts > now)
            rem_active = max(0, int(self.emergency_end_ts - now)) if active else 0
            elapsed_since_use = now - self.emergency_last_used_ts
            cooldown_rem = max(0, int(EMERGENCY_COOLDOWN_SECONDS - elapsed_since_use))
            can_use = (not active) and (cooldown_rem == 0)
            return {
                "active": active,
                "rem_active_sec": rem_active,
                "can_use": can_use,
                "cooldown_rem_sec": cooldown_rem,
            }

    def trigger_emergency_unlock(self) -> tuple:
        """
        Haftada yalnızca 1 kez kullanılabilen Acil Durum Butonu:
        Tüm kilitli uygulama ve siteleri 30 dakikalığına açar, 30 dakika sonunda otomatik tekrar kilitler.
        """
        now = time.time()
        with self.lock:
            if self.emergency_active and self.emergency_end_ts > now:
                return False, "🚨 Acil Durum Modu zaten şu an aktif!"

            elapsed = now - self.emergency_last_used_ts
            if elapsed < EMERGENCY_COOLDOWN_SECONDS:
                rem = int(EMERGENCY_COOLDOWN_SECONDS - elapsed)
                days = rem // 86400
                hrs = (rem % 86400) // 3600
                mins = (rem % 3600) // 60
                return (
                    False,
                    f"⛔ Haftalık Acil Durum hakkınızı zaten kullandınız! Yeni hak için kalan süre: {days} gün {hrs} saat {mins} dk."
                )

            blocked_ids = [item_id for item_id, item in self.items.items() if item.get("blocked")]
            if not blocked_ids:
                return False, "ℹ️ Şu an kilitli hiçbir uygulama veya site bulunmuyor (Hakkınız harcanmadı)."

            self.emergency_saved_blocked_ids = blocked_ids
            self.emergency_active = True
            self.emergency_end_ts = now + EMERGENCY_DURATION_SECONDS
            self.emergency_last_used_ts = now

            for bid in blocked_ids:
                self.items[bid]["blocked"] = False
                self.items[bid]["until_ts"] = 0.0

        self.sync_hosts_file()
        self.add_log("🚨 ACİL DURUM BUTONU KULLANILDI: Tüm kilitler 30 dakikalığına açıldı (1 hafta boyunca tekrar kullanılamaz).")
        self._notify_change()
        return True, "🚨 Acil Durum Modu Başladı! Tüm engeller 30 dakikalığına kaldırıldı; 30 dk sonunda otomatik tekrar kilitlenecek."

    def _ensure_day_bucket(self, day_str: str = "") -> dict:
        if not day_str:
            day_str = datetime.now().strftime("%Y-%m-%d")
        bucket = self.daily_history.get(day_str)
        if not isinstance(bucket, dict):
            bucket = {
                "seconds": {s["id"]: 0.0 for s in SUBJECT_DEFINITIONS},
                "questions": {s["id"]: 0 for s in SUBJECT_DEFINITIONS},
            }
            self.daily_history[day_str] = bucket
        else:
            if "seconds" not in bucket or not isinstance(bucket["seconds"], dict):
                bucket["seconds"] = {s["id"]: 0.0 for s in SUBJECT_DEFINITIONS}
            if "questions" not in bucket or not isinstance(bucket["questions"], dict):
                bucket["questions"] = {s["id"]: 0 for s in SUBJECT_DEFINITIONS}
            for s in SUBJECT_DEFINITIONS:
                sid = s["id"]
                if sid not in bucket["seconds"]:
                    bucket["seconds"][sid] = 0.0
                if sid not in bucket["questions"]:
                    bucket["questions"][sid] = 0
        return bucket

    def _record_study_seconds(self, subj_id: str, dt: float):
        if dt <= 0.0:
            return
        self.subject_seconds[subj_id] = self.subject_seconds.get(subj_id, 0.0) + dt
        bucket = self._ensure_day_bucket()
        bucket["seconds"][subj_id] = float(bucket["seconds"].get(subj_id, 0.0)) + dt

    def add_solved_questions(self, subject_id: str, count: int) -> int:
        """
        Belirtilen derse çözülen soru sayısını kümülatif (üzerine ekleyerek) kaydeder.
        Örn: Önce 7, sonra 10 girildiğinde toplam 17 soru olarak güncellenir.
        Eğer count == 0 girilirse 'Bu periyotta soru çözülmedi (Konu çalışıldı)' olarak işaretler.
        """
        if count < 0:
            return 0
        with self.lock:
            if subject_id not in self.subject_questions:
                self.subject_questions[subject_id] = 0
            if count == 0:
                self.subject_last_session_status[subject_id] = "no_questions"
                new_total = int(self.subject_questions.get(subject_id, 0))
            else:
                self.subject_questions[subject_id] = int(self.subject_questions.get(subject_id, 0)) + int(count)
                bucket = self._ensure_day_bucket()
                bucket["questions"][subject_id] = int(bucket["questions"].get(subject_id, 0)) + int(count)
                self.subject_last_session_status[subject_id] = f"+{int(count)}"
                new_total = self.subject_questions[subject_id]

            if self.last_stopped_manual_subject_id == subject_id:
                self.last_stopped_manual_subject_id = ""
                self.last_stopped_manual_ts = 0.0
            subj_info = get_subject_info(subject_id)

        if count == 0:
            self.add_log(f"📖 {subj_info['name']}: Bu periyotta soru çözülmedi (Konu çalışması olarak kaydedildi).")
        else:
            self.add_log(f"📝 {subj_info['name']}: +{count} çözülen soru eklendi (Toplam: {new_total} soru).")
        self._notify_change()
        return new_total

    def get_stats_for_period(self, period_key: str = "all") -> tuple:
        """
        Seçilen zaman dilimine ('today', 'week', 'month', 'all') göre
        (subject_seconds_dict, subject_questions_dict) döndürür.
        """
        with self.lock:
            sec_out = {s["id"]: 0.0 for s in SUBJECT_DEFINITIONS}
            q_out = {s["id"]: 0 for s in SUBJECT_DEFINITIONS}

            if period_key == "all":
                for sid in sec_out:
                    sec_out[sid] = float(self.subject_seconds.get(sid, 0.0))
                    q_out[sid] = int(self.subject_questions.get(sid, 0))
                return sec_out, q_out

            now_dt = datetime.now()
            today_date = now_dt.date()
            today_str = today_date.strftime("%Y-%m-%d")
            monday_date = today_date - timedelta(days=today_date.weekday())
            month_prefix = today_date.strftime("%Y-%m-")

            for day_key, bucket in self.daily_history.items():
                if not isinstance(bucket, dict):
                    continue
                include = False
                if period_key == "today":
                    include = (day_key == today_str)
                elif period_key == "month":
                    include = day_key.startswith(month_prefix)
                elif period_key == "week":
                    try:
                        d_obj = datetime.strptime(day_key, "%Y-%m-%d").date()
                        include = (monday_date <= d_obj <= today_date)
                    except Exception:
                        include = False

                if include:
                    b_sec = bucket.get("seconds", {})
                    b_q = bucket.get("questions", {})
                    for sid in sec_out:
                        sec_out[sid] += float(b_sec.get(sid, 0.0))
                        q_out[sid] += int(b_q.get(sid, 0))

            return sec_out, q_out

    def toggle_manual_study(self, subject_id: str) -> bool:
        """
        Bilgisayar dışında (test çözerken / kitap çalışırken) her derse özel manuel Başlat/Durdur sayacı.
        Hem ilgili dersin süresini hem de 2 saatlik ödül mola sayacını ilerletir.
        Durdurulduğunda o dersin altındaki soru giriş alanını öne çıkarır.
        """
        with self.lock:
            if self.manual_study_active and self.manual_study_subject_id == subject_id:
                self.manual_study_active = False
                self.manual_study_subject_id = ""
                self.is_study_counting = False
                self.last_stopped_manual_subject_id = subject_id
                self.last_stopped_manual_ts = time.time()
                active_now = False
            else:
                if self.manual_study_active and self.manual_study_subject_id:
                    self.last_stopped_manual_subject_id = self.manual_study_subject_id
                    self.last_stopped_manual_ts = time.time()
                self.manual_study_active = True
                self.manual_study_subject_id = subject_id
                self._last_loop_ts = time.time()
                active_now = True
        self._notify_change()
        return active_now

    def stop_manual_study(self):
        with self.lock:
            if self.manual_study_active and self.manual_study_subject_id:
                self.last_stopped_manual_subject_id = self.manual_study_subject_id
                self.last_stopped_manual_ts = time.time()
            self.manual_study_active = False
            self.manual_study_subject_id = ""
            self.is_study_counting = False
        self._notify_change()

    def set_preferred_solution_subject(self, subj_id: str):
        with self.lock:
            self.preferred_solution_subject = subj_id
        self.save_state()

    def get_study_sources(self) -> list:
        with self.lock:
            return [dict(s) for s in self.study_sources]

    def add_study_source(self, raw_input: str, subject_id: str = "soru_cozum") -> tuple:
        """
        Kaynak Siteler menüsüne yeni bir ders/video çözüm sitesi ekler.
        Dönüş: (eklenen_kaynak_veya_None, mesaj)
        """
        raw = (raw_input or "").strip()
        if not raw:
            return None, "⚠️ Lütfen eklenecek kaynak sitenin adını veya adresini (örn: 3dyayinlari.com) yazın."

        src_obj = build_custom_study_source(raw, subject_id=subject_id)
        if not src_obj:
            return None, "⚠️ Geçerli bir site adı veya adresi girilemedi."

        with self.lock:
            for existing in self.study_sources:
                if (
                    existing["id"] == src_obj["id"]
                    or existing.get("domain", "").lower() == src_obj.get("domain", "").lower()
                    or existing.get("name", "").lower() == src_obj.get("name", "").lower()
                ):
                    if existing.get("locked") or existing["id"] == "src_youtube":
                        return None, "🔒 YouTube sabit sistem kaynağıdır; değiştirilemez ve silinemez."
                    existing["subject_id"] = src_obj["subject_id"]
                    for kw in src_obj.get("keywords", []):
                        if kw not in existing.get("keywords", []):
                            existing.setdefault("keywords", []).append(kw)
                    set_dynamic_study_sources(self.study_sources)
                    cat_lbl = get_source_category_label(existing["subject_id"])
                    self.add_log(f"🌐 Kaynak site güncellendi: {existing['name']} → {cat_lbl}")
                    self._notify_change()
                    return dict(existing), f"'{existing['name']}' kaynağı '{cat_lbl}' kategorisine güncellendi."

            self.study_sources.append(src_obj)
            set_dynamic_study_sources(self.study_sources)
            cat_lbl = get_source_category_label(src_obj["subject_id"])

        self.add_log(f"🌐 Yeni kaynak site eklendi: {src_obj['name']} ({cat_lbl})")
        self._notify_change()
        return dict(src_obj), f"✅ '{src_obj['name']}' kaynak sitelere eklendi! İzlenen videolar '{cat_lbl}' kategorisine işleyecek."

    def update_study_source_category(self, source_id: str, new_subject_id: str) -> tuple:
        """Var olan bir kaynak sitenin ders/kategori hedefini değiştirir (YouTube hariç)."""
        valid_ids = {opt["id"] for opt in SOURCE_CATEGORY_OPTIONS}
        if new_subject_id not in valid_ids:
            new_subject_id = "soru_cozum"

        with self.lock:
            for s in self.study_sources:
                if s.get("id") == source_id:
                    if s.get("locked") or source_id == "src_youtube":
                        return False, "🔒 YouTube sabit sistem kaynağıdır ve değiştirilemez."
                    s["subject_id"] = new_subject_id
                    src_name = s.get("name", source_id)
                    set_dynamic_study_sources(self.study_sources)
                    cat_lbl = get_source_category_label(new_subject_id)
                    break
            else:
                return False, "⚠️ Kaynak site bulunamadı."

        self.add_log(f"🌐 '{src_name}' kaynak kategorisi güncellendi → {cat_lbl}")
        self._notify_change()
        return True, f"✅ '{src_name}' kaynağından izlenen videolar artık '{cat_lbl}' kategorisine işleyecek."

    def remove_study_source(self, source_id: str) -> tuple:
        """Kaynak Siteler menüsünden kaynak siler (YouTube silinemez)."""
        with self.lock:
            for idx, s in enumerate(self.study_sources):
                if s.get("id") == source_id:
                    if s.get("locked") or source_id == "src_youtube":
                        return False, "🔒 YouTube sabit sistem kaynağıdır ve silinemez!"
                    removed = self.study_sources.pop(idx)
                    set_dynamic_study_sources(self.study_sources)
                    rem_name = removed.get("name", source_id)
                    break
            else:
                return False, "⚠️ Silinecek kaynak site bulunamadı."

        self.add_log(f"🗑️ Kaynak site listeden kaldırıldı: {rem_name}")
        self._notify_change()
        return True, f"🗑️ '{rem_name}' kaynak sitelerden kaldırıldı."

    def reset_subject_stats(self):
        with self.lock:
            for k in list(self.subject_seconds.keys()):
                self.subject_seconds[k] = 0.0
            for k in list(self.subject_questions.keys()):
                self.subject_questions[k] = 0
            self.daily_history = {}
        self._notify_change()

    def _detect_browser_pause_input(self, is_browser_fg: bool, video_hwnd: int) -> bool:
        """
        Kullanıcı YouTube veya Kaynak Siteler üzerinde videoyu duraklatmak için:
        - Boşluk (Space), 'K' veya Medya Oynat/Duraklat tuşuna bastığında, VEYA
        - Tarayıcı penceresinin video/içerik alanına (sekme/adres çubuğunun altına) sol tıkladığında
        bunu donanımsal olarak (<0.05 sn) algılar.
        """
        try:
            user32 = ctypes.windll.user32
            if user32.GetAsyncKeyState(0xB3) & 0x8001:  # VK_MEDIA_PLAY_PAUSE
                return True
            if not is_browser_fg:
                return False
            if (user32.GetAsyncKeyState(0x20) & 0x8001) or (user32.GetAsyncKeyState(0x4B) & 0x8001):
                return True
            if user32.GetAsyncKeyState(0x01) & 0x8001:  # VK_LBUTTON
                if not video_hwnd:
                    return True
                rect = wintypes.RECT()
                pt = wintypes.POINT()
                if user32.GetWindowRect(video_hwnd, ctypes.byref(rect)) and user32.GetCursorPos(ctypes.byref(pt)):
                    if (rect.left <= pt.x <= rect.right) and ((rect.top + 82) <= pt.y <= rect.bottom):
                        return True
        except Exception:
            pass
        return False

    def _update_study_tracker(self):
        now = time.time()
        raw_dt = now - self._last_loop_ts
        self._last_loop_ts = now

        # Bilgisayar kapatılıp açıldıysa (Hızlı Başlatma / Uyku / Hibernation nedeniyle >90 sn sıçrama olduysa)
        # 2 saatlik ödül mola sayacını sıfırla (Ders Sürelerim korunur!)
        if raw_dt > 90.0:
            with self.lock:
                self.study_watched_seconds = 0.0
                self.reward_available = False
                self.reward_popup_shown = False
                self.manual_study_active = False
                self.manual_study_subject_id = ""
                self.current_study_video = ""
                self.current_study_subject_id = ""
                self.is_study_counting = False
            self._notify_change()
            return

        dt = max(0.0, min(1.0, raw_dt))

        # Cihaz açıkken her 5 saniyede bir canlılık zaman damgasını (heartbeat) kaydet
        if now - self._last_heartbeat_save_ts >= 5.0:
            self._last_heartbeat_save_ts = now
            self.save_state()

        # 2 saatlik baraj dolduysa veya 10 dakikalık ödül molasındaysak TÜM SAYAÇLARI ANINDA DURDUR!
        with self.lock:
            if self.reward_available or (self.reward_break_item_id and now < self.reward_break_end_ts):
                self.current_study_video = ""
                self.current_study_subject_id = ""
                self.is_study_counting = False
                self.manual_study_active = False
                self.manual_study_subject_id = ""
                return
            man_active = self.manual_study_active
            man_subj = self.manual_study_subject_id

        # 1. Durum: Kullanıcı bilgisayar dışında test/konu çalışmak için Manuel Ders Sayacını başlattıysa
        if man_active and man_subj:
            subj_info = get_subject_info(man_subj)
            with self.lock:
                self.current_study_video = f"Test / Masa Başı Çalışma ({subj_info['name']})"
                self.current_study_subject_id = man_subj
                self.is_study_counting = True
                self._record_study_seconds(man_subj, dt)
                self.study_watched_seconds = min(
                    float(self.study_goal_seconds),
                    self.study_watched_seconds + dt
                )
                if self.study_watched_seconds >= self.study_goal_seconds:
                    # Baraj geçildiği anda tüm sayma işlemlerini ANINDA durdur!
                    self.reward_available = True
                    self.reward_popup_shown = False
                    self.is_study_counting = False
                    self.last_stopped_manual_subject_id = man_subj
                    self.last_stopped_manual_ts = now
                    self.manual_study_active = False
                    self.manual_study_subject_id = ""
                    goal_lbl = format_goal_short_tr(self.study_goal_seconds)
                    self.add_log(f"🏆 {goal_lbl} ders çalışma hedefi tamamlandı! Tüm sayaçlar durduruldu, {self.reward_break_minutes} dk mola hakkı kazanıldı.")
                    self._notify_change()
                elif now - self._last_study_save_ts >= 2.0:
                    self._last_study_save_ts = now
                    self.save_state()
            return

        # 2. Durum: Tarayıcıda YouTube veya Kaynak Siteler ders videosu takibi
        if self._audio_detector is None:
            self._audio_detector = AudioPeakDetector()
        if self._media_monitor is None:
            self._media_monitor = BrowserMediaSessionMonitor()

        video_title, is_fg, video_hwnd = find_active_study_video(return_hwnd=True)
        if not video_title:
            bg_study_title, bg_study_hwnd = self._media_monitor.get_playing_study_tab()
            if bg_study_title:
                video_title, video_hwnd = bg_study_title, bg_study_hwnd

        if not video_title:
            with self.lock:
                self._last_audio_ts = 0.0
                self._manual_pause_latched = False
                self.current_study_video = ""
                self.current_study_subject_id = ""
                self.is_study_counting = False
            return

        if self._detect_browser_pause_input(is_fg, video_hwnd):
            self._last_user_pause_input_ts = now

        audio_playing_now = self._audio_detector.is_audio_playing()
        if audio_playing_now:
            self._last_audio_ts = now
            self._manual_pause_latched = False
        elif (now - self._last_user_pause_input_ts) <= 0.65:
            # Kullanıcı tarayıcıda tıkladı veya Space/K tuşuna bastı ve ses kesildi -> ANINDA (<0.1 sn) duraklat!
            self._last_audio_ts = 0.0
            self._manual_pause_latched = True

        # Yan sütun (sidebar mini oynatıcı / inline preview) ve SMTC/TabBar ana medya oturumu doğrulaması:
        verified_ok, verified_title, block_reason = self._media_monitor.verify_main_study_video(
            video_title, video_hwnd
        )

        with self.lock:
            if not verified_ok:
                # Kullanıcı videoyu duraklattıysa veya ders dışı ses/yan sütun algılandıysa ANINDA durdur!
                self._last_audio_ts = 0.0
                self.current_study_subject_id = detect_subject_id(video_title, self.preferred_solution_subject, hwnd=video_hwnd)
                self.is_study_counting = False
                if block_reason == "non_study_playing":
                    self.current_study_video = (
                        verified_title
                        if (verified_title and verified_title.startswith("🚫"))
                        else "🚫 Ders Dışı Ses / Müzik Algılandı — Derse Sayılmıyor!"
                    )
                elif block_reason == "sidebar_hover" and audio_playing_now:
                    self.current_study_video = "🚫 Yan Sütun (Mini Oynatıcı) Üzerindesiniz — Derse Sayılmıyor!"
                elif block_reason == "main_video_paused" and audio_playing_now:
                    self.current_study_video = "🚫 Ders Sekmesi Duraklatıldı (Başka Sekme / Önizleme Sesi Sayılmaz!)"
                else:
                    self.current_study_video = video_title
                return

            effective_title = verified_title or video_title
            self.current_study_video = effective_title
            subj_id = detect_subject_id(effective_title, self.preferred_solution_subject, hwnd=video_hwnd)
            self.current_study_subject_id = subj_id

            # Eğer kullanıcı tıklayarak/Space ile videoyu duraklattıysa ve ses yoksa:
            # (SMTC henüz güncellenmemiş olsa veya gömülü oynatıcıda SMTC olmasa bile) ANINDA durdur!
            if self._manual_pause_latched and not audio_playing_now:
                if (now - self._last_user_pause_input_ts) > 0.70 and block_reason == "confirmed_playing":
                    # Tıklamadan 0.7 sn geçti ve Windows SMTC hâlâ 'Playing' diyor (video durmamış, hoca sessiz):
                    self._manual_pause_latched = False
                else:
                    self.is_study_counting = False
                    return

            # Hocanın nefes alma, soru okuma veya tahtaya/tablete sessizce işlem yazma anlarında
            # (YouTube ve Kaynak Siteler dahil) video oynatıcısı 'playing' durumundaysa
            # veya kaynak sitede yakın zamanda ses algılandıysa süreyi ASLA kesme!
            is_sol_site = is_solution_site_title(effective_title, hwnd=video_hwnd)
            grace_seconds = 30.0 if (block_reason == "confirmed_playing" or is_sol_site) else 15.0
            in_speech_grace = (self._last_audio_ts > 0.0) and ((now - self._last_audio_ts) <= grace_seconds)
            player_confirmed_playing = (block_reason == "confirmed_playing")

            if audio_playing_now or in_speech_grace or player_confirmed_playing:
                self.is_study_counting = True
                self._record_study_seconds(subj_id, dt)
                self.study_watched_seconds = min(
                    float(self.study_goal_seconds),
                    self.study_watched_seconds + dt
                )
                if self.study_watched_seconds >= self.study_goal_seconds:
                    # Baraj geçildiği anda tüm sayma işlemlerini ANINDA durdur!
                    self.reward_available = True
                    self.reward_popup_shown = False
                    self.is_study_counting = False
                    self.manual_study_active = False
                    self.manual_study_subject_id = ""
                    goal_lbl = format_goal_short_tr(self.study_goal_seconds)
                    self.add_log(f"🏆 {goal_lbl} ders izleme hedefi tamamlandı! Tüm sayaçlar durduruldu, {self.reward_break_minutes} dk mola hakkı kazanıldı.")
                    self._notify_change()
                elif now - self._last_study_save_ts >= 2.0:
                    self._last_study_save_ts = now
                    self.save_state()
            else:
                self.is_study_counting = False

    def get_tyt_countdown(self) -> dict:
        info = self.self_defense.get_countdown_info()
        info["committed"] = bool(self.lock_target_committed)
        return info

    def is_tyt_unlocked(self) -> bool:
        return self.self_defense.is_unlock_date_reached()

    def update_lock_target(
        self,
        new_unlock_dt: datetime,
        target_title: str,
        countdown_prefix: str = "Hedef Kilidi",
        target_badge: str = "ODAK",
        preset_id: str = "custom",
    ) -> tuple:
        """
        Custom Lock Chooser (Özel Kilit Hedefi & Tarih Seçici) ayarlarını kaydeder.
        Katı Koruma Kuralı:
        - Eğer mevcut bir kilit aktifse (süresi henüz dolmamışsa) ve daha önce kilit onaylanmışsa (committed),
          kullanıcı tarihi YALNIZCA mevcut tarihten ileriye uzatabilir veya adını değiştirebilir;
          tarihi erkene çekerek kilidi erken açma hilesi yapamaz!
        - Mevcut kilit süresi dolduğunda (TYT/hedef bittiğinde) veya ilk kurulumda ise
          gelecekteki herhangi bir tarih serbestçe seçilip yeni kilit başlatılabilir.
        """
        now_ts = self.self_defense.get_verified_timestamp()
        new_ts = float(new_unlock_dt.timestamp())
        cur_ts = float(self.self_defense.unlock_timestamp)
        cur_unlocked = (now_ts >= cur_ts)

        if new_ts <= now_ts + 60:
            return False, "⚠️ Seçilen kilit açılış tarihi gelecekte bir tarih olmalıdır!"

        with self.lock:
            if self.lock_target_committed and not cur_unlocked:
                # Mevcut kilit hâlâ aktif: Tarih erkene çekilemez!
                if new_ts < (cur_ts - 60):
                    return (
                        False,
                        f"⛔ Katı Koruma Aktif: Mevcut kilit süresi ({self.self_defense.unlock_date_str}) dolmadan "
                        f"bitiş tarihini erkene çekemezsiniz! Tarihi yalnızca ileriye uzatabilir veya mevcut hedef bittiğinde yeni bir tarih seçebilirsiniz.",
                    )

            clean_title = (target_title or "Özel Odak Hedefi").strip()
            clean_prefix = (countdown_prefix or "Hedef Kilidi").strip()
            clean_badge = (target_badge or "ODAK").strip()[:14]

            self.self_defense.configure_lock_target(
                unlock_ts=new_ts,
                target_title=clean_title,
                countdown_prefix=clean_prefix,
                target_badge=clean_badge,
                preset_id=preset_id,
            )
            self.lock_target_committed = True
            self.tyt_auto_unlocked = False

            # Kilit bittikten sonra yeni bir hedef seçildiyse Antigravity koruma paketini tekrar kilitle
            active_break_ids = {self.reward_break_item_id} | set(self.reward_break_related_ids)
            for item_id, item in self.items.items():
                if item.get("antigravity_pick"):
                    if not self.emergency_active and item_id not in active_break_ids:
                        item["blocked"] = True

        self.sync_hosts_file()
        self.enforce_processes_once()
        self.enforce_browser_tabs_once()
        self.add_log(f"🔒 Kilit Hedefi Güncellendi: {clean_title} → {self.self_defense.unlock_date_str}")
        self._notify_change()
        return True, f"✅ Yeni Kilit Hedefi aktif: {clean_title} (Kilit Açılışı: {self.self_defense.unlock_date_str})"

    def _check_expirations(self):
        """Ödül molasının, 30 dk Acil Durum modunun, TYT kilit açılış tarihinin ve odak sayacının süresini kontrol eder."""
        now = time.time()
        changed = False
        relocked_name = None
        relocked_break_mins = self.reward_break_minutes
        emergency_relocked = False
        tyt_just_unlocked = False

        with self.lock:
            # 0) TYT'den 1 gün öncesine (18 Haziran 2027 Cuma 00:00) ulaşıldı mı?
            if not self.tyt_auto_unlocked and self.self_defense.is_unlock_date_reached():
                self.tyt_auto_unlocked = True
                self.emergency_active = False
                self.emergency_end_ts = 0.0
                self.reward_break_item_id = None
                self.reward_break_end_ts = 0.0
                for item in self.items.values():
                    item["blocked"] = False
                    item["until_ts"] = 0.0
                tyt_just_unlocked = True
                changed = True

            # 1) Ödül molası bitti mi? (Bittiyse doğrudan tekrar yasakla!)
            if self.reward_break_item_id and now >= self.reward_break_end_ts:
                rb_id = self.reward_break_item_id
                rb_rel = list(self.reward_break_related_ids)
                relocked_break_mins = max(1, int(round(self.reward_break_duration_sec / 60.0)))
                self.reward_break_item_id = None
                self.reward_break_related_ids = []
                self.reward_break_end_ts = 0.0
                if rb_id in self.items:
                    self.items[rb_id]["blocked"] = True
                    self.items[rb_id]["until_ts"] = 0.0
                    relocked_name = self.items[rb_id]["name"]
                for rid in rb_rel:
                    if rid in self.items:
                        self.items[rid]["blocked"] = True
                        self.items[rid]["until_ts"] = 0.0
                changed = True

            # 2) 30 dakikalık Acil Durum süresi bitti mi? (Bittiyse tüm kilitleri geri yükle!)
            if self.emergency_active and now >= self.emergency_end_ts:
                self.emergency_active = False
                self.emergency_end_ts = 0.0
                for bid in self.emergency_saved_blocked_ids:
                    if bid in self.items:
                        self.items[bid]["blocked"] = True
                        self.items[bid]["until_ts"] = 0.0
                emergency_relocked = True
                changed = True

            # 3) Genel sayaç bitti mi? (Katı modda kilitler açılmaz)
            if self.timer_active and now >= self.timer_end_ts:
                self.timer_active = False
                self.timer_end_ts = 0.0
                changed = True
                self.add_log("⏰ Odak sayacı süresi doldu.")

        if tyt_just_unlocked:
            self.self_defense.release_all_protections()
            self.sync_hosts_file(force_clean=True)
            self.add_log("🎉 18 Haziran 2027 (TYT'den 1 Gün Önce) geldi! Tüm kilitler ve silme koruması otomatik olarak kaldırıldı. Sınavda başarılar!")

        if relocked_name:
            self.add_log(f"🔒 {relocked_break_mins} dakikalık mola süresi doldu! {relocked_name} oyunun/sohbetin ortasında anında kapatıldı ve yasaklandı.")
            self.sync_hosts_file()
            self.enforce_processes_once()
            self.enforce_browser_tabs_once(force_all_windows=True)

        if emergency_relocked:
            self.add_log("🔒 30 dakikalık Acil Durum süresi doldu! Tüm uygulama, oyun ve siteler anında kapatıldı ve tekrar kilitlendi.")
            self.sync_hosts_file()
            self.enforce_processes_once()
            self.enforce_browser_tabs_once(force_all_windows=True)

        if changed:
            self._notify_change()

    def _enforcement_loop(self):
        attach_to_default_desktop()
        self._last_loop_ts = time.time()
        while self._running:
            try:
                now = time.time()
                self.self_defense.enforce_periodic()
                self._update_study_tracker()
                self._check_expirations()
                if now - self._last_proc_enforce_ts >= 1.2:
                    self._last_proc_enforce_ts = now
                    self.enforce_processes_once()
                self.enforce_browser_tabs_once()
            except Exception:
                pass
            time.sleep(0.10)

    def get_running_user_apps(self):
        """
         Sadece Görev Çubuğu (Taskbar) ve Sistem Tepsisi / Gizli Simgeler (Hidden Icons)
        içerisinde görünen aktif kullanıcı uygulamalarını döndürür.
        Arka plan sistem servislerini göstermez.
        """
        import winreg

        ignore_exes = set(SAFE_SYSTEM_PROCESSES) | {
            "explorer.exe", "python.exe", "pythonw.exe", "antigravity.exe",
            "nvcontainer.exe", "nvdisplay.container.exe", "nvsphelper64.exe",
            "nvidia overlay.exe", "securityhealthsystray.exe", "jucheck.exe",
            "jusched.exe", "textinputhost.exe", "applicationframehost.exe",
            "shellexperiencehost.exe", "startmenuexperiencehost.exe", "searchhost.exe",
            "widgets.exe", "widgetservice.exe", "msedgewebview2.exe", "conhost.exe",
            "cmd.exe", "powershell.exe", "pwsh.exe", "taskmgr.exe"
        }

        friendly_names = {
            "opera.exe": "Opera GX",
            "operagx.exe": "Opera GX",
            "browser_assistant.exe": "Opera GX Asistan",
            "chrome.exe": "Google Chrome",
            "msedge.exe": "Microsoft Edge",
            "brave.exe": "Brave",
            "firefox.exe": "Mozilla Firefox",
            "discord.exe": "Discord",
            "steam.exe": "Steam",
            "spotify.exe": "Spotify",
            "whatsapp.exe": "WhatsApp",
            "telegram.exe": "Telegram",
            "wallpaper64.exe": "Wallpaper Engine",
            "wallpaper32.exe": "Wallpaper Engine",
            "rainmeter.exe": "Rainmeter",
            "epicgameslauncher.exe": "Epic Games",
            "riotclientservices.exe": "Riot Client",
            "valorant.exe": "Valorant",
            "hd-player.exe": "BlueStacks 5",
            "hd-multiinstancemanager.exe": "BlueStacks Manager",
            "bluestacksweb.exe": "BlueStacks X",
            "robloxplayerbeta.exe": "Roblox",
            "robloxstudiobeta.exe": "Roblox Studio",
            "osu!.exe": "osu!",
            "tetr.io.exe": "TETR.IO",
            "capcut.exe": "CapCut",
            "obs64.exe": "OBS Studio",
            "photoshop.exe": "Adobe Photoshop",
        }

        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000
        GW_OWNER = 4
        DWMWA_CLOAKED = 14

        # 1. Görev Çubuğunda (Taskbar) açık penceresi olan süreçleri bul
        taskbar_pids = {}

        def _enum_cb(hwnd, _lparam):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                cloaked = ctypes.c_int(0)
                dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if cloaked.value != 0:
                    return True
                ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                owner = user32.GetWindow(hwnd, GW_OWNER)
                is_taskbar = (not (ex_style & WS_EX_TOOLWINDOW) and not owner) or bool(ex_style & WS_EX_APPWINDOW)
                if not is_taskbar:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value and pid.value not in taskbar_pids:
                    taskbar_pids[pid.value] = buf.value
            except Exception:
                pass
            return True

        cb_func = WNDENUMPROC(_enum_cb)
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            user32.EnumDesktopWindows(hdesk, cb_func, 0)
            user32.CloseDesktop(hdesk)
        else:
            user32.EnumWindows(cb_func, 0)

        # 2. Gizli Simgeler / Sistem Tepsisi (NotifyIconSettings) kayıtlarını oku
        tray_info = {}
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\NotifyIconSettings")
            idx = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(key, idx)
                    sub_key = winreg.OpenKey(key, sub_name)
                    exe_path = ""
                    tooltip = ""
                    try:
                        exe_path, _ = winreg.QueryValueEx(sub_key, "ExecutablePath")
                    except OSError:
                        pass
                    try:
                        tooltip, _ = winreg.QueryValueEx(sub_key, "InitialTooltip")
                    except OSError:
                        pass
                    if exe_path:
                        base = os.path.basename(exe_path).lower()
                        clean_tip = tooltip.splitlines()[0].strip() if tooltip else ""
                        if base not in tray_info or (clean_tip and not tray_info[base]):
                            tray_info[base] = clean_tip
                    idx += 1
                except OSError:
                    break
        except Exception:
            pass

        # 3. Çalışan süreçlerle eşleştir
        apps = {}
        my_pid = os.getpid()
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                pid = proc.info["pid"]
                if pid == my_pid or pid <= 4:
                    continue
                pname = proc.info["name"] or ""
                pname_low = pname.lower()
                if not pname_low or pname_low in ignore_exes:
                    continue

                in_taskbar = pid in taskbar_pids
                in_tray = pname_low in tray_info

                if not (in_taskbar or in_tray):
                    continue

                if pname_low not in apps:
                    disp = friendly_names.get(pname_low)
                    if not disp and in_tray and tray_info.get(pname_low):
                        disp = tray_info[pname_low]
                    if not disp:
                        disp = pname[:-4] if pname_low.endswith(".exe") else pname

                    exe_p = proc.info.get("exe") or ""
                    icon_png = extract_icon_to_cache(f"run_{pname_low}", target_path=exe_p)
                    if not icon_png:
                        icon_png = generate_badge_icon(f"run_{pname_low}", disp[0].upper(), "#3b82f6")

                    apps[pname_low] = {
                        "exe_name": pname,
                        "display_name": disp,
                        "source": "Görev Çubuğu" if in_taskbar else "Gizli Simgeler",
                        "exe_path": exe_p,
                        "icon_png": icon_png,
                    }
                elif in_taskbar and apps[pname_low]["source"] != "Görev Çubuğu":
                    apps[pname_low]["source"] = "Görev Çubuğu"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return sorted(apps.values(), key=lambda x: (x["source"] != "Görev Çubuğu", x["display_name"].lower()))

    def shutdown(self):
        self._running = False
        if self.settings.get("clean_hosts_on_exit", True):
            self.sync_hosts_file(force_clean=True)
        self.save_state()
