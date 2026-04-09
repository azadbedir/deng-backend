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
        name = user_data.get('display_name', 'Dostum') 
        
        # EKLENEN KISIM: Kullanıcının tercihini veritabanından çek (Varsayılan True)
        notif_daily = user_data.get('notif_daily', True)

        # GÜNCELLENEN KISIM: Hem token varsa hem de bildirim izni açıksa gönder
        if token and notif_daily:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=f"Hey {name}! Pratik Zamanı 🚀", 
                        body="Deng seni bekliyor, gel ve hemen 5 dakika pratik yapalım!"
                    ),
                    token=token, 
                )
                response = messaging.send(message)
                print(f"✅ {name} adlı kişiye bildirim gönderildi!")
                
            except Exception as e:
                print(f"❌ {name} için bildirim gönderilemedi. Hata: {e}")

# Fonksiyonu çalıştır
if __name__ == "__main__":
    send_personalized_notifications()
