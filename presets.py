# -*- coding: utf-8 -*-
"""
Odak Asistanı - Uygulama, Oyun ve "Asistan'ın Seçtikleri" Dopamin Tuzakları Veritabanı
"""

# Asla kapatılmaması gereken kritik Windows ve geliştirici süreçleri
SAFE_SYSTEM_PROCESSES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "svchost.exe", "fontdrvhost.exe",
    "winlogon.exe", "dwm.exe", "explorer.exe", "taskhostw.exe", "sihost.exe",
    "ctfmon.exe", "conhost.exe", "runtimebroker.exe", "searchhost.exe",
    "startmenuexperiencehost.exe", "shellexperiencehost.exe", "textinputhost.exe",
    "securityhealthservice.exe", "securityhealthsystray.exe", "audiodg.exe",
    "spoolsv.exe", "dllhost.exe", "taskmgr.exe", "mmc.exe", "regedit.exe",
    "cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe", "wt.exe",
    "python.exe", "pythonw.exe", "py.exe", "code.exe", "antigravity.exe",
    "lsaiso.exe", "wmiprvse.exe", "msiexec.exe", "smartscreen.exe",
    "applicationframehost.exe", "systemsettings.exe", "lockapp.exe", "logonui.exe"
}

# Sekme başlığı kontrolü yapılacak tarayıcı süreçleri (tarayıcının kendisi kapatılmaz, sadece sekmesi kapatılır)
BROWSER_PROCESSES = {
    "chrome.exe", "msedge.exe", "brave.exe", "opera.exe", "operagx.exe",
    "firefox.exe", "vivaldi.exe", "waterfox.exe", "arc.exe", "thorium.exe"
}

