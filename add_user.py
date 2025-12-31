import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from main import create_app
from extensions import db
from models import Kullanici

app = create_app()

with app.app_context():
    existing_user = Kullanici.query.filter_by(kullanici_adi='battalbey').first()
    
    if existing_user:
        print("Bu kullanıcı adı zaten var!")
    else:
        yeni_kullanici = Kullanici(
            kullanici_adi='battalbey',
            sifre='eb07'
        )
        db.session.add(yeni_kullanici)
        db.session.commit()
        print("Yeni hesap başarıyla eklendi!")
        print(f"Kullanıcı Adı: battalbey")
        print(f"Şifre: eb07")
