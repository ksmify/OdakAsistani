# -*- coding: utf-8 -*-
"""
Odak Asistanı - Akıllı YouTube & Soru Çözüm Siteleri (345 / Bilgi Sarmal) Ders Takip Sistemi
Tarayıcıdaki YouTube ders videolarını (TYT, AYT, Kamp, Matematik, Fizik, Kimya, Biyoloji vb.)
ve ucdortbesvideo.frns.in / bilgisarmalvideo.frns.in soru çözüm sitelerini gerçek zamanlı takip eder.
- Uygulama penceresi kapalı (arka planda) olsa bile cihaz açıkken izlenen ders videolarını tespit eder.
- Her bir tarayıcı sekmesinin (TabItem) kendi ses durumunu (Mute tab ikonu), Windows SMTC medya oturumunu
  ve Windows Core Audio ses seviyesini birlikte denetler:
  * Arka planda veya başka sekmede müzik / ders dışı video çalarken ders sekmesi duraklatılmışsa ASLA saymaz!
  * Yalnızca gerçek ders sekmesinin kendisinden ses çıkarken (oynatılırken) sayacı ilerletir!
  * Yan sütun (sidebar) mini oynatıcı önizlemelerini ve ders dışı müzik/eğlence videolarını filtreler.
"""

import atexit
import base64
import ctypes
from ctypes import wintypes, POINTER, c_float, c_uint32, c_int, byref
import json
import re
import subprocess
import threading
import time
import psutil

from presets import BROWSER_PROCESSES

# Varsayılan Mola Barajı: 2 Saatlik Ders Hedefi (7200 sn) ve 10 Dakikalık Mola
STUDY_GOAL_SECONDS = 2 * 3600  # 7200 sn (2 saat)
REWARD_BREAK_MINUTES = 10      # 10 dakika

# Mola Barajı İçin İzin Verilen Ders Çalışma Süresi Seçenekleri:
# 40 DK / 45 DK / 1 SAAT / 2 SAAT / 3 SAAT
STUDY_GOAL_OPTIONS = [
    {"label": "40 DK", "minutes": 40, "seconds": 40 * 60},
    {"label": "45 DK", "minutes": 45, "seconds": 45 * 60},
    {"label": "1 SAAT", "minutes": 60, "seconds": 60 * 60},
    {"label": "2 SAAT", "minutes": 120, "seconds": 120 * 60},
    {"label": "3 SAAT", "minutes": 180, "seconds": 180 * 60},
]
ALLOWED_STUDY_GOAL_SECONDS = {opt["seconds"] for opt in STUDY_GOAL_OPTIONS}

# Mola Barajı İçin İzin Verilen Mola Süresi Seçenekleri:
# 5 DK / 10 DK / 15 DK / 20 DK / 30 DK
REWARD_BREAK_OPTIONS = [
    {"label": "5 DK", "minutes": 5, "seconds": 5 * 60},
    {"label": "10 DK", "minutes": 10, "seconds": 10 * 60},
    {"label": "15 DK", "minutes": 15, "seconds": 15 * 60},
    {"label": "20 DK", "minutes": 20, "seconds": 20 * 60},
    {"label": "30 DK", "minutes": 30, "seconds": 30 * 60},
]
ALLOWED_REWARD_BREAK_MINUTES = {opt["minutes"] for opt in REWARD_BREAK_OPTIONS}

# Dengeli Mola Barajı Kuralı: Her hedef çalışma süresi için izin verilen maksimum ödül molası (dakika)
# 40 dk -> max 10 dk | 45 dk -> max 10 dk | 1 saat -> max 15 dk | 2 saat -> max 20 dk | 3 saat -> max 30 dk
MAX_BREAK_MINUTES_BY_GOAL = {
    40 * 60: 10,
    45 * 60: 10,
    60 * 60: 15,
    120 * 60: 20,
    180 * 60: 30,
}


def get_max_break_for_goal(goal_seconds: int) -> int:
    return int(MAX_BREAK_MINUTES_BY_GOAL.get(int(goal_seconds), 15))


def clamp_break_minutes_for_goal(goal_seconds: int, break_minutes: int) -> int:
    max_b = get_max_break_for_goal(goal_seconds)
    valid = sorted(m for m in ALLOWED_REWARD_BREAK_MINUTES if m <= max_b)
    if not valid:
        return 5
    b = int(break_minutes)
    if b in valid:
        return b
    lower_or_eq = [m for m in valid if m <= b]
    return lower_or_eq[-1] if lower_or_eq else valid[0]



def format_goal_short_tr(goal_seconds: int) -> str:
    """Örn: 2400 -> '40 Dakikalık', 2700 -> '45 Dakikalık', 3600 -> '1 Saatlik', 7200 -> '2 Saatlik', 10800 -> '3 Saatlik'."""
    mins = int(round(goal_seconds / 60.0))
    if mins == 60:
        return "1 Saatlik"
    if mins == 120:
        return "2 Saatlik"
    if mins == 180:
        return "3 Saatlik"
    if mins % 60 == 0 and mins >= 60:
        return f"{mins // 60} Saatlik"
    return f"{mins} Dakikalık"


def format_goal_bar_target(goal_seconds: int) -> str:
    """Alt bardaki Mola Barajı hedef metni için: örn. '00s 40dk', '00s 45dk', '01s 00dk', '02s 00dk', '03s 00dk'."""
    total_mins = int(round(goal_seconds / 60.0))
    hrs, mins = divmod(total_mins, 60)
    return f"{hrs:02d}s {mins:02d}dk"

# Ders / Branş Kategorileri ve Anahtar Kelimeleri
SUBJECT_DEFINITIONS = [
    {
        "id": "matematik",
        "name": "Matematik",
        "icon": "📐",
        "color": "#ef4444",
        "keywords": [
            "matematik", "rehber matematik", "mert hoca", "eyüp b", "bıyıklı matematik",
            "ilyas güneş", "orijinal matematik", "acil matematik", "apotemi", "3d matematik",
            "fonksiyon", "polinom", "çarpanlara ayırma", "denklem", "eşitsizlik",
            "üslü", "köklü", "logaritma", "dizi", "limit", "türev", "integral",
            "trigonometri", "olasılık", "permütasyon", "kombinasyon", "problem",
            "temel kavramlar", "rasyonel", "mutlak değer", "oran orantı", "küme", "mantık", "binom"
        ],
    },
    {
        "id": "geometri",
        "name": "Geometri",
        "icon": "📏",
        "color": "#eab308",
        "keywords": [
            "geometri", "kenan kara", "üçgen", "çember", "daire", "analitik",
            "çokgen", "dörtgen", "yamuk", "paralelkenar", "eşkenar", "dikdörtgen",
            "kare", "katı cisim", "prizma", "piramit", "koni", "küre", "silindir"
        ],
    },
    {
        "id": "fizik",
        "name": "Fizik",
        "icon": "⚡",
        "color": "#f59e0b",
        "keywords": [
            "fizik", "vip fizik", "özcan aykın", "altuğ güneş", "ertan sinan şahin",
            "vektör", "kuvvet", "hareket", "newton", "enerji", "momentum", "itme",
            "tork", "denge", "basit makineler", "elektrik", "manyetizma", "alternatif akım",
            "optik", "dalgalar", "modern fizik", "atom fiziği", "radyoaktivite",
            "basınç", "kaldırma kuvveti", "ısı ve sıcaklık", "genleşme", "elektrostatik",
            "çembersel hareket", "basit harmonik", "kütle çekim", "kepler", "özkütle"
        ],
    },
    {
        "id": "kimya",
        "name": "Kimya",
        "icon": "🧪",
        "color": "#10b981",
        "keywords": [
            "kimya", "görkem şahin", "paraksilen", "kimya adası", "orbital", "aydın yayınları",
            "atom ve periyodik", "periyodik", "kimyasal türler", "mol", "kimyasal hesaplamalar",
            "gazlar", "sıvı çözeltiler", "çözelti", "entalpi", "entelpi", "tepkime hızı",
            "kimyasal denge", "asit", "baz", "tuz", "çözünürlük dengesi", "kçç",
            "elektrokimya", "redoks", "organik kimya", "organik", "hidrokarbon", "alkol",
            "eter", "karbonil", "karboksilik", "ester", "modern atom"
        ],
    },
    {
        "id": "biyoloji",
        "name": "Biyoloji",
        "icon": "🧬",
        "color": "#22c55e",
        "keywords": [
            "biyoloji", "dr biyoloji", "dr. biyoloji", "selin hoca", "betül biyoloji",
            "biosem", "biyotik", "senin biyolojin", "canlıların ortak", "inorganik",
            "organik bileşikler", "hücre", "madde geçişleri", "sınıflandırma", "mitoz",
            "mayoz", "üreme", "kalıtım", "genetik", "ekoloji", "ekosistem", "sinir sistemi",
            "endokrin", "duyu organları", "destek ve hareket", "sindirim", "dolaşım",
            "bağışıklık", "solunum", "üriner", "boşaltım", "üreme sistemi", "komünite",
            "popülasyon", "genetik şifre", "protein sentezi", "dna", "rna", "fotosentez",
            "kemosentez", "hücresel solunum", "bitki biyolojisi", "bitki"
        ],
    },
    {
        "id": "turkce",
        "name": "Türkçe & Edebiyat",
        "icon": "📖",
        "color": "#ec4899",
        "keywords": [
            "türkçe", "edebiyat", "paragraf", "dil bilgisi", "rüştü hoca", "kadir gümüş",
            "türkçenin matematiği", "deniz hoca", "emek taştan", "sözcükte anlam",
            "cümlede anlam", "ses bilgisi", "yazım kuralları", "noktalama", "sözcükte yapı",
            "isim", "sıfat", "zamir", "zarf", "edat", "bağlaç", "fiil", "fiilimsi",
            "cümle ögeleri", "cümle türleri", "anlatım bozukluğu", "şiir bilgisi",
            "edebi sanatlar", "islamiyet öncesi", "halk edebiyatı", "divan edebiyatı",
            "tanzimat", "servetifünun", "fecriati", "milli edebiyat", "cumhuriyet dönemi"
        ],
    },
    {
        "id": "sosyal",
        "name": "Tarih / Coğrafya / Felsefe",
        "icon": "🌍",
        "color": "#a855f7",
        "keywords": [
            "tarih", "coğrafya", "felsefe", "din kültürü", "sosyal", "ramazan yetgin",
            "soner ardıç", "coğrafyanın kodları", "yavuz tuna", "celal hoca",
            "iklim", "nüfus", "harita bilgisi", "iç kuvvetler", "dış kuvvetler",
            "türkiye coğrafyası", "osmanlı", "inkılap", "kurtuluş savaşı", "ilk çağ",
            "orta çağ", "islamiyet", "selçuklu", "atatürk"
        ],
    },
    {
        "id": "soru_cozum",
        "name": "Soru Çözümü / Deneme",
        "icon": "📝",
        "color": "#f97316",
        "keywords": [
            "video çözüm", "soru çözüm", "çözümleri", "deneme", "tyt", "ayt", "yks",
            "kamp", "ders", "sınav", "fen", "tekrar", "çıkmış sorular"
        ],
    },
]