# ==============================================================================
# 1. STANDART UYGULAMALAR VE DERS İÇİN AÇIK KALACAK SİTELER (Başlangıçta AÇIK)
# ==============================================================================
DEFAULT_ITEMS = [
    {
        "id": "yt_shorts",
        "name": "YouTube Shorts (Sekme)",
        "icon": "📱",
        "category": "Video & Yayın",
        "item_type": "site",
        "domains": [],
        "url_rules": ["youtube.com/shorts"],
        "title_all_keywords": [["shorts", "youtube"], ["#shorts", "youtube"]],
        "exe_names": [],
        "tab_keywords": [],
        "aliases": ["youtube shorts", "yt shorts", "shorts"]
    },
    {
        "id": "yt_playables",
        "name": "YouTube Playables (Oyunlar)",
        "icon": "🎮",
        "category": "Video & Yayın",
        "item_type": "site",
        "domains": [],
        "url_rules": ["youtube.com/playables"],
        "title_all_keywords": [
            ["playables", "youtube"],
            ["oyunlar", "youtube"],
            ["mini", "oyunlar", "youtube"],
            ["mini", "oyun", "youtube"]
        ],
        "exe_names": [],
        "tab_keywords": [],
        "aliases": ["youtube playables", "yt playables", "playables", "youtube oyunlar"]
    },
    {
        "id": "discord",
        "name": "Discord (Uygulama)",
        "icon": "💬",
        "category": "Mesajlaşma & Bildirim",
        "item_type": "app",
        "domains": ["discord.com", "discordapp.com", "discord.gg"],
        "exe_names": ["Discord.exe", "DiscordPTB.exe", "DiscordCanary.exe", "DiscordDevelopment.exe"],
        "tab_keywords": ["discord"],
        "aliases": ["discord", "dc", "diskord"]
    },
    {
        "id": "bluestacks",
        "name": "BlueStacks 5",
        "icon": "📱",
        "category": "Oyun & Platform",
        "item_type": "app",
        "domains": ["bluestacks.com"],
        "exe_names": [
            "HD-Player.exe", "HD-MultiInstanceManager.exe",
            "BlueStacksWeb.exe", "BlueStacks.exe", "BstkSVC.exe",
            "BlueStacksServices.exe", "BlueStacks X.exe"
        ],
        "tab_keywords": ["bluestacks"],
        "aliases": [
            "bluestacks", "bluestacks 5", "bluestack", "bluestacks x",
            "hd-player", "brawl stars", "brawlstars"
        ]
    },
    {
        "id": "whatsapp",
        "name": "WhatsApp (Uygulama)",
        "icon": "🟢",
        "category": "Mesajlaşma & Bildirim",
        "item_type": "app",
        "domains": ["web.whatsapp.com", "whatsapp.com"],
        "exe_names": ["WhatsApp.exe", "WhatsApp.Root.exe"],
        "tab_keywords": ["whatsapp"],
        "aliases": ["whatsapp", "wp", "watsap", "whatsap"]
    },
    {
        "id": "steam",
        "name": "Steam (Uygulama)",
        "icon": "🎮",
        "category": "Oyun & Platform",
        "item_type": "app",
        "domains": ["steampowered.com", "steamcommunity.com"],
        "exe_names": ["steam.exe", "steamwebhelper.exe", "steamservice.exe", "gameoverlayui.exe"],
        "tab_keywords": ["steam"],
        "aliases": ["steam", "stim"]
    },
    {
        "id": "roblox",
        "name": "Roblox (Uygulama)",
        "icon": "🧱",
        "category": "Oyun & Platform",
        "item_type": "app",
        "domains": ["roblox.com", "www.roblox.com", "rbxcdn.com"],
        "exe_names": [
            "RobloxPlayerBeta.exe", "RobloxPlayerLauncher.exe", "Roblox.exe",
            "RobloxStudioBeta.exe", "RobloxPlayerInstaller.exe", "RobloxCrashHandler.exe"
        ],
        "tab_keywords": ["roblox"],
        "aliases": ["roblox", "roblox player", "roblox studio"]
    },
    {
        "id": "valorant",
        "name": "Valorant & Riot",
        "icon": "🔫",
        "category": "Oyun & Platform",
        "item_type": "app",
        "domains": ["playvalorant.com", "riotgames.com"],
        "exe_names": [
            "VALORANT.exe", "VALORANT-Win64-Shipping.exe",
            "RiotClientServices.exe", "RiotClientUx.exe"
        ],
        "tab_keywords": ["valorant", "riot"],
        "aliases": ["valorant", "valo", "riot", "riot client"]
    },
    {
        "id": "lol",
        "name": "League of Legends",
        "icon": "⚔️",
        "category": "Oyun & Platform",
        "item_type": "app",
        "domains": ["leagueoflegends.com", "riotgames.com"],
        "exe_names": [
            "LeagueClient.exe", "LeagueClientUx.exe", "League of Legends.exe",
            "RiotClientServices.exe", "RiotClientUx.exe"
        ],
        "tab_keywords": ["league of legends", "leagueclient"],
        "aliases": ["lol", "league of legends", "league"]
    },
    {
        "id": "epicgames",
        "name": "Epic Games & Rocket League",
        "icon": "🕹️",
        "category": "Oyun & Platform",
        "item_type": "app",
        "domains": ["epicgames.com", "rocketleague.com"],
        "exe_names": [
            "EpicGamesLauncher.exe", "EpicWebHelper.exe", "RocketLeague.exe", "cs2.exe",
            "FortniteClient-Win64-Shipping.exe"
        ],
        "tab_keywords": ["epic games", "rocket league", "fortnite"],
        "aliases": [
            "epic", "epic games", "rocket league", "rl", "cs2",
            "counter strike", "fortnite"
        ]
    },
    {
        "id": "osu",
        "name": "osu! & TETR.IO (Uygulama)",
        "icon": "🎯",
        "category": "Oyun & Platform",
        "item_type": "app",
        "domains": ["ppy.sh", "tetr.io"],
        "exe_names": ["osu!.exe", "TETR.IO.exe"],
        "tab_keywords": ["osu!", "tetr.io"],
        "aliases": ["osu", "osu!", "osulazer", "tetr.io", "tetrio", "tetris"]
    },
    {
        "id": "minecraft",
        "name": "CraftRise & Minecraft",
        "icon": "⛏️",
        "category": "Oyun & Platform",
        "item_type": "app",
        "domains": ["minecraft.net", "craftrise.com.tr"],
        "exe_names": [
            "CraftRise.exe", "Minecraft.Windows.exe", "MinecraftLauncher.exe",
            "javaw.exe", "java.exe", "Minecraft.exe"
        ],
        "tab_keywords": ["minecraft", "craftrise"],
        "aliases": ["craftrise", "craft rise", "minecraft", "mc"]
    },
    {
        "id": "telegram",
        "name": "Telegram (Uygulama)",
        "icon": "✈️",
        "category": "Mesajlaşma & Bildirim",
        "item_type": "app",
        "domains": ["web.telegram.org", "telegram.org", "t.me"],
        "exe_names": ["Telegram.exe", "Unigram.exe"],
        "tab_keywords": ["telegram"],
        "aliases": ["telegram", "tg"]
    },
    {
        "id": "spotify",
        "name": "Spotify (Uygulama)",
        "icon": "🎧",
        "category": "Video & Yayın",
        "item_type": "app",
        "domains": ["spotify.com", "open.spotify.com"],
        "exe_names": ["Spotify.exe"],
        "tab_keywords": ["spotify"],
        "aliases": ["spotify", "spoti"]
    },
    {
        "id": "capcut",
        "name": "CapCut",
        "icon": "✂️",
        "category": "Diğer",
        "item_type": "app",
        "domains": [],
        "exe_names": ["CapCut.exe"],
        "tab_keywords": [],
        "aliases": ["capcut", "cap cut"]
    },
]


