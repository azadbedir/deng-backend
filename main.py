import os
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import google.generativeai as genai
from PIL import Image
import io

# --- API KEY ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
genai.configure(api_key=GEMINI_API_KEY)

model_flash = "models/gemini-flash-latest" 

app = FastAPI()

# --- DİNAMİK ROLLER ---
# Artık promptu dinamik oluşturacağız
def get_system_instruction(role, target_lang, source_lang):
    # target_lang: Öğrenilen dil (Örn: English)
    # source_lang: Kullanıcının dili / Açıklama dili (Örn: Kurdish)
    
    base_instruction = f"""
    Senin adın Deng. Görevin kullanıcının {target_lang} öğrenmesine yardımcı olmak.
    Kullanıcı ile {target_lang} diliyle samimi bir konuşma yapmak.
    ANCAK, gramer hatalarını açıklarken veya konuyu anlatırken MUTLAKA {source_lang} dilini kullan.
    Samimi, sabırlı ve yardımsever ol.kısa cevaplar ver.
    """
    
    if role == "teacher":
        return base_instruction + " Bir öğretmen gibi gramer kuralları ver. yapılan yanlışları nazikçe düzelt. cümlelerin çokta uzun olmasın."
    # elif role == "waiter":
    #     return base_instruction + f" Sen bir garsonsun. {target_lang} konuşulan bir kafedesin. Sipariş al."
    elif role == "interviewer":
        return base_instruction + f" Sen bir işe alım uzmanısın. {target_lang} dilinde mülakat yap."
    else: # friend
        return base_instruction + " Bir arkadaş gibi doğal, kısa, arkadaş canlısı ve samimi bir arkadaşmış gibi konuş."

# --- 1. SOHBET ENDPOINT ---
class ChatRequest(BaseModel):
    text: str
    role: str = "friend"
    target_lang: str = "English" # Öğrenilecek dil
    source_lang: str = "Turkish" # Bilenen dil (Açıklama dili)

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        # Dilleri prompt'a gömüyoruz
        system_instruction = get_system_instruction(request.role, request.target_lang, request.source_lang)
        
        model = genai.GenerativeModel(model_flash)
        chat = model.start_chat(history=[
            {"role": "user", "parts": ["System Instruction: " + system_instruction]},
            {"role": "model", "parts": ["Understood. I am ready."]}
        ])
        
        response = chat.send_message(request.text)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": "Connection error / Bağlantı hatası", "error": str(e)}
    

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