# Kaynak Siteler İçin Kategori Seçenekleri
SOURCE_CATEGORY_OPTIONS = [
    {"id": "soru_cozum", "label": "Genel (Soru Çözümü / Deneme)"},
    {"id": "otomatik", "label": "Otomatik (Başlıktan Ders Algıla)"},
    {"id": "matematik", "label": "Matematik"},
    {"id": "geometri", "label": "Geometri"},
    {"id": "fizik", "label": "Fizik"},
    {"id": "kimya", "label": "Kimya"},
    {"id": "biyoloji", "label": "Biyoloji"},
    {"id": "turkce", "label": "Türkçe & Edebiyat"},
    {"id": "sosyal", "label": "Tarih / Coğrafya / Felsefe"},
]

# Varsayılan Kaynak Siteler:
# - YouTube: Sabit sistem kaynağıdır (silinemez ve değiştirilemez).
# - ÜçDörtBeş Video & Bilgi Sarmal Video: Kullanıcının kategorisini değiştirebileceği veya silebileceği kaynaklardır.
DEFAULT_STUDY_SOURCES = [
    {
        "id": "src_youtube",
        "name": "YouTube",
        "domain": "youtube.com",
        "keywords": ["youtube", "youtu.be"],
        "subject_id": "otomatik",
        "locked": True,
    },
    {
        "id": "src_ucdortbes",
        "name": "ÜçDörtBeş Video Çözüm",
        "domain": "ucdortbesvideo.frns.in",
        "keywords": ["ucdortbesvideo", "üçdörtbeş video", "üçdörtbeş", "ucdortbes", "345 video"],
        "subject_id": "soru_cozum",
        "locked": False,
    },
    {
        "id": "src_bilgisarmal",
        "name": "Bilgi Sarmal Video Çözüm",
        "domain": "bilgisarmalvideo.frns.in",
        "keywords": ["bilgisarmalvideo", "bilgi sarmal video", "bilgi sarmal", "frns.in", "fernus"],
        "subject_id": "soru_cozum",
        "locked": False,
    },
]

_SOURCES_LOCK = threading.Lock()
_DYNAMIC_STUDY_SOURCES = [dict(s) for s in DEFAULT_STUDY_SOURCES]
_ACTIVE_BROWSER_URLS = {}  # hwnd -> active url/domain string
_ACTIVE_BROWSER_SELECTED_TITLES = {}  # hwnd -> active/selected tab title
_ACTIVE_BROWSER_ALL_TABS = {}  # hwnd -> list of all tab dicts


def set_dynamic_study_sources(sources_list: list):
    """BlockerEngine tarafından yüklendiğinde veya güncellendiğinde aktif kaynak siteleri senkronize eder."""
    global _DYNAMIC_STUDY_SOURCES
    cleaned = []
    has_yt = False
    for s in (sources_list or []):
        if not isinstance(s, dict):
            continue
        item = dict(s)
        if item.get("id") == "src_youtube":
            item["locked"] = True
            item["subject_id"] = "otomatik"
            has_yt = True
        cleaned.append(item)
    if not has_yt:
        cleaned.insert(0, dict(DEFAULT_STUDY_SOURCES[0]))
    with _SOURCES_LOCK:
        _DYNAMIC_STUDY_SOURCES = cleaned


def get_dynamic_study_sources() -> list:
    with _SOURCES_LOCK:
        return [dict(s) for s in _DYNAMIC_STUDY_SOURCES]


def get_source_category_label(subject_id: str) -> str:
    for opt in SOURCE_CATEGORY_OPTIONS:
        if opt["id"] == subject_id:
            return opt["label"]
    for subj in SUBJECT_DEFINITIONS:
        if subj["id"] == subject_id:
            return subj["name"]
    return "Genel (Soru Çözümü / Deneme)"


def get_source_benefit_description(source: dict) -> str:
    """Kaynak sitenin altında 'oradan izlenen videolar neye yarayacak' bilgisini döndürür."""
    if source.get("locked") or source.get("id") == "src_youtube":
        return (
            "Sabit Sistem Kaynağı (Silinemez / Değiştirilemez)  •  "
            "İzlenen ders videolarını başlığından otomatik algılar; ilgili dersin süresine ve Mola Barajına işler."
        )
    subj_id = source.get("subject_id", "soru_cozum")
    if subj_id == "otomatik":
        return (
            "Bu kaynaktan izlenen videolar: Başlıktaki ders adına göre ilgili derse "
            "(branş yazmıyorsa Soru Çözümü / Deneme'ye) ve Mola Barajına işler."
        )
    if subj_id == "soru_cozum":
        return (
            "Bu kaynaktan izlenen videolar: Doğrudan 'Soru Çözümü / Deneme' (Genel) "
            "süresine ve Mola Barajına işler."
        )
    subj_info = get_subject_info(subj_id)
    return (
        f"Bu kaynaktan izlenen videolar: Doğrudan '{subj_info['name']}' "
        f"ders süresine ve Mola Barajına işler."
    )


