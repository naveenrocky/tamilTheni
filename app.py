import streamlit as st
import pandas as pd
import random
import time
import os
import hmac
import base64
import re
from openai import OpenAI
from gtts import gTTS

# --- 1. CONFIGURATION & SECRETS ---
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
APP_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]

client = OpenAI(api_key=OPENAI_API_KEY)

# Ensure folder names match your GitHub repo exactly
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
    fallback_vocab = ["nose.png", "ear.png", "hair.png", "thigh.png", "head.png", "hand.png", "tongue.png", "neck.png", "leg.png", "lip.png"]
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

# --- 4. IMAGE SYNCING ---
if not os.path.exists(IMAGE_PATH):
    st.error(f"Folder '{IMAGE_PATH}' not found. Please check your GitHub repository.")
    st.stop()

# Get all files and map them (handling case sensitivity)
all_files = [f for f in os.listdir(IMAGE_PATH) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
image_map = {os.path.splitext(f)[0].strip().lower(): f for f in all_files}

vocab = load_vocabulary(EXCEL_FILE_NAME)
valid_names = [v for v in vocab if v in image_map]

# --- 5. UI & LESSON LOOP ---
if "running" not in st.session_state: 
    st.session_state.running = False

with st.sidebar:
    st.title("🐘 Tamil Theni Settings")
    if st.session_state.running:
        if st.button("⏹ Stop Practice"):
            st.session_state.running = False
            st.rerun()
    st.write(f"Total Images Linked: {len(valid_names)}")
    with st.expander("Show Detected Files"):
        st.write(list(image_map.keys()))

if not st.session_state.running:
    st.title("🐘 Tamil Theni AI Flashcards")
    st.info("AI will generate logical Tamil sentences based on your uploaded images.")
    if st.button("🚀 Start 15s Practice"):
        st.session_state.running = True
        st.rerun()
else:
    # Get AI Result
    with st.spinner("AI is pairing items..."):
        ai_result = get_ai_pairing(valid_names)

    if ai_result:
        w1, w2, sentence = ai_result
        
        # Verification: Only display if both images truly exist in our map
        if w1 in image_map and w2 in image_map:
            card_placeholder = st.empty()
            
            # PHASE 1: 15-second Preview (with countdown)
            for i in range(15, 0, -1):
                with card_placeholder.container():
                    st.markdown(f"<h3 style='text-align: center;'>Next Lesson in {i}s...</h3>", unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    
                    # Fetching images using the mapped filename to handle case sensitivity
                    img1_path = os.path.join(IMAGE_PATH, image_map[w1])
                    img2_path = os.path.join(IMAGE_PATH, image_map[w2])
                    
                    col1.image(img1_path, caption=w1.upper(), use_container_width=True)
                    col2.image(img2_path, caption=w2.upper(), use_container_width=True)
                time.sleep(1)

            # PHASE 2: 5-second Audio Lesson
            with card_placeholder.container():
                st.markdown(f"""
                    <div style='background-color: #fdfd96; padding: 40px; border-radius: 20px; text-align: center; border: 5px solid #FFD700;'>
                        <h1 style='font-size: 50px; color: #333;'>{sentence}</h1>
                    </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                col1.image(os.path.join(IMAGE_PATH, image_map[w1]), use_container_width=True)
                col2.image(os.path.join(IMAGE_PATH, image_map[w2]), use_container_width=True)
                
                speak_tamil(sentence)
                time.sleep(5) # Give time for audio to finish
            
            st.rerun()
        else:
            # If AI picks a word we don't have, rerun immediately
            st.rerun()
    else:
        st.warning("AI had trouble finding a pair. Retrying...")
        time.sleep(2)
        st.rerun()