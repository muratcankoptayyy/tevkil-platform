"""
UDF Şablon Doldurma Test Script
"""
from udf_service import create_authorization_udf
import zipfile

# Test verileri
post_owner = {
    'name': 'Murat Can KOPTAY',
    'baro': 'Ankara Barosu',
    'sicil': '12345',
    'tax_office': 'Çankaya V.D.',
    'tax_number': '1234567890',
    'address': 'Çankaya/Ankara Kızılay Mahallesi Test Sokak No:1'
}

applicant = {
    'name': 'Ahmet YILMAZ',
    'baro': 'İstanbul Barosu',
    'sicil': '67890',
    'tax_office': 'Beşiktaş V.D.',
    'tax_number': '0987654321',
    'address': 'Beşiktaş/İstanbul Barbaros Bulvarı No:5'
}

post_data = {
    'title': 'Boşanma Davası',
    'category': 'Aile Hukuku',
    'location': 'Ankara',
    'description': 'Boşanma davası için yetkilendirme',
    'client_name': 'Ali VELİ',
    'client_address': 'Keçiören/Ankara Test Mahallesi No:10',
    'vekaletname_info': '15.05.2024 tarih ve 1234 yevmiye nolu noterlik belgesi'
}

application_info = {
    'created_at': '20.10.2025',
    'accepted_at': '23.10.2025'
}

print("🔄 UDF Şablon Test Başlıyor...")
print("-" * 60)

try:
    # UDF oluştur
    udf_buffer = create_authorization_udf(
        post_owner=post_owner,
        applicant=applicant,
        post=post_data,
        application=application_info,
        price=5000
    )
    
    print("✅ UDF başarıyla oluşturuldu!")
    print(f"📦 Boyut: {len(udf_buffer.getvalue())} bytes")
    
    # Test dosyasına kaydet
    with open('test_yetki_belgesi.udf', 'wb') as f:
        f.write(udf_buffer.getvalue())
    print("💾 test_yetki_belgesi.udf dosyası kaydedildi")
    
    # İçeriği kontrol et
    udf_buffer.seek(0)
    with zipfile.ZipFile(udf_buffer, 'r') as zf:
        content_xml = zf.read('content.xml').decode('utf-8')
        
        # CDATA içeriğini çıkar
        cdata_start = content_xml.find('<![CDATA[') + 9
        cdata_end = content_xml.find(']]></content>')
        text_content = content_xml[cdata_start:cdata_end]
        
        print("\n" + "=" * 60)
        print("📄 DOLDURULMUŞ BELGE İÇERİĞİ:")
        print("=" * 60)
        print(text_content)
        print("=" * 60)
        
        # Kontroller
        print("\n🔍 Doldurma Kontrolü:")
        
        checks = [
            ('Yetki veren adı', 'Murat Can KOPTAY' in text_content),
            ('Yetki veren baro', 'Ankara Barosu' in text_content),
            ('Yetki veren sicil', '12345' in text_content),
            ('Yetki veren vergi dairesi', 'Çankaya V.D.' in text_content),
            ('Yetki veren adres', 'Çankaya/Ankara' in text_content),
            ('Yetkilendirilen baro', 'İstanbul Barosu' in text_content),
            ('Yetkilendirilen sicil', '67890' in text_content),
            ('Yetkilendirilen vergi dairesi', 'Beşiktaş V.D.' in text_content),
            ('Yetkilendirilen adres', 'Beşiktaş/İstanbul' in text_content),
            ('Vekil eden (müvekkil)', 'Ali VELİ' in text_content),
            ('Müvekkil adres', 'Keçiören/Ankara' in text_content),
            ('Vekaletname bilgisi', '15.05.2024' in text_content),
            ('Tarih dolduruldu', '../../....' not in text_content),
            ('İmza dolduruldu', 'Av. .......................' not in text_content),
            ('Boş alan kalmadı', '..............' not in text_content)
        ]
        
        all_ok = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"{status} {check_name}: {'OK' if result else 'HATA'}")
            if not result:
                all_ok = False
        
        print("\n" + "=" * 60)
        if all_ok:
            print("🎉 TÜM KONTROLLER BAŞARILI!")
            print("📋 Şablon doğru şekilde dolduruldu")
            print("✨ UDF dosyası UYAP'ta kullanıma hazır")
        else:
            print("⚠️  BAZI KONTROLLER BAŞARISIZ!")
            print("🔧 Doldurma işlemini kontrol edin")
        print("=" * 60)
        
except Exception as e:
    print(f"\n❌ HATA: {str(e)}")
    import traceback
    traceback.print_exc()