# Bilinen YKS Yayınevleri ve Eğitim Platformları İçin Akıllı Kısaltma & İsimlendirme Sözlüğü
KNOWN_YKS_SOURCE_BRANDS = [
    (["3dyayinlari", "3d yayinlari", "3d yayınları", "3dvideo", "3d video", "3d"], "3D Yayınları Video Çözüm", "3D", "3dyayinlari.com"),
    (["orijinalyayinlari", "orijinal yayinlari", "orijinal yayınları", "orijinal matematik", "orijinal"], "Orijinal Yayınları Video Çözüm", "ORJ", "orijinalyayinlari.com"),
    (["apotemi", "apotemiyayinlari", "apotemi yayınları"], "Apotemi Yayınları Video Çözüm", "APO", "apotemi.com.tr"),
    (["acilyayinlari", "acil yayinlari", "acil yayınları", "acil matematik", "acil geo"], "Acil Yayınları Video Çözüm", "ACL", "acilyayinlari.com.tr"),
    (["barisyayinlari", "barış yayınları", "baris yayinlari", "barisayhan", "barış ayhan"], "Barış Yayınları Video Çözüm", "BRŞ", "barisyayinlari.com"),
    (["bilgisarmal", "bilgi sarmal"], "Bilgi Sarmal Video Çözüm", "BS", "bilgisarmalvideo.frns.in"),
    (["ucdortbes", "üçdörtbeş", "345"], "ÜçDörtBeş Video Çözüm", "345", "ucdortbesvideo.frns.in"),
    (["karekok", "karekök", "karekokyayinlari"], "Karekök Yayınları Video Çözüm", "KRK", "karekokvideocozum.com"),
    (["palme", "palmeyayinevi", "palme yayınevi"], "Palme Yayınevi Video Çözüm", "PLM", "palmeyayinevi.com"),
    (["aydinyayinlari", "aydın yayınları", "aydin yayinlari"], "Aydın Yayınları Video Çözüm", "AYD", "aydinyayinlari.com.tr"),
    (["orbital", "orbitalyayinlari", "orbital yayınları"], "Orbital Yayınları Video Çözüm", "ORB", "orbitalyayinlari.com"),
    (["biyotik", "biyotikyayinlari", "biyotik yayınları"], "Biyotik Yayınları Video Çözüm", "BİY", "biyotik.com.tr"),
    (["paraf", "parafyayinlari", "paraf yayınları", "parafvideo"], "Paraf Yayınları Video Çözüm", "PRF", "parafyayinlari.com"),
    (["eisyayinlari", "eis yayınları", "eis yayinlari", "eis"], "EİS Yayınları Video Çözüm", "EİS", "eisyayinlari.com"),
    (["capyayinlari", "çap yayınları", "cap yayinlari", "capvideo", "çap video"], "Çap Yayınları Video Çözüm", "ÇAP", "capyayinlari.com.tr"),
    (["hizverenk", "hız ve renk", "hizrenk", "hız renk"], "Hız ve Renk Video Çözüm", "HVR", "hizrenk.com"),
    (["toprak", "toprakyayincilik", "toprak yayıncılık"], "Toprak Yayıncılık Video Çözüm", "TPR", "toprakyayincilik.com"),
    (["endemik", "endemikyayinlari", "endemik yayınları"], "Endemik Yayınları Video Çözüm", "END", "endemikyayinlari.com.tr"),
    (["metinyayinlari", "metin yayınları", "metin yayinlari"], "Metin Yayınları Video Çözüm", "MTN", "metinyayinlari.com"),
    (["supara", "suparayayinlari", "supara yayınları"], "Supara Yayınları Video Çözüm", "SPR", "suparayayinlari.com"),
    (["miray", "mirayyayinlari", "miray yayınları"], "Miray Yayınları Video Çözüm", "MRY", "mirayyayinlari.com.tr"),
    (["limityayinlari", "limit yayınları", "limit yayinlari"], "Limit Yayınları Video Çözüm", "LMT", "limityayinlari.com"),
    (["vipyayinlari", "vip yayınları", "vip yayinlari"], "VİP Yayınları Video Çözüm", "VİP", "vipyayinlari.com"),
    (["ensyayinlari", "ens yayınları", "ens yayinlari"], "ENS Yayınları Video Çözüm", "ENS", "ensyayinlari.com.tr"),
    (["besyayinlari", "beş yayınları", "ultiyayinlari", "ulti yayınları"], "BES / Ulti Video Çözüm", "BES", "besyayinlari.com"),
    (["kafadengi", "kafa dengi"], "Kafa Dengi Yayınları Video Çözüm", "KFD", "kafadengiyayinlari.com"),
    (["ozdebir", "özdebir"], "Özdebir Video Çözüm", "ÖZD", "ozdebir.org.tr"),
    (["toder", "töder"], "TÖDER Video Çözüm", "TÖD", "toder.org"),
    (["ogmmateryal", "ogm materyal", "eba.gov.tr", "eba"], "MEB OGM Materyal", "OGM", "ogmmateryal.eba.gov.tr"),
    (["ertansinansahin", "ertan sinan şahin", "ertan sinan sahin"], "Ertan Sinan Şahin", "ESŞ", "ertansinansahin.com"),
    (["kunduz"], "Kunduz Soru Çözüm", "KNZ", "kunduz.com"),
    (["dopinghafiza", "doping hafıza", "doping hafiza"], "Doping Hafıza", "DPH", "dopinghafiza.com"),
    (["raunt"], "Raunt Akademi", "RNT", "raunt.com"),
    (["pakodemy"], "Pakodemy", "PKD", "pakodemy.com"),
    (["benimhocam", "benim hocam"], "Benim Hocam", "BH", "benimhocam.com"),
    (["krakademi", "kr akademi"], "KR Akademi", "KRA", "krakademi.com"),
    (["udemy"], "Udemy Ders Platformu", "UDM", "udemy.com"),
    (["khanacademy", "khan academy"], "Khan Academy", "KHN", "khanacademy.org"),
]

_GENERIC_SUBDOMAINS = {
    "www", "ww2", "m", "mobile", "video", "videocozum", "cozum", "sorucozum",
    "dijital", "akilli", "ogrenci", "panel", "app", "play", "watch", "izle", "kurs", "ders"
}
_GENERIC_TLDS = {
    "com", "net", "org", "tr", "edu", "gov", "in", "io", "co", "tv", "app",
    "online", "site", "xyz", "info", "biz", "me", "frns", "fernus"
}
_GENERIC_TITLE_STOPWORDS = {
    "yayınları", "yayinlari", "yayınevi", "yayinevi", "yayıncılık", "yayincilik",
    "video", "çözüm", "cozum", "soru", "bankası", "bankasi", "ders", "kurs",
    "akademi", "eğitim", "egitim", "online", "dijital", "platformu"
}


def _tr_upper(text: str) -> str:
    return (text or "").replace("i", "İ").replace("ı", "I").upper()


def _tr_title_word(word: str) -> str:
    if not word:
        return ""
    first = _tr_upper(word[0])
    rest = word[1:].replace("İ", "i").replace("I", "ı").lower()
    return first + rest


def _generate_smart_badge_code(display_name: str, core_brand: str) -> str:
    """
    Herhangi bir kaynak adı veya domain için 2-3 harflik yüksek kaliteli rozet kısaltması üretir.
    Örn:
      - 'Mustafa Yağcı Matematik' -> 'MYM'
      - 'Kafa Dengi Yayınları' -> 'KD'
      - 'Ankera Yayınları' -> 'ANK'
      - 'Pusula Akademi' -> 'PSL'
    """
    words = [
        w for w in re.split(r"[\s\-_/\.]+", (display_name or "").strip())
        if w and w.lower() not in _GENERIC_TITLE_STOPWORDS and w.lower() not in _GENERIC_TLDS
    ]
    if len(words) >= 2:
        initials = "".join(_tr_upper(w[0]) for w in words[:3] if w)
        if len(initials) >= 2:
            return initials[:3]

    target = words[0] if words else (core_brand or display_name or "WEB")
    target_clean = re.sub(r"[^a-zA-Z0-9çğıöşüÇĞİÖŞÜ]", "", target)
    if not target_clean:
        return "WEB"

    up = _tr_upper(target_clean)
    if len(up) <= 3:
        return up

    # Tek kelimeli markalarda sessiz harf ağırlıklı 3 harfli kök kısaltma (Örn: Pusula -> PSL, Ankera -> ANK, Karekök -> KRK)
    vowels = set("AEIİOÖUÜ")
    consonants = [ch for ch in up[1:] if ch not in vowels]
    if len(consonants) >= 2:
        return up[0] + consonants[0] + consonants[1]
    return up[:3]


def _prettify_brand_from_slug(core_slug: str, is_frns: bool = False) -> str:
    """
    'kafadengiyayinlari' veya 'sinavvideo' gibi bitişik domain köklerini
    'Kafadengi Yayınları' veya 'Sınav Video Çözüm' gibi şık başlıklara dönüştürür.
    """
    s = (core_slug or "").strip().lower()
    if not s:
        return "Özel Kaynak"

    suffix_replacements = [
        ("videocozum", " Video Çözüm"),
        ("sorucozum", " Soru Çözüm"),
        ("yayinlari", " Yayınları"),
        ("yayinevi", " Yayınevi"),
        ("yayincilik", " Yayıncılık"),
        ("akademi", " Akademi"),
        ("egitim", " Eğitim"),
        ("koleji", " Koleji"),
        ("okullari", " Okulları"),
        ("video", " Video Çözüm"),
        ("cozum", " Video Çözüm"),
    ]
    suffix_label = ""
    for suf, nice_suf in suffix_replacements:
        if s.endswith(suf) and len(s) > len(suf) + 1:
            s = s[: -len(suf)]
            suffix_label = nice_suf
            break

    words = [_tr_title_word(p) for p in re.split(r"[\-_]+", s) if p]
    base_title = " ".join(words) if words else _tr_title_word(s)
    full_title = f"{base_title}{suffix_label}".strip()
    if is_frns and "Video" not in full_title and "Çözüm" not in full_title:
        full_title += " Video Çözüm"
    return full_title


def get_source_badge_code(source: dict) -> str:
    """Kaynak kartının solundaki rozet için 2-3 karakterlik kaliteli kısaltmayı döndürür."""
    if not isinstance(source, dict):
        return "WEB"
    if source.get("badge"):
        return str(source["badge"])[:3]
    src_id = source.get("id", "")
    if source.get("locked") or src_id == "src_youtube":
        return "YT"
    if src_id == "src_ucdortbes":
        return "345"
    if src_id == "src_bilgisarmal":
        return "BS"

    haystack = f"{source.get('name', '')} {source.get('domain', '')}".lower()
    for triggers, _nice_name, badge_code, _def_dom in KNOWN_YKS_SOURCE_BRANDS:
        if any(t in haystack for t in triggers):
            return badge_code

    return _generate_smart_badge_code(source.get("name", ""), source.get("domain", ""))


