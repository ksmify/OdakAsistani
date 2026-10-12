# -*- coding: utf-8 -*-
"""
Odak Asistanı - Doğal Türkçe Komut Çözümleyici (NLP Command Parser)
Kullanıcının "youtube ve discord'u kapat", "steam'i 45 dk engelle",
"instagram'ı aç", "beni uyaran her şeyi kapat", "her şeyi aç" gibi
doğal Türkçe emirlerini anlayıp BlockerEngine üzerinde uygular.
"""

import re
from blocker_engine import BlockerEngine


# Kapatma / Engelleme fiilleri ve anahtar kelimeleri
BLOCK_VERBS = [
    "kapat", "kapa", "engelle", "yasakla", "durdur", "sustur", "kilitle",
    "blokla", "kes", "kapansın", "engellensin"
]

# Açma / Serbest bırakma fiilleri ve anahtar kelimeleri
UNBLOCK_VERBS = [
    "aç", "ac", "serbest bırak", "engelini kaldır", "engeli kaldır",
    "engelleri kaldır", "izin ver", "aktifleştir", "normalleştir",
    "açılsın", "serbest"
]

# Cümle içindeki gereksiz bağlaç ve dolgu kelimeleri
STOP_WORDS = {
    "ve", "ile", "ya", "da", "de", "hem", "ayrıca", "lütfen", "hemen",
    "şimdi", "bana", "benim", "için", "bunu", "şunu", "uygulamasını",
    "uygulamayı", "sitesini", "siteyi", "programını", "programı",
    "oyununu", "oyunu", "boyunca", "süreyle", "süreliğine", "kadar",
    "dakika", "dk", "saat", "saniye", "sn", "artık", "sadece", "bir", "bu", "şu"
}

# Türkçe çekim eklerini (belirtme/yönelme) temizlemek için sonek listesi (uzundan kısaya)
TURKISH_SUFFIXES = [
    "larını", "lerini", "larını", "lerini",
    "sını", "sini", "sunu", "sünü",
    "nı", "ni", "nu", "nü",
    "yı", "yi", "yu", "yü",
    "ya", "ye",
    "dan", "den", "tan", "ten",
    "ı", "i", "u", "ü", "a", "e"
]


def normalize_turkish_token(token: str) -> list:
    """
    Bir kelimenin olası kök adaylarını döndürür.
    Örn: "discord'u" -> ["discord"], "instagramı" -> ["instagramı", "instagram"]
    """
    t = token.strip().lower()
    # Eğer bu bir URL, domain veya dosya yolu ise Türkçe ek ayıklaması yapma, tam halini koru
    if "." in t or "/" in t or "\\" in t:
        for apo in ["’", "‘", "`", "´", "'"]:
            if apo in t:
                t = t.split(apo)[0].strip()
        return [t]

    # Kesme işaretlerini standartlaştır
    for apo in ["’", "‘", "`", "´", "'"]:
        if apo in t:
            t = t.split(apo)[0].strip()

    candidates = [t]
    for suf in TURKISH_SUFFIXES:
        if len(t) > len(suf) + 1 and t.endswith(suf):
            stem = t[:-len(suf)]
            if stem not in candidates:
                candidates.append(stem)
    return candidates


def extract_duration_minutes(text: str) -> int:
    """
    Metin içindeki süreyi dakika cinsinden çıkarır.
    Örn: "45 dakika" -> 45, "2 saat" -> 120, "1.5 saat" -> 90, "30 dk" -> 30
    """
    t = text.lower()
    total_minutes = 0

    # Saat eşleşmesi
    hour_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:saat|sa)\b", t)
    if hour_match:
        val = float(hour_match.group(1).replace(",", "."))
        total_minutes += int(round(val * 60))

    # Dakika eşleşmesi
    min_match = re.search(r"(\d+)\s*(?:dakika|dk|dak)\b", t)
    if min_match:
        total_minutes += int(min_match.group(1))

    # "yarım saat" kontrolü
    if "yarım saat" in t and total_minutes == 0:
        total_minutes = 30

    return total_minutes


