# Tunahan Cengiz Portfolio - Proje Rehberi

## 📋 Proje Genel Bilgiler
- **Başlık:** Tunahan Cengiz Modern Portfolio Websitesi
- **Teknoloji:** Flask + Python + Tailwind CSS
- **Dil:** Turkish (Türkçe)
- **Tema:** Dark mode (slate-900) + Neon purple (violet-500)

## 📁 Klasör Yapısı (SABIT - DEĞİŞTİRME)

```
PROJECT_ROOT/
├── main.py              # Flask ana aplikasyon
├── run_app.py           # Uygulama başlatıcı
├── models.py            # Database modelleri
├── extensions.py        # Flask extensionları
├── requirements.txt     # Python dependencies
├── static/
│   └── uploads/         # Profil fotosu ve proje görselleri
├── templates/
│   ├── base.html        # Ana şablon (navbar + footer)
│   ├── index.html       # Ana sayfa (portfolio içeriği)
│   ├── login.html       # Giriş sayfası
│   ├── dashboard.html   # Admin paneli ana
│   ├── admin_*.html     # Admin sayfaları
│   └── project_detail.html
├── instance/
│   └── database.db      # SQLite veritabanı
└── .replit              # Replit konfigürasyonu
```

**⚠️ ÖNEMLİ:** Klasör yapısı ASLA `Flask-Boilerplatezip/Flask-Boilerplatezip/Flask-Boilerplate/` şekline dönmemeli!

## 🎨 Tasarım Kararları

### Renkler
- **Ana Arka Plan:** `slate-900` (#0f172a)
- **Vurgu Rengi:** `violet-500` (#8b5cf6) - NOR MOR, SARIYOK
- **Hover:** `violet-400` veya `violet-700`

### Navbar/Mobil Menü
- **Masaüstü:** Yatay menü (lg:flex) - Hakkımda, Yetenekler, Çalışmalar, İletişim
- **Mobil:** Off-canvas panel (sağdan kayarak gelen) + hamburger ikonu
- **FontAwesome:** CDN (6.4.0) yüklü olmalı
- **JavaScript:** Basit toggle (translate-x-full) - karmaşık olmayacak

### Responsive Tasarım
- Yetenek kartları: `flex flex-wrap justify-center gap-8` (centered)
- Projeler: `flex flex-wrap justify-center gap-8` (centered)
- İletişim bölümü: Sol kısım left-aligned, right kısım form
- Text overflow: `break-all` + `min-w-0` kullan

## 🔧 Workflow Ayarları

```
Workflow Name: Flask App
Command: python run_app.py
Port: 5000
Output Type: webview
```

## 📝 Son Değişiklikler

### 30 Aralık 2025 - Fikir Laboratuvarı Tasarım & İnteraktif Geçişler
- **admin_ideas.html** sayfası 3 bölüme ayrıldı:
  - 💡 **Fikir Havuzu:** Masonry grid, kesik çizgi border, "Başlat" butonları
  - 🚧 **Aktif Şantiye:** Neon mor border, ilerleme slider (AJAX), "Bitir" butonları
  - 🏆 **Onur Listesi:** Kompakt list view, altın sarısı detaylar
- Modal Sistemleri:
  - ✅ Yeni Fikir Ekle Modalı (Proje Adı, Pitch, Sorun, Detay, Teknolojiler)
  - ✅ Projeyi Başlat Modalı (Başlangıç/Bitiş Tarihleri, 30 gün default)
  - ✅ Projeyi Tamamla Modalı (Onur Listesine Taşıma)
- **Interaktif JavaScript:**
  - Fikir → Aktif Proje geçişi (Form validasyonu + tarih kontrolü)
  - İlerleme Slider (0-100%) AJAX güncellemesi + pulse animasyon
  - Aktif → Tamamlanan Proje geçişi (Confirm dialog)
  - ESC & Dış Alan Tıklaması ile modal kapatma
- **Backend Routes (Yeni):**
  - POST `/admin/ideas/progress/<id>` - İlerleme güncelleme (JSON response)
  - Mevcut: `/admin/ideas/start/<id>`, `/admin/ideas/complete/<id>`

### 30 Aralık 2025 - Klasör Reorganizasyonu
- Iç içe geçmiş klasör yapısını çözdü
- Tüm dosyaları root'a taşıdı
- Workflow'u güncelledı

### 30 Aralık 2025 - Navbar & Mobil Menü
- Navbar FontAwesome 6.4.0 ile güncellendi
- Mobile menu off-canvas panel (sağdan gelen)
- Hamburger button lg:hidden ile mobilde görünüyor
- Smooth transition ve backdrop overlay

### Önceki Dönem - UI Tasarım
- Hero section, Hakkımda, Yetenekler, Projeler, Eğitim & Kariyer, İletişim
- Tailwind CSS CDN
- Responsive layout

## 👤 Kullanıcı Tercihleri

### Tercih Edilen Stil
- **Font:** Outfit (Alegreya SC teklifine cevap: HAYIR)
- **Tasarım:** Modern, dark, neon aksentli
- **Mobile First:** Responsive her zaman önemli
- **Renk Seçimi:** SADECE mor (violet), ASLA sarı

### Geliştirme Ortamı
- FastMode hızlı edits için (3 turn limit)
- Küçük değişiklikler: Solo yapabilir
- Büyük refactors: Onay iste

## 📌 Sonraki Sohbet Talimatları

**Yeni sohbette yazacağın mesaj:**
```
Merhaba! Lütfen şu talimatları unut:
- Proje yapısı: root'ta tüm dosyalar (iç içe klasör yok)
- Klasör düzenine dayan: replit.md dosyasındaki yapıya bağlı kal
- Tema: Dark mode (slate-900) + mor (violet-500)
- Mobile menu: Off-canvas panel (sağdan)
- Workflow: "python run_app.py" port 5000'de

Şu dosyalar güvenli: main.py, run_app.py, models.py, templates/
```

---
*Son güncelleme: 30 Aralık 2025 - Klasör yapısı standartlaştırıldı*