def build_custom_study_source(raw_input: str, subject_id: str = "soru_cozum") -> dict:
    """
    Kullanıcının girdiği uzun URL, domain veya yayınevi adını kaliteli şekilde kısaltır,
    şık bir başlık, temiz bir kök domain ve 2-3 harflik rozet koduyla kaynak nesnesi üretir.
    """
    raw = (raw_input or "").strip()
    if not raw:
        return {}
    low = raw.lower()

    # URL şemasını, www. önekini ve uzun dosya/sorgu yollarını temizle
    clean_url = re.sub(r"^[a-z]+://", "", low).strip()
    host_part = clean_url.split("/")[0].split("?")[0].split("#")[0].strip()
    if ":" in host_part:
        host_part = host_part.split(":")[0]
    if host_part.startswith("www."):
        host_part = host_part[4:]

    is_url_like = ("." in host_part and " " not in raw) or ("/" in clean_url)
    is_frns = "frns.in" in host_part or "fernus" in low

    # 1. Bilinen YKS Yayınevi / Platform eşleşmesi var mı kontrol et
    matched_brand = None
    for triggers, nice_name, badge_code, default_dom in KNOWN_YKS_SOURCE_BRANDS:
        for t in triggers:
            if len(t) <= 3:
                if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", low) or host_part.startswith(t):
                    matched_brand = (triggers, nice_name, badge_code, default_dom)
                    break
            elif t in low:
                matched_brand = (triggers, nice_name, badge_code, default_dom)
                break
        if matched_brand:
            break

    # 2. Kök domain ve ana marka kelimesini (core_brand) ayıkla
    domain_tokens = [
        p for p in host_part.split(".")
        if p and p not in _GENERIC_SUBDOMAINS and p not in _GENERIC_TLDS
    ]
    core_brand = domain_tokens[0] if domain_tokens else (host_part.split(".")[0] if host_part else raw)

    # Gösterilecek temiz domain etiketi (Örn: 'https://video.3dyayinlari.com/cozum/12?x=1' -> '3dyayinlari.com')
    if matched_brand:
        _triggers, display_name, badge_code, default_dom = matched_brand
        short_domain = host_part if ("." in host_part and len(host_part) <= 34) else default_dom
    elif is_url_like and "." in host_part:
        # Gereksiz 'video.', 'cozum.', 'www.' alt alan adlarını kırpıp temiz domain bırak
        host_parts = host_part.split(".")
        while len(host_parts) > 2 and host_parts[0] in _GENERIC_SUBDOMAINS and "frns" not in host_parts:
            host_parts.pop(0)
        short_domain = ".".join(host_parts)
        display_name = _prettify_brand_from_slug(core_brand, is_frns=is_frns)
        badge_code = _generate_smart_badge_code(display_name, core_brand)
    else:
        # Kullanıcı doğrudan isim yazdıysa (Örn: 'kafa dengi yayınları' -> 'Kafa Dengi Yayınları')
        words = [_tr_title_word(w) for w in raw.split() if w]
        display_name = " ".join(words) if words else raw
        if len(display_name) > 38:
            display_name = display_name[:35].rstrip() + "..."
        badge_code = _generate_smart_badge_code(display_name, core_brand)
        tr_map_dom = str.maketrans("çğıöşü", "cgiosu")
        slug_dom = re.sub(r"[^a-z0-9]", "", low.translate(tr_map_dom))
        short_domain = f"{slug_dom[:22]}.com" if slug_dom else raw[:24]

    # 3. Tarayıcı başlığı ve URL'de aranacak anahtar kelimeleri oluştur
    keywords = set()
    if host_part and "." in host_part:
        keywords.add(host_part)
    if short_domain and "." in short_domain:
        keywords.add(short_domain)
    if core_brand and len(core_brand) >= 2:
        keywords.add(core_brand)
        # Eğer 'kafadengiyayinlari' gibi bitişikse 'kafadengi' kökünü de ekle
        for suf in ("videocozum", "sorucozum", "yayinlari", "yayinevi", "yayincilik", "video", "cozum"):
            if core_brand.endswith(suf) and len(core_brand) > len(suf) + 2:
                keywords.add(core_brand[: -len(suf)])

    if matched_brand:
        for t in matched_brand[0]:
            if len(t) >= 2:
                keywords.add(t)

    if not is_url_like and len(low) >= 2:
        keywords.add(low)

    tr_map = str.maketrans("çğıöşü", "cgiosu")
    for kw in list(keywords):
        ascii_kw = kw.translate(tr_map)
        if len(ascii_kw) >= 2:
            keywords.add(ascii_kw)

    slug_base = matched_brand[2].lower() if matched_brand else core_brand
    slug = re.sub(r"[^a-z0-9_]", "", slug_base.translate(tr_map).replace(".", "_").replace("-", "_"))
    if not slug:
        slug = f"custom_{int(time.time())}"

    valid_subj_ids = {opt["id"] for opt in SOURCE_CATEGORY_OPTIONS}
    if subject_id not in valid_subj_ids:
        subject_id = "soru_cozum"

    return {
        "id": f"src_{slug}",
        "name": display_name,
        "domain": short_domain,
        "badge": badge_code,
        "keywords": sorted(k for k in keywords if len(k) >= 2),
        "subject_id": subject_id,
        "locked": False,
    }


# Kitap satış / alışveriş / yapay zeka / arama motoru siteleri (Başlığında "TYT Matematik" veya yayınevi adı geçse bile ASLA video ders değildir!)
NON_STUDY_SITE_EXCLUSIONS = [
    "nadir kitap", "nadirkitap", "kitapyurdu", "bkmkitap", "kitapsepeti",
    "kitapsec", "kitap seç", "dr.com.tr", "idefix", "pandora", "kidega",
    "trendyol", "hepsiburada", "amazon", "n11", "çiçeksepeti", "ciceksepeti",
    "sahibinden", "letgo", "dolap", "gardrops", "akakçe", "akakce", "cimri",
    "google arama", "- google'da ara", "google search", "google.com/search",
    "gemini", "gemini.google", "chatgpt", "chat.openai", "openai",
    "claude.ai", "perplexity", "copilot", "yandex", "bing"
]

# Müzik / Rahatlatıcı Ses / Lo-Fi / Eğlence videoları (Başlığında "ders", "odak", "enerji", "dalgalar" geçse bile ders DEĞİLDİR!)
NON_STUDY_MUSIC_EXCLUSIONS = [
    "rahatlatıcı", "rahatlatici", "relaxing", "relax", "müzik", "muzik", "müziği", "muzigi",
    "music", "şarkı", "sarki", "lofi", "lo-fi", "lo fi", "chill", "beats", "playlist",
    "meditasyon", "meditation", "ambient", "ambience", "piyano", "piano", "keman", "violin",
    "gitar", "klasik müzik", "fon müziği", "uyku müziği", "yağmur sesi", "su sesi",
    "kamp ateşi", "şömine", "doğa sesleri", "white noise", "brown noise", "pink noise",
    "binaural", "alpha waves", "alfa dalgaları", "432 hz", "432hz", "528 hz", "528hz",
    "852 hz", "soundtrack", "ost", "karaoke", "remix", "instrumental", "enstrümantal",
    "akustik", "acoustic", "slowed", "reverb", "sped up", "nightcore", "asmr",
    "fragman", "trailer", "maç özeti", "gameplay", "montage", "highlights",
    "official video", "official audio", "lyrics", "şarkı sözleri", "study music", "study with me"
]

# Başlıkta aranacak tüm ders, sınav, branş, hoca, yayın anahtar kelimeleri
STUDY_TITLE_KEYWORDS = [
    # Genel sınav / ders kelimeleri
    "tyt", "ayt", "yks", "ydt", "kpss", "dgs", "ales", "lgs", "msü",
    "kamp", "kampı", "ders", "dersi", "sınav", "konu anlatım", "konu anlatımı", "soru çözüm",
    "video çözüm", "çözümleri", "deneme", "tekrar", "full tekrar", "fulleme",
    "çıkmış sorular", "matematik", "geometri", "fizik", "kimya", "biyoloji",
    "fen", "türkçe", "edebiyat", "tarih", "coğrafya", "felsefe", "din kültürü",
    "paragraf", "dil bilgisi", "problem", "fonksiyon", "polinom",
    "çarpanlara ayırma", "denklem", "eşitsizlik", "üslü", "köklü",
    "logaritma", "dizi", "limit", "türev", "integral", "trigonometri",
    "olasılık", "permütasyon", "kombinasyon", "üçgen", "çember", "analitik",
    "vektör", "kuvvet", "hareket", "enerji", "momentum", "elektrik",
    "manyetizma", "optik", "dalgalar", "modern fizik", "atom", "periyodik",
    "özkütle", "kütle", "basınç", "kaldırma kuvveti",
    "mol", "gazlar", "çözelti", "entelpi", "entalpi", "denge", "asit", "baz",
    "elektrokimya", "organik", "hücre", "kalıtım", "ekoloji", "sistemler",
    "bitki", "solunum", "fotosentez", "dna", "rna", "protein", "temel kavramlar",
    "rasyonel", "üslü sayılar", "köklü sayılar", "mutlak değer", "oran orantı",
    "rehber matematik", "mert hoca", "eyüp b", "bıyıklı matematik",
    "ilyas güneş", "benim hocam", "vip fizik", "özcan aykın", "altuğ güneş",
    "görkem şahin", "paraksilen", "kimya adası", "dr biyoloji", "selin hoca",
    "betül biyoloji", "biosem", "kenan kara", "rüştü hoca", "kadir gümüş",
    "türkçenin matematiği", "ramazan yetgin", "soner ardıç", "coğrafyanın kodları",
    "3d yayınları", "345", "orijinal matematik",
    "apotemi", "acil matematik", "aydın yayınları", "biyotik", "orbital",
    "hız ve renk", "karekök", "çap yayınları", "ogm materyal", "mebi", "eba"
]

# Kısa kelimeler yalnızca tam kelime (word boundary) olarak eşleşmelidir
SHORT_BOUNDARY_KEYWORDS = {"tyt", "ayt", "yks", "ydt", "dgs", "lgs", "msü", "fen", "mol", "baz", "dna", "rna", "eba", "345"}


def tr_lower(text: str) -> str:
    """Türkçe İ/ı ve I/i karakter dönüşümlerini ve birleşik unicode işaretlerini düzelten lowercase fonksiyonu."""
    if not text:
        return ""
    s = text.replace("İ", "i").replace("I", "ı")
    return s.lower().replace("\u0307", "")


