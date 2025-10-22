#!/bin/bash
# PythonAnywhere Deployment Script
# Kullanıcı: muratcankoptay
# Proje: Ulusal Tevkil Ağı Projesi

echo "🚀 Ulusal Tevkil Ağı - PythonAnywhere Deploy"
echo "Kullanıcı: muratcankoptay"
echo "=========================================="
echo ""

# Proje dizinine git
cd /home/muratcankoptay/tevkil_proje

# Virtual environment oluştur
echo "📦 Virtual environment oluşturuluyor..."
python3.11 -m venv venv
source venv/bin/activate

# Bağımlılıkları yükle
echo "📥 Bağımlılıklar yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt

# Database oluştur
echo "🗄️  Database oluşturuluyor..."
python3.11 << END
from app import app, db
with app.app_context():
    db.create_all()
    print("✅ Database oluşturuldu!")
END

# Admin kullanıcısı oluştur
echo "👤 Admin kullanıcısı oluşturuluyor..."
python3.11 << END
from app import app, db, User
with app.app_context():
    # Önce kontrol et
    existing = User.query.filter_by(email='admin@tevkil.com').first()
    if not existing:
        user = User(
            email='admin@tevkil.com',
            full_name='Murat Can Koptay',
            city='İstanbul',
            bar_association='İstanbul Barosu',
            lawyer_type='avukat',
            phone='5551234567',
            verified=True
        )
        user.set_password('Tevkil2025!')
        db.session.add(user)
        db.session.commit()
        print("✅ Admin kullanıcısı oluşturuldu!")
        print("   Email: admin@tevkil.com")
        print("   Şifre: Tevkil2025!")
    else:
        print("ℹ️  Admin kullanıcısı zaten mevcut")
END

echo ""
echo "✅ Kurulum tamamlandı!"
echo ""
echo "📋 ŞİMDİ YAPMANIZ GEREKENLER:"
echo "1. PythonAnywhere Web sekmesine gidin"
echo "2. 'Reload muratcankoptay.pythonanywhere.com' butonuna basın"
echo "3. https://muratcankoptay.pythonanywhere.com adresini açın"
echo ""
echo "🔐 GİRİŞ BİLGİLERİ:"
echo "Email: admin@tevkil.com"
echo "Şifre: Tevkil2025!"
echo ""
