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
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Kullanici.query.get(int(user_id))

    def get_live_rates():
        rates = {'ALTIN': 0.0, 'GUMUS': 0.0, 'USD': 0.0, 'EUR': 0.0}
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get('https://www.doviz.com/', headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                def parse_val(el):
                    if not el: return 0.0
                    return float(el.text.replace('.', '').replace(',', '.'))
                gold_buy = soup.find('span', {'data-socket-key': 'gram-altin', 'data-socket-attr': 'buy'})
                usd_buy = soup.find('span', {'data-socket-key': 'USD', 'data-socket-attr': 'buy'})
                eur_buy = soup.find('span', {'data-socket-key': 'EUR', 'data-socket-attr': 'buy'})
                gumus_buy = soup.find('span', {'data-socket-key': 'gumus', 'data-socket-attr': 'buy'})
                if gold_buy: rates['ALTIN'] = parse_val(gold_buy)
                if usd_buy: rates['USD'] = parse_val(usd_buy)
                if eur_buy: rates['EUR'] = parse_val(eur_buy)
                if gumus_buy: rates['GUMUS'] = parse_val(gumus_buy)
        except: pass
        return rates

    @app.context_processor
    def inject_globals():
        if current_user.is_authenticated:
            unseen_count = Mesaj.query.filter_by(okundu_mu=False).count()
            return dict(unseen_count=unseen_count)
        return dict(unseen_count=0)

    @app.route('/')
    def home():
        try:
            ip = request.remote_addr
            bugun = date.today()
            mevcut_ziyaret = Ziyaretci.query.filter(Ziyaretci.ip_adresi == ip, func.date(Ziyaretci.tarih) == bugun).first()
            if not mevcut_ziyaret:
                yeni_ziyaret = Ziyaretci(ip_adresi=ip, sayfa='/')
                db.session.add(yeni_ziyaret)
                db.session.commit()
        except: pass
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
        proje_sayisi = Proje.query.count()
        yetenek_sayisi = Yetenek.query.count()
        mesaj_sayisi = Mesaj.query.count()
        return render_template('dashboard.html', toplam_ziyaret=toplam_ziyaret, bugun_ziyaret=bugun_ziyaret, proje_sayisi=proje_sayisi, yetenek_sayisi=yetenek_sayisi, mesaj_sayisi=mesaj_sayisi)

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
            admin.show_phone = 'show_phone' in request.form
            admin.sosyal_github = request.form.get('sosyal_github')
            admin.sosyal_linkedin = request.form.get('sosyal_linkedin')
            admin.website_label = request.form.get('website_label')
            admin.website_url = request.form.get('website_url')
            if 'profil_foto' in request.files:
                file = request.files['profil_foto']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    admin.profil_foto_url = url_for('static', filename='uploads/' + filename)
            db.session.commit()
            flash('Ayarlar güncellendi.', 'success')
            return redirect(url_for('admin_settings'))
        return render_template('admin_settings.html', admin=admin)

    @app.route('/admin/resume', methods=['GET', 'POST'])
    @login_required
    def admin_resume():
        if request.method == 'POST':
            tip = request.form.get('tip')
            baslik = request.form.get('baslik')
            notlar = request.form.get('notlar')
            order_index = int(request.form.get('order_index') or 1)
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            is_active = 'is_active' in request.form
            degree = request.form.get('degree') if tip == 'Egitim' else None
            position = request.form.get('position') if tip == 'Deneyim' else None
            logo_url = None
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    logo_url = url_for('static', filename='uploads/' + filename)
            yeni_item = YolHaritasi(tip=tip, baslik=baslik, notlar=notlar, logo_url=logo_url, order_index=order_index, start_date=start_date, end_date=end_date, is_active=is_active, position=position, degree=degree)
            db.session.add(yeni_item)
            db.session.commit()
            flash('Kayıt eklendi.', 'success')
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
            item.notlar = request.form.get('notlar')
            item.order_index = int(request.form.get('order_index') or 1)
            item.start_date = request.form.get('start_date')
            item.end_date = request.form.get('end_date')
            item.is_active = 'is_active' in request.form
            item.degree = request.form.get('degree') if item.tip == 'Egitim' else None
            item.position = request.form.get('position') if item.tip == 'Deneyim' else None
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    item.logo_url = url_for('static', filename='uploads/' + filename)
            db.session.commit()
            flash('Kayıt güncellendi.', 'success')
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

    @app.route('/iletisim', methods=['POST'])
    def contact():
        yeni_mesaj = Mesaj(gonderen_ad=request.form.get('ad_soyad'), gonderen_email=request.form.get('email'), konu=request.form.get('konu'), mesaj_icerigi=request.form.get('mesaj'))
        db.session.add(yeni_mesaj)
        db.session.commit()
        flash('Mesajınız gönderildi.', 'success')
        return redirect(url_for('home', _anchor='iletisim'))

    @app.route('/admin/inbox')
    @login_required
    def admin_inbox():
        mesajlar = Mesaj.query.order_by(Mesaj.tarih.desc()).all()
        return render_template('admin_inbox.html', mesajlar=mesajlar)

    @app.route('/project/<int:id>')
    def project_detail(id):
        admin = Kullanici.query.first()
        proje = Proje.query.get_or_404(id)
        return render_template('project_detail.html', admin=admin, proje=proje)

    @app.route('/admin/projects', methods=['GET', 'POST'])
    @login_required
    def admin_projects():
        if request.method == 'POST':
            yeni_proje = Proje(baslik=request.form.get('baslik'), notlar=request.form.get('notlar'), detayli_icerik=request.form.get('detayli_icerik'), github_link=request.form.get('github_link'), canli_link=request.form.get('canli_link'))
            if 'kapak_resmi' in request.files:
                file = request.files['kapak_resmi']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    yeni_proje.kapak_resmi = url_for('static', filename='uploads/' + filename)
            db.session.add(yeni_proje)
            db.session.commit()
            flash('Proje eklendi.', 'success')
            return redirect(url_for('admin_projects'))
        return render_template('admin_projects.html', projeler=Proje.query.all())

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
            if islem.islem_turu == 'GELIR':
                varliklar['NAKIT']['toplam'] += islem.tutar_tl
                varliklar['NAKIT']['fiziksel'] += islem.tutar_tl
            elif islem.islem_turu == 'GIDER':
                varliklar['NAKIT']['toplam'] -= islem.tutar_tl
                varliklar['NAKIT']['fiziksel'] -= islem.tutar_tl
            elif islem.islem_turu in ['VARLIK_ALIM', 'VARLIK_SATIM']:
                carpan = 1 if islem.islem_turu == 'VARLIK_ALIM' else -1
                varliklar['NAKIT']['toplam'] -= (islem.tutar_tl * carpan)
                varliklar['NAKIT']['fiziksel'] -= (islem.tutar_tl * carpan)
                v_turu = islem.doviz_turu or islem.kategori
                if v_turu in varliklar:
                    miktar = islem.miktar
                    varliklar[v_turu]['toplam'] += (miktar * carpan)
                    if islem.varlik_konumu == 'BANKA':
                        varliklar[v_turu]['banka'] += (miktar * carpan)
                    else:
                        varliklar[v_turu]['fiziksel'] += (miktar * carpan)

        canli_kurlar = get_live_rates()
        net_servet = varliklar['NAKIT']['toplam']
        net_servet += varliklar['ALTIN']['toplam'] * canli_kurlar['ALTIN']
        net_servet += varliklar['GUMUS']['toplam'] * canli_kurlar['GUMUS']
        net_servet += varliklar['USD']['toplam'] * canli_kurlar['USD']
        net_servet += varliklar['EUR']['toplam'] * canli_kurlar['EUR']

        islemler = FinansIslem.query.order_by(FinansIslem.tarih.desc()).limit(20).all()
        return render_template('admin_finance.html', varliklar=varliklar, net_servet=net_servet, canli_kurlar=canli_kurlar, islemler=islemler)

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
            kategori = request.form.get('doviz_turu')
            miktar = float(request.form.get('miktar') or 0)
            banka_adi = request.form.get('banka')
            varlik_konumu = request.form.get('varlik_konumu', 'FIZIKSEL')
            doviz_turu = request.form.get('doviz_turu')

        aciklama = request.form.get('aciklama')
        birim_fiyat = tutar_tl / miktar if miktar > 0 else 0
        yeni_islem = FinansIslem(islem_turu=islem_turu, kategori=kategori, tutar_tl=tutar_tl, miktar=miktar, banka_adi=banka_adi, varlik_konumu=varlik_konumu, birim_fiyat=birim_fiyat, doviz_turu=doviz_turu, aciklama=aciklama)
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
        gunluk_plan = Gorev.query.filter(func.date(Gorev.son_tarih) == bugun, Gorev.kategori == 'GOREV').order_by(Gorev.saat).all()
        gunun_onemlileri = Gorev.query.filter(func.date(Gorev.son_tarih) == bugun, Gorev.onemli_mi == True).all()
        hafta_basla = bugun - timedelta(days=bugun.weekday())
        hafta_sonu = hafta_basla + timedelta(days=6)
        haftalik_gorevler = Gorev.query.filter(Gorev.son_tarih.isnot(None), func.date(Gorev.son_tarih) >= hafta_basla, func.date(Gorev.son_tarih) <= hafta_sonu).all()
        haftalik_plan = {'Pazartesi': [], 'Salı': [], 'Çarşamba': [], 'Perşembe': [], 'Cuma': [], 'Cumartesi': [], 'Pazar': []}
        gun_map = {0: 'Pazartesi', 1: 'Salı', 2: 'Çarşamba', 3: 'Perşembe', 4: 'Cuma', 5: 'Cumartesi', 6: 'Pazar'}
        for gorev in haftalik_gorevler:
            if gorev.son_tarih:
                gun_index = gorev.son_tarih.date().weekday()
                gun_adi = gun_map.get(gun_index)
                if gun_adi: haftalik_plan[gun_adi].append(gorev)
        tum_gorevler = Gorev.query.all()
        yillik_hedefler = Gorev.query.filter_by(kategori='HEDEF').all()
        return render_template('admin_planner.html', gunluk_plan=gunluk_plan, gunun_onemlileri=gunun_onemlileri, haftalik_plan=haftalik_plan, tum_gorevler=tum_gorevler, yillik_hedefler=yillik_hedefler)

    @app.route('/admin/planner/add', methods=['POST'])
    @login_required
    def add_planner_task():
        baslik = request.form.get('baslik')
        aciklama = request.form.get('aciklama')
        oncelik = request.form.get('oncelik')
        son_tarih_str = request.form.get('son_tarih')
        saat = request.form.get('saat')
        kategori = request.form.get('kategori', 'GOREV')
        ceyrek = request.form.get('ceyrek')
        onemli_mi = 'onemli_mi' in request.form
        son_tarih = datetime.strptime(son_tarih_str, '%Y-%m-%d') if son_tarih_str else None
        ceyrek_int = int(ceyrek) if ceyrek and ceyrek.isdigit() else None
        yeni_gorev = Gorev(baslik=baslik, aciklama=aciklama, oncelik=oncelik, son_tarih=son_tarih, saat=saat, kategori=kategori, ceyrek=ceyrek_int, onemli_mi=onemli_mi)
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
        yeni_kayit = Gunluk(baslik=baslik, icerik=icerik, tur=tur, duygu=duygu, tarih=datetime.utcnow())
        db.session.add(yeni_kayit)
        db.session.commit()
        flash('Yeni kayıt başarıyla eklendi.', 'success')
        return redirect(url_for('admin_diaries'))

    @app.route('/admin/diaries/update/<int:id>', methods=['POST'])
    @login_required
    def update_diary(id):
        gunluk = Gunluk.query.get_or_404(id)
        data = request.get_json()
        gunluk.baslik = data.get('baslik', gunluk.baslik)
        gunluk.icerik = data.get('icerik', gunluk.icerik)
        if gunluk.tur == 'GUNLUK':
            gunluk.duygu = data.get('duygu', gunluk.duygu)
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
        yillar_query = db.session.query(extract('year', Kitap.okunma_tarihi)).filter(Kitap.okunma_tarihi.isnot(None)).distinct().all()
        yillar = sorted([int(y[0]) for y in yillar_query if y[0] is not None], reverse=True)
        query = Kitap.query
        if secili_yil and secili_yil != 'genel':
            query = query.filter(extract('year', Kitap.okunma_tarihi) == int(secili_yil))
            secili_yil_display = secili_yil
        else:
            secili_yil_display = 'Genel'
            secili_yil = 'genel'
        kitaplar = query.order_by(Kitap.okunma_tarihi.desc()).all()
        toplam_kitap = len(kitaplar)
        toplam_sayfa = sum(kitap.sayfa_sayisi for kitap in kitaplar if kitap.sayfa_sayisi)
        toplam_yazar = len(set([kitap.yazar for kitap in kitaplar if kitap.yazar]))
        return render_template('admin_books.html', books=kitaplar, toplam_kitap=toplam_kitap, toplam_sayfa=toplam_sayfa, toplam_yazar=toplam_yazar, yillar=yillar, secili_yil=secili_yil, secili_yil_display=secili_yil_display)

    @app.route('/admin/books/add', methods=['POST'])
    @login_required
    def add_book():
        okunma_tarihi_str = request.form.get('okunma_tarihi')
        okunma_tarihi = datetime.strptime(okunma_tarihi_str, '%Y-%m-%d') if okunma_tarihi_str else None
        yeni_kitap = Kitap(kitap_adi=request.form.get('kitap_adi'), yazar=request.form.get('yazar'), sayfa_sayisi=int(request.form.get('sayfa_sayisi') or 0), okunma_tarihi=okunma_tarihi)
        db.session.add(yeni_kitap)
        db.session.commit()
        flash('Kitap eklendi.', 'success')
        return redirect(url_for('admin_books'))

    @app.route('/admin/books/delete/<int:id>')
    @login_required
    def delete_book(id):
        kitap = Kitap.query.get_or_404(id)
        db.session.delete(kitap)
        db.session.commit()
        flash('Kitap silindi.', 'success')
        return redirect(url_for('admin_books'))

    @app.route('/admin/ideas')
    @login_required
    def admin_ideas():
        fikirler = ProjeFikri.query.filter_by(durum='FIKIR').order_by(ProjeFikri.olusturma_tarihi.desc()).all()
        aktif_projeler = ProjeFikri.query.filter_by(durum='AKTIF').order_by(ProjeFikri.baslangic_tarihi.desc()).all()
        for proje in aktif_projeler:
            toplam = len(proje.gorevler)
            biten = len([g for g in proje.gorevler if g.durum == 'BITTI'])
            proje.ilerleme_yuzde = (biten / toplam * 100) if toplam > 0 else 0
        biten_projeler = ProjeFikri.query.filter_by(durum='BITTI').order_by(ProjeFikri.bitis_tarihi.desc()).all()
        return render_template('admin_ideas.html', fikirler=fikirler, aktif_projeler=aktif_projeler, biten_projeler=biten_projeler, now=datetime.now())

    @app.route('/admin/ideas/add', methods=['POST'])
    @login_required
    def add_idea():
        yeni_fikir = ProjeFikri(baslik=request.form.get('baslik'), ozet=request.form.get('ozet'), detay=request.form.get('detay'), sorun=request.form.get('sorun'), teknolojiler=request.form.get('teknolojiler'), durum='FIKIR')
        db.session.add(yeni_fikir)
        db.session.commit()
        flash('Fikir eklendi.', 'success')
        return redirect(url_for('admin_ideas'))

    @app.route('/admin/ideas/start/<int:id>', methods=['POST'])
    @login_required
    def start_idea(id):
        fikir = ProjeFikri.query.get_or_404(id)
        fikir.durum = 'AKTIF'
        if request.form.get('baslangic_tarihi'):
            fikir.baslangic_tarihi = datetime.strptime(request.form.get('baslangic_tarihi'), '%Y-%m-%d')
        if request.form.get('bitis_tarihi'):
            fikir.bitis_tarihi = datetime.strptime(request.form.get('bitis_tarihi'), '%Y-%m-%d')
        db.session.commit()
        flash('Proje başlatıldı.', 'success')
        return redirect(url_for('admin_ideas'))

    @app.route('/admin/studio')
    @login_required
    def admin_studio():
        projeler = StudioProject.query.order_by(StudioProject.olusturma_tarihi.desc()).all()
        return render_template('studio.html', projeler=projeler)

    @app.route('/admin/studio/add', methods=['POST'])
    @login_required
    def add_studio_project():
        yeni_proje = StudioProject(name=request.form.get('name'), category=request.form.get('category'), secure_data=request.form.get('secure_data'))
        db.session.add(yeni_proje)
        db.session.commit()
        flash('Studio projesi eklendi.', 'success')
        return redirect(url_for('admin_studio'))

    @app.route('/admin/studio/log/<int:id>', methods=['POST'])
    @login_required
    def add_studio_log(id):
        yeni_log = StudioWorkLog(proje_id=id, note=request.form.get('note'))
        db.session.add(yeni_log)
        db.session.commit()
        flash('Çalışma notu eklendi.', 'success')
        return redirect(url_for('admin_studio'))

    @app.route('/admin/studio/delete/<int:id>')
    @login_required
    def delete_studio_project(id):
        proje = StudioProject.query.get_or_404(id)
        db.session.delete(proje)
        db.session.commit()
        flash('Proje silindi.', 'success')
        return redirect(url_for('admin_studio'))

    @app.route('/admin/ideas/complete/<int:id>', methods=['POST'])
    @login_required
    def complete_idea(id):
        fikir = ProjeFikri.query.get_or_404(id)
        fikir.durum = 'BITTI'
        fikir.bitis_tarihi = datetime.now()
        db.session.commit()
        flash('Proje tamamlandı.', 'success')
        return redirect(url_for('admin_ideas'))

    @app.route('/admin/ideas/delete/<int:id>')
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
        if data and 'ilerleme' in data:
            fikir.ilerleme = int(data['ilerleme'])
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False}), 400

    @app.route('/admin/books/update/<int:id>', methods=['POST'])
    @login_required
    def update_book(id):
        kitap = Kitap.query.get_or_404(id)
        data = request.get_json()
        if data:
            kitap.kitap_adi = data.get('kitap_adi', kitap.kitap_adi)
            kitap.yazar = data.get('yazar', kitap.yazar)
            kitap.sayfa_sayisi = int(data.get('sayfa_sayisi') or kitap.sayfa_sayisi)
            if data.get('okunma_tarihi'):
                try:
                    kitap.okunma_tarihi = datetime.strptime(data.get('okunma_tarihi'), '%Y-%m-%d')
                except: pass
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False}), 400

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

    @app.route('/admin/studio/update/<int:id>', methods=['POST'])
    @login_required
    def update_studio_project(id):
        proje = StudioProject.query.get_or_404(id)
        proje.name = request.form.get('name')
        proje.category = request.form.get('category')
        proje.secure_data = request.form.get('secure_data')
        db.session.commit()
        flash('Proje güncellendi.', 'success')
        return redirect(url_for('admin_studio'))

    @app.route('/admin/skill/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_skill(id):
        yetenek = Yetenek.query.get_or_404(id)
        if request.method == 'POST':
            yetenek.ad = request.form.get('ad')
            yetenek.yuzde = int(request.form.get('yuzde'))
            db.session.commit()
            flash('Yetenek güncellendi.', 'success')
            return redirect(url_for('admin_skills'))
        return render_template('admin_skill_edit.html', yetenek=yetenek)

    @app.route('/admin/skill/delete/<int:id>')
    @login_required
    def delete_skill(id):
        yetenek = Yetenek.query.get_or_404(id)
        db.session.delete(yetenek)
        db.session.commit()
        flash('Yetenek silindi.', 'success')
        return redirect(url_for('admin_skills'))

    @app.route('/admin/projects/edit/<int:id>', methods=['GET', 'POST'])
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
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    proje.kapak_resmi = url_for('static', filename='uploads/' + filename)
            db.session.commit()
            flash('Proje güncellendi.', 'success')
            return redirect(url_for('admin_projects'))
        return render_template('admin_project_edit.html', proje=proje)

    @app.route('/admin/projects/delete/<int:id>')
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
            db.session.add(Yetenek(ad=request.form.get('ad'), yuzde=int(request.form.get('yuzde'))))
            db.session.commit()
            flash('Yetenek eklendi.', 'success')
            return redirect(url_for('admin_skills'))
        return render_template('admin_skills.html', yetenekler=Yetenek.query.all())

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
