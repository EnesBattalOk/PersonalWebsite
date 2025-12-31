from extensions import db
from flask_login import UserMixin
from datetime import datetime

class Kullanici(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(150), unique=True, nullable=False)
    sifre = db.Column(db.String(150), nullable=False)
    unvan = db.Column(db.String(100))
    profil_foto_url = db.Column(db.String(255))
    hakkimda_yazisi = db.Column(db.Text)
    iletisim_telefon = db.Column(db.String(20))
    iletisim_email = db.Column(db.String(150))
    iletisim_konum = db.Column(db.String(200))
    telefon_gorunur = db.Column(db.Boolean, default=False)
    sosyal_linkedin = db.Column(db.String(255))
    sosyal_github = db.Column(db.String(255))

class Gunluk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    tur = db.Column(db.String(20), nullable=False) # 'GUNLUK' veya 'YILLIK'
    duygu = db.Column(db.String(50)) # 'harika', 'iyi', 'orta', 'kotu'

class Varlik(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tur = db.Column(db.String(100), nullable=False)
    konum = db.Column(db.String(100))
    miktar = db.Column(db.Float)
    alis_fiyati = db.Column(db.Float)
    alis_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

class CalismaKategori(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)

class YolHaritasi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kategori_id = db.Column(db.Integer, db.ForeignKey('calisma_kategori.id'), nullable=True)
    baslik = db.Column(db.String(200), nullable=False)
    durum = db.Column(db.String(50))
    notlar = db.Column(db.Text)
    tip = db.Column(db.String(50)) # 'Egitim' veya 'Deneyim'
    tarih_araligi = db.Column(db.String(100))
    logo_url = db.Column(db.String(255))
    
    kategori = db.relationship('CalismaKategori', backref=db.backref('yol_haritalari', lazy=True))

class Yetenek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    yuzde = db.Column(db.Integer, default=50)

class Proje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    notlar = db.Column(db.Text)
    github_link = db.Column(db.String(255))
    canli_link = db.Column(db.String(255))
    versiyon_gecmisi = db.Column(db.Text)
    kapak_resmi = db.Column(db.String(255))
    detayli_icerik = db.Column(db.Text)

    @property
    def ilerleme_yuzde(self):
        return 0

class Kitap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kitap_adi = db.Column(db.String(200), nullable=False)
    yazar = db.Column(db.String(150))
    sayfa_sayisi = db.Column(db.Integer)
    okunma_tarihi = db.Column(db.DateTime)

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    icerik = db.Column(db.Text, nullable=False)
    plan_tipi = db.Column(db.String(50))
    hedef_tarih = db.Column(db.DateTime)
    tamamlandi_mi = db.Column(db.Boolean, default=False)
    arsivlendi_mi = db.Column(db.Boolean, default=False)

class Fikir(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text)
    teknoloji_stack = db.Column(db.String(255))
    olusturulma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

class FinansIslem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    islem_turu = db.Column(db.String(50), nullable=False) # 'GELIR', 'GIDER', 'VARLIK_ALIM', 'VARLIK_SATIM'
    kategori = db.Column(db.String(50), nullable=False) # 'NAKIT', 'ALTIN', 'GUMUS', 'DOVIZ', 'DIJITAL'
    tutar_tl = db.Column(db.Float, nullable=False)
    miktar = db.Column(db.Float, default=0) # Varlık miktarı (gram, adet vb.)
    banka = db.Column(db.String(100)) # Eski banka alanı (geriye dönük uyumluluk için tutulabilir veya banka_adi ile birleştirilebilir)
    varlik_konumu = db.Column(db.String(50)) # 'FIZIKSEL', 'BANKA'
    banka_adi = db.Column(db.String(100)) # Banka ismi (Örn: Ziraat)
    birim_fiyat = db.Column(db.Float) # Alım sırasındaki birim fiyat
    doviz_turu = db.Column(db.String(20)) # 'USD', 'EUR', 'ALTIN', 'GUMUS', 'KRIPTO'
    aciklama = db.Column(db.String(255))

class Gorev(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text)
    durum = db.Column(db.String(50), default='YAPILACAK') # 'YAPILACAK', 'SURUYOR', 'BITTI'
    oncelik = db.Column(db.String(50), default='NORMAL') # 'DUSUK', 'NORMAL', 'YUKSEK'
    son_tarih = db.Column(db.DateTime)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    kategori = db.Column(db.String(50), default='GOREV') # 'GOREV' veya 'HEDEF'
    ceyrek = db.Column(db.Integer) # 1, 2, 3, 4 (Sadece Yıllık Hedefler için)
    saat = db.Column(db.String(10)) # '09:00', '14:30' vb.
    onemli_mi = db.Column(db.Boolean, default=False) # Günün "En Önemli 3 İşi"nden biri mi?

class Mesaj(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gonderen_ad = db.Column(db.String(100), nullable=False)
    gonderen_email = db.Column(db.String(150), nullable=False)
    konu = db.Column(db.String(200))
    mesaj_icerigi = db.Column(db.Text, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    okundu_mu = db.Column(db.Boolean, default=False)

class Ziyaretci(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_adresi = db.Column(db.String(50))
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    sayfa = db.Column(db.String(200))

class ProjeFikri(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    ozet = db.Column(db.String(255)) # Kısa açıklama (Pitch)
    detay = db.Column(db.Text) # Detaylı açıklama
    sorun = db.Column(db.Text) # Çözdüğü sorun nedir?
    teknolojiler = db.Column(db.String(255)) # Virgülle ayrılmış etiketler
    durum = db.Column(db.String(50), default='FIKIR') # 'FIKIR', 'AKTIF', 'BITTI'
    baslangic_tarihi = db.Column(db.DateTime) # Sadece AKTIF ve BITTI ise dolu
    bitis_tarihi = db.Column(db.DateTime) # Tahmini veya gerçekleşen bitiş
    ilerleme = db.Column(db.Integer, default=0) # 0-100 (Sadece AKTIF ise)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    
    gorevler = db.relationship('ProjeGorev', backref=db.backref('proje', lazy=True), cascade='all, delete-orphan')

class ProjeGorev(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proje_id = db.Column(db.Integer, db.ForeignKey('proje_fikri.id'), nullable=False)
    baslik = db.Column(db.String(200), nullable=False)
    faz = db.Column(db.String(100)) # Örn: "Faz 1", "Backend", "UI/UX"
    baslangic_tarihi = db.Column(db.DateTime)
    durum = db.Column(db.String(50), default='BEKLIYOR') # 'BEKLIYOR', 'YAPILACAK', 'SURUYOR', 'BITTI'
    sira = db.Column(db.Integer, default=0) # Görev sırası

class StudioProject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False) # 'Web', 'Mobil', 'IoT', 'Masaüstü' vb.
    secure_data = db.Column(db.Text, default='') # Şifreler, API keyleri, notlar
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    
    work_logs = db.relationship('StudioWorkLog', backref=db.backref('proje', lazy=True), cascade='all, delete-orphan')

class StudioWorkLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proje_id = db.Column(db.Integer, db.ForeignKey('studio_project.id'), nullable=False)
    note = db.Column(db.Text, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
