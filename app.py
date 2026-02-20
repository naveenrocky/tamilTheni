import streamlit as st
import pandas as pd
import random
import time
import os
import hmac
from openai import OpenAI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. CONFIGURATION & SECRETS ---
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
APP_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]

client = OpenAI(api_key=OPENAI_API_KEY)

IMAGE_PATH = "images" 
EXCEL_FILE_NAME = "TT2026-Word-List-Theni-1_2_3_4 conv.xlsx"

st.set_page_config(page_title="Tamil Theni - Level 2", page_icon="🐘", layout="wide")

# Custom CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;700&display=swap');
        body, h1, h2, h3, p, div { font-family: 'Noto Sans Tamil', sans-serif !important; color: #333; }
        .stMarkdown h1 { font-size: 60px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SECURITY ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    st.title("🔐 Tamil Theni - Level 2")
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

# --- 3. DATA LOADING & AI LOGIC ---

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
    except Exception as e:
        return fallback_vocab

def get_ai_pairing(valid_names):
    if len(valid_names) < 2: return None
    sample = random.sample(valid_names, min(len(valid_names), 30))
    prompt = f"Pick 2 related words from {sample}. Format: word1 | word2"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a Tamil teacher. Use pipe | separator."},
                      {"role": "user", "content": prompt}],
            timeout=10
        )
        content = response.choices[0].message.content
        parts = [p.strip() for p in content.split("|")]
        if len(parts) == 2 and parts[0] in valid_names and parts[1] in valid_names:
            return parts
        return None
    except Exception:
        return None

def load_image_as_bytes(img_path):
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as img_file: return img_file.read()
    except Exception: return None

# --- NEW: ENTERPRISE COMBINATION GENERATOR ---
@st.cache_data
def generate_all_combinations(word_list):
    """Processes 400+ words in chunks to generate a massive list of logical pairs."""
    all_pairs = []
    chunk_size = 50 
    chunks = [word_list[i:i + chunk_size] for i in range(0, len(word_list), chunk_size)]
    
    progress_bar = st.progress(0, text="Analyzing 400+ words...")
    
    for i, chunk in enumerate(chunks):
        prompt = f"Using these words: {chunk}, create as many logical pairs as possible for kids' sentences. Format: Word A | Word B | Category"
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Only return pipe-separated values: word|word|category"},
                          {"role": "user", "content": prompt}]
            )
            lines = response.choices[0].message.content.strip().split('\n')
            all_pairs.extend([line for line in lines if "|" in line])
        except: continue
        progress_bar.progress((i + 1) / len(chunks))
    
    progress_bar.empty()
    return all_pairs

# --- 4. IMAGE SYNCING ---
image_map = {}
if os.path.exists(IMAGE_PATH):
    for root, _, files in os.walk(IMAGE_PATH):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                base_name = os.path.splitext(f)[0].strip().lower()
                image_map[base_name] = os.path.relpath(os.path.join(root, f), IMAGE_PATH)

valid_names = list(image_map.keys())

# --- 5. UI NAVIGATION ---
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Game"

with st.sidebar:
    st.title("🐘 Control Panel")
    if st.button("🚀 Start Practice Game", use_container_width=True):
        st.session_state.view_mode = "Game"
    if st.button("📚 View All Word Pairs", use_container_width=True):
        st.session_state.view_mode = "Combinations"
    st.divider()
    st.write(f"Images Found: {len(valid_names)}")

# --- PAGE 1: ALL COMBINATIONS ---
if st.session_state.view_mode == "Combinations":
    st.title("📚 Comprehensive Word Combinations")
    st.write("This list displays all logical pairings possible from your 400+ word library.")
    
    if st.button("Clear Cache & Regenerate"):
        st.cache_data.clear()
        st.rerun()

    raw_pairs = generate_all_combinations(valid_names)
    parsed = []
    for p in raw_pairs:
        parts = p.split("|")
        if len(parts) >= 2:
            parsed.append({"Word 1": parts[0].strip(), "Word 2": parts[1].strip(), "Category": parts[2].strip() if len(parts)>2 else "General"})
    
    df = pd.DataFrame(parsed)
    st.dataframe(df, use_container_width=True, height=600)
    st.download_button("Download CSV", df.to_csv(index=False), "word_pairs.csv", "text/csv")
    st.stop()

# --- PAGE 2: EXISTING PRACTICE LOGIC (UNTOUCHED) ---
if "running" not in st.session_state: st.session_state.running = False
if "paused" not in st.session_state: st.session_state.paused = False
if "pair_count" not in st.session_state: st.session_state.pair_count = 0
if "session_valid_names" not in st.session_state: st.session_state.session_valid_names = []
if "current_pair" not in st.session_state: st.session_state.current_pair = None
if "display_start_time" not in st.session_state: st.session_state.display_start_time = None

if not st.session_state.running:
    st.title("🐘 Tamil Theni - Level 2")
    if st.button("🚀 Start Practice"):
        st.session_state.running = True
        st.session_state.pair_count = 0
        st.session_state.session_valid_names = random.sample(valid_names, len(valid_names))
        st.rerun()
else:
    # Game Loop Logic exactly as per your working version...
    if st.session_state.pair_count >= 20:
        st.success("Completed 20 sets!")
        st.session_state.running = False
        st.rerun()

    if st.session_state.current_pair is None:
        with st.spinner("AI is pairing..."):
            ai_result = get_ai_pairing(st.session_state.session_valid_names)
            if ai_result:
                w1, w2 = ai_result
                st.session_state.current_pair = (w1, w2)
                st.session_state.display_start_time = time.time()
                st.rerun()
    else:
        w1, w2 = st.session_state.current_pair
        img1_bytes = load_image_as_bytes(os.path.join(IMAGE_PATH, image_map[w1]))
        img2_bytes = load_image_as_bytes(os.path.join(IMAGE_PATH, image_map[w2]))
        
        elapsed = time.time() - st.session_state.display_start_time
        remaining = max(0, 15 - int(elapsed))
        st.markdown(f"<h3 style='text-align: center;'>Answer in {remaining}s...</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        if img1_bytes: col1.image(img1_bytes, caption=w1.upper())
        if img2_bytes: col2.image(img2_bytes, caption=w2.upper())

        if elapsed >= 15:
            st.session_state.pair_count += 1
            st.session_state.current_pair = None
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()