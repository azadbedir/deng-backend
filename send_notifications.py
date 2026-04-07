import firebase_admin
from firebase_admin import credentials, firestore, messaging

# 1. Firebase Anahtarını Tanıt (İndirdiğin JSON dosyasının adı)
cred = credentials.Certificate(r"C:\Users\Azad\OneDrive\Desktop\english_buddy_backend\firebase-key.json")
firebase_admin.initialize_app(cred)

# Veritabanına (Firestore) bağlan
db = firestore.client()

def send_personalized_notifications():
    print("Kullanıcılar taranıyor...")
    
    # 2. 'users' koleksiyonundaki tüm kullanıcıları çek
    users_ref = db.collection('users').stream()

    for user in users_ref:
        user_data = user.to_dict()
        token = user_data.get('fcm_token')
        
        # Eğer kullanıcının ismi yoksa varsayılan olarak 'Dostum' yaz
        name = user_data.get('display_name', 'Dostum') 

        # Sadece bildirim adresi (token) olanlara gönder
        if token:
            try:
                # 3. Bildirimi isme özel olarak hazırla
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=f"Hey {name}! Pratik Zamanı 🚀", # İSİM BURAYA GELECEK
                        body="Deng seni bekliyor, gel ve hemen 5 dakika pratik yapalım!"
                    ),
                    token=token, # Sadece bu kişinin telefonuna gönderir
                )

                # 4. Bildirimi ateşle!
                response = messaging.send(message)
                print(f"✅ {name} adlı kişiye bildirim gönderildi! (ID: {response})")
                
            except Exception as e:
                print(f"❌ {name} için bildirim gönderilemedi. Hata: {e}")

# Fonksiyonu çalıştır
if __name__ == "__main__":
    send_personalized_notifications()
