# -*- coding: utf-8 -*-
"""
Odak Asistanı - Bilgisayar Uygulama Tarayıcısı ve Gerçek İkon Çıkarıcı
Bilgisayardaki masaüstü ve başlat menüsü kısayollarını tarar,
gerçek Windows uygulama ikonlarını (.exe / .lnk / .ico) PNG olarak önbelleğe alır.
"""

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import re
import subprocess
import warnings
from PIL import Image, ImageDraw, ImageFont

warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_CACHE_DIR = os.path.join(BASE_DIR, "icon_cache")
PC_APPS_CACHE_FILE = os.path.join(BASE_DIR, "pc_apps_cache.json")

os.makedirs(ICON_CACHE_DIR, exist_ok=True)

shell32 = ctypes.windll.shell32
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName", wintypes.WCHAR * 80),
    ]


# İstenmeyen kurulum/kaldırma/yardım/sistem kısayollarını filtrelemek için kelimeler
SKIP_SHORTCUT_KEYWORDS = [
    "uninstall", "kaldır", "setup -", "about java", "check for updates",
    "configure java", "get help", "visit java", "support center",
    "yardım", "kılavuz", "redistributable", "command prompt", "powershell",
    "control panel", "denetim masası", "görev yöneticisi", "task manager",
    "hesap makinesi", "kayıt defteri", "regedit", "disk temizleme",
    "cleanmgr", "kaynak izleyicisi", "ekran alıntısı", "snipping tool",
    "file explorer", "run", "odak asistan", "ders odak", "capcut exports",
    "aygit secici", "device selector", "configuration editor", "nsight",
    "python 3.", "windows terminal", "astral uv", "antigravity",
    "bluestacks services", "bluestacks çoklu", "bluestacks manager",
    "windows media player legacy", "rampage spear v2", "benchmark"
]


def _hicon_to_pil(hicon, size: int = 32):
    """Win32 HICON tutamacını RGBA PIL.Image nesnesine dönüştürür."""
    try:
        hdc = user32.GetDC(0)
        mem_dc = gdi32.CreateCompatibleDC(hdc)
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = size
        bmi.biHeight = -size
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        bits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        old_bmp = gdi32.SelectObject(mem_dc, hbmp)

        user32.DrawIconEx(mem_dc, 0, 0, hicon, size, size, 0, 0, 0x0003)

        buf_len = size * size * 4
        raw = ctypes.string_at(bits, buf_len)
        img = Image.frombuffer("RGBA", (size, size), raw, "raw", "BGRA", 0, 1).copy()

        gdi32.SelectObject(mem_dc, old_bmp)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(0, hdc)
        return img
    except Exception:
        return None


