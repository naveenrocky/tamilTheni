import streamlit as st
import pandas as pd
import random
import time
import os
import hmac
import base64
from openai import OpenAI
from gtts import gTTS

# --- 1. CONFIGURATION & SECRETS ---
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
APP_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]

client = OpenAI(api_key=OPENAI_API_KEY)

IMAGE_PATH = "images" 
EXCEL_FILE_NAME = "TT2026-Word-List-Theni-1_2_3_4_Extracted.xlsx"

st.set_page_config(page_title="Tamil Theni AI", page_icon="🐘", layout="wide")

# --- 2. SECURITY ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    st.title("🔐 Tamil Theni Private Access")
    pwd = st.text_input("Enter Access Password", type="password")
    if st.button("Sign In"):
        if hmac.compare_digest(pwd, APP_PASSWORD):
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Access Denied.")
    return False

if not check_password():
    st.stop()

# --- 3. DATA LOADING ---
@st.cache_data
def load_vocabulary(file_path):
    fallback_vocab = ["nose", "ear", "hair", "thigh", "head", "hand", "tongue", "neck", "leg", "lip"]
    if not os.path.exists(file_path):
        return fallback_vocab
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        all_words = df.iloc[:, [1, 6]].values.flatten()
        extracted = list(set([str(w).strip().lower() for w in all_words if len(str(w)) > 2]))
        return extracted if len(extracted) > 0 else fallback_vocab
    except:
        return fallback_vocab

def get_ai_pairing(valid_names):
    sample = random.sample(valid_names, min(len(valid_names), 30))
    prompt = f"Pick 2 related words from {sample}. Write a simple 4-word Tamil sentence for kids. Format: word1 | word2 | sentence"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a Tamil teacher. Use pipe | separator."}],
            timeout=10
        )
        parts = [p.strip() for p in response.choices[0].message.content.split("|")]
        return parts if len(parts) == 3 else None
    except:
        return None

def speak_tamil(text):
    try:
        tts = gTTS(text=text, lang='ta')
        tts.save("temp_voice.mp3")
        with open("temp_voice.mp3", "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    except: pass

# --- 4. FILE SYSTEM SYNC ---
if not os.path.exists(IMAGE_PATH):
    st.error(f"❌ Folder '{IMAGE_PATH}' not found.")
    st.stop()

all_files = [f for f in os.listdir(IMAGE_PATH) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
image_map = {os.path.splitext(f)[0].strip().lower(): f for f in all_files}
vocab = load_vocabulary(EXCEL_FILE_NAME)
valid_names = [v for v in vocab if v in image_map]

# --- 5. APP UI ---
if "running" not in st.session_state: 
    st.session_state.running = False

# Sidebar for controls
with st.sidebar:
    st.title("🐘 Tamil Theni Controls")
    if st.session_state.running:
        if st.button("⏹ Stop Practice"):
            st.session_state.running = False
            st.rerun()
    st.write(f"Images Mapped: {len(valid_names)}")

if not st.session_state.running:
    st.title("🐘 Tamil Theni Flashcards")
    st.success(f"Ready to start with {len(valid_names)} images.")
    if st.button("🚀 Start Practice"):
        st.session_state.running = True
        st.rerun()
else:
    # --- PRACTICING LOGIC ---
    # Instead of a while loop, we run this block ONCE and then rerun the script.
    ai_result = get_ai_pairing(valid_names)
    
    if ai_result:
        w1, w2, sentence = [s.strip().lower() for s in ai_result]
        
        if w1 in image_map and w2 in image_map:
            # Container for the current flashcard
            card_container = st.empty()
            
            # Phase 1: 8-second Preview
            for i in range(8, 0, -1):
                with card_container.container():
                    st.write(f"### Next pair in {i}s...")
                    c1, c2 = st.columns(2)
                    c1.image(os.path.join(IMAGE_PATH, image_map[w1]), use_container_width=True)
                    c1.markdown(f"<h2 style='text-align:center;'>{w1.upper()}</h2>", unsafe_allow_html=True)
                    c2.image(os.path.join(IMAGE_PATH, image_map[w2]), use_container_width=True)
                    c2.markdown(f"<h2 style='text-align:center;'>{w2.upper()}</h2>", unsafe_allow_html=True)
                time.sleep(1)

            # Phase 2: 4-second Lesson
            with card_container.container():
                st.markdown(f"<div style='background:#fdfd96; padding:30px; border-radius:15px; text-align:center;'><h1>{sentence}</h1></div>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.image(os.path.join(IMAGE_PATH, image_map[w1]), use_container_width=True)
                c2.image(os.path.join(IMAGE_PATH, image_map[w2]), use_container_width=True)
                speak_tamil(sentence)
            time.sleep(4)
            
            # TRIGGER NEXT LOOP
            st.rerun()
        else:
            # If AI picks a word we don't have, rerun immediately to try again
            st.rerun()
    else:
        st.error("AI was unable to generate a pair. Retrying...")
        time.sleep(2)
        st.rerun()