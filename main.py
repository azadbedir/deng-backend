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

# --- YENİ NESİL MODEL GÜNCELLEMESİ ---
model_text = "gemini-2.5-flash"         
model_vision = "gemini-2.5-flash"

app = FastAPI()

# --- GELİŞMİŞ ROLLER VE KESİN DİL KURALLARI ---
def get_system_instruction(role, target_lang, source_lang, level):

    # SEVİYE AYARLARI (İngilizce yazıyoruz ki LLM komutu dille karıştırmasın)
    level_instruction = ""
    if "A1" in level:
        level_instruction = f"The user is at BEGINNER (A1-A2) level in {target_lang}. Use extremely simple vocabulary, very short sentences, and basic grammar. AVOID complex structures."
    elif "B1" in level:
        level_instruction = f"The user is at INTERMEDIATE (B1-B2) level in {target_lang}. Use everyday conversational language, but avoid overly complex idioms."
    else: # C1-C2
        level_instruction = f"The user is at ADVANCED (C1-C2) level in {target_lang}. Use rich vocabulary, idioms, and complex structures. Speak like a native."

    # ORTAK KURALLAR (Çok Kesin Sınırlar - Firewall)
    base = f"""
    You are 'Deng', an AI language practice companion.
    
    CRITICAL LANGUAGE RULES:
    1. THE MAIN CONVERSATION LANGUAGE IS: {target_lang}. You MUST speak, chat, and reply ONLY in {target_lang}.
    2. EXPLANATION LANGUAGE: {source_lang}. ONLY use {source_lang} if the user explicitly asks for a translation, says they don't understand, or if you need to explain a grammar mistake. 
    3. NEVER mix {target_lang} and {source_lang} in the same sentence unless you are translating a specific word.
    
    USER'S LEVEL: {level_instruction}
    
    GENERAL RULES:
    - Keep your responses SHORT and CONCISE. Maximum 2-3 sentences. Do NOT write long paragraphs.
    """

    if role == "teacher":
        return base + f"""
        [YOUR ROLE: TEACHER]
        - You are a polite, patient, and supportive teacher.
        - If the user makes a grammar mistake in {target_lang}, gently correct it using {source_lang}, then continue the conversation in {target_lang}.
        - Use emojis like 📚, ✍️, ✨.
        - If the user says "Hello", ask if they are ready for the lesson in {target_lang}.
        """
        
    elif role == "friend":
        return base + f"""
        [YOUR ROLE: BEST FRIEND]
        - You are a casual friend, NOT a teacher. Do NOT give grammar lessons.
        - Ignore minor mistakes if the meaning is clear.
        - Use casual language, slang, and a very friendly tone in {target_lang}.
        - Use emojis like 😎, 😂, 🔥, 👋.
        - If the user says "Hello", reply with a casual "What's up?" or similar natural greeting in {target_lang}.
        """
        
    elif role == "interviewer":
        return base + f"""
        [YOUR ROLE: JOB INTERVIEWER]
        - You are a serious, professional hiring manager.
        - You are conducting a job interview in {target_lang}.
        - Ask one professional interview question at a time. Wait for the user's answer, evaluate it professionally, and ask the next question.
        """
        
    else:
        return base + f"\n[YOUR ROLE: HELPFUL ASSISTANT]\nConverse naturally in {target_lang}."

# --- CHAT MODELİ ---
class ChatRequest(BaseModel):
    text: str
    role: str = "friend"
    target_lang: str = "English"
    source_lang: str = "Turkish"
    level: str = "A1-A2 (Beginner)"
    history: List[Dict[str, str]] = []

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        system_instruction = get_system_instruction(
            request.role, 
            request.target_lang, 
            request.source_lang, 
            request.level 
        )
        
        # DÜZELTİLDİ: Stabil metin modeli kullanılıyor
        model = genai.GenerativeModel(model_text)
        
        gemini_history = [
            {"role": "user", "parts": ["System Instruction: " + system_instruction]},
            {"role": "model", "parts": ["Understood. I will strictly follow these language rules."]}
        ]

        for msg in request.history[-10:]: 
            role = "user" if msg['role'] == "user" else "model"
            content = msg.get('content', '')
            if content:
                gemini_history.append({"role": role, "parts": [content]})
        
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(request.text)
        
        return {"reply": response.text}
    except Exception as e:
        # DÜZELTİLDİ: Gerçek hata mesajını Deng'in ağzından göreceğiz
        error_message = str(e)
        return {"reply": f"Sistem Hatası: {error_message}", "error": error_message}
    

# --- 2. GÖRSEL ZEKA ENDPOINT ---
@app.post("/vision")
async def vision_endpoint(file: UploadFile = File(...), prompt: str = Form(...), source_lang: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        full_prompt = f"{prompt}. Please explain in {source_lang}."
        
        # DÜZELTİLDİ: Stabil görsel model kullanılıyor
        model = genai.GenerativeModel(model_vision)
        response = model.generate_content([full_prompt, image])
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Görsel Hatası: {str(e)}", "error": str(e)}
    
# --- 3. SÖZLÜK ENDPOINT ---
class DefineRequest(BaseModel):
    word: str
    source_lang: str 

@app.post("/define")
def define_endpoint(request: DefineRequest):
    try:
        prompt = (
            f"Translate the word '{request.word}' into {request.source_lang}. "
            f"Return ONLY the direct translations separated by commas (e.g. 'Meaning1, Meaning2'). "
            f"DO NOT write sentences. DO NOT give definitions. DO NOT add pronunciation. "
            f"Just the words."
        )
        
        # DÜZELTİLDİ: Stabil metin modeli kullanılıyor
        model = genai.GenerativeModel(model_text) 
        response = model.generate_content(prompt)
        
        clean_text = response.text.strip().replace("\n", "").rstrip(".")
        return {"definition": clean_text}
        
    except Exception as e:
        print(f"Hata: {e}")
        return {"definition": f"Hata: {str(e)}", "error": str(e)}

# --- 4. CÜMLE ÇEVİRİ ENDPOINT ---
class TranslateRequest(BaseModel):
    text: str
    target_lang: str  

@app.post("/translate_sentence")
def translate_sentence_endpoint(request: TranslateRequest):
    try:
        prompt = (
            f"Translate the following sentence into {request.target_lang}. "
            f"Provide a natural, fluent translation. No explanations, just the translation.\n\n"
            f"Sentence: {request.text}"
        )
        
        # DÜZELTİLDİ: Stabil metin modeli kullanılıyor
        model = genai.GenerativeModel(model_text)
        response = model.generate_content(prompt)
        
        return {"translation": response.text.strip()}
    except Exception as e:
        return {"translation": f"Çeviri Hatası: {str(e)}", "error": str(e)}