def extract_icon_to_cache(cache_key: str, lnk_path: str = "", target_path: str = "", icon_loc: str = "") -> str:
    """
    Verilen kısayol veya .exe dosyasının gerçek Windows ikonunu çıkarıp
    icon_cache klasörüne 32x32 PNG olarak kaydeder ve dosya yolunu döndürür.
    """
    safe_key = hashlib.md5(cache_key.encode("utf-8", errors="ignore")).hexdigest()[:16]
    out_png = os.path.join(ICON_CACHE_DIR, f"{safe_key}.png")
    if os.path.exists(out_png):
        return out_png

    img = None

    # 1. icon_loc doğrudan bir .ico veya .exe gösteriyorsa
    if icon_loc:
        parts = icon_loc.split(",")
        ico_file = os.path.expandvars(parts[0].strip().strip('"'))
        ico_idx = 0
        if len(parts) > 1 and parts[1].strip().lstrip("-").isdigit():
            ico_idx = int(parts[1].strip())

        if os.path.exists(ico_file):
            if ico_file.lower().endswith((".ico", ".png")):
                try:
                    loaded = Image.open(ico_file).convert("RGBA")
                    img = loaded.resize((32, 32), Image.Resampling.LANCZOS)
                except Exception:
                    pass
            if img is None:
                img = _extract_from_binary(ico_file, ico_idx)

    # 2. .url dosyasıysa içindeki IconFile satırına bak
    if img is None and lnk_path and lnk_path.lower().endswith(".url") and os.path.exists(lnk_path):
        try:
            with open(lnk_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("IconFile="):
                        ico_f = line.split("=", 1)[1].strip()
                        if os.path.exists(ico_f):
                            if ico_f.lower().endswith((".ico", ".png")):
                                loaded = Image.open(ico_f).convert("RGBA")
                                img = loaded.resize((32, 32), Image.Resampling.LANCZOS)
                            else:
                                img = _extract_from_binary(ico_f, 0)
                        break
        except Exception:
            pass

    # 3. Target .exe üzerinden ExtractIconExW dene
    if img is None and target_path and os.path.exists(target_path):
        img = _extract_from_binary(target_path, 0)

    # 4. Kısayol (.lnk) üzerinden SHGetFileInfoW dene
    if img is None and lnk_path and os.path.exists(lnk_path):
        img = _extract_via_shgetfileinfo(lnk_path)

    # 5. Target üzerinden SHGetFileInfoW dene
    if img is None and target_path and os.path.exists(target_path):
        img = _extract_via_shgetfileinfo(target_path)

    if img is not None:
        try:
            img.save(out_png, "PNG")
            return out_png
        except Exception:
            pass
    return ""


def _extract_from_binary(file_path: str, icon_index: int = 0):
    try:
        large = (wintypes.HICON * 1)()
        small = (wintypes.HICON * 1)()
        shell32.ExtractIconExW(file_path, icon_index, large, small, 1)
        hicon = large[0] or small[0]
        img = None
        if hicon:
            img = _hicon_to_pil(hicon, 32)
        if large[0]:
            user32.DestroyIcon(large[0])
        if small[0]:
            user32.DestroyIcon(small[0])
        return img
    except Exception:
        return None


def _extract_via_shgetfileinfo(file_path: str):
    try:
        shfi = SHFILEINFOW()
        SHGFI_ICON = 0x000000100
        SHGFI_LARGEICON = 0x000000000
        shell32.SHGetFileInfoW(file_path, 0, ctypes.byref(shfi), ctypes.sizeof(shfi), SHGFI_ICON | SHGFI_LARGEICON)
        if shfi.hIcon:
            img = _hicon_to_pil(shfi.hIcon, 32)
            user32.DestroyIcon(shfi.hIcon)
            return img
    except Exception:
        pass
    return None


def generate_badge_icon(item_id: str, label_char: str, bg_hex: str) -> str:
    """Web siteleri için renkli, şık yuvarlatılmış rozet ikonu oluşturur."""
    out_png = os.path.join(ICON_CACHE_DIR, f"badge_{item_id}.png")
    if os.path.exists(out_png):
        return out_png

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg_hex = bg_hex.lstrip("#")
    r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
    draw.rounded_rectangle((4, 4, 60, 60), radius=16, fill=(r, g, b, 255))

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 30)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label_char, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((64 - tw) / 2, (64 - th) / 2 - 4), label_char, fill=(255, 255, 255, 255), font=font)

    img = img.resize((32, 32), Image.Resampling.LANCZOS)
    img.save(out_png, "PNG")
    return out_png


