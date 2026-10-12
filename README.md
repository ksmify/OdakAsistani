# 🎯 Odak Asistanı (YKS / Ders Odak & Katı Koruma Sistemi)

**Odak Asistanı**, sınav hazırlık sürecinde (YKS / TYT / AYT ve genel ders çalışma) dikkat dağıtan uygulama, oyun ve web sitelerini katı koruma altına alan; **YouTube**, **ÜçDörtBeş**, **Bilgi Sarmal** ve kendi eklediğiniz tüm **Kaynak Sitelerden** izlenen ders videolarını saniyesi saniyesine algılayıp hem ders sürelerinize hem de **Ödül Mola Barajına** işleyen modern bir masaüstü uygulamasıdır.

---

## ✨ Temel Özellikler

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

- **⏸️ Milisaniyelik Oynatma / Duraklatma Algılama (GSMTC + WASAPI + Sekme Kontrolü):**
  - Tarayıcıda ders videosu gerçekten oynarken sayaç ilerler; videoyu durdurduğunuz (`Pause`) veya sekmeyi değiştirdiğiniz anda **1 saniye içinde** sayacı bekletir. Hoca nefes aldığında veya kısa sessizliklerde sürenizi kesmez.

- **⚖️ Ölçeklenebilir Adaletli Mola Barajı:**
  - Sağ alttaki **⚙️ Ayar** simgesinden hedef ders süresini (**40 DK / 45 DK / 1 SAAT / 2 SAAT / 3 SAAT**) ve ödül mola süresini (**5 DK / 10 DK / 20 DK / 30 DK**) istediğiniz an değiştirebilirsiniz.
  - Hedef süreyi değiştirdiğinizde mevcut ilerlemeniz **sıfırlanmaz**; matematiksel oranla (ör. 3 saatten 45 dakikaya geçildiğinde 1/4 ölçeğiyle) yeni hedefe adaletli şekilde uyarlanır.

- **🏆 0 → 100.000 Soru Rütbe ve Çerçeve Evrim Algoritması:**
  - Çözdüğünüz soru sayısı arttıkça (`0-10`, `10-50`, `50-100`, `100-250`, ... `100.000+`) ders kartlarının ve genel soru sayacının çerçeve rengi ile rütbesi otomatik olarak seviye atlar.

- **🧹 Taşınabilir ve Kolay Kaldırılabilir Yapı:**
  - GitHub sürümünde silme engellemesi zorlanmaz; başka kullanıcıların bilgisayarında sistem kilitleri oluşturmaz.
  - Uygulamadan çıkıldığında veya **`Kaldir.bat`** çalıştırıldığında tüm hosts kısıtlamaları ve başlangıç kayıtları temizlenir, klasör dilediğinde silinebilir.

---

## 🚀 Kurulum ve Çalıştırma (Sıfırdan Başka Bilgisayarda Kullanım)

1. Bilgisayarınızda **Python 3.10+** yüklü olduğundan emin olun ([python.org/downloads](https://www.python.org/downloads/)).
2. Bu depoyu indirin (`Code -> Download ZIP` veya `git clone`).
3. Klasör içindeki **`Kurulum_ve_Baslat.bat`** (veya **`Baslat.bat`**) dosyasına çift tıklayın.
   - İlk açılışta gerekli kütüphaneler (`customtkinter`, `Pillow`, `pystray`) otomatik yüklenir.
   - Masaüstünüze **Odak Asistanı** kısayolu oluşturulur ve tüm sayaçlar/veriler bilgisayarınızda **sıfırdan** başlar.
4. Web sitelerini `hosts` düzeyinde de engellemek için **`Yonetici_Olarak_Baslat.bat`** ile çalıştırabilirsiniz.

---

## 🗑️ Uygulamayı Kaldırma

Uygulamayı ve koyduğu tüm engelleri tek tıkla kaldırmak için:
- Klasördeki **`Kaldir.bat`** dosyasına çift tıklamanız yeterlidir. Tüm hosts yasakları, başlangıç kayıtları ve kısayollar temizlenir.
