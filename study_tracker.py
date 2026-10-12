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
# 5 DK / 10 DK / 20 DK / 30 DK
REWARD_BREAK_OPTIONS = [
    {"label": "5 DK", "minutes": 5, "seconds": 5 * 60},
    {"label": "10 DK", "minutes": 10, "seconds": 10 * 60},
    {"label": "20 DK", "minutes": 20, "seconds": 20 * 60},
    {"label": "30 DK", "minutes": 30, "seconds": 30 * 60},
]
ALLOWED_REWARD_BREAK_MINUTES = {opt["minutes"] for opt in REWARD_BREAK_OPTIONS}


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


def build_custom_study_source(raw_input: str, subject_id: str = "soru_cozum") -> dict:
    """Kullanıcının girdiği site adresi veya isimden akıllı eşleşme anahtarlarına sahip bir kaynak nesnesi üretir."""
    raw = (raw_input or "").strip()
    if not raw:
        return {}
    low = raw.lower()
    clean_url = re.sub(r"^https?://", "", low).strip()
    domain_part = clean_url.split("/")[0].strip()
    if domain_part.startswith("www."):
        domain_part = domain_part[4:]

    keywords = set()
    keywords.add(low)
    if domain_part:
        keywords.add(domain_part)
        parts = [p for p in domain_part.split(".") if p and p not in ("www", "com", "net", "org", "tr", "edu", "gov", "in", "io", "co", "tv", "app", "video", "online")]
        for p in parts:
            if len(p) >= 3:
                keywords.add(p)
        if len(parts) >= 2:
            keywords.add(" ".join(parts))

    # Türkçe karakter / boşluk varyasyonları
    tr_map = str.maketrans("çğıöşü", "cgiosu")
    for kw in list(keywords):
        ascii_kw = kw.translate(tr_map)
        if len(ascii_kw) >= 3:
            keywords.add(ascii_kw)

    slug = re.sub(r"[^a-z0-9_]", "", domain_part.translate(tr_map).replace(".", "_").replace("-", "_"))
    if not slug:
        slug = f"custom_{int(time.time())}"

    display_name = raw if (" " in raw or not ("." in domain_part)) else domain_part
    valid_subj_ids = {opt["id"] for opt in SOURCE_CATEGORY_OPTIONS}
    if subject_id not in valid_subj_ids:
        subject_id = "soru_cozum"

    return {
        "id": f"src_{slug}",
        "name": display_name,
        "domain": domain_part if "." in domain_part else raw,
        "keywords": sorted(k for k in keywords if len(k) >= 2),
        "subject_id": subject_id,
        "locked": False,
    }