def _matches_keyword(text_low: str, kw: str) -> bool:
    kw_low = tr_lower(kw).strip()
    if not kw_low or not text_low:
        return False
    # Kelime sınırını Türkçe harflere göre kesinleştir:
    # "organik" kelimesi "inorganik" içindeyken (başında harf olduğu için) ASLA eşleşmez!
    # Tek kelimeler için Türkçe ek uyumu: başında harf olamaz, sonunda opsiyonel çekim eki olabilir.
    if " " in kw_low:
        pattern = rf"(?<![a-zçğıöşü0-9]){re.escape(kw_low)}(?![a-zçğıöşü0-9])"
    else:
        pattern = rf"(?<![a-zçğıöşü0-9]){re.escape(kw_low)}(?:ler|lar|de|da|te|ta|den|dan|ten|tan|in|ın|un|ün|nin|nın|nun|nün|e|a|i|ı|u|ü|ye|ya|yi|yı|yu|yü|le|la|si|sı|su|sü)?(?![a-zçğıöşü0-9])"
    return bool(re.search(pattern, text_low))


def find_matching_study_source(title: str, url: str = "", hwnd: int = 0) -> dict:
    """
    Verilen pencere/sekme başlığının veya aktif sekme URL'sinin Kaynak Siteler listesindeki
    (YouTube dışındaki) herhangi bir kaynak siteyle eşleşip eşleşmediğini döner.
    """
    combined = tr_lower(f"{title or ''} {url or ''}").strip()
    if hwnd and hwnd in _ACTIVE_BROWSER_URLS:
        combined = f"{combined} {tr_lower(_ACTIVE_BROWSER_URLS.get(hwnd, ''))}".strip()
    if not combined:
        return {}

    for ex in NON_STUDY_SITE_EXCLUSIONS:
        if ex in combined:
            return {}

    with _SOURCES_LOCK:
        sources = list(_DYNAMIC_STUDY_SOURCES)

    for src in sources:
        if src.get("id") == "src_youtube" or src.get("locked"):
            continue
        dom = (src.get("domain") or "").strip().lower()
        if dom and len(dom) >= 3 and dom in combined:
            return dict(src)
        for kw in (src.get("keywords") or []):
            kw_low = tr_lower(kw).strip()
            if kw_low and _matches_keyword(combined, kw_low):
                return dict(src)
    return {}


def is_solution_site_title(title: str, url: str = "", hwnd: int = 0) -> bool:
    """Başlığın veya URL'nin Kaynak Siteler'deki (YouTube dışı) bir kaynağa ait olup olmadığını döner."""
    return bool(find_matching_study_source(title, url=url, hwnd=hwnd))


def is_study_video_title(title: str, require_platform: bool = False, url: str = "", hwnd: int = 0) -> bool:
    """
    Verilen video veya sekme başlığının gerçekten bir ders içeriğine ait olup olmadığını kontrol eder.
    - Alışveriş / kitap satış sitelerini (Nadir Kitap, Kitapyurdu, Trendyol vb.) reddeder.
    - Rahatlatıcı müzik, Lo-Fi, şarkı, ambient, yağmur sesi vb. videoları reddeder.
    - Eğer Kaynak Siteler menüsündeki özel bir kaynak siteyle eşleşiyorsa doğrudan ders kabul eder!
    - YouTube üzerindeyse ders/konu/hoca anahtar kelimelerinden birini içermesini kontrol eder.
    """
    if not title and not url:
        return False
    title_low = tr_lower(title or "")

    for ex in NON_STUDY_SITE_EXCLUSIONS:
        if ex in title_low:
            return False

    for mex in NON_STUDY_MUSIC_EXCLUSIONS:
        if mex in title_low:
            return False

    # Kaynak Siteler menüsündeki (YouTube dışı) herhangi bir kaynakla eşleşiyorsa doğrudan ders kabul et!
    matched_source = find_matching_study_source(title, url=url, hwnd=hwnd)
    if matched_source:
        return True

    if require_platform:
        is_yt = ("youtube" in title_low) or ("youtu.be" in (url or "").lower())
        if not is_yt:
            return False

    for kw in STUDY_TITLE_KEYWORDS:
        if _matches_keyword(title_low, kw):
            return True
    return False


def clean_browser_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(
        r"\s*[-—]\s*(?:youtube.*|google chrome|microsoft​? edge|brave|opera.*|mozilla firefox|vivaldi|arc).*$",
        "",
        title,
        flags=re.IGNORECASE
    ).strip()


PRIMARY_SUBJECT_IDENTIFIERS = {
    "biyoloji": [
        "biyoloji", "biyolojisi", "biyolojiye", "biosem", "dr biyoloji", "dr. biyoloji",
        "selin hoca", "betül biyoloji", "biyotik", "senin biyolojin", "biyosem"
    ],
    "kimya": [
        "kimya", "kimyası", "kimyaya", "görkem şahin", "paraksilen", "kimya adası",
        "orbital kimya", "ferrum kimya", "meschemy kimya"
    ],
    "fizik": [
        "fizik", "fiziği", "fiziğe", "vip fizik", "özcan aykın", "altuğ güneş",
        "ertan sinan şahin", "tolga bilgin"
    ],
    "geometri": [
        "geometri", "geometrisi", "geometriye", "kenan kara", "merkeze teğet"
    ],
    "matematik": [
        "matematik", "matematiği", "matematiğe", "rehber matematik", "mert hoca",
        "eyüp b", "bıyıklı matematik", "ilyas güneş", "orijinal matematik",
        "acil matematik", "3d matematik", "şenol hoca", "tunç kurt"
    ],
    "turkce": [
        "türkçe", "türkçesi", "edebiyat", "edebiyatı", "paragraf", "dil bilgisi",
        "rüştü hoca", "kadir gümüş", "türkçenin matematiği", "deniz hoca", "emek taştan"
    ],
    "sosyal": [
        "tarih", "tarihi", "coğrafya", "coğrafyası", "felsefe", "felsefesi",
        "din kültürü", "ramazan yetgin", "coğrafyanın kodları", "yavuz tuna", "celal hoca"
    ],
}


def detect_subject_id(video_title: str, preferred_solution_subject: str = "otomatik", url: str = "", hwnd: int = 0) -> str:
    """
    İzlenen videonun/sekmenin hangi derse ait olduğunu tespit eder:
    1) Kaynak Siteler'den gelen özel branş tanımı (345, Bilgi Sarmal vb.)
    2) Kesin Branş / Ana Kanal İsmi Eşleşmesi (En Yüksek Öncelik):
       Başlıkta doğrudan branş adı ("biyoloji", "kimya", "fizik", "matematik", "geometri", "türkçe", "edebiyat", "tarih", "coğrafya")
       veya o branşın ana hocası ("biosem", "dr biyoloji", "vip fizik", "kenan kara", "rehber matematik" vb.)
       geçiyorsa doğrudan o branşa yönlendirilir.
    3) Konu Başlıkları ve Anahtar Kelime Puanlaması (Scoring):
       Başlıkta branş adı açıkça yazmıyorsa (örn. sadece "İnorganik Bileşikler" veya "Limit ve Süreklilik"),
       eşleşen en uzun / en spesifik anahtar kelimelerin ağırlıklı puanı hesaplanır ve en yüksek puana sahip branş seçilir.
    """
    title_low = tr_lower(video_title or "")
    if not title_low:
        return "soru_cozum"

    # 1. Kaynak Siteler listesindeki kaynağın kendi branş ayarı
    matched_source = find_matching_study_source(video_title, url=url, hwnd=hwnd)
    if matched_source:
        src_subj = matched_source.get("subject_id", "soru_cozum")
        if src_subj and src_subj != "otomatik":
            for subj in SUBJECT_DEFINITIONS:
                if subj["id"] == src_subj:
                    return subj["id"]

    # 2. Kesin Branş / Hoca Eşleşmesi (Doğrudan branş adı yazıyorsa ASLA yanılma!)
    for sid, p_kws in PRIMARY_SUBJECT_IDENTIFIERS.items():
        for kw in p_kws:
            if _matches_keyword(title_low, kw):
                return sid

    # 3. Konu Anahtar Kelimeleri Ağırlıklı Puanlama (En spesifik branş kazanır)
    scores = {}
    for subj in SUBJECT_DEFINITIONS:
        sid = subj["id"]
        if sid == "soru_cozum":
            continue
        subj_score = 0
        for kw in subj["keywords"]:
            if _matches_keyword(title_low, kw):
                kw_len = len(kw)
                weight = kw_len + (10 if " " in kw else 0)
                subj_score += weight
        if subj_score > 0:
            scores[sid] = subj_score

    if scores:
        best_sid = max(scores.items(), key=lambda x: x[1])[0]
        return best_sid

    if preferred_solution_subject and preferred_solution_subject != "otomatik":
        for subj in SUBJECT_DEFINITIONS:
            if subj["id"] == preferred_solution_subject:
                return subj["id"]

    return "soru_cozum"


def get_subject_info(subject_id: str) -> dict:
    for subj in SUBJECT_DEFINITIONS:
        if subj["id"] == subject_id:
            return subj
    return SUBJECT_DEFINITIONS[-1]