# ==============================================================================
# 2. ASİSTAN'IN SEÇTİKLERİ (SADECE WEB SİTELERİ — UYGULAMALARA DOKUNMAZ!)
# Ucuz dopamin salgılatan sosyal medya, kısa video, yayın, dizi/film, anime,
# tarayıcı oyunları, bahis/kumar, alışveriş, yapay zeka sohbet ve +18 uygunsuz
# sitelerin tamamı. Hedef kilit tarihine kadar KİLİTLİ gelir.
# ==============================================================================
ASISTAN_SITE_PICKS = [
    # --- A. SONSUZ KAYDIRMA & KISA VİDEO (SOSYAL MEDYA) ---
    {
        "id": "instagram",
        "name": "Instagram (Reels & DM)",
        "icon": "📸",
        "badge_char": "I",
        "badge_color": "#e1306c",
        "category": "Sosyal Medya & Reels",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "instagram.com", "www.instagram.com", "i.instagram.com",
            "l.instagram.com", "instagr.am"
        ],
        "exe_names": [],
        "tab_keywords": [
            "instagram", "• instagram", "• direct", "gelen kutusu •",
            "sohbetler •", "inbox • direct"
        ],
        "aliases": ["instagram", "insta", "ig"]
    },
    {
        "id": "tiktok",
        "name": "TikTok (Kısa Video Tuzağı)",
        "icon": "🎵",
        "badge_char": "T",
        "badge_color": "#db2777",
        "category": "Sosyal Medya & Reels",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "tiktok.com", "www.tiktok.com", "m.tiktok.com",
            "vm.tiktok.com", "vt.tiktok.com"
        ],
        "exe_names": [],
        "tab_keywords": ["tiktok", "- tiktok", "| tiktok"],
        "aliases": ["tiktok", "tik tok"]
    },
    {
        "id": "twitter",
        "name": "X / Twitter (Doomscrolling)",
        "icon": "🐦",
        "badge_char": "X",
        "badge_color": "#0284c7",
        "category": "Sosyal Medya & Reels",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "twitter.com", "www.twitter.com", "mobile.twitter.com",
            "x.com", "www.x.com", "t.co"
        ],
        "exe_names": [],
        "tab_keywords": ["/ x", "twitter", "x'te "],
        "aliases": ["twitter", "x", "x.com", "twit"]
    },
    {
        "id": "reddit",
        "name": "Reddit (Sonsuz Forum & Meme)",
        "icon": "👽",
        "badge_char": "R",
        "badge_color": "#ea580c",
        "category": "Sosyal Medya & Reels",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "reddit.com", "www.reddit.com", "old.reddit.com",
            "new.reddit.com", "out.reddit.com", "redd.it"
        ],
        "exe_names": [],
        "tab_keywords": ["reddit -", ": reddit", "r/"],
        "aliases": ["reddit", "redit"]
    },
    {
        "id": "eksisozluk",
        "name": "Ekşi, Uludağ & İnci Sözlük",
        "icon": "🍋",
        "badge_char": "E",
        "badge_color": "#65a30d",
        "category": "Gündem & Sözlük",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "eksisozluk.com", "www.eksisozluk.com", "eksisozluk1923.com",
            "eksisozluk111.com", "eksiseyler.com", "uludagsozluk.com",
            "www.uludagsozluk.com", "incisozluk.com.tr", "normalsozluk.com"
        ],
        "exe_names": [],
        "tab_keywords": ["ekşi sözlük", "ekşi şeyler", "uludağ sözlük", "inci sözlük"],
        "aliases": ["ekşi", "eksisozluk", "ekşi sözlük", "uludağ sözlük"]
    },
    {
        "id": "facebook",
        "name": "Facebook, Threads & Bluesky",
        "icon": "📘",
        "badge_char": "F",
        "badge_color": "#1d4ed8",
        "category": "Sosyal Medya & Reels",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "facebook.com", "www.facebook.com", "m.facebook.com", "fb.com",
            "fb.watch", "threads.net", "www.threads.net", "bsky.app"
        ],
        "exe_names": [],
        "tab_keywords": ["facebook", "threads", "bluesky"],
        "aliases": ["facebook", "face", "fb", "threads", "bluesky"]
    },
    {
        "id": "ag_pinterest_tumblr_9gag",
        "name": "9GAG, Pinterest, Tumblr & Imgur",
        "icon": "🎭",
        "badge_char": "9",
        "badge_color": "#ca8a04",
        "category": "Sosyal Medya & Reels",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "9gag.com", "www.9gag.com", "pinterest.com", "www.pinterest.com",
            "tr.pinterest.com", "tumblr.com", "www.tumblr.com",
            "imgur.com", "www.imgur.com", "knowyourmeme.com", "ifunny.co"
        ],
        "exe_names": [],
        "tab_keywords": ["9gag", "pinterest", "tumblr", "imgur"],
        "aliases": ["9gag", "pinterest", "tumblr", "imgur"]
    },
    {
        "id": "ag_snapchat_webchat",
        "name": "Snapchat Web, NGL, Ask.fm & Anonim Sohbet",
        "icon": "👻",
        "badge_char": "S",
        "badge_color": "#eab308",
        "category": "Web Sohbet & Mesajlaşma",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "snapchat.com", "www.snapchat.com", "web.snapchat.com",
            "ngl.link", "ask.fm", "tellonym.me", "kik.com", "yubo.live"
        ],
        "exe_names": [],
        "tab_keywords": ["snapchat", "tellonym", "ask.fm"],
        "aliases": ["snapchat", "snapchat web", "tellonym", "ask.fm"]
    },

    # --- B. CANLI YAYIN, DİZİ, FİLM & ANİME TUZAKLARI ---
    {
        "id": "twitch",
        "name": "Twitch (Canlı Yayın)",
        "icon": "🟣",
        "badge_char": "T",
        "badge_color": "#9333ea",
        "category": "Canlı Yayın & Video",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": ["twitch.tv", "www.twitch.tv", "m.twitch.tv", "clips.twitch.tv"],
        "exe_names": [],
        "tab_keywords": ["- twitch", "twitch"],
        "aliases": ["twitch", "twich"]
    },
    {
        "id": "kick",
        "name": "Kick (Canlı Yayın)",
        "icon": "🟩",
        "badge_char": "K",
        "badge_color": "#16a34a",
        "category": "Canlı Yayın & Video",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": ["kick.com", "www.kick.com"],
        "exe_names": [],
        "tab_keywords": ["| kick", "- kick"],
        "aliases": ["kick", "kick.com"]
    },
    {
        "id": "netflix",
        "name": "Netflix, Disney+ & Prime Video",
        "icon": "🎬",
        "badge_char": "N",
        "badge_color": "#b91c1c",
        "category": "Dizi & Film Platformları",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "netflix.com", "www.netflix.com", "disneyplus.com", "www.disneyplus.com",
            "primevideo.com", "www.primevideo.com", "tv.apple.com", "max.com", "hbomax.com"
        ],
        "exe_names": [],
        "tab_keywords": ["netflix", "disney+", "prime video", "hbo max"],
        "aliases": ["netflix", "disney+", "disney plus", "prime video"]
    },
    {
        "id": "ag_yerli_dizi_platform",
        "name": "BluTV, Exxen, Gain, TOD & Tabii",
        "icon": "🍿",
        "badge_char": "B",
        "badge_color": "#2563eb",
        "category": "Dizi & Film Platformları",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "blutv.com", "www.blutv.com", "exxen.com", "www.exxen.com",
            "gain.tv", "www.gain.tv", "todtv.com.tr", "www.todtv.com.tr",
            "mubi.com", "www.mubi.com", "tabii.com", "www.tabii.com",
            "puhutv.com", "www.puhutv.com"
        ],
        "exe_names": [],
        "tab_keywords": ["blutv", "exxen", "gain", "tod tv", "mubi", "puhutv"],
        "aliases": ["blutv", "exxen", "gain", "tod", "mubi", "tabii", "puhutv"]
    },
    {
        "id": "ag_korsan_film_dizi",
        "name": "Korsan Dizi & Film Siteleri (HDFilm, Dizibox, YabancıDizi)",
        "icon": "🎞️",
        "badge_char": "F",
        "badge_color": "#dc2626",
        "category": "Dizi & Film Platformları",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "hdfilmcehennemi.com", "www.hdfilmcehennemi.com", "hdfilmcehennemi.de",
            "hdfilmcehennemi.cx", "hdfilmcehennemi.life", "hdfilmcehennemi.nl",
            "dizibox.com", "dizibox.tv", "dizibox.de", "dizibox.pro",
            "yabancidizi.pro", "yabancidizi.tv", "yabancidizi.org", "yabancidizi.pw",
            "jetfilmizle.com", "jetfilmizle.de", "jetfilmizle.live", "jetfilmizle.cx",
            "fullhdfilmizlesene.de", "fullhdfilmizlesene.pw", "fullhdfilmizlesene.com",
            "sinefy.com", "dizilla.com", "dizilla.club", "dizigom.tv",
            "sezonlukdizi.vip", "dizipal.com", "webteizle.vip", "webteizle.info",
            "stremio.com", "web.stremio.com"
        ],
        "exe_names": [],
        "tab_keywords": [
            "hdfilmcehennemi", "dizibox", "yabancıdizi", "yabancidizi",
            "jetfilmizle", "fullhdfilmizlesene", "dizilla", "dizigom",
            "sezonlukdizi", "dizipal", "webteizle", "film izle", "dizi izle"
        ],
        "aliases": ["hdfilmcehennemi", "dizibox", "yabancidizi", "jetfilmizle", "dizipal"]
    },
    {
        "id": "ag_anime_manga_webtoon",
        "name": "Anime, Manga & Webtoon Siteleri (TürkAnime, Crunchyroll)",
        "icon": "⛩️",
        "badge_char": "A",
        "badge_color": "#f97316",
        "category": "Anime & Manga",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "turkanime.co", "www.turkanime.co", "turkanime.tv",
            "crunchyroll.com", "www.crunchyroll.com", "anizm.net", "anizm.tv",
            "animecix.net", "animecix.tv", "diziwatch.net", "tranimeizle.co",
            "tranimeizle.top", "webtoons.com", "www.webtoons.com",
            "mangadenizi.net", "sadscans.com", "mangasehri.com", "asurascans.com",
            "asuracomic.net", "9anime.pe", "hianime.to", "aniwave.to",
            "mangadex.org", "myanimelist.net"
        ],
        "exe_names": [],
        "tab_keywords": [
            "türkanime", "turkanime", "crunchyroll", "anizm", "animecix",
            "diziwatch", "tranimeizle", "anime izle", "manga oku", "webtoon"
        ],
        "aliases": ["turkanime", "türkanime", "crunchyroll", "animecix", "diziwatch", "manga"]
    },

    # --- C. UYGUNSUZ (+18 / YETİŞKİN / NSFW / CAM / ONLYFANS) DOPAMİN TUZAKLARI ---
    {
        "id": "ag_nsfw_tube_1",
        "name": "+18 Yetişkin Video Siteleri (Küresel - Paket 1)",
        "icon": "🔞",
        "badge_char": "18",
        "badge_color": "#991b1b",
        "category": "Uygunsuz (+18 / NSFW)",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "pornhub.com", "www.pornhub.com", "rt.pornhub.com", "de.pornhub.com",
            "xvideos.com", "www.xvideos.com", "xv-ru.com",
            "xnxx.com", "www.xnxx.com", "xnxx.tv",
            "xhamster.com", "www.xhamster.com", "tr.xhamster.com", "xhamster.desi",
            "redtube.com", "www.redtube.com", "youporn.com", "www.youporn.com",
            "tube8.com", "www.tube8.com", "spankbang.com", "www.spankbang.com",
            "tr.spankbang.com", "la.spankbang.com", "eporner.com", "www.eporner.com",
            "hqporner.com", "www.hqporner.com", "beeg.com", "www.beeg.com",
            "thumbzilla.com", "txxx.com", "vjav.com", "javhd.com", "missav.com"
        ],
        "exe_names": [],
        "tab_keywords": [
            "pornhub", "xvideos", "xnxx", "xhamster", "redtube", "youporn",
            "spankbang", "eporner", "hqporner", "beeg", "thumbzilla"
        ],
        "aliases": ["pornhub", "xvideos", "xnxx", "xhamster", "spankbang"]
    },
    {
        "id": "ag_nsfw_tube_2",
        "name": "+18 Yetişkin Video & Arşiv Siteleri (Paket 2)",
        "icon": "🔞",
        "badge_char": "18",
        "badge_color": "#7f1d1d",
        "category": "Uygunsuz (+18 / NSFW)",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "brazzers.com", "www.brazzers.com", "realitykings.com",
            "naughtyamerica.com", "bangbros.com", "mofos.com", "babes.com",
            "digitalplayground.com", "twistys.com", "vixen.com", "blacked.com",
            "tushy.com", "deeper.com", "shesfreaky.com", "motherless.com",
            "heavy-r.com", "efukt.com", "daftsex.com", "sxyprn.com",
            "porntrex.com", "www.porntrex.com", "fuq.com", "pornone.com",
            "tnaflix.com", "drtuber.com", "sunporno.com", "anyporn.com",
            "upornia.com", "gotporn.com", "empflix.com", "slutload.com"
        ],
        "exe_names": [],
        "tab_keywords": [
            "brazzers", "realitykings", "bangbros", "vixen", "blacked",
            "motherless", "sxyprn", "porntrex", "tnaflix", "daftsex"
        ],
        "aliases": ["brazzers", "porntrex", "sxyprn", "motherless"]
    },
    {
        "id": "ag_nsfw_cam_onlyfans",
        "name": "+18 Canlı Kamera, OnlyFans, Fansly & Görüntülü Sohbet",
        "icon": "🚫",
        "badge_char": "OF",
        "badge_color": "#be123c",
        "category": "Uygunsuz (+18 / NSFW)",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "onlyfans.com", "www.onlyfans.com", "fansly.com", "www.fansly.com",
            "manyvids.com", "loyalfans.com", "mym.fans",
            "chaturbate.com", "www.chaturbate.com", "stripchat.com", "www.stripchat.com",
            "bongacams.com", "www.bongacams.com", "livejasmin.com", "www.livejasmin.com",
            "cam4.com", "www.cam4.com", "myfreecams.com", "camsoda.com",
            "flirt4free.com", "jerkmate.com", "coomeet.com", "omegle.com",
            "ometv.chat", "monkey.app", "emeraldchat.com", "dirtyroulette.com",
            "chatrandom.com", "chatroulette.com", "bazoocam.org", "shagle.com"
        ],
        "exe_names": [],
        "tab_keywords": [
            "onlyfans", "fansly", "chaturbate", "stripchat", "bongacams",
            "livejasmin", "cam4", "camsoda", "jerkmate", "ometv", "omegle",
            "coomeet", "chatrandom", "chatroulette"
        ],
        "aliases": ["onlyfans", "fansly", "chaturbate", "stripchat", "ometv", "omegle"]
    },
    {
        "id": "ag_nsfw_hentai_leaks",
        "name": "+18 NSFW Görsel, Sızıntı, Rule34 & Hentai Siteleri",
        "icon": "🔞",
        "badge_char": "R",
        "badge_color": "#881337",
        "category": "Uygunsuz (+18 / NSFW)",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "rule34.xxx", "rule34.paheal.net", "rule34video.com", "rule34.us",
            "nhentai.net", "www.nhentai.net", "nhentai.to", "hanime.tv",
            "www.hanime.tv", "hentaihaven.xxx", "e-hentai.org", "exhentai.org",
            "gelbooru.com", "danbooru.donmai.us", "sankakucomplex.com",
            "kemono.su", "coomer.su", "fapello.com", "www.fapello.com",
            "thothub.to", "thothub.lol", "simpcity.su", "erome.com",
            "www.erome.com", "redgifs.com", "www.redgifs.com", "imagefap.com",
            "luscious.net", "bunkr.si", "bunkr.ALBUM", "cyberdrop.me",
            "joyreactor.cc", "hitomi.la", "tsumino.com"
        ],
        "exe_names": [],
        "tab_keywords": [
            "rule34", "nhentai", "hanime", "hentaihaven", "e-hentai",
            "gelbooru", "fapello", "thothub", "simpcity", "erome", "redgifs",
            "kemono", "coomer", "hitomi.la"
        ],
        "aliases": ["rule34", "nhentai", "hanime", "fapello", "erome", "redgifs"]
    },
    {
        "id": "ag_dating_flirt",
        "name": "Flört & Tanışma Siteleri (Tinder, Bumble, Badoo, C2)",
        "icon": "💘",
        "badge_char": "T",
        "badge_color": "#ec4899",
        "category": "Uygunsuz (+18 / NSFW)",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "tinder.com", "www.tinder.com", "bumble.com", "www.bumble.com",
            "badoo.com", "www.badoo.com", "okcupid.com", "www.okcupid.com",
            "happn.com", "feeld.co", "siberalem.com", "www.siberalem.com",
            "c2me.cc", "connected2.me", "azarslive.com", "azarlive.com",
            "litmatchapp.com", "wink.org"
        ],
        "exe_names": [],
        "tab_keywords": [
            "tinder", "bumble", "badoo", "okcupid", "siberalem", "connected2"
        ],
        "aliases": ["tinder", "bumble", "badoo", "okcupid", "c2", "connected2"]
    },

    # --- D. TARAYICI OYUNLARI, .IO OYUNLARI & OYUN TOPLULUKLARI ---
    {
        "id": "ag_browser_io_games",
        "name": "Tarayıcı & .io Oyunları (Poki, CrazyGames, Krunker, Gartic)",
        "icon": "🕹️",
        "badge_char": "I",
        "badge_color": "#4f46e5",
        "category": "Tarayıcı Oyunları",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "poki.com", "www.poki.com", "poki.com.tr", "crazygames.com",
            "www.crazygames.com", "itch.io", "www.itch.io", "krunker.io",
            "agar.io", "slither.io", "diep.io", "surviv.io", "shellshock.io",
            "1v1.lol", "ev.io", "venge.io", "zombsroyale.io", "paper-io.com",
            "hole-io.com", "gartic.io", "garticphone.com", "skribbl.io",
            "codenames.game", "geoguessr.com", "www.geoguessr.com", "neal.fun",
            "miniclip.com", "y8.com", "kongregate.com", "newgrounds.com",
            "oyunkolu.com", "oyunskor.com", "kraloyun.com"
        ],
        "exe_names": [],
        "tab_keywords": [
            "poki", "crazygames", "krunker", "agar.io", "slither.io",
            "gartic", "skribbl", "geoguessr", "1v1.lol", "oyunskor", "kraloyun"
        ],
        "aliases": ["poki", "crazygames", "krunker", "gartic", "agar.io", "slither.io"]
    },
    {
        "id": "ag_chess_puzzles",
        "name": "Hızlı Satranç & Oyun İstatistik Siteleri (Chess.com, Lichess, OP.GG)",
        "icon": "♟️",
        "badge_char": "C",
        "badge_color": "#15803d",
        "category": "Tarayıcı Oyunları",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "chess.com", "www.chess.com", "lichess.org", "www.lichess.org",
            "op.gg", "www.op.gg", "u.gg", "tracker.gg", "blitz.gg",
            "futbin.com", "hltv.org", "vlr.gg"
        ],
        "exe_names": [],
        "tab_keywords": [
            "chess.com", "lichess",
            "op.gg", "tracker.gg", "futbin", "hltv", "vlr.gg"
        ],
        "aliases": ["chess.com", "lichess", "op.gg", "futbin", "hltv", "vlr.gg"]
    },

    # --- E. BAHİS, İDDAA, KUMAR & CS2 KASA AÇMA SİTELERİ ---
    {
        "id": "ag_gambling_betting",
        "name": "Bahis, İddaa, Canlı Skor & CS2 Kasa Açma Siteleri",
        "icon": "🎰",
        "badge_char": "$",
        "badge_color": "#b45309",
        "category": "Bahis & Şans Oyunları",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "nesine.com", "www.nesine.com", "misli.com", "www.misli.com",
            "bilyoner.com", "www.bilyoner.com", "tuttur.com", "www.tuttur.com",
            "iddaa.com", "www.iddaa.com", "mackolik.com", "www.mackolik.com",
            "sahadan.com", "www.sahadan.com", "flashscore.com.tr", "sofascore.com",
            "stake.com", "roobet.com", "key-drop.com", "hellcase.com",
            "csgoroll.com", "datdrop.com", "farmskins.com", "clash.gg",
            "rustclash.com", "gamdom.com", "bc.game", "1xbet.com"
        ],
        "exe_names": [],
        "tab_keywords": [
            "nesine", "misli", "bilyoner", "tuttur", "iddaa", "mackolik",
            "maçkolik", "sahadan", "key-drop", "hellcase", "csgoroll", "stake"
        ],
        "aliases": ["nesine", "misli", "bilyoner", "mackolik", "iddaa", "key-drop", "hellcase"]
    },

    # --- F. ALIŞVERİŞ & VİTRİN GEZİNME (DOPAMİN ALIŞVERİŞİ) ---
    {
        "id": "ag_ilan_vitrin",
        "name": "İlan & Vitrin Gezinme (Sahibinden, Letgo, Dolap, Arabam)",
        "icon": "🚗",
        "badge_char": "S",
        "badge_color": "#eab308",
        "category": "Alışveriş & Vitrin",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "sahibinden.com", "www.sahibinden.com", "letgo.com", "www.letgo.com",
            "dolap.com", "www.dolap.com", "gardrops.com", "www.gardrops.com",
            "arabam.com", "www.arabam.com"
        ],
        "exe_names": [],
        "tab_keywords": ["sahibinden.com", "sahibinden", "letgo", "dolap", "arabam.com"],
        "aliases": ["sahibinden", "letgo", "dolap", "arabam"]
    },
    {
        "id": "ag_eticaret_alisveris",
        "name": "E-Ticaret & İndirim Gezinme (Trendyol, Hepsiburada, Temu)",
        "icon": "🛍️",
        "badge_char": "T",
        "badge_color": "#f97316",
        "category": "Alışveriş & Vitrin",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "trendyol.com", "www.trendyol.com", "hepsiburada.com", "www.hepsiburada.com",
            "n11.com", "www.n11.com", "temu.com", "www.temu.com",
            "aliexpress.com", "tr.aliexpress.com", "akakce.com", "www.akakce.com",
            "cimri.com", "www.cimri.com", "ciceksepeti.com", "boyner.com.tr"
        ],
        "exe_names": [],
        "tab_keywords": [
            "trendyol", "hepsiburada", "temu", "aliexpress", "akakçe", "cimri"
        ],
        "aliases": ["trendyol", "hepsiburada", "temu", "aliexpress", "akakce", "n11"]
    },

    # --- G. YAPAY ZEKA KARAKTER SOHBET & DEDİKODU / TEST SİTELERİ ---
    {
        "id": "ag_ai_roleplay",
        "name": "Yapay Zeka Karakter & Rol Sohbet (Character.AI, JanitorAI, Chai)",
        "icon": "🤖",
        "badge_char": "AI",
        "badge_color": "#6366f1",
        "category": "Yapay Zeka Rol Sohbet",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "character.ai", "beta.character.ai", "old.character.ai",
            "janitorai.com", "www.janitorai.com", "crushon.ai", "spicychat.ai",
            "chub.ai", "polybuzz.ai", "talkie-ai.com", "caveduck.io",
            "joyland.ai", "chai-research.com", "venus.chub.ai", "figgs.ai",
            "sakura.fm", "dopple.ai", "yodayo.com", "moescape.ai"
        ],
        "exe_names": [],
        "tab_keywords": [
            "character.ai", "janitorai", "crushon", "spicychat", "polybuzz",
            "talkie", "dopple.ai"
        ],
        "aliases": ["character.ai", "c.ai", "janitorai", "spicychat", "crushon"]
    },
    {
        "id": "ag_dedikodu_magazin_forum",
        "name": "Magazin, Test & Boş Gezinme (Onedio, KızlarSoruyor, BuzzFeed)",
        "icon": "🗞️",
        "badge_char": "O",
        "badge_color": "#0ea5e9",
        "category": "Gündem & Sözlük",
        "item_type": "site",
        "antigravity_pick": True,
        "default_blocked": True,
        "domains": [
            "onedio.com", "www.onedio.com", "kizlarsoruyor.com", "www.kizlarsoruyor.com",
            "buzzfeed.com", "www.buzzfeed.com", "boredpanda.com", "listelist.com",
            "donanimhaber.com", "forum.donanimhaber.com", "technopat.net",
            "shiftdelete.net", "webtekno.com", "인벤", "9gag.com"
        ],
        "exe_names": [],
        "tab_keywords": [
            "onedio", "kızlarsoruyor", "kizlarsoruyor", "buzzfeed", "donanımhaber"
        ],
        "aliases": ["onedio", "kizlarsoruyor", "kızlarsoruyor", "buzzfeed", "donanimhaber"]
    },
]

# Tüm varsayılan öğelerin birleşimi (BlockerEngine tarafından yüklenir)
ANTIGRAVITY_SITE_PICKS = ASISTAN_SITE_PICKS
ALL_PRESET_ITEMS = DEFAULT_ITEMS + ASISTAN_SITE_PICKS
