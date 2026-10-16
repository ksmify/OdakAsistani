# -*- coding: utf-8 -*-
"""
Odak Asistanı — Zengin Psikolojik Motivasyon & Koçluk Motoru (LLM-Free, Ultra Hafif)
110+ Durumsal Askeri / YKS Koçu / Nöro-Biyoloji Sözü ve Geri Bildirim Sistemi.
"""

import random

MOTIVATION_DATABASE = {
    # 1. SERT DİSİPLİNCİ KOMUTAN PERSONASI
    "komutan": {
        "idle": [
            "Masaya otur asker! Düşmanların uyumuyor, rakiplerin soru bankalarını parçalıyor!",
            "Tembellik bu odada yasaklandı! Sayacı başlat ve kalemini kılıç gibi kullan!",
            "Ertelediğin her dakika, amfideki koltuğunu bir başkasına hibe ediyorsun!",
            "Masa başında pineklemeye gelmedik. Başla ve masayı inlet!",
            "Komutan emrediyor: Oyunu, telefonu, bahaneleri bırak. Hedef tahtasına geç!",
            "Bahaneler zayıfların sığınağıdır. Masaya geç ve gücünü göster asker!",
            "Düşünmeyi bırak, harekete geç! Bir asker zaferi masada kazanır!",
            "Boş oturmak senin rütbene yakışmıyor. Derhal ders sayacını aktif et!",
            "Askerin en büyük silahı disiplindir. Masaya geç ve taarruza başla!",
            "Zafer tesadüf değildir. Masada ter dökmeyen amfide gurur duyamaz!",
        ],
        "studying": [
            "Mükemmel tempo asker! Bu odaklanmayı hiçbir güç kıramaz!",
            "Baskı altında parlayanlar şampiyon olur. Çizgini bozma, devam et!",
            "Şu an hissettiğin yorgunluk, yarın hissedeceğin pişmanlıktan bin kat daha hafiftir!",
            "Kaleminin ucu körelene kadar devam! Hedefine giden yol bu masadan geçer!",
            "Odaklan asker! Gözün sadece soruda ve konuda olsun!",
            "Zafer terle kazanılır. Sayacın her saniyesi rütbene yeni bir yıldız ekliyor!",
            "Taviz yok, geri adım yok! Sonuna kadar taarruz!",
            "Gözünü hedeften ayırma! Bir soruyu çözmek, bir kaleyi fethetmektir!",
            "Yorulmak yok asker! Rakiplerin yorulduğunda sen devam ettiğin için kazanacaksın!",
            "Sert ol, kararlı ol! Bu masadan galip çıkacağız!",
        ],
        "break_approaching": [
            "Baraja çok az kaldı asker! Son metrelerde temposunu artıranlar yarışı kazanır!",
            "Mola hakkını söke söke almak üzeresin. Son sprinti at ve bitir!",
            "Baraj kapıları açılmak üzere, son gayretini ortaya koy!",
            "Hak edilmiş zafer molasına dakikalar var. Dikkati en üst seviyede tut!",
            "Son 5 dakika asker! Sancağı en tepeye dikene kadar gevşemek yasak!",
        ],
        "break_time": [
            "Hak edilmiş mola başladı asker! Nefes al, suyunu iç ama zihnini rehavete teslim etme!",
            "Dinlenmek askerin hakkıdır. Süren dolduğunda aynı sertlikle masaya döneceksin!",
            "Molanı al ama gardını düşürme. Zafer henüz bitmedi!",
            "Bu molayı alın teriyle kazandın. Enerjini topla!",
            "Rehavet düşmanın müttefikidir. Dinlen ama zihnini teyakkuzda tut!",
        ],
        "break_ending": [
            "Mola bitti asker! Oyun kapandı, dinlenme tamamlandı. Derhal masaya dön!",
            "Rehavet düşmandır! Molan bitti, savaş kaldığı yerden devam ediyor!",
            "Zaman doldu asker! Masana otur ve sayacı tekrar ateşle!",
            "Kalk o koltuktan! Hedeflediğin üniversite seni bekliyor!",
            "Emir geldi: Mola kapandı! Kalemleri çek, derhal taarruza!",
        ],
        "goal_reached": [
            "GÖREV TAMAMLANDI ASKER! Bugün hedefini darmadağın ettin!",
            "Tebrikler asker! Rakiplerin pes ederken sen zafer bayrağını diktin!",
            "İşte bu! Gerçek bir irade ve disiplin zaferi. Gurur duy!",
            "Bugünkü muharebeyi mutlak zaferle kazandın. Rütben tebrik edilmeye değer!",
        ],
        "night": [
            "Saat 00:00'ı geçti asker! Biyolojini bozma, dinlenmiş bir zihin yarın iki kat daha güçlü vurur!",
            "Günün zaferi tamamlandıysa istirahate çekil. Yarın yeni bir cephe açılacak!",
            "Uykun da disiplinin bir parçasıdır. Gözlerini dinlendir ve yarına hazırlan!",
            "Geceyi boş geçirme ama uykunu da feda etme. Zinde uyanan asker cepheyi fetheder!",
        ]
    },

    # 2. STRATEJİK YKS DERECE KOÇU PERSONASI
    "yks_kocu": {
        "idle": [
            "Her gün çözdüğün fazladan 20 soru, seni sıralamada 5.000 kişinin önüne taşır.",
            "Sonuç belgendeki derece tesadüfen yazılmayacak; bugün masada attığın adımlarla yazılacak.",
            "Ertelemek, gelecekteki potansiyeline borçlanmaktır. Şimdi başla, faiz ödeme.",
            "Hedefin ilk 1.000 ise, ilk 10.000 gibi çalışamazsın. Başla!",
            "Sınav anında 'keşke' dememek için şu an 'iyi ki' diyeceğin çalışmayı yap.",
            "Netlerin masada geçirilen odaklı saatlerle doğru orantılıdır. Sayacı başlat.",
            "Rakiplerin şu an deneme analizinde. Masaya geç ve farkı kapat!",
            "Büyük hedefler küçük ve istikrarlı bloklarla kazanılır. İlk bloğunu başlat.",
        ],
        "studying": [
            "Müthiş bir derinleşme! Yanlış yaptığın her soru, sınavda çıkabilecek bir açığı kapatmaktır.",
            "Zorlandığın yer tam da netlerinin artacağı eşiktir. Pes etme, üstüne git.",
            "Turlama taktiğini unutma: Yapamadığın soruyu işaretle, devam et, geri dön.",
            "Şu anki odak kaliten, gerçek sınavdaki soğukkanlılığının temelini atıyor.",
            "Günde 4 kaliteli blok, 8 saatlik dağınık çalışmadan kat kat üstündür.",
            "Zihnini tek bir soruya ada. Stratejik odaklanma net kazandırır.",
            "Çözdüğün her kaliteli soru, net havuzuna bir damla daha ekliyor.",
            "Bu çalışma seni hedeflediğin kampüse bir adım daha yaklaştırdı.",
        ],
        "break_approaching": [
            "Bloğun sonuna geliyoruz. Son soruları dikkatle incele, dikkati dağıtma.",
            "Mola kapısı açılmak üzere. Son dakikalarda gelen konsantrasyon sınav pratiğidir.",
            "Hedef çalışma sürene 5 dakika kaldı. Bu bloğu mükemmel kapat.",
            "Mola yaklaşırken odağını düşürme; son virajı en iyi şekilde al.",
        ],
        "break_time": [
            "Stratejik dinlenme vakti. Ekrandan uzaklaş, beynine bilgileri sindirmesi için alan tanı.",
            "10 dakikalık mola, nörolojik olarak öğrenilenlerin pekişmesini sağlar. İyi değerlendir.",
            "Gözlerini ve boynunu dinlendir. Bir sonraki blok için zihnini tazele.",
            "Kısa bir nefes molası, sonraki bloğun verimini iki katına çıkaracaktır.",
        ],
        "break_ending": [
            "Mola süresi tamamlandı. Şimdi yeni bir soru bloğuyla stratejiyi sürdürme zamanı.",
            "Zaman doldu. Masana dön ve netlerini artırmaya devam et.",
            "Gevşeme bitti; sıradaki ders bloğu masada seni bekliyor.",
            "Planına sadık kal. İkinci yarı başlıyor, masaya dön!",
        ],
        "goal_reached": [
            "Günün soru hedefi kusursuz tamamlandı! İstikrar budur, başarı budur.",
            "Bugünkü stratejik planı harfiyen uyguladın. Bu disiplin seni dereceye taşıyacak.",
            "Tebrikler! Günlük kotanı aştın, yarın aynı azimle devam edeceğiz.",
        ],
        "night": [
            "Gece geç saatlerde verim düşer. Günün tekrarını yapıp uykuya geçmek en doğrusudur.",
            "Zihinsel konsolidasyon için kaliteli uyku şarttır. Yarın erken başlamak için dinlen.",
            "Bugünkü emeğinin karşılığını beynin uykuda işleyecek. İstirahate geç.",
        ]
    },

    # 3. NÖRO-BİYOLOJİ & STOİK ODAK PERSONASI
    "noro_biyoloji": {
        "idle": [
            "Dopamin detoksu masada başlar. Kısa vadeli hazzı ertele, uzun vadeli zafere odaklan.",
            "Prefrontal korteksini kontrol altına al. Dürtülerine değil, hedefine boyun eğdir.",
            "Başlamak en zor nöral geçiştir; ilk 5 dakikayı atlattığında akış hormonu salgılanır.",
            "Zihnini sakinleştir, solunumunu yavaşlat ve odağını tek bir göreve daralt.",
            "Stoik felsefe: Kontrol edemeyeceğin şeyleri bırak, şu an masada yapabileceğin tek şeye odaklan.",
            "Dikkatin dağılması bir sinyaldir; iradeni çalıştırarak dikkat kasını güçlendir.",
            "Beynin nöroplastisite özelliği sayesinde bugün zorlandığın her şey yarın kolaylaşacak.",
            "Dopamin rezervini ucuz bildirimlerle tüketme; masadaki derin çalışmaya sakla.",
        ],
        "studying": [
            "Derin çalışma (Deep Work) modundasın. Nöral devrelerin en yüksek verimde ateşleniyor.",
            "Dikkatin dağılmak istediğinde diren; her direniş prefrontal korteksini kalınlaştırır.",
            "Akış (Flow) durumunu yakaladın. Dış uyaranları filtrelemeye devam et.",
            "Bilişsel dayanıklılık inşa ediyorsun. Bu zihinsel maraton seni güçlendiriyor.",
            "Zorlandığın an glikoz yakımı artar; bu senin zihninin geliştiğinin kanıtıdır.",
            "Gözlerini tek bir noktaya sabitlemek, zihinsel odağı biyolojik olarak güçlendirir.",
            "Sakin ve kararlı zihin, en karmaşık problemleri bile çözer.",
            "Şu an nörolojik olarak yeni sinaptik bağlar kuruyorsun; sabırla devam et.",
        ],
        "break_approaching": [
            "Nöral yorgunluk eşiğine yaklaşırken son bir gayret odak süreni tamamla.",
            "Odaklanma devresi tamamlanmak üzere. Nörolojik toparlanma periyodu geliyor.",
            "Sinapslar dinlenme sinyali vermeden hemen önce son bilişsel bloğu tamamla.",
            "Biyolojik ritmine uygun mola için son dakikalar; odağını koru.",
        ],
        "break_time": [
            "Göz kaslarını dinlendir, uzağa bak ve dopamin reseptörlerini nötralize et.",
            "Kısa bir yürüyüş ve su, beynindeki adenozin seviyesini dengeleyecektir.",
            "Ekran dışı dinlenme, öğrendiklerinin hipokampusa kaydedilmesini hızlandırır.",
            "Biyolojik sıfırlama anı: Derin diyafram nefesi al ve zihnini boşalt.",
        ],
        "break_ending": [
            "Toparlanma evresi tamamlandı. Korteksin dinlendi, şimdi yeniden derin odak modu.",
            "Mola bitti. Prefrontal odak ağlarını derhal aktif hale getir.",
            "Dikkatin dağılmadan masaya dön; akış durumuna geçişi hızlandır.",
            "Dinlenme süresi doldu. Nöral enerjiyi yeniden derse kanalize et.",
        ],
        "goal_reached": [
            "Günün hedefi başarıyla kapatıldı. Nöroplastisite döngüsü bugün için zaferle tamamlandı.",
            "Yüksek irade, güçlü prefrontal korteks. Bugün zihnine hükmettin.",
            "Bilişsel kapasiten bugün yeni bir seviyeye ulaştı. Tebrikler.",
        ],
        "night": [
            "Uyku, beynin glimfatik sistemiyle toksinleri temizlediği ve hafızayı sabitlediği andır.",
            "Gece saatlerinde melatonin salgısını bozma; kaliteli uyku yarınki odaklanmanın anahtarıdır.",
            "Sirkadiyen ritmini koru; karanlık ve derin bir uyku nöronlarını yenileyecektir.",
        ]
    }
}


