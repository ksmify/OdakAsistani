import os
import sys
import time
import shutil
import socket
import struct
import ctypes
from datetime import datetime, timedelta
import subprocess

# ==============================================================================
# VARSAYILAN HEDEF KİLİT TARİHİ (2027 YKS / TYT) VE HAZIR HEDEF ŞABLONLARI
# ==============================================================================
TYT_EXAM_DATE_STR = "19 Haziran 2027 Cumartesi"
TYT_UNLOCK_DATE_STR = "18 Haziran 2027 Cuma 00:00"
TYT_UNLOCK_DATETIME = datetime(2027, 6, 18, 0, 0, 0)
TYT_UNLOCK_TIMESTAMP = TYT_UNLOCK_DATETIME.timestamp()

TR_MONTH_NAMES = [
    "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
]
TR_MONTH_SHORT = [
    "", "Oca", "Şub", "Mar", "Nis", "May", "Haz",
    "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"
]
TR_WEEKDAY_NAMES = [
    "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"
]


def format_turkish_date_full(dt: datetime) -> str:
    m_name = TR_MONTH_NAMES[dt.month]
    w_name = TR_WEEKDAY_NAMES[dt.weekday()]
    return f"{dt.day:02d} {m_name} {dt.year} {w_name} {dt.hour:02d}:{dt.minute:02d}"


def format_turkish_date_short(dt: datetime) -> str:
    m_short = TR_MONTH_SHORT[dt.month]
    return f"{dt.day:02d} {m_short} {dt.year}"


