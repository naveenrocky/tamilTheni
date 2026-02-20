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

# Custom CSS for UI layout
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;700&display=swap');
        body, h1, h2, h3, p, div {
            font-family: 'Noto Sans Tamil', sans-serif !important;
        }
        .timer-header {
            text-align: center;
            font-size: 26px;
            font-weight: bold;
            color: #d32f2f;
            background-color: #fff5f5;
            padding: 10px;
            border-radius: 50px;
            width: 300px;
            margin: 0 auto 20px auto;
            border: 2px solid #ffcdd2;
        }
        .tamil-sentence-box {
            background-color: #f0f9f0;
            border-left: 10px solid #2E7D32;
            padding: 25px;
            font-size: 36px !important;
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

# --- 3. AI LOGIC & INSTRUCTIONS ---
KIDS_AI_INSTRUCTIONS = """You are a Kindergarten Tamil Teacher. 
1. Use ONLY Pure Tamil words (e.g., 'உடல்' not 'பாடி').
2. MANDATORY: The sentence MUST include ALL provided words.
3. SIMPLICITY: Use ONLY 3-5 words in Subject-Object-Verb structure.
4. STRICT: No unrelated words (like fire, fan, apple) at the end. Only the sentence."""

def get_ai_pairing(valid_names):
    if len(valid_names) < 2: return None
    sample = random.sample(valid_names, min(len(valid_names), 50))
    prompt = f"Words: {sample}. Pick 2 words. Format: word1, word2 | Simple Tamil Sentence"
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "system", "content": KIDS_AI_INSTRUCTIONS}, {"role": "user", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        if "|" in content:
            parts = content.split("|")
            words = [w.strip().lower() for w in parts[0].split(",")]
            sentence = parts[1].split('\n')[0].strip()
            return words, sentence
    except: return None

@st.cache_data
def generate_all_combinations(word_list):
    all_results = []
    chunk_size = 30
    progress_bar = st.progress(0, text="Generating All Possible Combinations...")
    for i in range(0, len(word_list), chunk_size):
        chunk = word_list[i:i + chunk_size]
        prompt = f"Words: {chunk}. Create all logical pairs. Format: Word1, Word2 | Sentence."
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": KIDS_AI_INSTRUCTIONS}, {"role": "user", "content": prompt}],
                temperature=0.3
            )
            all_results.extend([l for l in response.choices[0].message.content.strip().split('\n') if "|" in l])
        except: continue
        progress_bar.progress(min((i + chunk_size) / len(word_list), 1.0))
    progress_bar.empty()
    return all_results

# --- 4. IMAGE LOADING (FIXED & RESTORED) ---
image_map = {}
if os.path.exists(IMAGE_PATH):
    for root, dirs, files in os.walk(IMAGE_PATH):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Store the key as the lowercase filename without extension
                name_key = os.path.splitext(f)[0].strip().lower()
                # Store the full path relative to IMAGE_PATH
                image_map[name_key] = os.path.join(root, f)

valid_names = sorted(list(image_map.keys()))

# --- 5. UI NAVIGATION ---
if "view_mode" not in st.session_state: st.session_state.view_mode = "Practice"

with st.sidebar:
    st.title("🐘 Tamil Theni Control")
    if st.button("🚀 Practice Game", use_container_width=True): 
        st.session_state.view_mode = "Practice"
        st.rerun()
    if st.button("📚 Teacher's Guide", use_container_width=True): 
        st.session_state.view_mode = "Combinations"
        st.rerun()
    st.divider()
    st.info(f"Library: {len(valid_names)} Images")

# --- PAGE: COMBINATIONS LIST ---
if st.session_state.view_mode == "Combinations":
    st.title("📚 Teachers' Master Curriculum")
    if st.button("🔄 Regenerate All"):
        st.cache_data.clear()
        st.rerun()
    raw_pairs = generate_all_combinations(valid_names)
    df = pd.DataFrame([{"Words": p.split("|")[0].upper(), "Sentence": p.split("|")[1]} for p in raw_pairs if "|" in p])
    st.dataframe(df, use_container_width=True, height=700)
    st.stop()

# --- PAGE: PRACTICE GAME ---
if "running" not in st.session_state: st.session_state.running = False
if "current_pair" not in st.session_state: st.session_state.current_pair = None

if not st.session_state.running:
    st.title("🐘 Tamil Theni - Level 2")
    if st.button("🚀 Start Unlimited Practice"):
        st.session_state.running = True
        st.session_state.current_pair = None
        st.rerun()
else:
    # 1. Timer Displayed at the Top
    if st.session_state.current_pair:
        elapsed = time.time() - st.session_state.display_start_time
        remaining = max(0, 15 - int(elapsed))
        st.markdown(f"<div class='timer-header'>Next set in: {remaining}s</div>", unsafe_allow_html=True)

    if st.session_state.current_pair is None:
        with st.spinner("AI is forming a connection..."):
            result = get_ai_pairing(valid_names)
            if result:
                st.session_state.current_pair, st.session_state.current_sentence = result
                st.session_state.display_start_time = time.time()
                st.rerun()
    else:
        # 2. Main Practice UI
        st.markdown(f"<div class='tamil-sentence-box'>{st.session_state.current_sentence}</div>", unsafe_allow_html=True)
        
        words = st.session_state.current_pair
        cols = st.columns(len(words))
        for idx, w in enumerate(words):
            if w in image_map:
                img_path = image_map[w] # This now contains the full correct path
                try:
                    with open(img_path, "rb") as f:
                        cols[idx].image(f.read(), caption=w.upper(), use_container_width=True)
                except Exception as e:
                    cols[idx].error(f"Error loading {w}")
            else:
                cols[idx].warning(f"Image not found: {w}")
        
        # 3. Auto-Refresh Logic
        if elapsed >= 15:
            st.session_state.current_pair = None
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()