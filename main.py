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