def scan_installed_pc_apps(force_rescan: bool = False) -> list:
    """
    Bilgisayardaki tüm kullanıcı uygulama ve oyunlarını (Masaüstü + Başlat Menüsü)
    tarar, gerçek ikonlarını çıkarır ve tekilleştirilmiş listesini döndürür.
    """
    if not force_rescan and os.path.exists(PC_APPS_CACHE_FILE):
        try:
            with open(PC_APPS_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached:
                return cached
        except Exception:
            pass

    ps_script = """
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $WshShell = New-Object -ComObject WScript.Shell
    $paths = @(
        [Environment]::GetFolderPath('Desktop'),
        [Environment]::GetFolderPath('CommonDesktopDirectory'),
        [Environment]::GetFolderPath('Programs'),
        [Environment]::GetFolderPath('CommonPrograms')
    )
    $results = @()
    foreach ($p in $paths) {
        if (Test-Path $p) {
            Get-ChildItem -Path $p -Recurse -Include *.lnk, *.url -ErrorAction SilentlyContinue | ForEach-Object {
                if ($_.Extension -eq '.lnk') {
                    try {
                        $sc = $WshShell.CreateShortcut($_.FullName)
                        $results += @{
                            name = $_.BaseName
                            lnk = $_.FullName
                            target = $sc.TargetPath
                            args = $sc.Arguments
                            icon = $sc.IconLocation
                        }
                    } catch {}
                } else {
                    $results += @{
                        name = $_.BaseName
                        lnk = $_.FullName
                        target = $_.FullName
                        args = ''
                        icon = ''
                    }
                }
            }
        }
    }
    $results | ConvertTo-Json -Compress
    """

    raw_items = []
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_script],
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10
        )
        if out and out.strip():
            raw_items = json.loads(out)
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
    except Exception:
        raw_items = []

    discovered = {}
    for entry in raw_items:
        raw_name = (entry.get("name") or "").strip()
        if not raw_name:
            continue
        name_low = raw_name.lower()

        if any(sk in name_low for sk in SKIP_SHORTCUT_KEYWORDS):
            continue

        # Parantez içi açıklamaları temizle (örn: "OBS Studio (Kayıt & Yayın)" -> "OBS Studio")
        display_name = re.sub(r"\s*\([^)]*\)", "", raw_name).strip()
        if not display_name:
            display_name = raw_name
        if "opera gx" in display_name.lower():
            display_name = "Opera GX"
        elif "equalizer apo" in display_name.lower() or display_name.lower() == "peace":
            display_name = "Peace Equalizer"

        lnk_path = entry.get("lnk") or ""
        target = (entry.get("target") or "").strip()
        args = (entry.get("args") or "").strip()
        icon_loc = (entry.get("icon") or "").strip()
        target_low = target.lower()

        if target_low.startswith("c:\\windows\\"):
            continue
        if target_low.endswith((".txt", ".chm", ".msi", ".bat", ".cmd", ".vbs", ".pdf", ".html")):
            continue
        if "unins" in target_low or "peacesetup.exe" in target_low or "javacpl.exe" in target_low:
            continue

        exe_names = []
        if lnk_path.lower().endswith(".url"):
            exe_names = _resolve_url_shortcut_exes(display_name, lnk_path)
        elif target_low.endswith(".exe"):
            exe_base = os.path.basename(target)
            if exe_base.lower() == "platform_experience_helper.exe":
                exe_base = "chrome.exe"
            elif exe_base.lower() == "update.exe" and "discord" in display_name.lower():
                exe_base = "Discord.exe"
            elif exe_base.lower() == "robloxstudioinstaller.exe":
                exe_base = "RobloxStudioBeta.exe"
            elif "wallpaper_engine" in target_low:
                exe_names = ["wallpaper64.exe", "wallpaper32.exe", "launcher.exe"]
            if not exe_names:
                exe_names.append(exe_base)

            if exe_base.lower() in ("hd-player.exe", "hd-multiinstancemanager.exe", "bluestacks x.exe", "bluestacksweb.exe"):
                for bs_exe in ["HD-Player.exe", "HD-MultiInstanceManager.exe", "BlueStacksWeb.exe", "BlueStacks X.exe"]:
                    if bs_exe not in exe_names:
                        exe_names.append(bs_exe)
        elif "craftrise" in name_low or "craftrise" in target_low:
            exe_names = ["CraftRise.exe", "javaw.exe"]

        if not exe_names:
            continue

        clean_key = re.sub(r"[^a-z0-9çğıöşü]", "", display_name.lower())
        if not clean_key or clean_key in discovered:
            continue

        custom_ico = icon_loc
        if "hd-player.exe" in target_low and "--package" in args:
            m = re.search(r'--package\s+"?([^"\s]+)"?', args)
            if m:
                pkg = m.group(1)
                bs_ico = rf"C:\ProgramData\BlueStacks_nxt\Engine\UserData\Gadget\{pkg}.ico"
                if os.path.exists(bs_ico):
                    custom_ico = bs_ico

        icon_png = extract_icon_to_cache(
            cache_key=f"{clean_key}_{target}_{custom_ico}",
            lnk_path=lnk_path,
            target_path=target,
            icon_loc=custom_ico
        )

        discovered[clean_key] = {
            "id": f"pc_{clean_key}",
            "name": display_name,
            "exe_names": exe_names,
            "target_path": target,
            "lnk_path": lnk_path,
            "icon_png": icon_png,
        }

    result_list = sorted(discovered.values(), key=lambda x: x["name"].lower())
    try:
        with open(PC_APPS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(result_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return result_list


def _resolve_url_shortcut_exes(name: str, url_path: str) -> list:
    """Steam ve Epic Games .url oyun kısayollarının çalıştırdığı .exe adlarını bulur."""
    name_low = name.lower()
    known_map = {
        "rocket league": ["RocketLeague.exe", "EpicGamesLauncher.exe"],
        "unturned": ["Unturned.exe", "Unturned_BE.exe"],
        "wallpaper engine": ["wallpaper64.exe", "wallpaper32.exe", "launcher.exe"],
        "euro truck": ["eurotrucks2.exe"],
        "trackmania": ["Trackmania.exe"],
        "counter-strike": ["cs2.exe"],
        "zenless zone zero": ["ZenlessZoneZero.exe"],
        "spooky": ["Spooky.exe", "steam.exe"],
        "scarlet skips": ["ScarletSkips.exe", "steam.exe"],
        "the supper": ["TheSupper.exe", "steam.exe"],
    }
    for k, exes in known_map.items():
        if k in name_low:
            return exes

    try:
        with open(url_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "steam://rungameid/" in content or "com.epicgames.launcher" in content:
            for line in content.splitlines():
                if line.startswith("IconFile=") and line.lower().endswith(".exe"):
                    exe_f = os.path.basename(line.split("=", 1)[1].strip())
                    return [exe_f]
            return ["steam.exe"]
    except Exception:
        pass
    return []