def get_lock_target_presets() -> list:
    """Custom Lock Chooser için hazır sınav ve kamp hedef şablonlarını döndürür."""
    now = datetime.now()
    d_30 = (now + timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    d_90 = (now + timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
    return [
        {
            "id": "yks_2027",
            "title": "YKS 2027 (TYT / AYT)",
            "countdown_prefix": "TYT Kilidi",
            "badge": "YKS 2027",
            "year": 2027, "month": 6, "day": 18, "hour": 0, "minute": 0,
            "desc": "18 Haziran 2027 Cuma 00:00 (TYT'den 1 gün öncesi)"
        },
        {
            "id": "yks_2028",
            "title": "YKS 2028 (TYT / AYT)",
            "countdown_prefix": "TYT Kilidi",
            "badge": "YKS 2028",
            "year": 2028, "month": 6, "day": 16, "hour": 0, "minute": 0,
            "desc": "16 Haziran 2028 Cuma 00:00 (2028 YKS Hedefi)"
        },
        {
            "id": "kpss_2027",
            "title": "KPSS Hazırlık Kampı",
            "countdown_prefix": "KPSS Kilidi",
            "badge": "KPSS",
            "year": 2027, "month": 7, "day": 18, "hour": 0, "minute": 0,
            "desc": "18 Temmuz 2027 Pazar 00:00 (KPSS Genel Kültür / Yetenek)"
        },
        {
            "id": "dgs_2027",
            "title": "DGS Hazırlık Kampı",
            "countdown_prefix": "DGS Kilidi",
            "badge": "DGS",
            "year": 2027, "month": 6, "day": 20, "hour": 0, "minute": 0,
            "desc": "20 Haziran 2027 Pazar 00:00 (Dikey Geçiş Sınavı)"
        },
        {
            "id": "ales_2027",
            "title": "ALES Hazırlık Kampı",
            "countdown_prefix": "ALES Kilidi",
            "badge": "ALES",
            "year": 2027, "month": 5, "day": 16, "hour": 0, "minute": 0,
            "desc": "16 Mayıs 2027 Pazar 00:00 (ALES İlkbahar Dönemi)"
        },
        {
            "id": "lgs_2027",
            "title": "LGS Hazırlık Kampı",
            "countdown_prefix": "LGS Kilidi",
            "badge": "LGS",
            "year": 2027, "month": 6, "day": 6, "hour": 0, "minute": 0,
            "desc": "06 Haziran 2027 Pazar 00:00 (Liselere Geçiş Sınavı)"
        },
        {
            "id": "finaller_30g",
            "title": "Vize / Final Odak Kampı (+30 Gün)",
            "countdown_prefix": "Final Kilidi",
            "badge": "FİNAL",
            "year": d_30.year, "month": d_30.month, "day": d_30.day, "hour": 0, "minute": 0,
            "desc": f"{format_turkish_date_full(d_30)} (30 Günlük Yoğun Dönem)"
        },
        {
            "id": "kamp_90g",
            "title": "90 Günlük Disiplin Kampı",
            "countdown_prefix": "Kamp Kilidi",
            "badge": "90 GÜN",
            "year": d_90.year, "month": d_90.month, "day": d_90.day, "hour": 0, "minute": 0,
            "desc": f"{format_turkish_date_full(d_90)} (90 Günlük Katı Odak)"
        },
        {
            "id": "custom",
            "title": "Özel Hedef & Tarih Seçimi",
            "countdown_prefix": "Hedef Kilidi",
            "badge": "ODAK",
            "year": 2027, "month": 6, "day": 18, "hour": 0, "minute": 0,
            "desc": "Kendi sınav/hedef adınızı ve kilit açılış tarihini aşağıdan belirleyin"
        },
    ]

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
SHORTCUT_PATH = os.path.join(DESKTOP_DIR, "Odak Asistanı.lnk")
VAULT_DIR = r"C:\ProgramData\OdakAsistaniVault"

CORE_FILES = [
    "main.py",
    "blocker_engine.py",
    "study_tracker.py",
    "presets.py",
    "nlp_parser.py",
    "pc_scanner.py",
    "self_defense.py",
    "odak_icon.ico",
]

# Windows CreateFileW sabitleri (Silme paylaşımını - FILE_SHARE_DELETE - hariç tutar)
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def query_ntp_utc_timestamp() -> float:
    """
    Kullanıcının bilgisayar saatini ileri alarak (örn. 2027'ye çekerek) kilidi kandırmasını
    önlemek için gerçek internet (NTP) zamanını sorgular.
    """
    ntp_hosts = ("time.windows.com", "pool.ntp.org", "time.google.com")
    for host in ntp_hosts:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(2.0)
            data = b"\x1b" + 47 * b"\0"
            client.sendto(data, (host, 123))
            resp, _ = client.recvfrom(1024)
            client.close()
            if resp and len(resp) >= 48:
                t = struct.unpack("!12I", resp)[10] - 2208988800
                if t > 1700000000:
                    return float(t)
        except Exception:
            pass
    return 0.0


# ==============================================================================
# SİLİNEMEZLİK & ÖZ-SAVUNMA KORUMA MODU (GITHUB / GENEL KULLANICI UYUMLULUĞU)
# ==============================================================================
# GitHub versiyonunda ve genel kullanıcı bilgisayarlarında silme engellemesi
# kesinlikle zorlanmaz. Kullanıcı dilediğinde klasörü silebilir ve kaldırabilir.
# Katı öz-savunma (NTFS deny-delete, kernel lock, vault respawn) varsayılan olarak KAPALIDIR.
ENABLE_STRICT_SELF_DEFENSE = False


class SelfDefenseManager:
    """
    Kilit Hedefi ve Süre Yönetimi:
    1) Geri sayım (Custom Lock Chooser) ve NTP zaman doğrulamasını yürütür.
    2) Masaüstü kısayolu ve başlangıç ayarlarını yönetir.
    3) ENABLE_STRICT_SELF_DEFENSE = False olduğunda kullanıcı dilediğinde uygulamayı silebilir,
       tüm kısıtlamalar ve hosts yasakları serbest bırakılabilir.
    """

    def __init__(self):
        self._locked_handles = {}
        self._ntp_offset = 0.0
        self._ntp_verified = False
        self._last_ntp_check_ts = 0.0
        self._last_defense_check_ts = 0.0
        self._protections_released = False

        # Dinamik Kilit Hedefi Bilgileri (Custom Lock Chooser ile güncellenebilir)
        self.target_preset_id = "yks_2027"
        self.target_title = "YKS 2027 (TYT / AYT)"
        self.countdown_prefix = "TYT Kilidi"
        self.target_badge = "YKS 2027"
        self.unlock_datetime = TYT_UNLOCK_DATETIME
        self.unlock_timestamp = float(TYT_UNLOCK_TIMESTAMP)
        self.unlock_date_str = TYT_UNLOCK_DATE_STR
        self.unlock_date_short = format_turkish_date_short(TYT_UNLOCK_DATETIME)

        # İlk NTP kontrolünü başlat
        self._sync_ntp_offset()

        # Eğer katı öz savunma kapalıysa (GitHub & taşınabilir mod):
        # Varsa eski NTFS engellerini serbest bırak, klasörün silinebilmesini sağla
        if not ENABLE_STRICT_SELF_DEFENSE:
            self.release_all_protections()
            self._ensure_desktop_shortcut()
            return

        if not self.is_unlock_date_reached():
            self.setup_vault_and_protect_all()
        else:
            self.release_all_protections()

    def configure_lock_target(
        self,
        unlock_ts: float,
        target_title: str = "YKS 2027 (TYT / AYT)",
        countdown_prefix: str = "TYT Kilidi",
        target_badge: str = "YKS 2027",
        preset_id: str = "yks_2027",
    ):
        """Kayıtlı durumdan veya Custom Lock Chooser'dan gelen hedef kilit bilgilerini uygular."""
        try:
            dt = datetime.fromtimestamp(float(unlock_ts))
        except Exception:
            dt = TYT_UNLOCK_DATETIME
            unlock_ts = float(TYT_UNLOCK_TIMESTAMP)

        self.target_preset_id = str(preset_id or "custom")
        self.target_title = str(target_title or "YKS 2027 (TYT / AYT)").strip()
        self.countdown_prefix = str(countdown_prefix or "TYT Kilidi").strip()
        self.target_badge = str(target_badge or "YKS 2027").strip()[:14]
        self.unlock_datetime = dt
        self.unlock_timestamp = float(unlock_ts)
        self.unlock_date_str = format_turkish_date_full(dt)
        self.unlock_date_short = format_turkish_date_short(dt)

        if not self.is_unlock_date_reached():
            self._protections_released = False
            self.setup_vault_and_protect_all()
        else:
            self.release_all_protections()

    def _sync_ntp_offset(self):
        now_local = time.time()
        if now_local - self._last_ntp_check_ts < 300.0 and self._ntp_verified:
            return
        self._last_ntp_check_ts = now_local
        ntp_ts = query_ntp_utc_timestamp()
        if ntp_ts > 0:
            self._ntp_offset = ntp_ts - now_local
            self._ntp_verified = True

    def get_verified_timestamp(self) -> float:
        """
        Bilgisayar saati ileri alınsa bile gerçek internet zamanına göre doğrulanmış zamanı döndürür.
        Eğer internet yoksa ve sistem saati şüpheli şekilde hedef tarihe sıçratılmışsa hileyi reddeder.
        """
        now_local = time.time()
        if now_local - self._last_ntp_check_ts >= 300.0:
            self._sync_ntp_offset()

        if self._ntp_verified:
            return now_local + self._ntp_offset

        if now_local >= self.unlock_timestamp:
            ntp_ts = query_ntp_utc_timestamp()
            if ntp_ts > 0:
                self._ntp_offset = ntp_ts - now_local
                self._ntp_verified = True
                return ntp_ts
        return now_local

    def is_unlock_date_reached(self) -> bool:
        return self.get_verified_timestamp() >= self.unlock_timestamp

    def get_countdown_info(self) -> dict:
        """
        Hedef kilit açılış tarihine kalan süreyi Gün : Saat : Dakika : Saniye olarak döndürür.
        """
        now_ts = self.get_verified_timestamp()
        rem = max(0, int(self.unlock_timestamp - now_ts))
        unlocked = rem <= 0

        days, rem_d = divmod(rem, 86400)
        hours, rem_h = divmod(rem_d, 3600)
        minutes, seconds = divmod(rem_h, 60)

        formatted_full = f"{days:02d} Gün : {hours:02d} Saat : {minutes:02d} Dakika : {seconds:02d} Saniye"
        formatted_short = f"{days:02d}G : {hours:02d}S : {minutes:02d}Dk : {seconds:02d}Sn"

        return {
            "unlocked": unlocked,
            "remaining_seconds": rem,
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "formatted_full": formatted_full,
            "formatted_short": formatted_short,
            "unlock_date_str": self.unlock_date_str,
            "unlock_date_short": self.unlock_date_short,
            "exam_date_str": self.target_title,
            "target_title": self.target_title,
            "countdown_prefix": self.countdown_prefix,
            "target_badge": self.target_badge,
            "preset_id": self.target_preset_id,
            "unlock_timestamp": self.unlock_timestamp,
            "year": self.unlock_datetime.year,
            "month": self.unlock_datetime.month,
            "day": self.unlock_datetime.day,
            "hour": self.unlock_datetime.hour,
            "minute": self.unlock_datetime.minute,
        }

    # ------------------------------------------------------------------
    # KERNEL HANDLE & NTFS SİLİNEMEZLİK KORUMASI
    # ------------------------------------------------------------------
    def _acquire_kernel_lock(self, path: str, is_dir: bool = False):
        """
        Dosyayı veya klasörü FILE_SHARE_DELETE olmadan açar.
        Katı savunma modu kapalıysa hiçbir kilit koymaz.
        """
        if not ENABLE_STRICT_SELF_DEFENSE:
            return
        norm_p = os.path.normcase(os.path.abspath(path))
        if norm_p in self._locked_handles:
            return
        if not os.path.exists(path):
            return
        try:
            flags = FILE_FLAG_BACKUP_SEMANTICS if is_dir else 0
            handle = ctypes.windll.kernel32.CreateFileW(
                path,
                GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE,  # FILE_SHARE_DELETE (0x04) YOK!
                None,
                OPEN_EXISTING,
                flags,
                None,
            )
            if handle and handle != INVALID_HANDLE_VALUE and handle != -1:
                self._locked_handles[norm_p] = handle
        except Exception:
            pass

    def _release_kernel_locks(self):
        for norm_p, handle in list(self._locked_handles.items()):
            try:
                ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                pass
        self._locked_handles.clear()

    def _apply_ntfs_deny_delete(self, path: str):
        """
        NTFS izinlerinde Everyone (*S-1-1-0) için yalnızca Silme (DE) iznini yasaklar.
        Katı savunma modu kapalıysa hiçbir NTFS kısıtlaması koymaz.
        """
        if not ENABLE_STRICT_SELF_DEFENSE:
            return
        if not os.path.exists(path):
            return
        try:
            subprocess.run(
                ["icacls", path, "/deny", "*S-1-1-0:(DE)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=4,
            )
        except Exception:
            pass

    def _remove_ntfs_deny_delete(self, path: str):
        if not os.path.exists(path):
            return
        try:
            subprocess.run(
                ["icacls", path, "/remove:d", "*S-1-1-0"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=4,
            )
        except Exception:
            pass

    def _ensure_desktop_shortcut(self):
        """
        Masaüstündeki 'Odak Asistanı.lnk' kısayolu silinmişse yedekten veya PowerShell ile anında geri oluşturur.
        """
        if os.path.exists(SHORTCUT_PATH) and os.path.getsize(SHORTCUT_PATH) > 100:
            return

        vault_lnk = os.path.join(VAULT_DIR, "Odak Asistanı.lnk")
        if os.path.exists(vault_lnk):
            try:
                self._remove_ntfs_deny_delete(SHORTCUT_PATH)
                shutil.copy2(vault_lnk, SHORTCUT_PATH)
                return
            except Exception:
                pass

        # Yedekte yoksa doğrudan oluştur
        try:
            odak_exe = os.path.join(APP_DIR, "OdakAsistani.exe")
            pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(odak_exe) and os.path.exists(pythonw_exe):
                try:
                    shutil.copy2(pythonw_exe, odak_exe)
                except Exception:
                    pass
            target_exe = odak_exe if os.path.exists(odak_exe) else (pythonw_exe if os.path.exists(pythonw_exe) else sys.executable)
            main_py = os.path.join(APP_DIR, "main.py")
            icon_ico = os.path.join(APP_DIR, "odak_icon.ico")
            ps_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{SHORTCUT_PATH}"); '
                f'$s.TargetPath = "{target_exe}"; '
                f'$s.Arguments = \'"{main_py}"\'; '
                f'$s.WorkingDirectory = "{APP_DIR}"; '
                f'$s.IconLocation = "{icon_ico},0"; '
                f'$s.Save()'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5,
            )
        except Exception:
            pass

    def _ensure_startup_persistence(self):
        """
        Kullanıcı Görev Yöneticisi -> Başlangıç Uygulamaları'ndan Odak Asistanı'nı devre dışı bıraksa bile
        otomatik olarak tekrar etkinleştirir ve bilgisayar açılır açılmaz uygulamanın ekranda açılmasını sağlar.
        Ayrıca eski 'Ders Odak' başlangıç kısayolunu ve kayıtlarını temizler.
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
            import winreg
            odak_exe = os.path.join(APP_DIR, "OdakAsistani.exe")
            pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            target_exe = odak_exe if os.path.exists(odak_exe) else (pythonw_exe if os.path.exists(pythonw_exe) else sys.executable)
            main_py = os.path.join(APP_DIR, "main.py")
            run_val = f'"{target_exe}" "{main_py}" --boot'

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
            ) as key:
                winreg.SetValueEx(key, "OdakAsistani", 0, winreg.REG_SZ, run_val)
                for old_name in ("Ders Odak", "DersOdak", "DersMotivasyon"):
                    try:
                        winreg.DeleteValue(key, old_name)
                    except Exception:
                        pass

            # StartupApproved\Run altında devre dışı bırakılmışsa (03...) tekrar etkin (02...) yap
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

            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder",
                0,
                winreg.KEY_SET_VALUE,
            ) as sf_key:
                try:
                    winreg.DeleteValue(sf_key, "Ders Odak.lnk")
                except Exception:
                    pass
        except Exception:
            pass

    def setup_vault_and_protect_all(self):
        """
        Kısayol ve başlangıç kayıtlarını kontrol eder.
        Eğer ENABLE_STRICT_SELF_DEFENSE aktifse ayrıca dosya kilitleri uygular.
        """
        self._ensure_desktop_shortcut()
        self._ensure_startup_persistence()

        if not ENABLE_STRICT_SELF_DEFENSE:
            # Taşınabilir / GitHub modunda silme koruması kesinlikle uygulanmaz
            self.release_all_protections()
            return

        try:
            os.makedirs(VAULT_DIR, exist_ok=True)
            ctypes.windll.kernel32.SetFileAttributesW(VAULT_DIR, 0x02)
        except Exception:
            pass

        # 1. Öz dosyaları yedekle
        for fname in CORE_FILES:
            src = os.path.join(APP_DIR, fname)
            dst = os.path.join(VAULT_DIR, fname)
            if os.path.exists(src):
                try:
                    if os.path.exists(dst):
                        self._remove_ntfs_deny_delete(dst)
                    shutil.copy2(src, dst)
                    self._apply_ntfs_deny_delete(dst)
                except Exception:
                    pass

        # 2. Masaüstü kısayolunu yedekle
        if os.path.exists(SHORTCUT_PATH):
            vault_lnk = os.path.join(VAULT_DIR, "Odak Asistanı.lnk")
            try:
                if os.path.exists(vault_lnk):
                    self._remove_ntfs_deny_delete(vault_lnk)
                shutil.copy2(SHORTCUT_PATH, vault_lnk)
                self._apply_ntfs_deny_delete(vault_lnk)
            except Exception:
                pass

        # 3. Ana klasör, dosyalar ve Masaüstü kısayoluna koruma uygula
        self._apply_ntfs_deny_delete(APP_DIR)
        self._acquire_kernel_lock(APP_DIR, is_dir=True)

        for fname in CORE_FILES:
            fpath = os.path.join(APP_DIR, fname)
            if os.path.exists(fpath):
                self._apply_ntfs_deny_delete(fpath)
                self._acquire_kernel_lock(fpath, is_dir=False)

        if os.path.exists(SHORTCUT_PATH):
            self._apply_ntfs_deny_delete(SHORTCUT_PATH)
            self._acquire_kernel_lock(SHORTCUT_PATH, is_dir=False)

    def enforce_periodic(self):
        """
        Arka plan döngüsünde periyodik kontrolleri yapar.
        Eğer katı savunma kapalıysa dosya kilitleme veya icacls alt süreçleri çalıştırmaz.
        """
        if not ENABLE_STRICT_SELF_DEFENSE:
            return

        now = time.time()
        if now - self._last_defense_check_ts < 10.0:
            return
        self._last_defense_check_ts = now

        if self.is_unlock_date_reached():
            if not self._protections_released:
                self.release_all_protections()
            return

        # Eksik dosya varsa kasadan geri yükle
        for fname in CORE_FILES:
            fpath = os.path.join(APP_DIR, fname)
            vpath = os.path.join(VAULT_DIR, fname)
            if not os.path.exists(fpath) and os.path.exists(vpath):
                try:
                    shutil.copy2(vpath, fpath)
                    self._apply_ntfs_deny_delete(fpath)
                except Exception:
                    pass
            if os.path.exists(fpath):
                self._acquire_kernel_lock(fpath, is_dir=False)

        # Masaüstü kısayolu kontrolü
        if not os.path.exists(SHORTCUT_PATH):
            self._ensure_desktop_shortcut()
            if os.path.exists(SHORTCUT_PATH):
                self._apply_ntfs_deny_delete(SHORTCUT_PATH)
        if os.path.exists(SHORTCUT_PATH):
            self._acquire_kernel_lock(SHORTCUT_PATH, is_dir=False)

        self._ensure_startup_persistence()

    def release_all_protections(self):
        """
        Tüm NTFS silme kısıtlamalarını ve kernel kilitlerini kaldırır.
        Uygulama klasörünün, dosyalarının ve kısayolunun kullanıcı tarafından
        kolayca silinebilmesini veya taşınabilmesini sağlar.
        """
        self._protections_released = True
        self._release_kernel_locks()
        self._remove_ntfs_deny_delete(SHORTCUT_PATH)
        self._remove_ntfs_deny_delete(APP_DIR)
        for fname in CORE_FILES:
            self._remove_ntfs_deny_delete(os.path.join(APP_DIR, fname))
            self._remove_ntfs_deny_delete(os.path.join(VAULT_DIR, fname))
        if os.path.exists(VAULT_DIR):
            self._remove_ntfs_deny_delete(VAULT_DIR)
            try:
                shutil.rmtree(VAULT_DIR, ignore_errors=True)
            except Exception:
                pass


def cleanup_and_uninstall():
    """
    Kullanıcı Odak Asistanı'nı tamamen kaldırmak istediğinde tüm kayıtları,
    hosts engellerini ve kısayolları temizler.
    """
    try:
        mgr = SelfDefenseManager()
        mgr.release_all_protections()
    except Exception:
        pass

    # Masaüstü kısayollarını sil
    for p in [SHORTCUT_PATH, os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "Odak Asistani.lnk")]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    # Windows başlangıç kayıtlarını temizle
    try:
        import winreg
        for subkey in [
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
        ]:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE) as k:
                    for vname in ["OdakAsistani", "Ders Odak", "DersOdak"]:
                        try:
                            winreg.DeleteValue(k, vname)
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass
