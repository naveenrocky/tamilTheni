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

# Custom CSS for clear Tamil fonts and sentence styling
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;700&display=swap');
        body, h1, h2, h3, p, div {
            font-family: 'Noto Sans Tamil', sans-serif !important;
            color: #333;
        }
        .tamil-sentence-box {
            background-color: #f0f9f0;
            border-left: 10px solid #2E7D32;
            padding: 20px;
            font-size: 32px !important;
            font-weight: bold;
            text-align: center;
            border-radius: 10px;
            margin: 20px 0;
            color: #1b5e20;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
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

# --- 3. CORE LOGIC & AI (ENHANCED) ---

# Pure Tamil & Simple Sentence Instructions
KIDS_AI_INSTRUCTIONS = """You are a Kindergarten Tamil Teacher. 
1. Use ONLY Pure Tamil words. Never use English words written in Tamil (e.g., use 'உடல்', NOT 'பாடி').
2. MANDATORY: The sentence MUST include ALL the words provided in the pair/triplet.
3. SIMPLICITY: Sentences must be 3 to 5 words long. Use basic Subject-Object-Verb structure.
4. Categories: Mix categories (e.g., Animal + Fruit) to make it interesting."""

def get_ai_pairing(valid_names):
    """Fetches creative cross-category pairings and a suggested sentence."""
    if len(valid_names) < 2: return None
    sample = random.sample(valid_names, min(len(valid_names), 50))
    
    prompt = f"Vocabulary: {sample}. Pick 2 or 3 words and form a VERY SIMPLE Pure Tamil sentence using ALL of them. Format: word1, word2 | Tamil Sentence"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Upgraded to gpt-4o for better constraint following
            messages=[{"role": "system", "content": KIDS_AI_INSTRUCTIONS},
                      {"role": "user", "content": prompt}],
            timeout=15
        )
        content = response.choices[0].message.content
        parts = content.split("|")
        words = [w.strip().lower() for w in parts[0].split(",")]
        sentence = parts[1].strip() if len(parts) > 1 else ""
        
        confirmed_words = [w for w in words if w in valid_names]
        if len(confirmed_words) >= 2:
            return confirmed_words, sentence
        return None
    except Exception as e:
        logging.error(f"AI Pairing Error: {e}")
        return None

@st.cache_data
def generate_all_combinations(word_list):
    """Generates a massive comprehensive list of cross-category connections."""
    all_results = []
    chunk_size = 30 
    chunks = [word_list[i:i + chunk_size] for i in range(0, len(word_list), chunk_size)]
    
    progress_bar = st.progress(0, text="Generating 1000+ Simple Pure Tamil Combinations...")
    
    for i, chunk in enumerate(chunks):
        prompt = f"Words: {chunk}. Create as many simple cross-category pairs as possible. Every sentence MUST use BOTH words and be very simple (3-5 words). Format: Word1, Word2 | Sentence"
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": KIDS_AI_INSTRUCTIONS},
                          {"role": "user", "content": prompt}]
            )
            lines = response.choices[0].message.content.strip().split('\n')
            all_results.extend([line for line in lines if "|" in line])
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
    if st.button("📚 Teacher's Guide (All Pairs)", use_container_width=True):
        st.session_state.view_mode = "Combinations"
        st.rerun()
    st.divider()
    st.write(f"Total Images: {len(valid_names)}")

# --- PAGE: COMBINATIONS LIST ---
if st.session_state.view_mode == "Combinations":
    st.title("📚 Teachers' Simple Sentence Guide")
    st.write("Comprehensive list of Pure Tamil simple sentences (3-5 words) using your library.")
    
    if st.button("🔄 Refresh / Regenerate List"):
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
    st.download_button("📥 Download as CSV", df.to_csv(index=False), "Tamil_Theni_Guide.csv")
    st.stop()

# --- PAGE: PRACTICE GAME ---
if "running" not in st.session_state: st.session_state.running = False
if "pair_count" not in st.session_state: st.session_state.pair_count = 0
if "current_pair" not in st.session_state: st.session_state.current_pair = None
if "current_sentence" not in st.session_state: st.session_state.current_sentence = ""
if "display_start_time" not in st.session_state: st.session_state.display_start_time = None

if not st.session_state.running:
    st.title("🐘 Tamil Theni - Level 2")
    if st.button("🚀 Start Practice"):
        st.session_state.running = True
        st.session_state.pair_count = 0
        st.rerun()
else:
    if st.session_state.pair_count >= 20:
        st.success("Practice Session Complete!")
        st.session_state.running = False
        st.rerun()

    if st.session_state.current_pair is None:
        with st.spinner("AI is thinking of a simple connection..."):
            result = get_ai_pairing(valid_names)
            if result:
                st.session_state.current_pair, st.session_state.current_sentence = result
                st.session_state.display_start_time = time.time()
                st.rerun()
    else:
        words = st.session_state.current_pair
        
        # Display simplified sentence box
        st.markdown(f"<div class='tamil-sentence-box'>{st.session_state.current_sentence}</div>", unsafe_allow_html=True)
        
        cols = st.columns(len(words))
        for idx, w in enumerate(words):
            img_path = os.path.join(IMAGE_PATH, image_map[w])
            with open(img_path, "rb") as f:
                cols[idx].image(f.read(), caption=w.upper(), use_container_width=True)
        
        elapsed = time.time() - st.session_state.display_start_time
        remaining = max(0, 15 - int(elapsed))
        st.write(f"Next set in: {remaining}s")
        
        if elapsed >= 15:
            st.session_state.pair_count += 1
            st.session_state.current_pair = None
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()