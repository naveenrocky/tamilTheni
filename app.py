import streamlit as st
import pandas as pd
import random
import time
import os
import hmac
import base64
from openai import OpenAI
from gtts import gTTS

# --- CONFIGURATION & SECRETS ---
# Ensure these are set in Streamlit Cloud -> Settings -> Secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
APP_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]

client = OpenAI(api_key=OPENAI_API_KEY)

# UPDATED PATHS TO MATCH YOUR GITHUB REPO
IMAGE_PATH = "images" 
EXCEL_FILE_NAME = "TT2026-Word-List-Theni-1_2_3_4_Extracted.xlsx"
EXCEL_FULL_PATH = EXCEL_FILE_NAME # Located in the main folder

st.set_page_config(page_title="Tamil Theni AI", page_icon="🐘", layout="wide")

# --- SECURITY: Password Protection ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔐 Tamil Theni Private Access")
    pwd = st.text_input("Enter Access Password", type="password")
    if st.button("Sign In"):
        if hmac.compare_digest(pwd, APP_PASSWORD): # Secure comparison
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Access Denied.")
    return False

if not check_password():
    st.stop()

# --- DATA LOADING ---
@st.cache_data
def load_vocabulary(file_path):
    try:
        if not os.path.exists(file_path):
            st.error(f"Excel file not found at: {file_path}")
            return []
        df = pd.read_excel(file_path, engine='openpyxl')
        # Extracting words from columns 1 and 6 as per your original logic
        all_words = df.iloc[:, [1, 6]].values.flatten()
        return list(set([str(w).strip().lower() for w in all_words if len(str(w)) > 2]))
    except Exception as e:
        st.error(f"Error loading Excel data: {e}")
        return []

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
        return parts if len(parts) == 3 else ["eye", "face", "கண்ணால் முகத்தைப் பார்."]
    except:
        return ["eye", "face", "கண்ணால் முகத்தைப் பார்."]

def speak_tamil(text):
    try:
        tts = gTTS(text=text, lang='ta')
        tts.save("temp_voice.mp3")
        with open("temp_voice.mp3", "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    except: pass

# --- APP UI ---
if "running" not in st.session_state: 
    st.session_state.running = False

st.sidebar.title("🐘 Settings")
if st.session_state.running:
    if st.sidebar.button("⏹ Stop Practice"):
        st.session_state.running = False
        st.rerun()

if not st.session_state.running:
    st.title("🐘 Tamil Theni Flashcards")
    if st.button("🚀 Start Lesson"):
        st.session_state.running = True
        st.rerun()
else:
    # Validate image directory exists in GitHub repo
    if not os.path.exists(IMAGE_PATH):
        st.error(f"The folder '{IMAGE_PATH}' was not found. Please ensure it is pushed to GitHub.")
        st.stop()
        
    all_files = [f for f in os.listdir(IMAGE_PATH) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    image_map = {os.path.splitext(f)[0].lower(): f for f in all_files}
    vocab = load_vocabulary(EXCEL_FULL_PATH)
    valid_names = [v for v in vocab if v in image_map]

    if not valid_names:
        st.error("No matches found between Excel words and image filenames.")
        st.stop()

    display = st.empty()
    while st.session_state.running:
        w1, w2, sentence = get_ai_pairing(valid_names)
        
        # 8s Timer Loop
        for i in range(8, 0, -1):
            with display.container():
                st.write(f"### Next pair in {i}s...")
                c1, c2 = st.columns(2)
                c1.image(os.path.join(IMAGE_PATH, image_map[w1]), use_container_width=True)
                c1.markdown(f"<h1 style='text-align:center;'>{w1.upper()}</h1>", unsafe_allow_html=True)
                c2.image(os.path.join(IMAGE_PATH, image_map[w2]), use_container_width=True)
                c2.markdown(f"<h1 style='text-align:center;'>{w2.upper()}</h1>", unsafe_allow_html=True)
            time.sleep(1)

        # 4s Audio Lesson
        with display.container():
            st.markdown(f"<div style='background:#fdfd96; padding:20px; border-radius:15px; text-align:center;'><h1>{sentence}</h1></div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.image(os.path.join(IMAGE_PATH, image_map[w1]), use_container_width=True)
            c2.image(os.path.join(IMAGE_PATH, image_map[w2]), use_container_width=True)
            speak_tamil(sentence)
        time.sleep(4)