"""
Meta Template Mesajı Testi
hello_world template'i ile test eder
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_template_message():
    """Meta'nın hello_world template'i ile test"""
    
    print("=" * 60)
    print("META TEMPLATE MESAJI TESTİ")
    print("=" * 60)
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    phone_number_id = os.getenv('META_PHONE_NUMBER_ID')
    
    # Template mesajı gönder
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # hello_world template (Meta'nın hazır template'i)
    payload = {
        "messaging_product": "whatsapp",
        "to": "905307111864",
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {
                "code": "en_US"
            }
        }
    }
    
    print("\n📤 Template mesajı gönderiliyor...")
    print(f"Template: hello_world")
    print(f"To: 905307111864")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"\n📊 Status Code: {response.status_code}")
        print(f"📊 Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            print(f"\n✅ TEMPLATE MESAJI GÖNDERİLDİ!")
            print(f"Message ID: {message_id}")
            print(f"\n📱 WhatsApp'ını kontrol et!")
            print("'Hello World' mesajını göreceksin!")
            return True
        else:
            print(f"\n❌ HATA!")
            error = response.json().get('error', {})
            print(f"Error: {error.get('message')}")
            print(f"Code: {error.get('code')}")
            
            # Alternatif: Normal text mesajı dene
            print("\n" + "=" * 60)
            print("ALTERNATİF: Normal text mesajı deneniyor...")
            return test_text_message()
    
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")
        return False


def test_text_message():
    """Normal text mesajı test et"""
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    phone_number_id = os.getenv('META_PHONE_NUMBER_ID')
    
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Basit text mesajı
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "905307111864",
        "type": "text",
        "text": {
            "preview_url": False,
            "body": "🎉 Test mesajı!\n\nBu mesaj Meta WhatsApp API ile gönderildi.\n\nTevkil Ağı - WhatsApp Bot"
        }
    }
    
    print(f"\n📤 Text mesajı gönderiliyor...")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            print(f"\n✅ TEXT MESAJI GÖNDERİLDİ!")
            print(f"Message ID: {message_id}")
            print(f"\n📱 WhatsApp'ını kontrol et!")
            return True
        else:
            error = response.json().get('error', {})
            print(f"\n❌ Text mesajı da gönderilemedi!")
            print(f"Error: {error.get('message')}")
            print(f"Code: {error.get('code')}")
            
            # Detaylı hata analizi
            if error.get('code') == 131047:
                print("\n🔧 SORUN: Re-engagement mesajı gerekiyor!")
                print("Çözüm:")
                print("1. İlk mesajı KULLANICI göndermeli (WhatsApp'tan sana yaz)")
                print("2. Veya onaylı template kullanmalısın")
                print("3. Veya 24 saat içinde kullanıcı sana mesaj yazmış olmalı")
            
            return False
    
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_template_message()
    
    if not success:
        print("\n" + "=" * 60)
        print("SORUN GİDERME:")
        print("=" * 60)
        print("\n1. Önce sen WhatsApp'tan BOT NUMARASINA mesaj at:")
        print("   - WhatsApp'ı aç")
        print("   - Bot numarasına 'Merhaba' yaz")
        print("   - Sonra bu scripti tekrar çalıştır")
        print("\n2. Veya Meta Business Manager'dan 'Send Test Message' kullan")