# Kitap satış / alışveriş / ders dışı siteler (Başlığında "TYT Matematik" yazsa bile ASLA video ders değildir!)
NON_STUDY_SITE_EXCLUSIONS = [
    "nadir kitap", "nadirkitap", "kitapyurdu", "bkmkitap", "kitapsepeti",
    "kitapsec", "kitap seç", "dr.com.tr", "idefix", "pandora", "kidega",
    "trendyol", "hepsiburada", "amazon", "n11", "çiçeksepeti", "ciceksepeti",
    "sahibinden", "letgo", "dolap", "gardrops", "akakçe", "akakce", "cimri",
    "google arama", "- google'da ara", "google search", "yandex", "bing"
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


def _matches_keyword(text_low: str, kw: str) -> bool:
    if kw in SHORT_BOUNDARY_KEYWORDS or len(kw) <= 3:
        return bool(re.search(rf"\b{re.escape(kw)}\b", text_low))
    return kw in text_low


def find_matching_study_source(title: str, url: str = "", hwnd: int = 0) -> dict:
    """
    Verilen pencere/sekme başlığının veya aktif sekme URL'sinin Kaynak Siteler listesindeki
    (YouTube dışındaki) herhangi bir kaynak siteyle eşleşip eşleşmediğini döner.
    """
    combined = f"{title or ''} {url or ''}".strip().lower()
    if hwnd and hwnd in _ACTIVE_BROWSER_URLS:
        combined = f"{combined} {_ACTIVE_BROWSER_URLS.get(hwnd, '')}".strip().lower()
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
            kw_low = (kw or "").strip().lower()
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
    title_low = (title or "").lower()

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


def detect_subject_id(video_title: str, preferred_solution_subject: str = "otomatik", url: str = "", hwnd: int = 0) -> str:
    """
    İzlenen videonun/sekmenin hangi derse ait olduğunu tespit eder:
    1) Eğer Kaynak Siteler listesindeki bir kaynak siteyle eşleşiyorsa ve o kaynağa özel bir
       kategori seçilmişse ('matematik', 'turkce', 'soru_cozum' vb.), doğrudan o kategoriyi döner!
    2) Kaynak 'otomatik' moddaysa veya YouTube videosuysa, başlıktaki ders/konu anahtar kelimesinden algılar.
    """
    title_low = (video_title or "").lower()
    matched_source = find_matching_study_source(video_title, url=url, hwnd=hwnd)
    if matched_source:
        src_subj = matched_source.get("subject_id", "soru_cozum")
        if src_subj and src_subj != "otomatik":
            for subj in SUBJECT_DEFINITIONS:
                if subj["id"] == src_subj:
                    return subj["id"]

    for subj in SUBJECT_DEFINITIONS:
        if subj["id"] == "soru_cozum":
            continue
        for kw in subj["keywords"]:
            if _matches_keyword(title_low, kw):
                return subj["id"]

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
            if (sbClass.ToString() == "Chrome_WidgetWin_1") {
                var sbTitle = new System.Text.StringBuilder(512);
                GetWindowTextW(hWnd, sbTitle, 512);
                string title = sbTitle.ToString();
                if (!string.IsNullOrEmpty(title) && !title.StartsWith("Volume Booster") &&
                    (title.EndsWith("Opera") || title.EndsWith("Opera GX") || title.EndsWith("Chrome") ||
                     title.EndsWith("Edge") || title.EndsWith("Brave") || title.EndsWith("Vivaldi") || title.EndsWith("Arc"))) {
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

    if ($tickCount % 14 -eq 0) {
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
                                for tb in tabs:
                                    if isinstance(tb, dict) and tb.get("selected") and tb.get("hwnd"):
                                        u_str = (tb.get("url") or "").strip()
                                        if u_str:
                                            _ACTIVE_BROWSER_URLS[int(tb["hwnd"])] = u_str
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
        """
        Kullanıcı ana videoyu açık bırakıp fareyi sağdaki önerilen videolar sütununda (#secondary)
        tutarak mini oynatıcıdan (inline preview) başka bir videoyu izliyor mu kontrol eder.
        """
        if not yt_hwnd:
            self._sidebar_enter_ts = 0.0
            return False
        try:
            user32 = ctypes.windll.user32
            if user32.IsIconic(yt_hwnd) or not user32.IsWindowVisible(yt_hwnd):
                self._sidebar_enter_ts = 0.0
                return False

            rect = wintypes.RECT()
            if not user32.GetWindowRect(yt_hwnd, ctypes.byref(rect)):
                self._sidebar_enter_ts = 0.0
                return False

            win_w = rect.right - rect.left
            win_h = rect.bottom - rect.top
            if win_w < 750 or win_h < 400:
                self._sidebar_enter_ts = 0.0
                return False

            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            if win_w >= screen_w - 4 and win_h >= screen_h - 4:
                self._sidebar_enter_ts = 0.0
                return False

            pt = wintypes.POINT()
            if not user32.GetCursorPos(ctypes.byref(pt)):
                self._sidebar_enter_ts = 0.0
                return False

            hwnd_at_pt = user32.WindowFromPoint(pt)
            if not hwnd_at_pt:
                self._sidebar_enter_ts = 0.0
                return False
            root_at_pt = user32.GetAncestor(hwnd_at_pt, 2)  # GA_ROOT = 2
            if root_at_pt != yt_hwnd:
                self._sidebar_enter_ts = 0.0
                return False

            rel_x = (pt.x - rect.left) / float(win_w)
            rel_y = (pt.y - rect.top) / float(win_h)

            in_sidebar = (0.63 <= rel_x <= 0.985) and (0.12 <= rel_y <= 0.96)
            now = time.time()
            if in_sidebar:
                if self._sidebar_enter_ts == 0.0:
                    self._sidebar_enter_ts = now
                return (now - self._sidebar_enter_ts) >= 1.0
            else:
                self._sidebar_enter_ts = 0.0
                return False
        except Exception:
            self._sidebar_enter_ts = 0.0
            return False

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

        # Eğer Windows SMTC açıkça tüm tarayıcı oturumlarının duraklatıldığını söylüyorsa arka plan sekmesini oynuyor sayma!
        if sessions:
            browser_sessions = [
                s for s in sessions
                if any(b in (s.get("app") or "").lower() for b in self.BROWSER_KEYWORDS)
            ]
            if browser_sessions:
                any_playing = any((bs.get("status") or "").strip().lower() == "playing" for bs in browser_sessions)
                if not any_playing:
                    return "", 0
                for bs in browser_sessions:
                    if (bs.get("status") or "").strip().lower() == "playing":
                        st_title = (bs.get("title") or "").strip()
                        if st_title and is_study_video_title(st_title, require_platform=False):
                            clean = clean_browser_title(st_title)
                            return (clean if clean else st_title), 0

        for t in tabs:
            t_title = (t.get("title") or "").strip()
            t_audio = bool(t.get("audio", False))
            t_hwnd = int(t.get("hwnd") or 0)
            t_url = (t.get("url") or "").strip()
            if t_audio and is_study_video_title(t_title, require_platform=True, url=t_url, hwnd=t_hwnd):
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

        # Yan sütun (sidebar) fare kontrolü (YouTube ise)
        if not is_sol_site and self._is_cursor_on_youtube_sidebar(window_hwnd):
            return (
                False,
                "🚫 Yan Sütun (Mini Oynatıcı) Üzerindesiniz — Derse Sayılmıyor!",
                "sidebar_hover"
            )

        # 1. KATMAN (EN HIZLI - 100ms): Windows SMTC Medya Oturumu Kontrolü
        if age < 5.0 and sessions:
            browser_sessions = [
                s for s in sessions
                if any(b in (s.get("app") or "").lower() for b in self.BROWSER_KEYWORDS)
            ]
            if browser_sessions:
                playing_study = []
                playing_non_study = []
                for bs in browser_sessions:
                    status = (bs.get("status") or "").strip().lower()
                    smtc_title = (bs.get("title") or "").strip()
                    if status == "playing":
                        if is_sol_site:
                            # Kaynak site (345, Bilgi Sarmal veya özel eklenen site) açıksa pencere başlığını/kaynağı baz al
                            playing_study.append(window_title)
                        elif smtc_title and is_study_video_title(smtc_title, require_platform=False, hwnd=window_hwnd):
                            playing_study.append(smtc_title)
                        elif not smtc_title and is_study_video_title(window_title, require_platform=False, hwnd=window_hwnd):
                            playing_study.append(window_title)
                        else:
                            playing_non_study.append(smtc_title or "Medya")

                if playing_study:
                    best_title = clean_browser_title(playing_study[0]) or clean_browser_title(window_title)
                    return True, best_title, "confirmed_playing"

                if playing_non_study:
                    # SMTC'de şarkı görünüyor; arka planda ayrıca ses çıkaran bir ders sekmesi var mı?
                    bg_study = [
                        (t.get("title") or "").strip()
                        for t in tabs
                        if bool(t.get("audio", False)) and is_study_video_title(
                            (t.get("title") or "").strip(),
                            require_platform=True,
                            url=(t.get("url") or "").strip(),
                            hwnd=int(t.get("hwnd") or 0)
                        )
                    ]
                    if bg_study:
                        return True, clean_browser_title(bg_study[0]), "confirmed_playing"
                    return (
                        False,
                        f"🚫 Ders Dışı Video / Müzik Algılandı ({playing_non_study[0]}) — Derse Sayılmıyor!",
                        "non_study_playing"
                    )

                # Tarayıcı medya oturumu var ama hiçbirisi 'Playing' değil -> Video DURAKLATILDI!
                return (
                    False,
                    clean_browser_title(window_title),
                    "main_video_paused"
                )

        # 2. KATMAN: SMTC oturumu oluşturmayan gömülü oynatıcılar için Sekme Çubuğu kontrolü
        if age < 5.0 and tabs:
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

            if playing_non_study_tabs and not playing_study_tabs:
                non_study_name = clean_browser_title(playing_non_study_tabs[0])
                return (
                    False,
                    f"🚫 Ders Dışı Ses / Müzik Algılandı ({non_study_name}) — Derse Sayılmıyor!",
                    "non_study_playing"
                )

        return True, clean_browser_title(window_title), ""


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

    fg_hwnd = user32.GetForegroundWindow()
    found = []

    def _cb(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return True
            pname = get_cached_process_name(pid.value)
            if pname not in BROWSER_PROCESSES:
                return True

            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value or ""

            if is_study_video_title(title, require_platform=True, hwnd=hwnd):
                clean = clean_browser_title(title)
                is_fg = (hwnd == fg_hwnd)
                is_iconic = bool(user32.IsIconic(hwnd))
                found.append((clean if clean else title, is_fg, is_iconic, hwnd))
        except Exception:
            pass
        return True

    cb_func = WNDENUMPROC(_cb)
    user32.EnumWindows(cb_func, 0)

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

