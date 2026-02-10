import os
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import google.generativeai as genai
from PIL import Image
import io
from typing import List, Dict

# --- API KEY ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
genai.configure(api_key=GEMINI_API_KEY)

model_flash = "models/gemini-1.5-flash" 

app = FastAPI()

# --- GELİŞMİŞ ROLLER ---
def get_system_instruction(role, target_lang, source_lang, level):

    # SEVİYE AYARLARI
    level_instruction = ""
    if "A1" in level:
        level_instruction = f"Kullanıcı {target_lang} dilinde BAŞLANGIÇ (Beginner) seviyesinde. Çok basit kelimeler kullan. Kısa ve net cümleler kur. Karmaşık gramer yapılarından kaçın."
    elif "B1" in level:
        level_instruction = f"Kullanıcı {target_lang} dilinde ORTA (Intermediate) seviyede. Günlük konuşma dilini kullanabilirsin ama çok ağır deyimlerden kaçın."
    else: # C1-C2
        level_instruction = f"Kullanıcı {target_lang} dilinde İLERİ (Advanced) seviyede. Zengin bir kelime dağarcığı, deyimler ve karmaşık yapılar kullanabilirsin. Zorlayıcı ol."
    
    # ORTAK KURALLAR
    base = f"""
    Senin adın Deng. Şu an bir rol yapma oyunundayız.
    Kullanıcının hedef dili: {target_lang}.
    Senin açıklamaların ve yardım dilin: {source_lang}.
    SEVİYE TALİMATI: {level_instruction}
    CEVAPLARIN KISA VE ÖZ OLSUN. Uzun paragraflar yazma.
    """

    if role == "teacher":
        return base + f"""
        [ROLÜN: ÖĞRETMEN]
        1. Çok nazik, sabırlı ve destekleyici bir öğretmensin.
        2. Kullanıcının {target_lang} gramer hatalarını ASLA affetme, hemen nazikçe düzelt.
        3. Düzeltmeyi yaptıktan sonra konuya devam et.
        4. Emojiler kullan: 📚, ✍️, ✨.
        5. Kullanıcı "Merhaba" derse, derse hazır olup olmadığını sor.
        """
    
    elif role == "friend":
        return base + f"""
        [ROLÜN: EN YAKIN ARKADAŞ (KANKA)]
        1. Sen bir 'öğretmen' DEĞİLSİN. Sakın ders verme.
        2. Kullanıcı hata yapsa bile, anlam bozulmuyorsa GÖRMEZDEN GEL ve sohbete devam et.
        3. Sokak ağzı (slang), kısaltmalar ve samimi bir dil kullan.
        4. "Dostum", "Kanka", "Bro" gibi hitaplar kullanabilirsin.
        5. Emojiler kullan: 😎, 😂, 🔥, 👋.
        6. Kullanıcı "Merhaba" derse, "Naber, ne yapıyorsun?" gibi doğal cevap ver.
        """
    
    # elif role == "interviewer":
    #     return base + f"""
    #     [ROLÜN: İŞE ALIM UZMANI]
    #     1. Ciddi, profesyonel ve resmi ol.
    #     2. {target_lang} dilinde mülakat yapıyorsun.
    #     3. Kullanıcının cevaplarını profesyonelce değerlendir ve bir sonraki zor soruyu sor.
    #     """
        
    else:
        return base + "Doğal ve yardımsever ol."

# --- CHAT MODELİ GÜNCELLENDİ ---
class ChatRequest(BaseModel):
    text: str
    role: str = "friend"
    target_lang: str = "English"
    source_lang: str = "Turkish"
    level: str = "A1-A2 (Beginner)" # <--- YENİ
    history: List[Dict[str, str]] = []

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        system_instruction = get_system_instruction(request.role, request.target_lang, request.source_lang)
        
        # Gemini Modeli Oluştur
        model = genai.GenerativeModel(model_flash)
        
        # 1. Sistem talimatını geçmişin en başına ekle
        gemini_history = [
            {"role": "user", "parts": ["System Instruction: " + system_instruction]},
            {"role": "model", "parts": ["Understood. I'm ready."]}
        ]

        # 2. Flutter'dan gelen geçmiş mesajları Gemini formatına çevirip ekle
        # (Son 10 mesajı alıyoruz ki token dolmasın)
        for msg in request.history[-10:]: 
            role = "user" if msg['role'] == "user" else "model"
            content = msg.get('content', '')
            if content:
                gemini_history.append({"role": role, "parts": [content]})
        
        # 3. Sohbeti başlat (Geçmiş yüklü olarak)
        chat = model.start_chat(history=gemini_history)
        
        # 4. Yeni mesajı gönder
        response = chat.send_message(request.text)
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "Connection error...", "error": str(e)}

# --- DİĞER ENDPOINTLER (vision, define) AYNI KALACAK ---
# ... (vision ve define kodlarını buraya eski haliyle yapıştırabilirsin)
    

# --- 2. GÖRSEL ZEKA ENDPOINT ---
@app.post("/vision")
async def vision_endpoint(file: UploadFile = File(...), prompt: str = Form(...), source_lang: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Resim için özel prompt
        full_prompt = f"{prompt}. Please explain in {source_lang}."
        
        model = genai.GenerativeModel(model_flash)
        response = model.generate_content([full_prompt, image])
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "Error seeing image.", "error": str(e)}
    
# --- 3. SÖZLÜK ENDPOINT (YENİ) ---
class DefineRequest(BaseModel):
    word: str
    source_lang: str # Kullanıcının ana dili (Örn: Türkçe)

@app.post("/define")
def define_endpoint(request: DefineRequest):
    try:
        # Gemini'ye sadece kelimenin anlamını soruyoruz
        prompt = f"What does the word '{request.word}' mean in {request.source_lang}? Give a very short definition or translation (max 1 sentence)."
        
        model = genai.GenerativeModel("models/gemini-flash-latest")
        response = model.generate_content(prompt)
        
        return {"definition": response.text.strip()}
    except Exception as e:
        return {"definition": "Could not find definition.", "error": str(e)}




