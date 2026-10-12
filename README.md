# 🎯 Odak Asistanı (YKS / Ders Odak & Katı Koruma Sistemi)

**Odak Asistanı**, sınav hazırlık sürecinde (YKS / TYT / AYT, KPSS, LGS ve genel ders çalışma) dikkat dağıtan uygulama, oyun ve web sitelerini katı koruma altına alan; **YouTube**, **ÜçDörtBeş**, **Bilgi Sarmal** ve kendi eklediğiniz tüm **Kaynak Sitelerden** izlenen ders videolarını saniyesi saniyesine algılayıp hem ders sürelerinize hem de **Ödül Mola Barajına** işleyen modern bir masaüstü uygulamasıdır.

---

## ✨ Temel Özellikler

- **🎓 İnteraktif Öğretici Modal ("🎓 Nasıl Çalışır?"):**
  - Üst çubukta yer alan butona tıklayarak menülerin işlevlerini, komut kutusunu, tavizsiz kilit kurallarını ve mola mantığını adım adım, akıcı obsidian kartları ve nokta göstergeleriyle inceleyebilirsiniz.

- **🛡️ Asistan'ın Seçtikleri:**
  - Sosyal medya, Shorts/Reels, canlı yayınlar, dizi/film, web oyunları ve dopamin hilesi yapılabilecek tüm dikkat dağıtıcılar özenle tek bir pakette toplanmıştır. Kilit koyduğunuz anda otomatik devreye girer.

- **🌐 Kaynak Siteler Menüsü (Dinamik Video Kaynak Yönetimi):**
  - **YouTube** sabit sistem kaynağı olarak yer alır ve izlenen ders videolarını başlığından otomatik algılar (`Matematik`, `Geometri`, `Fizik`, `Kimya`, `Biyoloji`, `Türkçe`, `Sosyal` vb.).
  - **ÜçDörtBeş (`frns.in`)**, **Bilgi Sarmal (`frns.in`)** veya kendi ekleyeceğiniz herhangi bir eğitim sitesini (`3dyayinlari.com`, `ogmmateryal.eba.gov.tr`, `ertansinansahin.com` vb.) **🌐 Kaynak Siteler** sekmesinden ekleyip silebilirsiniz.
  - Eklediğiniz her site için bir **Kategori / Ders** (`Genel (Soru Çözümü / Deneme)`, `Matematik`, `Türkçe & Edebiyat`, `Fizik`, `Kimya`, `Biyoloji`, `Geometri`, `Tarih / Coğrafya / Felsefe` veya `Otomatik`) seçebilirsiniz; o siteden izlenen her video doğrudan seçtiğiniz dersin süresine ve mola barajına işler.
  - Yeni kaynak eklenirken domain ve yayıncı adı otomatik temizlenip şık bir 2-3 harfli rozet kodu ve sade alan adına dönüştürülür.

- **🚫 Sekme Düzeyinde Sayfa Engelleme (Tab Guard & Akıllı URL Kuralı):**
  - `youtube.com/playables` veya `youtube.com/shorts` gibi belirli alt yolları kapatmak istediğinizde, YouTube alan adının tamamı **asla engellenmez** (hosts dosyasına yazılmaz).
  - Yalnızca o adresteki sekme (İngilizce/Türkçe başlık ve adres çubuğu eşleşmesiyle) `Ctrl+W` ile anında kapatılır; ders videoları ve ana sayfa sorunsuz çalışmaya devam eder.

- **🔒 Custom Lock Chooser (Dinamik Kilit Hedefi & Geri Sayım):**
  - Üst bardaki kilit butonuna tıklayarak hedef sınavınızı veya odak kampınızı seçebilirsiniz:
    - **YKS 2027** (18 Haziran 2027 TYT Kilidi)
    - **YKS 2028**
    - **KPSS**, **DGS**, **ALES**, **LGS** Hazırlık Kampları
    - **Vize / Final Odak Kampı (+30 Gün)**
    - **Özel Hedef Tarihi** (Dilediğiniz gün, ay, yıl ve saati belirleme imkanı)
  - **Altın Kural:** Kilit süresi kısaltılamaz, yalnızca ileri tarihe uzatılabilir. Süre dolduğunda ise sayaç yerini otomatik olarak **"Yeni kilit oluştur."** butonuna bırakır.

- **⏸️ Milisaniyelik Oynatma / Duraklatma Algılama (GSMTC + WASAPI + Sekme Kontrolü):**
  - Tarayıcıda ders videosu gerçekten oynarken sayaç ilerler; videoyu durdurduğunuz (`Pause`) veya sekmeyi değiştirdiğiniz anda **1 saniye içinde** sayacı bekletir. Hoca nefes aldığında veya kısa sessizliklerde sürenizi kesmez.

- **⚖️ Ölçeklenebilir Adaletli Mola Barajı:**
  - Sağ alttaki **⚙️ Ayar** simgesinden hedef ders süresini (**40 DK / 45 DK / 1 SAAT / 2 SAAT / 3 SAAT**) ve ödül mola süresini (**5 DK / 10 DK / 20 DK / 30 DK**) istediğiniz an değiştirebilirsiniz.
  - Hedef süreyi değiştirdiğinizde mevcut ilerlemeniz **sıfırlanmaz**; matematiksel oranla yeni hedefe adaletli şekilde uyarlanır.

- **🏆 0 → 100.000 Soru Rütbe ve Çerçeve Evrim Algoritması:**
  - Çözdüğünüz soru sayısı arttıkça ders kartlarının ve genel soru sayacının çerçeve rengi ile rütbesi otomatik olarak seviye atlar.

- **🧹 Taşınabilir ve Kolay Kaldırılabilir Yapı:**
  - GitHub sürümünde silme engellemesi zorlanmaz; başka kullanıcıların bilgisayarında sistem kilitleri oluşturmaz.
  - Uygulamadan çıkıldığında veya **`Kaldir.bat`** çalıştırıldığında tüm hosts kısıtlamaları ve başlangıç kayıtları temizlenir, klasör dilediğinde silinebilir.

---

## 🚀 Hızlı Kurulum (Setup)

Yeni veya sıfır bir bilgisayarda kurulum yapmak için:

1. Bu depoyu indirin (`Code -> Download ZIP` veya `git clone`).
2. Klasör içindeki **`Setup.bat`** (veya **`Kurulum.bat`**) dosyasına çift tıklayın:
   - Bilgisayarınızda Python 3.10+ yoksa **resmi python.org üzerinden otomatik indirir ve kurar**.
   - Gerekli kütüphaneleri (`customtkinter`, `Pillow`, `pystray`, `pywin32`) yükler.
   - Görev yöneticisinde ve görev çubuğunda **Odak Asistanı** logosu ve adı görünmesi için ortamı hazırlar.
   - Masaüstünüze **Odak Asistanı** kısayolu oluşturur ve uygulamayı başlatır.

---

## 🗑️ Uygulamayı Kaldırma

Uygulamayı ve koyduğu tüm engelleri tek tıkla kaldırmak için:
- Klasördeki **`Kaldir.bat`** (veya **`Kaldır.bat`**) dosyasına çift tıklamanız yeterlidir. Tüm hosts yasakları, başlangıç kayıtları ve masaüstü kısayolları anında temizlenir.
