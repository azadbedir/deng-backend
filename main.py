import os
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import google.generativeai as genai
from PIL import Image
import io
from typing import List, Dict, Optional

# --- API KEY ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
genai.configure(api_key=GEMINI_API_KEY)

# MODEL (Kararlı Sürüm)
model_flash = "models/gemini-1.5-flash" 

app = FastAPI()

# --- SİSTEM TALİMATI ---
def get_system_instruction(role, target_lang, source_lang):
    base = f"""
    Senin adın Deng. Şu an bir rol yapma oyunundayız.
    Kullanıcının hedef dili: {target_lang}.
    Senin açıklamaların ve yardım dilin: {source_lang}.
    CEVAPLARIN KISA VE ÖZ OLSUN. Uzun paragraflar yazma.
    """
    if role == "teacher":
        return base + " Nazik bir öğretmensin, hataları düzelt."
    elif role == "friend":
        return base + " Samimi bir arkadaşsın (kanka), hataları görmezden gel."
    else:
        return base + " Doğal ve yardımsever ol."

# --- CHAT MODELİ ---
class ChatRequest(BaseModel):
    text: str
    role: str = "friend"
    target_lang: str = "English"
    source_lang: str = "Turkish"
    # History listesini tanımlıyoruz (Hata almamak için opsiyonel yaptık)
    history: List[Dict[str, str]] = [] 

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        # 1. Sistem talimatı
        system_instruction = get_system_instruction(request.role, request.target_lang, request.source_lang)
        
        # 2. Modeli hazırla
        model = genai.GenerativeModel(model_flash)
        
        # 3. Geçmişi Gemini formatına çevir
        gemini_history = [
            {"role": "user", "parts": ["System Instruction: " + system_instruction]},
            {"role": "model", "parts": ["Understood. I'm ready."]}
        ]

        # 4. Flutter'dan gelen geçmişi GÜVENLİ şekilde ekle
        if request.history:
            for msg in request.history[-10:]: # Son 10 mesaj
                # .get() kullanarak hata riskini sıfıra indiriyoruz
                r = msg.get('role', 'user') 
                c = msg.get('content', '')
                
                # 'deng' rolü gelirse 'model' yap
                if r not in ["user", "model"]: 
                    r = "model"
                
                if c: # İçerik boş değilse ekle
                    gemini_history.append({"role": r, "parts": [str(c)]})
        
        # 5. Sohbeti başlat ve mesajı gönder
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(request.text)
        
        return {"reply": response.text}

    except Exception as e:
        # --- İŞTE BURASI ÇOK ÖNEMLİ ---
        # Hatayı gizlemek yerine ekrana yazdırıyoruz!
        hata_mesaji = f"SİSTEM HATASI: {str(e)}"
        print(hata_mesaji) 
        return {"reply": hata_mesaji}

# --- 2. GÖRSEL ZEKA ENDPOINT ---
@app.post("/vision")
async def vision_endpoint(file: UploadFile = File(...), prompt: str = Form(...), source_lang: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        full_prompt = f"{prompt}. Please explain in {source_lang}."
        
        model = genai.GenerativeModel(model_flash)
        response = model.generate_content([full_prompt, image])
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Vision Error: {str(e)}"}
    
# --- 3. SÖZLÜK ENDPOINT ---
class DefineRequest(BaseModel):
    word: str
    source_lang: str 

@app.post("/define")
def define_endpoint(request: DefineRequest):
    try:
        prompt = f"What does the word '{request.word}' mean in {request.source_lang}? Give a very short definition or translation (max 1 sentence)."
        
        # BURAYI DA GÜNCELLEDİM (Eski 'flash-latest' hata verebilir)
        model = genai.GenerativeModel(model_flash) 
        response = model.generate_content(prompt)
        
        return {"definition": response.text.strip()}
    except Exception as e:
        return {"definition": "Could not find definition.", "error": str(e)}
