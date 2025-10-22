"""
#ILAN komutu ile test - Gemini'siz
"""
from whatsapp_central_bot import central_bot
from app import app, db, User, TevkilPost

with app.app_context():
    user = User.query.filter_by(email='test@koptay.av.tr').first()
    
    print("\n" + "="*70)
    print("🧪 #ILAN KOMUTU İLE TEST (Gemini gerektirmez)")
    print("="*70)
    
    # Template based ilan
    ilan_template = """#ILAN
Başlık: İzmir Ticaret Mahkemesi Duruşması
Kategori: Ticaret Hukuku
Şehir: İzmir
Açıklama: 23.10.2025 tarihinde saat 15:00 duruşma
Fiyat: 4000
Aciliyet: Normal"""
    
    print("\n📝 İLAN MESAJI (Template Format):")
    print("-" * 70)
    print(ilan_template)
    print("-" * 70)
    
    r1 = central_bot.process_message(user.phone, ilan_template)
    
    if r1['success']:
        print("\n✅ İLAN OLUŞTURULDU!")
        print(f"\nYanıt:")
        print(r1['message'])
        
        # En son oluşturulan ilanı kontrol et
        latest_post = TevkilPost.query.order_by(TevkilPost.id.desc()).first()
        if latest_post:
            print(f"\n📊 VERİTABANI KONTROLÜ:")
            print(f"   ID: #{latest_post.id}")
            print(f"   Başlık: {latest_post.title}")
            print(f"   Şehir: {latest_post.city}")
            print(f"   Mahkeme: {latest_post.courthouse}")
            print(f"   Kategori: {latest_post.category}")
            print(f"   Ücret: {latest_post.price_max} TL")
            print(f"   Durum: {latest_post.status}")
    else:
        print("\n❌ HATA!")
        print(r1['message'])
    
    print("\n" + "="*70)
    print("✅ TEST TAMAMLANDI")
    print("="*70)
