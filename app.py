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
# Ensure these are in Streamlit Cloud -> Settings -> Secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
APP_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]

client = OpenAI(api_key=OPENAI_API_KEY)

# Repo paths
IMAGE_PATH = "images" 
EXCEL_FILE_NAME = "TT2026-Word-List-Theni-1_2_3_4_Extracted.xlsx"

st.set_page_config(page_title="Tamil Theni AI", page_icon="🐘", layout="wide")

# --- 2. SECURITY: Password Protection ---
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

# --- 3. DATA LOADING LOGIC ---
@st.cache_data
def load_vocabulary(file_path):
    # Hardcoded fallback list in case Excel is missing or has no matches
    fallback_vocab = ["elephant", "apple", "banana", "cat", "dog", "ant", "ball", "car", "egg", "fish"]
    
    if not os.path.exists(file_path):
        return fallback_vocab
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        all_words = df.iloc[:, [1, 6]].values.flatten()
        extracted = list(set([str(w).strip().lower() for w in all_words if len(str(w)) > 2]))
        return extracted if len(extracted) > 0 else fallback_vocab
    except Exception as e:
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
    st.error(f"❌ Folder '{IMAGE_PATH}' not found in the repository root.")
    st.stop()

# Build the map: { "elephant": "Elephant.png" }
all_files = [f for f in os.listdir(IMAGE_PATH) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
image_map = {os.path.splitext(f)[0].strip().lower(): f for f in all_files}

# Load Vocab and filter for existing images
vocab = load_vocabulary(EXCEL_FILE_NAME)
valid_names = [v for v in vocab if v in image_map]

# Sidebar Debugging
with st.sidebar:
    st.title("🐘 System Status")
    with st.expander("🛠 Developer Logs"):
        st.write(f"Files in /images: {len(all_files)}")
        st.write(f"Matches found: {len(valid_names)}")
        st.write("Image Keys:", list(image_map.keys()))

# --- 5. APP UI ---
if "running" not in st.session_state: 
    st.session_state.running = False

if st.session_state.running:
    if st.sidebar.button("⏹ Stop Practice"):
        st.session_state.running = False
        st.rerun()

if not st.session_state.running:
    st.title("🐘 Tamil Theni Flashcards")
    st.success(f"System Ready: {len(valid_names)} images mapped successfully.")
    if st.button("🚀 Start Practice"):
        st.session_state.running = True
        st.rerun()
else:
    if len(valid_names) < 2:
        st.error("Not enough matching images found. Check the sidebar logs.")
        st.stop()

    display = st.empty()
    while st.session_state.running:
        ai_result = get_ai_pairing(valid_names)
        
        if ai_result:
            w1, w2, sentence = [s.strip().lower() for s in ai_result]
            
            # Double check keys exist to prevent KeyError
            if w1 in image_map and w2 in image_map:
                # 8s Preview
                for i in range(8, 0, -1):
                    with display.container():
                        st.write(f"### Next pair in {i}s...")
                        c1, c2 = st.columns(2)
                        c1.image(os.path.join(IMAGE_PATH, image_map[w1]), use_container_width=True)
                        c1.markdown(f"<h2 style='text-align:center;'>{w1.upper()}</h2>", unsafe_allow_html=True)
                        c2.image(os.path.join(IMAGE_PATH, image_map[w2]), use_container_width=True)
                        c2.markdown(f"<h2 style='text-align:center;'>{w2.upper()}</h2>", unsafe_allow_html=True)
                    time.sleep(1)

                # 4s Audio Lesson
                with display.container():
                    st.markdown(f"<div style='background:#fdfd96; padding:30px; border-radius:15px; text-align:center;'><h1>{sentence}</h1></div>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    c1.image(os.path.join(IMAGE_PATH, image_map[w1]), use_container_width=True)
                    c2.image(os.path.join(IMAGE_PATH, image_map[w2]), use_container_width=True)
                    speak_tamil(sentence)
                time.sleep(4)
            else:
                continue
        else:
            time.sleep(1)