# Tcl/Tk Windows Türkçe klavye karakter dönüşüm tablosu (cp1254 -> utf-8)
TURKISH_CHAR_FIX = str.maketrans({
    "ý": "ı",
    "Ý": "İ",
    "ð": "ğ",
    "Ð": "Ğ",
    "þ": "ş",
    "Þ": "Ş",
})


def fix_turkish_text(text: str) -> str:
    """
    Windows Tcl/Tk kaynaklı bozuk Türkçe karakterleri (ý->ı, ð->ğ, þ->ş) düzeltir
    ve boşluksuz bitişik yazılmış fiilleri (örn: "Instagram'ıkapat") otomatik ayırır.
    """
    if not text:
        return ""
    fixed = text.translate(TURKISH_CHAR_FIX)
    # Kesme işaretinden veya kelimeden hemen sonra boşluksuz "kapat / engelle / aç" yazıldıysa ayır
    fixed = re.sub(
        r"([a-zA-Z0-9çğıöşüÇĞİÖŞÜ'’`]+?)(kapat|kapa|engelle|yasakla|durdur|sustur|serbest bırak|engelini kaldır)\b",
        r"\1 \2",
        fixed,
        flags=re.IGNORECASE
    )
    return fixed


class CommandParser:
    def __init__(self, engine: BlockerEngine):
        self.engine = engine

    def execute_command(self, raw_command: str) -> dict:
        """
        Kullanıcının yazdığı doğal Türkçe komutu çözümler ve uygular.
        Dönüş: {"success": bool, "message": str, "action": str}
        """
        cmd = fix_turkish_text(raw_command).strip()
        if not cmd:
            return {
                "success": False,
                "message": "Lütfen bir emir yazın. Örn: \"youtube ve discord'u kapat\" veya \"instagram'ı aç\"",
                "action": "none"
            }

        with self.engine.lock:
            self.engine.stats["commands_executed"] = self.engine.stats.get("commands_executed", 0) + 1

        cmd_lower = cmd.lower()
        duration_mins = extract_duration_minutes(cmd_lower)

        # 1. GENEL "HER ŞEYİ AÇ / NORMAL MODA DÖN" KOMUTLARI
        if any(phrase in cmd_lower for phrase in [
            "her şeyi aç", "hepsini aç", "tümünü aç", "tüm engelleri kaldır",
            "engelleri kaldır", "normal moda dön", "normal mod", "her şeyi serbest bırak",
            "hepsini serbest bırak", "engelleri sıfırla", "sıfırla"
        ]):
            if self.engine.is_tyt_unlocked():
                count = self.engine.unblock_all()
                return {
                    "success": True,
                    "message": f"🔓 TYT kilit tarihi geçtiği için tüm engeller kaldırıldı ({count} öğe açıldı).",
                    "action": "unblock_all"
                }
            cd = self.engine.get_tyt_countdown()
            return {
                "success": False,
                "message": f"⛔ Kilitler TYT'den 1 gün öncesine ({cd['unlock_date_str']}) kadar açılamaz! Kalan: {cd['formatted_short']}",
                "action": "forbidden_unblock"
            }

        # 2. SAYACI DURDUR KOMUTU
        if any(phrase in cmd_lower for phrase in ["sayacı durdur", "süreyi durdur", "zamanlayıcıyı kapat", "sayacı sıfırla"]):
            self.engine.stop_timer()
            return {
                "success": True,
                "message": "⏹️ Odak sayacı durduruldu.",
                "action": "timer_stop"
            }

        # 3. GENEL "BENİ UYARAN HER ŞEYİ KAPAT / ODAK MODU / DERS MODU" KOMUTLARI
        if any(phrase in cmd_lower for phrase in [
            "beni uyaran her şeyi kapat", "her şeyi kapat", "hepsini kapat",
            "tümünü kapat", "her şeyi engelle", "odak modunu başlat", "odak modu",
            "ders modunu başlat", "ders modu", "derse başla", "odaklan"
        ]):
            all_ids = [item["id"] for item in self.engine.get_all_items()]
            names = self.engine.set_multiple_blocked(all_ids, True, 0)
            return {
                "success": True,
                "message": f"🛡️ Ders & Odak Modu Aktif! Sizi uyaran {len(names)} uygulama ve site TYT'den 1 gün öncesine kadar kilitlendi.",
                "action": "block_all"
            }

        # 4. KATEGORİ BAZLI TOPLU KOMUTLAR (Örn: "oyunları kapat", "bildirimleri kapat", "sosyal medyayı kapat")
        cat_result = self._check_category_command(cmd_lower, duration_mins)
        if cat_result:
            return cat_result

        # 5. SADECE SAYAÇ BAŞLATMA KOMUTU (Örn: "45 dakika sayaç başlat", "25 dk pomodoro başlat")
        if duration_mins > 0 and any(w in cmd_lower for w in ["sayaç", "sayacı", "pomodoro", "zamanlayıcı"]):
            self.engine.start_timer(duration_mins)
            return {
                "success": True,
                "message": f"⏱️ {duration_mins} dakikalık odak sayacı başlatıldı!",
                "action": "timer_start"
            }

        # 6. BİRDEN FAZLA Yüklemli Cümleleri Ayırma
        clauses = self._split_into_clauses(cmd_lower)
        if len(clauses) > 1:
            messages = []
            any_success = False
            for clause in clauses:
                res = self._process_single_clause(clause, duration_mins)
                if res["success"]:
                    any_success = True
                messages.append(res["message"])
            return {
                "success": any_success,
                "message": " | ".join(messages),
                "action": "multi"
            }

        # 7. TEKİL VEYA ÇOKLU HEDEF CÜMLESİ (Örn: "youtube, discord ve steam'i kapat")
        return self._process_single_clause(cmd_lower, duration_mins)

    def _check_category_command(self, cmd_lower: str, duration_mins: int):
        is_unblock = any(v in cmd_lower for v in UNBLOCK_VERBS)
        is_block = any(v in cmd_lower for v in BLOCK_VERBS)
        if not is_block and not is_unblock:
            return None

        if is_unblock and not self.engine.is_tyt_unlocked():
            cd = self.engine.get_tyt_countdown()
            return {
                "success": False,
                "message": f"⛔ Kilitlenen kategoriler TYT'den 1 gün öncesine ({cd['unlock_date_str']}) kadar açılamaz! Kalan: {cd['formatted_short']}",
                "action": "forbidden_unblock"
            }

        target_block_state = not is_unblock
        matched_category = None
        cat_label = ""

        if any(k in cmd_lower for k in ["oyunları", "oyun", "oyunlar"]):
            matched_category = "Oyun & Platform"
            cat_label = "Oyun & Platform"
        elif any(k in cmd_lower for k in ["sosyal medya", "sosyal medyayı", "sosyal"]):
            matched_category = "Sosyal Medya"
            cat_label = "Sosyal Medya"
        elif any(k in cmd_lower for k in ["bildirim", "bildirimleri", "mesajlaşma", "mesajları", "sohbet", "sohbetleri", "uyaranları"]):
            matched_category = "Mesajlaşma & Bildirim"
            cat_label = "Mesajlaşma & Bildirim"
        elif any(k in cmd_lower for k in ["video", "videoları", "yayın", "yayınları", "dizi"]):
            matched_category = "Video & Yayın"
            cat_label = "Video & Yayın"

        if matched_category:
            ids = [
                item["id"] for item in self.engine.get_all_items()
                if item.get("category") == matched_category
            ]
            names = self.engine.set_multiple_blocked(ids, target_block_state, 0)
            return {
                "success": True,
                "message": f"🔒 {cat_label} kategorisindeki {len(names)} öğe kilitlendi: {', '.join(names)}",
                "action": "category_block"
            }
        return None

    def _split_into_clauses(self, text: str) -> list:
        """
        Eğer cümlede hem kapatma hem açma fiili varsa (örn: 'youtube kapat ama discord aç'),
        cümleyi alt emirlere böler.
        """
        has_block = any(re.search(rf"\b{re.escape(v)}", text) for v in BLOCK_VERBS)
        has_unblock = any(re.search(rf"\b{re.escape(v)}", text) for v in UNBLOCK_VERBS)
        if not (has_block and has_unblock):
            return [text]

        parts = re.split(r"\b(?:ama|fakat|ancak|veya)\b|[;.]", text)
        if len(parts) == 1 and "," in text:
            comma_parts = [p.strip() for p in text.split(",") if p.strip()]
            if all(
                any(v in p for v in BLOCK_VERBS + UNBLOCK_VERBS)
                for p in comma_parts
            ):
                return comma_parts
        return [p.strip() for p in parts if p.strip()]

    def _process_single_clause(self, clause: str, duration_mins: int) -> dict:
        # Niyet (Intent) tespiti: Kapatma mı Açma mı?
        is_unblock = False
        is_block = False

        for v in UNBLOCK_VERBS:
            if re.search(rf"\b{re.escape(v)}\b", clause):
                is_unblock = True
                break

        if not is_unblock and any(w in clause for w in ["kaldır", "serbest", "izin ver"]):
            is_unblock = True

        for v in BLOCK_VERBS:
            if re.search(rf"\b{re.escape(v)}", clause):
                is_block = True
                break

        # Katı Odak Modu: TYT'den 1 gün öncesine kadar manuel kilit açma emirleri yasaktır!
        if is_unblock and not self.engine.is_tyt_unlocked():
            cd = self.engine.get_tyt_countdown()
            return {
                "success": False,
                "message": f"⛔ Kilitler TYT'den 1 gün öncesine ({cd['unlock_date_str']}) kadar açılamaz! Kalan: {cd['formatted_short']}",
                "action": "forbidden_unblock"
            }

        target_state = not is_unblock

        # Fiilleri ve süre ifadelerini cümleden temizleyerek hedef isimlerini çıkar
        cleaned = clause
        cleaned = re.sub(r"\d+(?:[.,]\d+)?\s*(?:saat|sa|dakika|dk|dak|saniye|sn)\b", " ", cleaned)
        cleaned = cleaned.replace("yarım saat", " ")

        for v in sorted(UNBLOCK_VERBS + BLOCK_VERBS + ["engelini", "engeli", "engellemeyi", "engellemesini", "kaldır"], key=len, reverse=True):
            cleaned = re.sub(rf"\b{re.escape(v)}\w*\b", " ", cleaned)

        # Hedefleri bul
        matched_ids = []
        custom_targets = []

        all_items = self.engine.get_all_items()

        # Önce çok kelimeli takma adları (örn: "league of legends", "ekşi sözlük", "epic games") kontrol et
        for item in all_items:
            for alias in sorted(item.get("aliases", []) + [item["name"].lower()], key=len, reverse=True):
                if " " in alias and alias in cleaned:
                    if item["id"] not in matched_ids:
                        matched_ids.append(item["id"])
                    cleaned = cleaned.replace(alias, " ")

        # Kalan metni virgül, iki nokta ve boşluklara göre kelimelere ayır
        raw_tokens = re.split(r"[,;:\s]+", cleaned)
        for tok in raw_tokens:
            tok = tok.strip()
            if not tok or tok in STOP_WORDS or tok.isdigit():
                continue

            stem_candidates = normalize_turkish_token(tok)
            if any(c in STOP_WORDS for c in stem_candidates):
                continue

            if target_state and any(c in ("youtube", "youtube.com", "yt", "youtu.be") for c in stem_candidates):
                return {
                    "success": False,
                    "message": "⚠️ YouTube sabit ders kaynağı olduğu için tamamı kapatılamaz. Belirli bir bölümü kapatmak için lütfen yolunu yazın (örn: youtube.com/shorts veya youtube.com/playables).",
                    "action": "youtube_protected"
                }

            found_id = self._match_token_to_item(stem_candidates, all_items)
            if found_id:
                if found_id not in matched_ids:
                    matched_ids.append(found_id)
            else:
                # Mevcut listede yoksa: çalışan bir uygulama mı veya yeni bir domain/exe mi?
                cleaned_tok = stem_candidates[0]
                if len(cleaned_tok) >= 2:
                    custom_targets.append(cleaned_tok)

        # Özel hedefleri (yalnızca domain, URL yolu, .exe veya şu an açık bir uygulama ise) işle
        added_custom_names = []
        last_custom_error = ""
        running_apps = self.engine.get_running_user_apps()

        for c_target in custom_targets:
            # Şu an çalışan uygulamalardan biriyle eşleşiyor mu?
            matched_running = None
            for rapp in running_apps:
                r_disp = rapp["display_name"].lower()
                r_exe = rapp["exe_name"].lower()
                if c_target == r_disp or c_target == r_exe or (len(c_target) >= 4 and c_target in r_disp):
                    matched_running = rapp["exe_name"]
                    break

            is_explicit_domain_or_exe = ("." in c_target) or ("/" in c_target) or c_target.endswith(".exe")
            if not matched_running and not is_explicit_domain_or_exe:
                continue

            target_to_add = matched_running if matched_running else c_target
            new_item, add_msg = self.engine.add_custom_item(
                target_to_add,
                category="Komutla Eklenen",
                block_immediately=target_state,
                duration_minutes=duration_mins
            )
            if new_item:
                added_custom_names.append(new_item["name"])
            elif add_msg:
                last_custom_error = add_msg

        changed_names = []
        if matched_ids:
            changed_names = self.engine.set_multiple_blocked(matched_ids, target_state, duration_mins)

        all_affected = changed_names + [n for n in added_custom_names if n not in changed_names]

        if not all_affected:
            if last_custom_error:
                return {
                    "success": False,
                    "message": last_custom_error,
                    "action": "rejected"
                }
            return {
                "success": False,
                "message": "⚠️ Hangi uygulama veya siteyi kastettiğinizi anlayamadım. Örn: \"youtube ve discord'u kapat\" veya \"ornek.com kapat\" yazabilirsiniz.",
                "action": "not_found"
            }

        if target_state and duration_mins > 0:
            self.engine.start_timer(duration_mins)

        joined_names = ", ".join(all_affected)
        if target_state:
            if duration_mins > 0:
                msg = f"🔒 Emriniz uygulandı: {joined_names} ({duration_mins} dakika boyunca) kapatıldı ve engellendi!"
            else:
                msg = f"🔒 Emriniz uygulandı: {joined_names} kapatıldı ve engellendi! (Siz 'aç' diyene kadar kapalı kalacak)"
            return {"success": True, "message": msg, "action": "blocked"}
        else:
            msg = f"🔓 Emriniz uygulandı: {joined_names} engeli kaldırıldı, artık normal şekilde kullanabilirsiniz."
            return {"success": True, "message": msg, "action": "unblocked"}

    def _match_token_to_item(self, candidates: list, all_items: list):
        """Aday kökleri mevcut öğelerin isim, id, alias, domain ve exe adlarıyla eşleştirir."""
        for cand in candidates:
            for item in all_items:
                if cand == item["id"].lower() or cand == item["name"].lower():
                    return item["id"]
                for alias in item.get("aliases", []):
                    if cand == alias.lower():
                        return item["id"]
                for dom in item.get("domains", []):
                    dom_base = dom.lower().replace("www.", "").split(".")[0]
                    if cand == dom.lower() or (len(dom_base) >= 3 and cand == dom_base):
                        return item["id"]
                for exe in item.get("exe_names", []):
                    exe_base = exe.lower().replace(".exe", "")
                    if cand == exe.lower() or cand == exe_base:
                        return item["id"]
        return None