class AudioPeakDetector:
    """
    Windows Core Audio üzerinden bilgisayarda gerçekten ses (video) oynayıp oynamadığını kontrol eder.
    Kulaklık / hoparlör değişimlerine uyum sağlamak için ses uç noktasını periyodik olarak yeniler.
    Video duraklatıldığında peak değeri ~0.0 olduğu için False döner ve sayaç boşa dönmez.
    """
    def __init__(self):
        self._meter = None
        self._last_init_ts = 0.0

    def _init_meter(self, force: bool = False):
        now = time.time()
        if not force and self._meter is not None and (now - self._last_init_ts) < 25.0:
            return
        self._last_init_ts = now
        try:
            import comtypes
            from comtypes import GUID, IUnknown, COMMETHOD, HRESULT

            CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
            IID_IMMDeviceEnumerator = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
            IID_IAudioMeterInformation = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")

            class IMMDevice(IUnknown):
                _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
                _methods_ = [
                    COMMETHOD(
                        [], HRESULT, "Activate",
                        (["in"], POINTER(GUID), "iid"),
                        (["in"], c_uint32, "dwClsCtx"),
                        (["in"], ctypes.c_void_p, "pActivationParams"),
                        (["out"], POINTER(POINTER(IUnknown)), "ppInterface"),
                    ),
                ]

            class IMMDeviceEnumerator(IUnknown):
                _iid_ = IID_IMMDeviceEnumerator
                _methods_ = [
                    COMMETHOD([], HRESULT, "EnumAudioEndpoints"),
                    COMMETHOD(
                        [], HRESULT, "GetDefaultAudioEndpoint",
                        (["in"], c_int, "dataFlow"),
                        (["in"], c_int, "role"),
                        (["out"], POINTER(POINTER(IMMDevice)), "ppEndpoint"),
                    ),
                ]

            class IAudioMeterInformation(IUnknown):
                _iid_ = IID_IAudioMeterInformation
                _methods_ = [
                    COMMETHOD([], HRESULT, "GetPeakValue", (["out"], POINTER(c_float), "pfPeak")),
                ]

            comtypes.CoInitialize()
            enumerator = comtypes.CoCreateInstance(
                CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER
            )
            device = enumerator.GetDefaultAudioEndpoint(0, 0)
            unk = device.Activate(byref(IID_IAudioMeterInformation), comtypes.CLSCTX_ALL, None)
            self._meter = unk.QueryInterface(IAudioMeterInformation)
        except Exception:
            self._meter = None

    def is_audio_playing(self) -> bool:
        self._init_meter()
        if self._meter is None:
            return False
        try:
            peak = float(self._meter.GetPeakValue())
            # Hocanın alçak sesle konuşmasını ve nefes aralarını kaçırmamak için hassas eşik (0.0004)
            return peak > 0.0004
        except Exception:
            self._init_meter(force=True)
            return False


class BrowserMediaSessionMonitor:
    """
    Sıfır-Kasma (Zero-Lag) & Anında Duraklatma Algılamalı Medya Doğrulama Motoru:
    1) Windows SMTC (GlobalSystemMediaTransportControls) Hızlı Denetimi (100ms):
       - Tarayıcı DOM ağacını (Chrome_RenderWidgetHostHWND) ASLA taramaz; böylece tarayıcıda ve PC'de
         %0 kasma / %0 CPU yükü oluşturur.
       - YouTube ve 345 / Bilgi Sarmal (frns.in) videoları duraklatıldığı anda ~0.1 saniye içinde
         'Paused' durumunu yakalar (sekme hoparlör ikonunun sönmesini 2 saniye beklemez!).
       - Hoca konuşurken nefes aldığında veya tahtaya/tablete sessizce işlem yazdığında SMTC durumu
         'Playing' kaldığı için 1 saniye bile süre kırmaz!
    2) Hafif Sekme Çubuğu (TabBar) Kontrolü (1.5 saniyede bir):
       - Arka planda açık olan ders veya müzik sekmelerini tespit eder.
    3) Yan Sütun (Sidebar) Mini Oynatıcı Fare Koruması.
    """
    BROWSER_KEYWORDS = ("opera", "chrome", "msedge", "edge", "brave", "firefox", "vivaldi", "arc")

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions = []
        self._tabs = []
        self._last_update_ts = 0.0
        self._sidebar_enter_ts = 0.0
        self._proc = None
        self._running = True
        atexit.register(self.stop)
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        proc = self._proc
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
            self._proc = None

    def _build_ps_script(self) -> str:
        return r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -TypeDefinition '
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class WinHelper {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern IntPtr OpenDesktopW(string lpszDesktop, int dwFlags, bool fInherit, uint dwDesiredAccess);
    [DllImport("user32.dll")]
    public static extern bool SetThreadDesktop(IntPtr hDesktop);
    [DllImport("user32.dll")]
    public static extern bool EnumDesktopWindows(IntPtr hDesktop, EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern int GetClassNameW(IntPtr hWnd, System.Text.StringBuilder lpClassName, int nMaxCount);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern int GetWindowTextW(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);

    public static IntPtr DefaultDesktop = IntPtr.Zero;

    public static void AttachDesktop() {
        if (DefaultDesktop == IntPtr.Zero) {
            DefaultDesktop = OpenDesktopW("Default", 0, false, 0x01FF);
        }
        if (DefaultDesktop != IntPtr.Zero) SetThreadDesktop(DefaultDesktop);
    }

    public static List<IntPtr> GetBrowserWindows() {
        List<IntPtr> list = new List<IntPtr>();
        if (DefaultDesktop == IntPtr.Zero) AttachDesktop();
        EnumDesktopWindows(DefaultDesktop, delegate(IntPtr hWnd, IntPtr lParam) {
            if (!IsWindowVisible(hWnd)) return true;
            var sbClass = new System.Text.StringBuilder(128);
            GetClassNameW(hWnd, sbClass, 128);
            string cls = sbClass.ToString();
            if (cls == "Chrome_WidgetWin_1" || cls == "MozillaWindowClass") {
                var sbTitle = new System.Text.StringBuilder(512);
                GetWindowTextW(hWnd, sbTitle, 512);
                string title = sbTitle.ToString();
                if (!string.IsNullOrEmpty(title) && !title.StartsWith("Volume Booster")) {
                    list.Add(hWnd);
                }
            }
            return true;
        }, IntPtr.Zero);
        return list;
    }
}
'
[WinHelper]::AttachDesktop()
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(150) | Out-Null
    if ($netTask.IsCompleted) { return $netTask.Result }
    return $null
}

$mgr = $null
try {
    $mgr = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
} catch {}

$walker = [System.Windows.Automation.TreeWalker]::RawViewWalker
$tabItemCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::TabItem)
$btnCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
$tabStripCache = @{}
$addrBarCache = @{}
$smtcTitleCache = @{}
$cachedTabList = @()
$tickCount = 0

Function FindBrowserChrome($rootEl) {
    $q = New-Object System.Collections.Queue
    $q.Enqueue($rootEl)
    $visited = 0
    $foundTab = $null
    $foundEdit = $null
    while ($q.Count -gt 0 -and $visited -lt 200) {
        $el = $q.Dequeue()
        $visited++
        try {
            $ct = $el.Current.ControlType.ProgrammaticName
            $cl = [string]$el.Current.ClassName
            if ($ct -eq 'ControlType.Document' -or $cl -eq 'Chrome_RenderWidgetHostHWND') {
                continue
            }
            if ($foundTab -eq $null -and $ct -eq 'ControlType.Tab' -and $cl -notmatch 'yt-|style-scope') {
                $foundTab = $el
            }
            if ($foundEdit -eq $null -and $ct -eq 'ControlType.Edit') {
                $foundEdit = $el
            }
            if ($foundTab -ne $null -and $foundEdit -ne $null) {
                break
            }
            $ch = $walker.GetLastChild($el)
            while ($ch -ne $null) {
                $q.Enqueue($ch)
                try { $ch = $walker.GetPreviousSibling($ch) } catch { $ch = $null }
            }
        } catch {}
    }
    return @{ tab = $foundTab; edit = $foundEdit }
}

