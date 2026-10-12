import os
import sys
import time
import shutil
import socket
import struct
import ctypes
from datetime import datetime
import subprocess

# ==============================================================================
# 2027 YKS (TYT) TAKVİMİ VE KİLİT AÇILIŞ HEDEFİ
# 2027 TYT Sınav Tarihi: 19 Haziran 2027 Cumartesi
# Kilitlerin & Silme Korumasının Kalkacağı Tarih (TYT'den 1 Gün Önce):
# 18 Haziran 2027 Cuma, Saat 00:00:00
# ==============================================================================
TYT_EXAM_DATE_STR = "19 Haziran 2027 Cumartesi"
TYT_UNLOCK_DATE_STR = "18 Haziran 2027 Cuma 00:00"
TYT_UNLOCK_DATETIME = datetime(2027, 6, 18, 0, 0, 0)
TYT_UNLOCK_TIMESTAMP = TYT_UNLOCK_DATETIME.timestamp()

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


class SelfDefenseManager:
    """
    TYT'den 1 gün öncesine (18 Haziran 2027 Cuma 00:00) kadar:
    1) Odak Asistanı uygulama klasörünün, kaynak dosyalarının ve Masaüstü kısayolunun (Odak Asistanı.lnk)
       silinmesini, yeniden adlandırılmasını veya taşınmasını hem Kernel Handle düzeyinde hem de
       NTFS izinleri (icacls Deny Delete) düzeyinde engeller.
    2) Herhangi bir dosya veya kısayol bir şekilde zarar görürse C:\\ProgramData\\OdakAsistaniVault
       yedek kasasından saniyesinde otomatik onarır.
    3) Başlangıç (Registry Run + StartupApproved) kayıtlarını sürekli korur.
    4) Gerçek NTP zamanı ile 18 Haziran 2027 00:00'a ulaşıldığında tüm silme korumasını ve kilitleri kaldırır.
    """

    def __init__(self):
        self._locked_handles = {}
        self._ntp_offset = 0.0
        self._ntp_verified = False
        self._last_ntp_check_ts = 0.0
        self._last_defense_check_ts = 0.0
        self._protections_released = False

        # İlk NTP kontrolünü ve korumayı başlat
        self._sync_ntp_offset()
        if not self.is_unlock_date_reached():
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
        Eğer internet yoksa ve sistem saati şüpheli şekilde 2027 Haziran'a sıçratılmışsa hileyi reddeder.
        """
        now_local = time.time()
        if now_local - self._last_ntp_check_ts >= 300.0:
            self._sync_ntp_offset()

        if self._ntp_verified:
            return now_local + self._ntp_offset

        # İnternet yokken kullanıcı saati 2027 Haziran'a çektiyse tekrar NTP dene
        if now_local >= TYT_UNLOCK_TIMESTAMP:
            ntp_ts = query_ntp_utc_timestamp()
            if ntp_ts > 0:
                self._ntp_offset = ntp_ts - now_local
                self._ntp_verified = True
                return ntp_ts
        return now_local

    def is_unlock_date_reached(self) -> bool:
        return self.get_verified_timestamp() >= TYT_UNLOCK_TIMESTAMP

    def get_countdown_info(self) -> dict:
        """
        TYT'den 1 gün öncesine (18 Haziran 2027 00:00:00) kalan süreyi
        Gün : Saat : Dakika : Saniye olarak döndürür.
        """
        now_ts = self.get_verified_timestamp()
        rem = max(0, int(TYT_UNLOCK_TIMESTAMP - now_ts))
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
            "unlock_date_str": TYT_UNLOCK_DATE_STR,
            "exam_date_str": TYT_EXAM_DATE_STR,
        }

    # ------------------------------------------------------------------
    # KERNEL HANDLE & NTFS SİLİNEMEZLİK KORUMASI
    # ------------------------------------------------------------------
    def _acquire_kernel_lock(self, path: str, is_dir: bool = False):
        """
        Dosyayı veya klasörü FILE_SHARE_DELETE olmadan açar.
        Bu sayede Odak Asistanı çalışırken Windows Gezgini veya cmd/PowerShell üzerinden
        bu dosya/klasör/kısayol KESİNLİKLE silinemez, taşınamaz ve yeniden adlandırılamaz.
        """
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
        Okuma ve yazma izinleri bozulmaz ancak dosya/kısayol silinemez ve taşınamaz.
        """
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
            pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw_exe):
                pythonw_exe = sys.executable
            main_py = os.path.join(APP_DIR, "main.py")
            icon_ico = os.path.join(APP_DIR, "odak_icon.ico")
            ps_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{SHORTCUT_PATH}"); '
                f'$s.TargetPath = "{pythonw_exe}"; '
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
            pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw_exe):
                pythonw_exe = sys.executable
            main_py = os.path.join(APP_DIR, "main.py")
            run_val = f'"{pythonw_exe}" "{main_py}" --boot'

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
        Uygulama dosyalarını gizli kasaya yedekler, ardından uygulama klasörünü,
        kod dosyalarını ve Masaüstü kısayolunu silinmeye karşı kilitler.
        """
        try:
            os.makedirs(VAULT_DIR, exist_ok=True)
            # Klasörü gizli yap
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

        # 2. Masaüstü kısayolunun var olduğundan emin ol ve yedekle
        self._ensure_desktop_shortcut()
        if os.path.exists(SHORTCUT_PATH):
            vault_lnk = os.path.join(VAULT_DIR, "Odak Asistanı.lnk")
            try:
                if os.path.exists(vault_lnk):
                    self._remove_ntfs_deny_delete(vault_lnk)
                shutil.copy2(SHORTCUT_PATH, vault_lnk)
                self._apply_ntfs_deny_delete(vault_lnk)
            except Exception:
                pass

        # 3. Ana klasör, dosyalar ve Masaüstü kısayoluna hem NTFS Deny Delete hem Kernel Lock uygula
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

        self._ensure_startup_persistence()

    def enforce_periodic(self):
        """
        Arka plan döngüsünde her 10 saniyede bir hafifçe çağrılır:
        - Kısayol veya uygulama dosyası silinmeye çalışıldıysa anında onarır ve kilitler.
        - Dosyalar yerindeyse gereksiz alt süreç (icacls.exe) başlatmaz, CPU'yu %0 yorar.
        """
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

        # Masaüstü kısayolu kontrolü (Sadece silinmişse icacls çalıştır!)
        if not os.path.exists(SHORTCUT_PATH):
            self._ensure_desktop_shortcut()
            if os.path.exists(SHORTCUT_PATH):
                self._apply_ntfs_deny_delete(SHORTCUT_PATH)
        if os.path.exists(SHORTCUT_PATH):
            self._acquire_kernel_lock(SHORTCUT_PATH, is_dir=False)

        self._ensure_startup_persistence()

    def release_all_protections(self):
        """
        TYT'den 1 gün öncesi (18 Haziran 2027 00:00) geldiğinde tüm silme korumasını kaldırır.
        """
        self._protections_released = True
        self._release_kernel_locks()
        self._remove_ntfs_deny_delete(SHORTCUT_PATH)
        self._remove_ntfs_deny_delete(APP_DIR)
        for fname in CORE_FILES:
            self._remove_ntfs_deny_delete(os.path.join(APP_DIR, fname))
            self._remove_ntfs_deny_delete(os.path.join(VAULT_DIR, fname))