def get_motivation_quote(persona: str = "komutan", context: str = "idle") -> str:
    """Belirtilen persona ve bağlama göre motive edici özel bir söz döndürür."""
    p_dict = MOTIVATION_DATABASE.get(persona) or MOTIVATION_DATABASE["komutan"]
    c_list = p_dict.get(context) or p_dict.get("idle") or []
    if not c_list:
        c_list = MOTIVATION_DATABASE["komutan"]["idle"]
    return random.choice(c_list)


def get_all_personas() -> list:
    """Arayüzde gösterilmek üzere mevcut koçluk stillerini listeler."""
    return [
        {
            "id": "komutan",
            "name": "Sert Disiplinci Komutan",
            "desc": "Tavizsiz, disiplinci, askeri ve keskin üslup. Bahanelere geçit vermez.",
            "badge": "KOMUTAN",
            "color": "#f43f5e"
        },
        {
            "id": "yks_kocu",
            "name": "Profesyonel YKS Derece Koçu",
            "desc": "Stratejik, hedef odaklı, net ve kararlı üslup. Derece öğrencisi zihniyeti aşılar.",
            "badge": "DERECE KOÇU",
            "color": "#38bdf8"
        },
        {
            "id": "noro_biyoloji",
            "name": "Nöro-Biyoloji & Stoik Odak",
            "desc": "Dopamin yönetimi, akış hali ve bilişsel bilim felsefesi. Zihinsel enerjiyi korur.",
            "badge": "BİLİMSEL ODAK",
            "color": "#10b981"
        }
    ]
