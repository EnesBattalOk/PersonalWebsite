import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from extensions import db, login_manager
from models import Kullanici, Gunluk, Varlik, YolHaritasi, Proje, Mesaj, Yetenek, Kitap, FinansIslem, Gorev, Ziyaretci, ProjeFikri, ProjeGorev, StudioProject, StudioWorkLog
from datetime import datetime, date
from sqlalchemy import func, extract

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'gizli-anahtar-123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Kullanici.query.get(int(user_id))

    def get_live_rates():
        """doviz.com üzerinden canlı kurları çeker (ALIŞ Fiyatları)."""
        rates = {
            'ALTIN': 0.0,
            'GUMUS': 0.0,
            'USD': 0.0,
            'EUR': 0.0
        }
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get('https://www.doviz.com/', headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Doviz.com'da ALIŞ sütunu genellikle tablolarda veya kartlarda ilk değerdir.
                # Ana sayfadaki 'value' class'lı spanlar Satış fiyatlarını verir. 
                # Gerçek Alış fiyatları için farklı bir yapı gerekebilir ama 
                # doviz.com'da kartlardaki değerler değişkendir.
                # ALIŞ fiyatlarını çekmek için 'data-socket-key' ve 'data-socket-attr="buy"' olanları bulalım.
                
                def parse_val(el):
                    if not el: return 0.0
                    return float(el.text.replace('.', '').replace(',', '.'))

                # Altın (Gram)
                gold_buy = soup.find('span', {'data-socket-key': 'gram-altin', 'data-socket-attr': 'buy'})
                # USD
                usd_buy = soup.find('span', {'data-socket-key': 'USD', 'data-socket-attr': 'buy'})
                # EUR
                eur_buy = soup.find('span', {'data-socket-key': 'EUR', 'data-socket-attr': 'buy'})
                # Gümüş
                gumus_buy = soup.find('span', {'data-socket-key': 'gumus', 'data-socket-attr': 'buy'})

                if gold_buy: rates['ALTIN'] = parse_val(gold_buy)
                if usd_buy: rates['USD'] = parse_val(usd_buy)
                if eur_buy: rates['EUR'] = parse_val(eur_buy)
                if gumus_buy: rates['GUMUS'] = parse_val(gumus_buy)
                
                # Fallback: Eğer socket keyler bulunamazsa (sayfa yapısı değişirse) value spanlarını al ama %0.5-1 düşür (simüle alış)
                if rates['ALTIN'] == 0:
                    items = soup.find_all('span', class_='value')
                    if len(items) >= 5:
                        rates['ALTIN'] = parse_val(items[0]) * 0.995 # %0.5 makas
                        rates['USD'] = parse_val(items[1]) * 0.995
                        rates['EUR'] = parse_val(items[2]) * 0.995
                        rates['GUMUS'] = parse_val(items[4]) * 0.99
        except Exception as e:
            print(f"Kur çekme hatası: {e}")
        return rates

    @app.context_processor
    def inject_globals():
        if current_user.is_authenticated:
            unseen_count = Mesaj.query.filter_by(okundu_mu=False).count()
            return dict(unseen_count=unseen_count)
        return dict(unseen_count=0)

    @app.route('/')
    def home():
        # Ziyaretçi Takip Sistemi (Tekil IP Kontrolü)
        try:
            ip = request.remote_addr
            bugun = date.today()
            
            # Bu IP bugün zaten kayıt edilmiş mi?
            mevcut_ziyaret = Ziyaretci.query.filter(
                Ziyaretci.ip_adresi == ip,
                func.date(Ziyaretci.tarih) == bugun
            ).first()
            
            if not mevcut_ziyaret:
                yeni_ziyaret = Ziyaretci(ip_adresi=ip, sayfa='/')
                db.session.add(yeni_ziyaret)
                db.session.commit()
        except Exception as e:
            print(f"Ziyaretçi kaydı hatası: {e}")

        admin = Kullanici.query.first()
        projeler = Proje.query.order_by(Proje.id.desc()).all()
        yetenekler = Yetenek.query.all()
        egitimler = YolHaritasi.query.filter_by(tip='Egitim').order_by(YolHaritasi.order_index.asc()).all()
        deneyimler = YolHaritasi.query.filter_by(tip='Deneyim').order_by(YolHaritasi.order_index.asc()).all()
        return render_template('index.html', admin=admin, projeler=projeler, yetenekler=yetenekler, egitimler=egitimler, deneyimler=deneyimler)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('kullanici_adi')
            password = request.form.get('sifre')
            user = Kullanici.query.filter_by(kullanici_adi=username).first()
            if user and user.sifre == password:
                login_user(user)
                flash('Başarıyla giriş yaptınız.', 'success')
                return redirect(url_for('dashboard'))
            flash('Hatalı kullanıcı adı veya şifre', 'error')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('home'))

    @app.route('/admin/dashboard')
    @login_required
    def dashboard():
        toplam_ziyaret = Ziyaretci.query.count()
        bugun = date.today()
        bugun_ziyaret = Ziyaretci.query.filter(func.date(Ziyaretci.tarih) == bugun).count()
        
        # İstatistik verilerini veritabanından çek
        proje_sayisi = Proje.query.count()
        yetenek_sayisi = Yetenek.query.count()
        mesaj_sayisi = Mesaj.query.count()
        
        return render_template('dashboard.html', 
                             toplam_ziyaret=toplam_ziyaret, 
                             bugun_ziyaret=bugun_ziyaret,
                             proje_sayisi=proje_sayisi,
                             yetenek_sayisi=yetenek_sayisi,
                             mesaj_sayisi=mesaj_sayisi)

    @app.route('/admin/settings', methods=['GET', 'POST'])
    @login_required
    def admin_settings():
        admin = Kullanici.query.first()
        if request.method == 'POST':
            admin.kullanici_adi = request.form.get('kullanici_adi')
            admin.unvan = request.form.get('unvan')
            admin.hakkimda_yazisi = request.form.get('hakkimda_yazisi')
            admin.iletisim_email = request.form.get('iletisim_email')
            admin.iletisim_telefon = request.form.get('iletisim_telefon')
            admin.iletisim_konum = request.form.get('iletisim_konum')
            admin.telefon_gorunur = 'telefon_gorunur' in request.form
            admin.show_phone = 'show_phone' in request.form
            admin.sosyal_github = request.form.get('sosyal_github')
            admin.sosyal_linkedin = request.form.get('sosyal_linkedin')
            admin.website_label = request.form.get('website_label')
            admin.website_url = request.form.get('website_url')

            # Cropper.js base64 data
            cropped_data = request.form.get('cropped_data')
            if cropped_data and cropped_data.startswith('data:image'):
                import base64
                
                # Delete old file
                if admin.profil_foto_url:
                    old_path = os.path.join(app.root_path, admin.profil_foto_url.lstrip('/'))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                header, encoded = cropped_data.split(",", 1)
                data = base64.b64decode(encoded)
                filename = f"profile_{admin.id}_{int(datetime.now().timestamp())}.jpg"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                with open(file_path, "wb") as f:
                    f.write(data)
                
                admin.profil_foto_url = url_for('static', filename='uploads/' + filename)
            
            elif 'profil_foto' in request.files:
                file = request.files['profil_foto']
                if file and file.filename != '':
                    # Delete old file
                    if admin.profil_foto_url:
                        old_path = os.path.join(app.root_path, admin.profil_foto_url.lstrip('/'))
                        if os.path.exists(old_path):
                            os.remove(old_path)
                            
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    admin.profil_foto_url = url_for('static', filename='uploads/' + filename)

            db.session.commit()
            flash('Ayarlar başarıyla güncellendi.', 'success')
            return redirect(url_for('admin_settings'))
        return render_template('admin_settings.html', admin=admin)

    @app.route('/admin/projects', methods=['GET', 'POST'])
    @login_required
    def admin_projects():
        if request.method == 'POST':
            baslik = request.form.get('baslik')
            notlar = request.form.get('notlar')
            detayli_icerik = request.form.get('detayli_icerik')
            github_link = request.form.get('github_link')
            canli_link = request.form.get('canli_link')
            
            kapak_resmi_url = None
            if 'kapak_resmi' in request.files:
                file = request.files['kapak_resmi']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    kapak_resmi_url = url_for('static', filename='uploads/' + filename)

            yeni_proje = Proje(
                baslik=baslik,
                notlar=notlar,
                detayli_icerik=detayli_icerik,
                github_link=github_link,
                canli_link=canli_link,
                kapak_resmi=kapak_resmi_url
            )
            db.session.add(yeni_proje)
            db.session.commit()
            flash('Proje başarıyla eklendi.', 'success')
            return redirect(url_for('admin_projects'))
            
        projeler = Proje.query.all()
        return render_template('admin_projects.html', projeler=projeler)

    @app.route('/admin/project/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_project(id):
        proje = Proje.query.get_or_404(id)
        if request.method == 'POST':
            proje.baslik = request.form.get('baslik')
            proje.notlar = request.form.get('notlar')
            proje.detayli_icerik = request.form.get('detayli_icerik')
            proje.github_link = request.form.get('github_link')
            proje.canli_link = request.form.get('canli_link')

            if 'kapak_resmi' in request.files:
                file = request.files['kapak_resmi']
                if file and file.filename != '':
                    # Delete old file if exists
                    if proje.kapak_resmi:
                        old_file_path = os.path.join(app.root_path, proje.kapak_resmi.lstrip('/'))
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    proje.kapak_resmi = url_for('static', filename='uploads/' + filename)

            db.session.commit()
            flash('Proje başarıyla güncellendi.', 'success')
            return redirect(url_for('admin_projects'))
        return render_template('admin_project_edit.html', proje=proje)

    @app.route('/admin/project/delete/<int:id>')
    @login_required
    def delete_project(id):
        proje = Proje.query.get_or_404(id)
        db.session.delete(proje)
        db.session.commit()
        flash('Proje silindi.', 'success')
        return redirect(url_for('admin_projects'))

    @app.route('/admin/skills', methods=['GET', 'POST'])
    @login_required
    def admin_skills():
        if request.method == 'POST':
            ad = request.form.get('ad')
            yuzde = request.form.get('yuzde')
            yeni_yetenek = Yetenek(ad=ad, yuzde=int(yuzde))
            db.session.add(yeni_yetenek)
            db.session.commit()
            flash('Yetenek başarıyla eklendi.', 'success')
            return redirect(url_for('admin_skills'))
            
        yetenekler = Yetenek.query.all()
        return render_template('admin_skills.html', yetenekler=yetenekler)

    @app.route('/admin/skill/delete/<int:id>')
    @login_required
    def delete_skill(id):
        yetenek = Yetenek.query.get_or_404(id)
        db.session.delete(yetenek)
        db.session.commit()
        flash('Yetenek silindi.', 'success')
        return redirect(url_for('admin_skills'))

    @app.route('/admin/skill/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_skill(id):
        yetenek = Yetenek.query.get_or_404(id)
        if request.method == 'POST':
            yetenek.ad = request.form.get('ad')
            yetenek.yuzde = int(request.form.get('yuzde'))
            db.session.commit()
            flash('Yetenek başarıyla güncellendi.', 'success')
            return redirect(url_for('admin_skills'))
        return render_template('admin_skill_edit.html', yetenek=yetenek)

    @app.route('/admin/resume', methods=['GET', 'POST'])
    @login_required
    def admin_resume():
        if request.method == 'POST':
            tip = request.form.get('tip')
            baslik = request.form.get('baslik')
            tarih_araligi = request.form.get('tarih_araligi')
            notlar = request.form.get('notlar')
            order_index = int(request.form.get('order_index') or 0)
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            is_active = 'is_active' in request.form
            position = request.form.get('position')
            
            logo_url = None
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    logo_url = url_for('static', filename='uploads/' + filename)

            yeni_item = YolHaritasi(
                tip=tip, baslik=baslik, tarih_araligi=tarih_araligi, notlar=notlar, 
                logo_url=logo_url, order_index=order_index, start_date=start_date,
                end_date=end_date, is_active=is_active, position=position
            )
            db.session.add(yeni_item)
            db.session.commit()
            flash('Kayıt başarıyla eklendi.', 'success')
            return redirect(url_for('admin_resume'))
            
        items = YolHaritasi.query.order_by(YolHaritasi.order_index.asc()).all()
        return render_template('admin_resume.html', items=items)

    @app.route('/admin/resume/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_resume(id):
        item = YolHaritasi.query.get_or_404(id)
        if request.method == 'POST':
            item.tip = request.form.get('tip')
            item.baslik = request.form.get('baslik')
            item.tarih_araligi = request.form.get('tarih_araligi')
            item.notlar = request.form.get('notlar')
            item.order_index = int(request.form.get('order_index') or 0)
            item.start_date = request.form.get('start_date')
            item.end_date = request.form.get('end_date')
            item.is_active = 'is_active' in request.form
            item.position = request.form.get('position')

            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename != '':
                    if item.logo_url:
                        old_file_path = os.path.join(app.root_path, item.logo_url.lstrip('/'))
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    item.logo_url = url_for('static', filename='uploads/' + filename)

            db.session.commit()
            flash('Kayıt başarıyla güncellendi.', 'success')
            return redirect(url_for('admin_resume'))
        return render_template('admin_resume_edit.html', item=item)

    @app.route('/admin/resume/delete/<int:id>')
    @login_required
    def delete_resume(id):
        item = YolHaritasi.query.get_or_404(id)
        db.session.delete(item)
        db.session.commit()
        flash('Kayıt silindi.', 'success')
        return redirect(url_for('admin_resume'))

    @app.route('/admin/diaries')
    @login_required
    def admin_diaries():
        gunlukler = Gunluk.query.filter_by(tur='GUNLUK').order_by(Gunluk.tarih.desc()).all()
        yilliklar = Gunluk.query.filter_by(tur='YILLIK').order_by(Gunluk.tarih.desc()).all()
        return render_template('admin_diaries.html', gunlukler=gunlukler, yilliklar=yilliklar)

    @app.route('/admin/diaries/add', methods=['POST'])
    @login_required
    def add_diary():
        tur = request.form.get('tur')
        baslik = request.form.get('baslik')
        icerik = request.form.get('icerik')
        duygu = request.form.get('duygu') if tur == 'GUNLUK' else None
        
        yeni_kayit = Gunluk(
            baslik=baslik,
            icerik=icerik,
            tur=tur,
            duygu=duygu,
            tarih=datetime.utcnow()
        )
        db.session.add(yeni_kayit)
        db.session.commit()
        flash('Yeni kayıt başarıyla eklendi.', 'success')
        return redirect(url_for('admin_diaries'))

    @app.route('/admin/diaries/update/<int:id>', methods=['POST'])
    @login_required
    def update_diary(id):
        gunluk = Gunluk.query.get_or_404(id)
        gunluk.baslik = request.json.get('baslik', gunluk.baslik)
        gunluk.icerik = request.json.get('icerik', gunluk.icerik)
        if gunluk.tur == 'GUNLUK':
            gunluk.duygu = request.json.get('duygu', gunluk.duygu)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Kayıt başarıyla güncellendi'})

    @app.route('/admin/diaries/delete/<int:id>')
    @login_required
    def delete_diary(id):
        gunluk = Gunluk.query.get_or_404(id)
        db.session.delete(gunluk)
        db.session.commit()
        flash('Kayıt silindi.', 'success')
        return redirect(url_for('admin_diaries'))

    @app.route('/admin/books')
    @login_required
    def admin_books():
        secili_yil = request.args.get('yil')
        
        # 1. Yıl Listesi: Tekil ve Ters Sıralı
        yillar_query = db.session.query(extract('year', Kitap.okunma_tarihi)).filter(Kitap.okunma_tarihi.isnot(None)).distinct().all()
        yillar = sorted([int(y[0]) for y in yillar_query if y[0] is not None], reverse=True)
        
        # 2. Filtreleme: URL'den gelen yıla göre veya hepsi
        query = Kitap.query
        if secili_yil and secili_yil != 'genel':
            query = query.filter(extract('year', Kitap.okunma_tarihi) == int(secili_yil))
            secili_yil_display = secili_yil
        else:
            secili_yil_display = 'Genel'
            secili_yil = 'genel'

        kitaplar = query.order_by(Kitap.okunma_tarihi.desc()).all()
        
        # 3. İSTATİSTİK HESAPLAMA (Filtrelenen kitap listesi üzerinden)
        toplam_kitap = len(kitaplar)
        toplam_sayfa = sum(kitap.sayfa_sayisi for kitap in kitaplar if kitap.sayfa_sayisi)
        
        # set() kullanarak benzersiz yazar sayısını hesapla
        toplam_yazar = len(set([kitap.yazar for kitap in kitaplar if kitap.yazar]))
        
        return render_template('admin_books.html', 
                               books=kitaplar, 
                               toplam_kitap=toplam_kitap, 
                               toplam_sayfa=toplam_sayfa, 
                               toplam_yazar=toplam_yazar,
                               yillar=yillar,
                               secili_yil=secili_yil,
                               secili_yil_display=secili_yil_display)

    @app.route('/admin/books/add', methods=['POST'])
    @login_required
    def add_book():
        kitap_adi = request.form.get('kitap_adi')
        yazar = request.form.get('yazar')
        sayfa_sayisi = int(request.form.get('sayfa_sayisi') or 0)
        okunma_tarihi_str = request.form.get('okunma_tarihi')
        
        okunma_tarihi = None
        if okunma_tarihi_str:
            okunma_tarihi = datetime.strptime(okunma_tarihi_str, '%Y-%m-%d')
            
        yeni_kitap = Kitap(
            kitap_adi=kitap_adi,
            yazar=yazar,
            sayfa_sayisi=sayfa_sayisi,
            okunma_tarihi=okunma_tarihi
        )
        db.session.add(yeni_kitap)
        db.session.commit()
        flash('Kitap başarıyla eklendi.', 'success')
        return redirect(url_for('admin_books'))

    @app.route('/admin/books/update/<int:id>', methods=['POST'])
    @login_required
    def update_book(id):
        kitap = Kitap.query.get_or_404(id)
        kitap.kitap_adi = request.json.get('kitap_adi', kitap.kitap_adi)
        kitap.yazar = request.json.get('yazar', kitap.yazar)
        kitap.sayfa_sayisi = request.json.get('sayfa_sayisi', kitap.sayfa_sayisi)
        
        okunma_tarihi_str = request.json.get('okunma_tarihi')
        if okunma_tarihi_str:
            kitap.okunma_tarihi = datetime.strptime(okunma_tarihi_str, '%Y-%m-%d')
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Kitap başarıyla güncellendi'})

    @app.route('/admin/books/delete/<int:id>')
    @login_required
    def delete_book(id):
        kitap = Kitap.query.get_or_404(id)
        db.session.delete(kitap)
        db.session.commit()
        flash('Kitap silindi.', 'success')
        return redirect(url_for('admin_books'))

    @app.route('/iletisim', methods=['POST'])
    def contact():
        ad_soyad = request.form.get('ad_soyad')
        email = request.form.get('email')
        konu = request.form.get('konu')
        mesaj_icerigi = request.form.get('mesaj')
        
        yeni_mesaj = Mesaj(
            gonderen_ad=ad_soyad,
            gonderen_email=email,
            konu=konu,
            mesaj_icerigi=mesaj_icerigi
        )
        db.session.add(yeni_mesaj)
        db.session.commit()
        
        flash('Mesajınız başarıyla gönderildi.', 'success')
        return redirect(url_for('home', _anchor='iletisim'))

    @app.route('/admin/inbox')
    @login_required
    def admin_inbox():
        mesajlar = Mesaj.query.order_by(Mesaj.tarih.desc()).all()
        return render_template('admin_inbox.html', mesajlar=mesajlar)

    @app.route('/admin/inbox/read/<int:id>')
    @login_required
    def read_message(id):
        mesaj = Mesaj.query.get_or_404(id)
        mesaj.okundu_mu = True
        db.session.commit()
        return render_template('admin_message_detail.html', mesaj=mesaj)

    @app.route('/admin/inbox/delete/<int:id>')
    @login_required
    def delete_message(id):
        mesaj = Mesaj.query.get_or_404(id)
        db.session.delete(mesaj)
        db.session.commit()
        flash('Mesaj silindi.', 'success')
        return redirect(url_for('admin_inbox'))

    @app.route('/admin/finance')
    @login_required
    def admin_finance():
        # Başlangıç Envanteri
        varliklar = {
            'ALTIN': {'toplam': 0.0, 'fiziksel': 0.0, 'banka': 0.0},
            'GUMUS': {'toplam': 0.0, 'fiziksel': 0.0, 'banka': 0.0},
            'USD': {'toplam': 0.0, 'fiziksel': 0.0, 'banka': 0.0},
            'EUR': {'toplam': 0.0, 'fiziksel': 0.0, 'banka': 0.0},
            'NAKIT': {'toplam': 0.0, 'fiziksel': 0.0, 'banka': 0.0}
        }

        tum_islemler = FinansIslem.query.all()
        
        for islem in tum_islemler:
            # Nakit TL Dengesi (GELIR/GIDER)
            if islem.islem_turu == 'GELIR':
                varliklar['NAKIT']['toplam'] += islem.tutar_tl
                varliklar['NAKIT']['fiziksel'] += islem.tutar_tl # Gelirler varsayılan nakit kabul edildi
            elif islem.islem_turu == 'GIDER':
                varliklar['NAKIT']['toplam'] -= islem.tutar_tl
                varliklar['NAKIT']['fiziksel'] -= islem.tutar_tl

            # Varlık Hareketleri
            elif islem.islem_turu in ['VARLIK_ALIM', 'VARLIK_SATIM']:
                carpan = 1 if islem.islem_turu == 'VARLIK_ALIM' else -1
                
                # Nakit TL etkilenmesi (Alımda azalır, Satımda artar)
                varliklar['NAKIT']['toplam'] -= (islem.tutar_tl * carpan)
                varliklar['NAKIT']['fiziksel'] -= (islem.tutar_tl * carpan)

                # İlgili varlık miktarının değişimi
                v_turu = islem.doviz_turu or islem.kategori
                if v_turu in varliklar:
                    miktar = islem.miktar
                    varliklar[v_turu]['toplam'] += (miktar * carpan)
                    if islem.varlik_konumu == 'BANKA':
                        varliklar[v_turu]['banka'] += (miktar * carpan)
                    else:
                        varliklar[v_turu]['fiziksel'] += (miktar * carpan)

        # Canlı Kurlar
        canli_kurlar = get_live_rates()

        # Net Servet Hesaplama
        net_servet = varliklar['NAKIT']['toplam']
        net_servet += varliklar['ALTIN']['toplam'] * canli_kurlar['ALTIN']
        net_servet += varliklar['GUMUS']['toplam'] * canli_kurlar['GUMUS']
        net_servet += varliklar['USD']['toplam'] * canli_kurlar['USD']
        net_servet += varliklar['EUR']['toplam'] * canli_kurlar['EUR']

        islemler = FinansIslem.query.order_by(FinansIslem.tarih.desc()).limit(20).all()

        return render_template('admin_finance.html', 
                             varliklar=varliklar, 
                             net_servet=net_servet, 
                             canli_kurlar=canli_kurlar,
                             islemler=islemler)

    @app.route('/admin/finance/add', methods=['POST'])
    @login_required
    def add_finance_item():
        islem_turu = request.form.get('islem_turu')
        
        if islem_turu in ['GELIR', 'GIDER']:
            tutar_tl = float(request.form.get('tutar_tl') or 0)
            kategori = request.form.get('kategori', 'NAKIT')
            miktar = 0
            banka_adi = None
            varlik_konumu = 'FIZIKSEL'
            doviz_turu = 'NAKIT'
        else:
            tutar_tl = float(request.form.get('v_tutar_tl') or 0)
            kategori = request.form.get('doviz_turu') # Varlık türünü kategoriye de yazalım
            miktar = float(request.form.get('miktar') or 0)
            banka_adi = request.form.get('banka')
            varlik_konumu = request.form.get('varlik_konumu', 'FIZIKSEL')
            doviz_turu = request.form.get('doviz_turu')

        aciklama = request.form.get('aciklama')
        birim_fiyat = tutar_tl / miktar if miktar > 0 else 0
        
        yeni_islem = FinansIslem(
            islem_turu=islem_turu,
            kategori=kategori,
            tutar_tl=tutar_tl,
            miktar=miktar,
            banka_adi=banka_adi,
            varlik_konumu=varlik_konumu,
            birim_fiyat=birim_fiyat,
            doviz_turu=doviz_turu,
            aciklama=aciklama
        )
        db.session.add(yeni_islem)
        db.session.commit()
        flash('Finansal işlem başarıyla kaydedildi.', 'success')
        return redirect(url_for('admin_finance'))

    @app.route('/admin/finance/delete/<int:id>')
    @login_required
    def delete_finance_item(id):
        islem = FinansIslem.query.get_or_404(id)
        db.session.delete(islem)
        db.session.commit()
        flash('İşlem silindi.', 'success')
        return redirect(url_for('admin_finance'))

    @app.route('/admin/planner')
    @login_required
    def admin_planner():
        from datetime import timedelta
        bugun = date.today()
        
        # Günlük Plan: Bugünün görevleri
        gunluk_plan = Gorev.query.filter(
            func.date(Gorev.son_tarih) == bugun,
            Gorev.kategori == 'GOREV'
        ).order_by(Gorev.saat).all()
        
        # Günün Önemlileri: Bugün + onemli_mi=True
        gunun_onemlileri = Gorev.query.filter(
            func.date(Gorev.son_tarih) == bugun,
            Gorev.onemli_mi == True
        ).all()
        
        # Haftalık Plan: Bu hafta görevleri (Pazartesi-Pazar)
        hafta_basla = bugun - timedelta(days=bugun.weekday())
        hafta_sonu = hafta_basla + timedelta(days=6)
        
        haftalik_gorevler = Gorev.query.filter(
            Gorev.son_tarih.isnot(None),
            func.date(Gorev.son_tarih) >= hafta_basla,
            func.date(Gorev.son_tarih) <= hafta_sonu
        ).all()
        
        haftalik_plan = {
            'Pazartesi': [], 'Salı': [], 'Çarşamba': [], 'Perşembe': [], 
            'Cuma': [], 'Cumartesi': [], 'Pazar': []
        }
        gun_map = {0: 'Pazartesi', 1: 'Salı', 2: 'Çarşamba', 3: 'Perşembe', 4: 'Cuma', 5: 'Cumartesi', 6: 'Pazar'}
        
        for gorev in haftalik_gorevler:
            if gorev.son_tarih:
                gun_index = gorev.son_tarih.date().weekday()
                gun_adi = gun_map.get(gun_index)
                if gun_adi:
                    haftalik_plan[gun_adi].append(gorev)
        
        # Takvim için tüm görevler
        tum_gorevler = Gorev.query.all()
        
        # Yıllık Hedefler: Kategori = HEDEF
        yillik_hedefler = Gorev.query.filter_by(kategori='HEDEF').all()
        
        return render_template('admin_planner.html', 
                             gunluk_plan=gunluk_plan,
                             gunun_onemlileri=gunun_onemlileri,
                             haftalik_plan=haftalik_plan,
                             tum_gorevler=tum_gorevler,
                             yillik_hedefler=yillik_hedefler)

    @app.route('/admin/planner/add', methods=['POST'])
    @login_required
    def add_planner_task():
        baslik = request.form.get('baslik')
        aciklama = request.form.get('aciklama')
        oncelik = request.form.get('oncelik')
        son_tarih_str = request.form.get('son_tarih')
        saat = request.form.get('saat')
        kategori = request.form.get('kategori', 'GOREV')  # GOREV veya HEDEF
        ceyrek = request.form.get('ceyrek')
        onemli_mi = 'onemli_mi' in request.form
        
        son_tarih = None
        if son_tarih_str:
            son_tarih = datetime.strptime(son_tarih_str, '%Y-%m-%d')
        
        ceyrek_int = None
        if ceyrek:
            try:
                ceyrek_int = int(ceyrek)
            except:
                pass
            
        yeni_gorev = Gorev(
            baslik=baslik,
            aciklama=aciklama,
            oncelik=oncelik,
            son_tarih=son_tarih,
            saat=saat,
            kategori=kategori,
            ceyrek=ceyrek_int,
            onemli_mi=onemli_mi
        )
        db.session.add(yeni_gorev)
        db.session.commit()
        flash('Görev başarıyla eklendi.', 'success')
        return redirect(url_for('admin_planner'))

    @app.route('/admin/planner/update_status/<int:id>', methods=['POST'])
    @login_required
    def update_task_status(id):
        data = request.get_json()
        gorev = Gorev.query.get_or_404(id)
        if data and 'yeni_durum' in data:
            gorev.durum = data['yeni_durum']
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False}), 400

    @app.route('/admin/planner/delete/<int:id>')
    @login_required
    def delete_planner_task(id):
        gorev = Gorev.query.get_or_404(id)
        db.session.delete(gorev)
        db.session.commit()
        flash('Görev silindi.', 'success')
        return redirect(url_for('admin_planner'))

    @app.route('/admin/planner/update_tarih/<int:id>', methods=['POST'])
    @login_required
    def update_planner_tarih(id):
        data = request.get_json()
        gorev = Gorev.query.get_or_404(id)
        if data and 'yeni_tarih' in data:
            try:
                yeni_tarih = datetime.strptime(data['yeni_tarih'], '%Y-%m-%d')
                gorev.son_tarih = yeni_tarih
                db.session.commit()
                return jsonify({'success': True})
            except:
                return jsonify({'success': False, 'error': 'Tarih formatı hatalı'}), 400
        return jsonify({'success': False, 'error': 'Tarih gönderilmedi'}), 400

    @app.route('/admin/ideas')
    @login_required
    def admin_ideas():
        fikirler = ProjeFikri.query.filter_by(durum='FIKIR').order_by(ProjeFikri.olusturma_tarihi.desc()).all()
        aktif_projeler = ProjeFikri.query.filter_by(durum='AKTIF').order_by(ProjeFikri.baslangic_tarihi.desc()).all()
        
        # Görev Durum Kontrolü ve Otomasyon
        # Eğer görev başlangıç tarihi bugün veya geçmişse, durumu YAPILACAK yap
        bugün = datetime.now().date()
        for proje in aktif_projeler:
            for gorev in proje.gorevler:
                if gorev.durum == 'BEKLIYOR' and gorev.baslangic_tarihi:
                    if gorev.baslangic_tarihi.date() <= bugün:
                        gorev.durum = 'YAPILACAK'
        db.session.commit()
        
        # Her proje için ilerleme hesapla ve görevleri sırala
        for proje in aktif_projeler:
            # Görevleri faz'a göre, sonra sıra/id'ye göre sırala
            proje.gorevler_sirali = sorted(
                proje.gorevler,
                key=lambda g: (g.faz or '', g.sira or g.id)
            )
            
            # İlerleme hesapla: biten_gorev / toplam_gorev * 100
            toplam_gorev = len(proje.gorevler)
            biten_gorev = len([g for g in proje.gorevler if g.durum == 'BITTI'])
            
            if toplam_gorev > 0:
                proje.ilerleme_yuzde = (biten_gorev / toplam_gorev) * 100
            else:
                proje.ilerleme_yuzde = 0
            
            proje.toplam_gorev = toplam_gorev
            proje.biten_gorev = biten_gorev
        
        biten_projeler = ProjeFikri.query.filter_by(durum='BITTI').order_by(ProjeFikri.bitis_tarihi.desc()).all()
        return render_template('admin_ideas.html', fikirler=fikirler, aktif_projeler=aktif_projeler, biten_projeler=biten_projeler, now=datetime.now())

    @app.route('/admin/ideas/add', methods=['POST'])
    @login_required
    def add_idea():
        baslik = request.form.get('baslik')
        ozet = request.form.get('ozet')
        detay = request.form.get('detay')
        sorun = request.form.get('sorun')
        teknolojiler = request.form.get('teknolojiler')
        
        yeni_fikir = ProjeFikri(
            baslik=baslik,
            ozet=ozet,
            detay=detay,
            sorun=sorun,
            teknolojiler=teknolojiler,
            durum='FIKIR'
        )
        db.session.add(yeni_fikir)
        db.session.commit()
        flash('Fikir başarıyla eklendi.', 'success')
        return redirect(url_for('admin_ideas'))

    @app.route('/admin/ideas/start/<int:id>', methods=['POST'])
    @login_required
    def start_idea(id):
        fikir = ProjeFikri.query.get_or_404(id)
        baslangic_tarihi = request.form.get('baslangic_tarihi')
        bitis_tarihi = request.form.get('bitis_tarihi')
        
        fikir.durum = 'AKTIF'
        if baslangic_tarihi:
            fikir.baslangic_tarihi = datetime.strptime(baslangic_tarihi, '%Y-%m-%d')
        if bitis_tarihi:
            fikir.bitis_tarihi = datetime.strptime(bitis_tarihi, '%Y-%m-%d')
        
        db.session.commit()
        flash('Proje başlatıldı.', 'success')
        return redirect(url_for('admin_ideas'))

    @app.route('/admin/ideas/complete/<int:id>', methods=['POST'])
    @login_required
    def complete_idea(id):
        fikir = ProjeFikri.query.get_or_404(id)
        fikir.durum = 'BITTI'
        db.session.commit()
        flash('Proje tamamlandı.', 'success')
        return redirect(url_for('admin_ideas'))

    @app.route('/admin/ideas/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_idea(id):
        fikir = ProjeFikri.query.get_or_404(id)
        db.session.delete(fikir)
        db.session.commit()
        flash('Fikir silindi.', 'success')
        return redirect(url_for('admin_ideas'))

    @app.route('/admin/ideas/progress/<int:id>', methods=['POST'])
    @login_required
    def update_idea_progress(id):
        fikir = ProjeFikri.query.get_or_404(id)
        data = request.get_json()
        ilerleme = data.get('ilerleme', 0)
        
        # Validate progress value
        if 0 <= ilerleme <= 100:
            fikir.ilerleme = ilerleme
            db.session.commit()
            return jsonify({'success': True, 'ilerleme': ilerleme})
        
        return jsonify({'success': False, 'error': 'Geçersiz değer'}), 400

    @app.route('/admin/ideas/plan_save/<int:id>', methods=['POST'])
    @login_required
    def plan_save_tasks(id):
        """Projeyi Aktif hale getirirken toplu görev ekleme"""
        fikir = ProjeFikri.query.get_or_404(id)
        data = request.get_json()
        
        # Mevcut görevleri sil
        ProjeGorev.query.filter_by(proje_id=id).delete()
        
        # Yeni görevleri ekle
        gorevler = data.get('gorevler', [])
        for sira, gorev_data in enumerate(gorevler):
            yeni_gorev = ProjeGorev(
                proje_id=id,
                baslik=gorev_data.get('baslik', ''),
                faz=gorev_data.get('faz', ''),
                baslangic_tarihi=datetime.strptime(gorev_data.get('baslangic_tarihi'), '%Y-%m-%d') if gorev_data.get('baslangic_tarihi') else None,
                durum='BEKLIYOR',
                sira=sira
            )
            db.session.add(yeni_gorev)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Görevler kaydedildi'})

    @app.route('/admin/ideas/task_update/<int:task_id>', methods=['POST'])
    @login_required
    def task_update(task_id):
        """Bir görevin durumunu güncelle"""
        gorev = ProjeGorev.query.get_or_404(task_id)
        data = request.get_json()
        
        yeni_durum = data.get('durum')
        if yeni_durum in ['BEKLIYOR', 'YAPILACAK', 'SURUYOR', 'BITTI']:
            gorev.durum = yeni_durum
            db.session.commit()
            return jsonify({'success': True, 'durum': yeni_durum})
        
        return jsonify({'success': False, 'error': 'Geçersiz durum'}), 400

    @app.route('/admin/ideas/project_roadmap/<int:project_id>')
    @login_required
    def project_roadmap(project_id):
        """Proje'nin tüm fazlarını ve görevlerini getir"""
        proje = ProjeFikri.query.get_or_404(project_id)
        gorevler = ProjeGorev.query.filter_by(proje_id=project_id).order_by(ProjeGorev.faz, ProjeGorev.sira, ProjeGorev.id).all()
        
        # Fazlara göre grupla
        fazlar = {}
        for gorev in gorevler:
            faz_adi = gorev.faz or 'Bilinmeyen Faz'
            if faz_adi not in fazlar:
                fazlar[faz_adi] = []
            fazlar[faz_adi].append({
                'baslik': gorev.baslik,
                'durum': gorev.durum
            })
        
        return jsonify({
            'baslik': proje.baslik,
            'fazlar': fazlar
        })

    @app.route('/proje/<int:id>')
    def project_detail(id):
        proje = Proje.query.get_or_404(id)
        return render_template('project_detail.html', proje=proje)

    @app.route('/admin/studio')
    @login_required
    def admin_studio():
        """Stüdyo Projelerini Listele"""
        projeler = StudioProject.query.order_by(StudioProject.olusturma_tarihi.desc()).all()
        return render_template('studio.html', projeler=projeler)

    @app.route('/admin/studio/add', methods=['POST'])
    @login_required
    def studio_add():
        """Yeni Stüdyo Projesi Ekle"""
        name = request.form.get('name')
        category = request.form.get('category')
        
        yeni_proje = StudioProject(name=name, category=category)
        db.session.add(yeni_proje)
        db.session.commit()
        flash('Proje başarıyla eklendi.', 'success')
        return redirect(url_for('admin_studio'))

    @app.route('/admin/studio/<int:id>')
    @login_required
    def studio_detail(id):
        """Stüdyo Proje Detayı"""
        proje = StudioProject.query.get_or_404(id)
        logs = StudioWorkLog.query.filter_by(proje_id=id).order_by(StudioWorkLog.tarih.desc()).all()
        return render_template('studio_detail.html', proje=proje, logs=logs)

    @app.route('/admin/studio/<int:id>/save_secure', methods=['POST'])
    @login_required
    def studio_save_secure(id):
        """Kritik Bilgileri Kaydet"""
        proje = StudioProject.query.get_or_404(id)
        proje.secure_data = request.form.get('secure_data', '')
        db.session.commit()
        return jsonify({'success': True, 'message': 'Kritik bilgiler kaydedildi'})

    @app.route('/admin/studio/<int:id>/add_log', methods=['POST'])
    @login_required
    def studio_add_log(id):
        """Proje Günlüğüne Not Ekle"""
        proje = StudioProject.query.get_or_404(id)
        not_metni = request.form.get('note', '')
        
        if not_metni.strip():
            yeni_log = StudioWorkLog(proje_id=id, note=not_metni)
            db.session.add(yeni_log)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Not eklendi'})
        
        return jsonify({'success': False, 'error': 'Not boş olamaz'}), 400

    return app

app = create_app()

with app.app_context():
    db.create_all()
    if not Kullanici.query.filter_by(kullanici_adi='battalbey').first():
        admin = Kullanici(
            kullanici_adi='battalbey',
            sifre='eb07',
            unvan='Full Stack Developer',
            hakkimda_yazisi='Merhaba! Ben bir Full Stack geliştiriciyim.'
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
