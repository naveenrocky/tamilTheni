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
st.set_page_config(page_title="Tamil Theni - Level 2", page_icon="🐘", layout="wide")

# Custom CSS for clear Tamil fonts, sentence styling, and top-timer
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;700&display=swap');
        body, h1, h2, h3, p, div {
            font-family: 'Noto Sans Tamil', sans-serif !important;
            color: #333;
        }
        .timer-container {
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            color: #d32f2f;
            background-color: #fff5f5;
            padding: 10px;
            border-radius: 50px;
            width: 250px;
            margin: 0 auto 20px auto;
            border: 2px solid #ffcdd2;
        }
        .tamil-sentence-box {
            background-color: #f0f9f0;
            border-left: 10px solid #2E7D32;
            padding: 25px;
            font-size: 38px !important;
            font-weight: bold;
            text-align: center;
            border-radius: 15px;
            margin-bottom: 30px;
            color: #1b5e20;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
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

# --- 3. CORE LOGIC & AI INSTRUCTIONS ---

KIDS_AI_INSTRUCTIONS = """You are a Kindergarten Tamil Teacher. 
1. Use ONLY Pure Tamil words. Never use English words written in Tamil (e.g., use 'உடல்', NOT 'பாடி').
2. MANDATORY: The sentence MUST include ALL the words provided in the list.
3. SIMPLICITY: Sentences must be 3 to 5 words long. Use basic Subject-Object-Verb structure.
4. STRICT RULE: DO NOT include any unrelated English words (like 'fire', 'fan', 'apple') at the end. Only return the requested format.
"""

def get_ai_pairing(valid_names):
    if len(valid_names) < 2: return None
    sample = random.sample(valid_names, min(len(valid_names), 50))
    prompt = f"Vocabulary: {sample}. Pick 2 or 3 words and form a VERY SIMPLE Pure Tamil sentence using ALL of them. Format: word1, word2 | Tamil Sentence"
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "system", "content": KIDS_AI_INSTRUCTIONS},
                      {"role": "user", "content": prompt}],
            timeout=15,
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        if "|" in content:
            parts = content.split("|")
            words_raw = parts[0].strip()
            sentence_part = parts[1].split('\n')[0].strip()
            words = [w.strip().lower() for w in words_raw.split(",")]
            confirmed_words = [w for w in words if w in valid_names]
            if len(confirmed_words) >= 2:
                return confirmed_words, sentence_part
        return None
    except Exception as e:
        logging.error(f"AI Pairing Error: {e}")
        return None

@st.cache_data
def generate_all_combinations(word_list):
    all_results = []
    chunk_size = 30 
    chunks = [word_list[i:i + chunk_size] for i in range(0, len(word_list), chunk_size)]
    progress_bar = st.progress(0, text="Generating Combinations...")
    for i, chunk in enumerate(chunks):
        prompt = f"Words: {chunk}. Create simple pairs. Format: Word1, Word2 | Sentence."
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": KIDS_AI_INSTRUCTIONS},
                          {"role": "user", "content": prompt}],
                temperature=0.3
            )
            raw_lines = response.choices[0].message.content.strip().split('\n')
            all_results.extend([line.strip() for line in raw_lines if "|" in line])
        except: continue
        progress_bar.progress((i + 1) / len(chunks))
    progress_bar.empty()
    return all_results

# --- 4. IMAGE DATA LOADING ---
image_map = {}
if os.path.exists(IMAGE_PATH):
    for root, _, files in os.walk(IMAGE_PATH):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                base_name = os.path.splitext(f)[0].strip().lower()
                image_map[base_name] = os.path.relpath(os.path.join(root, f), IMAGE_PATH)

valid_names = sorted(list(image_map.keys()))

# --- 5. UI NAVIGATION STATE ---
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Practice"

with st.sidebar:
    st.title("🐘 Tamil Theni Control")
    if st.button("🚀 Practice Game", use_container_width=True):
        st.session_state.view_mode = "Practice"
        st.rerun()
    if st.button("📚 Teacher's Guide (Full List)", use_container_width=True):
        st.session_state.view_mode = "Combinations"
        st.rerun()
    st.divider()
    st.write(f"Total Images: {len(valid_names)}")

# --- PAGE: COMBINATIONS LIST ---
if st.session_state.view_mode == "Combinations":
    st.title("📚 Teachers' Simple Sentence Guide")
    if st.button("🔄 Regenerate List"):
        st.cache_data.clear()
        st.rerun()
    raw_pairs = generate_all_combinations(valid_names)
    parsed = []
    for p in raw_pairs:
        parts = p.split("|")
        if len(parts) == 2:
            parsed.append({"Vocabulary Pair": parts[0].strip().upper(), "Simple Tamil Sentence": parts[1].strip()})
    df = pd.DataFrame(parsed)
    st.dataframe(df, use_container_width=True, height=700)
    st.stop()

# --- PAGE: PRACTICE GAME ---
if "running" not in st.session_state: st.session_state.running = False
if "current_pair" not in st.session_state: st.session_state.current_pair = None

if not st.session_state.running:
    st.title("🐘 Tamil Theni - Level 2")
    if st.button("🚀 Start Practice"):
        st.session_state.running = True
        st.session_state.current_pair = None
        st.rerun()
else:
    # 1. Timer logic - TOP ONLY
    if st.session_state.current_pair:
        elapsed = time.time() - st.session_state.display_start_time
        remaining = max(0, 15 - int(elapsed))
        st.markdown(f"<div class='timer-container'>Next set in: {remaining}s</div>", unsafe_allow_html=True)
        
        if elapsed >= 15:
            st.session_state.current_pair = None
            st.rerun()

    # 2. Game Display
    if st.session_state.current_pair is None:
        with st.spinner("Preparing next set..."):
            result = get_ai_pairing(valid_names)
            if result:
                st.session_state.current_pair, st.session_state.current_sentence = result
                st.session_state.display_start_time = time.time()
                st.rerun()
    else:
        # Display simplified sentence box (Bigger font for kids)
        st.markdown(f"<div class='tamil-sentence-box'>{st.session_state.current_sentence}</div>", unsafe_allow_html=True)
        
        # Display Images ONLY (No captions, no vocabulary text)
        words = st.session_state.current_pair
        cols = st.columns(len(words))
        for idx, w in enumerate(words):
            if w in image_map:
                img_path = os.path.join(IMAGE_PATH, image_map[w])
                with open(img_path, "rb") as f:
                    # caption parameter is removed to hide text below image
                    cols[idx].image(f.read(), use_container_width=True)
        
        time.sleep(1)
        st.rerun()