while ($true) {
    $smtcList = @()
    if ($mgr -ne $null) {
        try {
            foreach ($s in $mgr.GetSessions()) {
                try {
                    $appId = [string]$s.SourceAppUserModelId
                    $info = $s.GetPlaybackInfo()
                    $status = [string]$info.PlaybackStatus
                    $title = ""
                    if (($tickCount % 8 -eq 0) -or (-not $smtcTitleCache.ContainsKey($appId))) {
                        $props = Await ($s.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
                        if ($props -ne $null -and $props.Title -ne $null) {
                            $title = [string]$props.Title
                            $smtcTitleCache[$appId] = $title
                        }
                    } else {
                        $title = [string]$smtcTitleCache[$appId]
                    }
                    $smtcList += @{
                        app = $appId
                        status = $status
                        title = $title
                    }
                } catch {}
            }
        } catch {}
    }

    # Her tick'te (100 ms) açık/seçili sekmeleri tara — engelli sekmeler anında yakalansın!
    if ($true) {
        $newTabs = @()
        try {
            $hwList = [WinHelper]::GetBrowserWindows()
            foreach ($hWnd in $hwList) {
                $key = [int64]$hWnd
                $tabStrip = $tabStripCache[$key]
                $addrBar = $addrBarCache[$key]
                if ($tabStrip -eq $null) {
                    try {
                        $rootEl = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd)
                        if ($rootEl -ne $null) {
                            $chromeRes = FindBrowserChrome $rootEl
                            $tabStrip = $chromeRes.tab
                            $addrBar = $chromeRes.edit
                            if ($tabStrip -ne $null) {
                                $tabStripCache[$key] = $tabStrip
                            }
                            if ($addrBar -ne $null) {
                                $addrBarCache[$key] = $addrBar
                            }
                        }
                    } catch {}
                }
                $winUrl = ""
                if ($addrBar -ne $null) {
                    try {
                        $vp = $addrBar.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
                        if ($vp -ne $null) {
                            $winUrl = [string]$vp.Current.Value
                        }
                    } catch {
                        $addrBarCache.Remove($key)
                    }
                }
                if ($tabStrip -ne $null) {
                    try {
                        $tabs = $tabStrip.FindAll([System.Windows.Automation.TreeScope]::Children, $tabItemCond)
                        if ($tabs.Count -eq 0) {
                            $tabs = $tabStrip.FindAll([System.Windows.Automation.TreeScope]::Descendants, $tabItemCond)
                        }
                        if ($tabs.Count -eq 0) {
                            $tabStripCache.Remove($key)
                        } else {
                            foreach ($t in $tabs) {
                                $tClass = [string]$t.Current.ClassName
                                if ($tClass -match 'yt-|style-scope') { continue }
                                $tName = [string]$t.Current.Name
                                if ([string]::IsNullOrWhiteSpace($tName) -or $tName -eq "GX Corner") { continue }
                                $sel = $false
                                try {
                                    $sel = [bool]$t.GetCurrentPropertyValue([System.Windows.Automation.SelectionItemPattern]::IsSelectedProperty)
                                } catch {}
                                $playing = $false
                                $btns = $t.FindAll([System.Windows.Automation.TreeScope]::Children, $btnCond)
                                if ($btns.Count -eq 0) {
                                    $btns = $t.FindAll([System.Windows.Automation.TreeScope]::Descendants, $btnCond)
                                }
                                foreach ($b in $btns) {
                                    $bn = ([string]$b.Current.Name).ToLower()
                                    if ($bn -match 'mute|sesi|ses') {
                                        $playing = $true
                                        break
                                    }
                                }
                                $newTabs += @{
                                    hwnd = $key
                                    title = $tName
                                    selected = $sel
                                    audio = $playing
                                    url = $(if ($sel) { $winUrl } else { "" })
                                }
                            }
                        }
                    } catch {
                        $tabStripCache.Remove($key)
                    }
                }
            }
        } catch {}
        $cachedTabList = $newTabs
    }

    $tickCount++
    $payload = @{
        smtc = @($smtcList)
        tabs = @($cachedTabList)
    }
    $json = ConvertTo-Json -InputObject $payload -Compress -Depth 4
    $b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($json))
    [Console]::Out.WriteLine($b64)
    [Console]::Out.Flush()
    Start-Sleep -Milliseconds 100
}
"""

    def _worker_loop(self):
        encoded = base64.b64encode(self._build_ps_script().encode("utf-16le")).decode("ascii")
        while self._running:
            try:
                self._proc = subprocess.Popen(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy", "Bypass",
                        "-EncodedCommand", encoded,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    encoding="ascii",
                    errors="ignore",
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                )
                while self._running and self._proc and self._proc.poll() is None:
                    line = self._proc.stdout.readline()
                    if not line:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw_json = base64.b64decode(line).decode("utf-8")
                        parsed = json.loads(raw_json)
                        if isinstance(parsed, dict):
                            smtc = parsed.get("smtc") or []
                            tabs = parsed.get("tabs") or []
                            if isinstance(smtc, dict):
                                smtc = [smtc]
                            if isinstance(tabs, dict):
                                tabs = [tabs]
                            if isinstance(tabs, list):
                                cur_sel_titles = {}
                                all_t_by_hwnd = {}
                                for tb in tabs:
                                    if isinstance(tb, dict) and tb.get("hwnd"):
                                        h_int = int(tb["hwnd"])
                                        all_t_by_hwnd.setdefault(h_int, []).append(tb)
                                        if tb.get("selected"):
                                            t_name = (tb.get("title") or "").strip()
                                            u_str = (tb.get("url") or "").strip()
                                            if t_name:
                                                cur_sel_titles[h_int] = t_name
                                            if u_str:
                                                _ACTIVE_BROWSER_URLS[h_int] = u_str
                                _ACTIVE_BROWSER_SELECTED_TITLES.clear()
                                _ACTIVE_BROWSER_SELECTED_TITLES.update(cur_sel_titles)
                                _ACTIVE_BROWSER_ALL_TABS.clear()
                                _ACTIVE_BROWSER_ALL_TABS.update(all_t_by_hwnd)
                            with self._lock:
                                self._sessions = smtc if isinstance(smtc, list) else []
                                self._tabs = tabs if isinstance(tabs, list) else []
                                self._last_update_ts = time.time()
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                if self._proc is not None:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
                    self._proc = None
            time.sleep(1.0)

    def _is_cursor_on_youtube_sidebar(self, yt_hwnd: int) -> bool:
        """Kullanıcının fare imleci nerede olursa olsun (oynatma listesi, notlar, yan panel) ders sayacını ASLA engelleme."""
        self._sidebar_enter_ts = 0.0
        return False

    def get_selected_tab_title(self, hwnd: int) -> str:
        """Belirtilen pencere tutamacına (HWND) ait aktif / seçili sekmenin başlığını döndürür."""
        with self._lock:
            for t in self._tabs:
                if int(t.get("hwnd") or 0) == hwnd and t.get("selected"):
                    return (t.get("title") or "").strip()
        return _ACTIVE_BROWSER_SELECTED_TITLES.get(hwnd, "")

    def get_selected_tab_info(self, hwnd: int) -> tuple:
        """(sekme_başlığı, adres_çubuğu_url) ikilisini döndürür."""
        with self._lock:
            for t in self._tabs:
                if int(t.get("hwnd") or 0) == hwnd and t.get("selected"):
                    return (t.get("title") or "").strip(), (t.get("url") or "").strip()
        return _ACTIVE_BROWSER_SELECTED_TITLES.get(hwnd, ""), _ACTIVE_BROWSER_URLS.get(hwnd, "")

    def get_all_tabs_for_window(self, hwnd: int) -> list:
        """Belirtilen pencereye ait tüm açık sekmelerin listesini döndürür."""
        with self._lock:
            return [t for t in self._tabs if int(t.get("hwnd") or 0) == hwnd]

    def get_playing_study_tab(self) -> tuple:
        """
        Kullanıcı tarayıcıda başka bir sekmeye (örn. şarkı sekmesine veya Google aramasına)
        tıklamış olsa bile, arka plandaki bir ders sekmesinden aktif olarak ses çıkıyorsa
        ve SMTC'de duraklatılmamışsa (başlık, hwnd) döndürür.
        """
        with self._lock:
            sessions = list(self._sessions)
            tabs = list(self._tabs)
            age = time.time() - self._last_update_ts

        if age >= 5.0:
            return "", 0

        # 1. SMTC üzerinde 'Playing' olan ders oturumu
        if sessions:
            browser_sessions = [
                s for s in sessions
                if any(b in (s.get("app") or "").lower() for b in self.BROWSER_KEYWORDS)
            ]
            for bs in browser_sessions:
                if (bs.get("status") or "").strip().lower() == "playing":
                    st_title = (bs.get("title") or "").strip()
                    if st_title and is_study_video_title(st_title, require_platform=False):
                        clean = clean_browser_title(st_title)
                        return (clean if clean else st_title), 0

        # 2. Açık sekmeler arasında ses veren (audio=True) veya aktif/seçili ders sekmesi
        for t in tabs:
            t_title = (t.get("title") or "").strip()
            t_audio = bool(t.get("audio", False))
            t_hwnd = int(t.get("hwnd") or 0)
            t_url = (t.get("url") or "").strip()
            if is_study_video_title(t_title, require_platform=True, url=t_url, hwnd=t_hwnd):
                if t_audio or t.get("selected"):
                    clean = clean_browser_title(t_title)
                    return (clean if clean else t_title), t_hwnd

        return "", 0

    def verify_main_study_video(self, window_title: str, window_hwnd: int = 0) -> tuple:
        """
        Bulunan ders penceresinin / sekmesinin gerçekten ders videosu oynatıp oynatmadığını doğrular.
        - Windows SMTC durumunu 100ms'de bir kontrol ederek YouTube veya Kaynak Siteler (345, Bilgi Sarmal vb.)
          videoları duraklatıldığı anda (sekme hoparlör ikonunun sönmesini beklemeden!) anında 'main_video_paused' döner!
        - Video gerçekten oynuyorsa ('Playing') hoca nefes alsa veya sessizce tahtaya yazsa bile
          'confirmed_playing' dönerek 1 saniye bile süre kırmaz!
        Dönüş: (onaylandı_mı: bool, doğrulanmış_başlık: str, engelleme_sebebi: str)
        """
        with self._lock:
            sessions = list(self._sessions)
            tabs = list(self._tabs)
            age = time.time() - self._last_update_ts

        if not window_title or not is_study_video_title(window_title, require_platform=False, hwnd=window_hwnd):
            return False, "", "not_study"

        is_sol_site = is_solution_site_title(window_title, hwnd=window_hwnd)

        # Fare konumu ne olursa olsun (oynatma listesi, açıklama, notlar) ana video çalıyorsa ders sayımını ASLA kesme!

        # 1. KATMAN (EN HIZLI - 100ms): Windows SMTC Medya Oturumu Kontrolü
        if age < 5.0 and sessions:
            browser_sessions = [
                s for s in sessions
                if any(b in (s.get("app") or "").lower() for b in self.BROWSER_KEYWORDS)
            ]
            if browser_sessions:
                playing_study = []
                paused_study = []
                playing_non_study = []
                for bs in browser_sessions:
                    status = (bs.get("status") or "").strip().lower()
                    smtc_title = (bs.get("title") or "").strip()
                    is_this_study = (
                        is_sol_site
                        or is_study_video_title(smtc_title, require_platform=False, hwnd=window_hwnd)
                        or (window_title and (
                            clean_browser_title(smtc_title).lower() in clean_browser_title(window_title).lower()
                            or clean_browser_title(window_title).lower() in clean_browser_title(smtc_title).lower()
                        ))
                    )
                    if status == "playing":
                        if is_this_study:
                            playing_study.append(smtc_title or window_title)
                        else:
                            playing_non_study.append(smtc_title or "Medya")
                    elif status == "paused":
                        if is_this_study:
                            paused_study.append(smtc_title or window_title)

                if playing_study:
                    best_title = clean_browser_title(playing_study[0]) or clean_browser_title(window_title)
                    return True, best_title, "confirmed_playing"

                if paused_study and not playing_study:
                    # SMTC'de ders videosu açıkça duraklatılmış (Paused)!
                    # Eğer bilgisayarda ses çıkmıyorsa anında durdur (Chromium'un gecikmeli hoparlör simgesine aldanma!)
                    is_audio_now = (
                        self._audio_detector.is_audio_playing()
                        if getattr(self, "_audio_detector", None)
                        else False
                    )
                    if not is_audio_now:
                        return False, clean_browser_title(window_title), "main_video_paused"

                    other_audio_study = any(
                        bool(t.get("audio", False)) and is_study_video_title(
                            (t.get("title") or "").strip(),
                            require_platform=True,
                            url=(t.get("url") or "").strip(),
                            hwnd=int(t.get("hwnd") or 0)
                        )
                        for t in tabs
                    )
                    if not other_audio_study:
                        return False, clean_browser_title(window_title), "main_video_paused"

                if playing_non_study:
                    # SMTC'de şarkı veya arka plan sesi çalıyor.
                    # Eğer açık sekmeler arasında GERÇEKTEN ses çıkaran (audio=True) bir ders sekmesi varsa dersi say:
                    bg_study_audio = [
                        (t.get("title") or "").strip()
                        for t in tabs
                        if bool(t.get("audio", False)) and is_study_video_title(
                            (t.get("title") or "").strip(),
                            require_platform=True,
                            url=(t.get("url") or "").strip(),
                            hwnd=int(t.get("hwnd") or 0)
                        )
                    ]
                    if bg_study_audio:
                        return True, clean_browser_title(bg_study_audio[0]), "confirmed_playing"
                    # Ders sekmesinden ses gelmiyor, sadece arka plan müziği çalıyor -> ders duraklatılmış!
                    return False, clean_browser_title(window_title), "main_video_paused"

        # 2. KATMAN: Sekme Çubuğu (TabBar) Kontrolü
        if age < 5.0 and tabs:
            is_audio_now = (
                self._audio_detector.is_audio_playing()
                if getattr(self, "_audio_detector", None)
                else False
            )
            playing_study_tabs = []
            playing_non_study_tabs = []
            for t in tabs:
                t_title = (t.get("title") or "").strip()
                t_audio = bool(t.get("audio", False))
                t_hwnd = int(t.get("hwnd") or 0)
                t_url = (t.get("url") or "").strip()
                if t_audio:
                    if is_study_video_title(t_title, require_platform=True, url=t_url, hwnd=t_hwnd):
                        playing_study_tabs.append(t_title)
                    else:
                        playing_non_study_tabs.append(t_title)

            # Chromium sekme hoparlör simgesi video duraklatıldıktan sonra 3 saniye boyunca
            # ekranda kalmaya devam eder! Bilgisayardan gerçek ses çıkmıyorsa video duraklatılmıştır!
            if playing_study_tabs and is_audio_now:
                return True, clean_browser_title(playing_study_tabs[0]), "confirmed_playing"

            if playing_non_study_tabs and not playing_study_tabs:
                # Başka bir sekmeden ses geliyor ama ders sekmesi sessiz -> ders duraklatılmış!
                return False, clean_browser_title(window_title), "main_video_paused"

            if not playing_study_tabs:
                # Tarayıcı sekmeleri aktif taranıyor ve hiçbir ders sekmesinde ses ikonu (audio=True) yok!
                # (1. Katmanda da SMTC üzerinden çalan bir ders oturumu doğrulanmadı)
                # Bu durumda Opera GX klavye yazma sesleri, arayüz efektleri veya sistem bildirimleri
                # ASLA ders videosunun oynatıldığı anlamına gelemez -> video duraklatılmıştır!
                return False, clean_browser_title(window_title), "main_video_paused"

        # 3. KATMAN: Sistem Sesi (Core Audio Peak) Kontrolü
        if getattr(self, "_audio_detector", None) is None:
            self._audio_detector = AudioPeakDetector()
        if self._audio_detector.is_audio_playing():
            return True, clean_browser_title(window_title), "confirmed_playing"

        # Hiçbir ses, SMTC playing veya sekme sesi yoksa video kesinlikle duraklatılmıştır!
        return False, clean_browser_title(window_title), "main_video_paused"


_PID_NAME_CACHE = {}


def get_cached_process_name(pid_val: int) -> str:
    if not pid_val:
        return ""
    cached = _PID_NAME_CACHE.get(pid_val)
    if cached is not None:
        return cached
    try:
        pname = psutil.Process(pid_val).name().lower()
        if len(_PID_NAME_CACHE) > 512:
            _PID_NAME_CACHE.clear()
        _PID_NAME_CACHE[pid_val] = pname
        return pname
    except Exception:
        return ""


def find_active_study_video(return_hwnd: bool = False):
    """
    Açık tarayıcı pencerelerinde YouTube ders videosu veya Kaynak Siteler menüsündeki
    herhangi bir kaynak sitenin sekmesi olup olmadığını sıfır CPU maliyetiyle kontrol eder.
    """
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    # Windows masaüstü pencerelerine güvenli ve eksiksiz erişim için Default desktop'a bağlan
    hDesk = None
    try:
        hDesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hDesk:
            user32.SetThreadDesktop(hDesk)
    except Exception:
        pass

    fg_hwnd = user32.GetForegroundWindow()
    found = []

    def _cb(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return True
            pname = get_cached_process_name(pid.value)
            if pname not in BROWSER_PROCESSES:
                return True

            h_int = int(hwnd)
            title = ""
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value or ""

            # 1. Doğrudan pencere başlığı kontrolü
            candidate_title = ""
            if title and is_study_video_title(title, require_platform=True, hwnd=hwnd):
                candidate_title = title
            else:
                # 2. UIAutomation ile yakalanan seçili sekme başlığı (Opera GX, Chrome vb.)
                sel_title = _ACTIVE_BROWSER_SELECTED_TITLES.get(h_int, "")
                if sel_title and is_study_video_title(sel_title, require_platform=True, hwnd=hwnd):
                    candidate_title = sel_title
                else:
                    # 3. Açık sekmeler arasında GERÇEKTEN ses veren (audio=True) veya seçili ders sekmesi
                    tabs_for_hwnd = _ACTIVE_BROWSER_ALL_TABS.get(h_int, [])
                    for t in tabs_for_hwnd:
                        t_name = (t.get("title") or "").strip()
                        t_audio = bool(t.get("audio", False))
                        t_sel = bool(t.get("selected", False))
                        if t_name and (t_audio or t_sel) and is_study_video_title(t_name, require_platform=True, hwnd=hwnd):
                            candidate_title = t_name
                            break

            if candidate_title:
                clean = clean_browser_title(candidate_title)
                is_fg = (hwnd == fg_hwnd)
                is_iconic = bool(user32.IsIconic(hwnd))
                found.append((clean if clean else candidate_title, is_fg, is_iconic, hwnd))
        except Exception:
            pass
        return True

    cb_func = WNDENUMPROC(_cb)
    if hDesk:
        try:
            user32.EnumDesktopWindows(hDesk, cb_func, 0)
        except Exception:
            user32.EnumWindows(cb_func, 0)
    else:
        user32.EnumWindows(cb_func, 0)

    # EnumWindows pencereyi kaçırdıysa doğrudan hafızadaki seçili ders sekmelerini kontrol et:
    if not found:
        for h_int, t_name in _ACTIVE_BROWSER_SELECTED_TITLES.items():
            if t_name and is_study_video_title(t_name, require_platform=True, hwnd=h_int):
                clean = clean_browser_title(t_name)
                is_fg = (h_int == fg_hwnd)
                is_iconic = bool(user32.IsIconic(h_int)) if user32.IsWindow(h_int) else False
                found.append((clean if clean else t_name, is_fg, is_iconic, h_int))

    if not found:
        if return_hwnd:
            return "", False, 0
        return "", False

    # Öncelik: 1) Ön plandaki pencere, 2) Minimize edilmemiş pencere, 3) Minimize edilmiş pencere
    found.sort(key=lambda x: (not x[1], x[2]))
    best_title, best_fg, _best_iconic, best_hwnd = found[0]
    if return_hwnd:
        return best_title, best_fg, best_hwnd
    return best_title, best_fg

