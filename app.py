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
        .queue-counter {
            text-align: center;
            font-size: 16px;
            color: #555;
            margin-top: -10px;
            margin-bottom: 20px;
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

# --- 3. CORE LOGIC & AI INSTRUCTIONS (UPDATED FOR LOGIC) ---

KIDS_AI_INSTRUCTIONS = """You are a Kindergarten Tamil Teacher. 
1. LOGIC PRIORITY: Sentences MUST make 100% real-world sense. Do NOT write nonsense like 'an apple read a book' or 'age got an award'.
2. TRICK FOR UNRELATED WORDS: If two words are difficult to connect directly (like 'age' and 'award'), introduce a human subject (like 'சிறுவன்' [boy], 'பெண்' [girl], or 'மாணவன்' [student]) to connect them logically. Example: "அந்த வயது சிறுவன் விருது பெற்றான்" (That age boy got an award).
3. PURE TAMIL: Use only pure Tamil words. 
4. MANDATORY: The sentence MUST include all words provided in the list.
5. SIMPLICITY: Keep it less than 7 words in Subject-Object-Verb (SOV) structure.
6. NO EXTRA TEXT: Return ONLY 'word1, word2 | Tamil Sentence'. No extra English words like fire, fan at the end.
"""

@st.cache_data
def generate_all_combinations(word_list):
    """Generates the master curriculum. Cached so it only runs once."""
    all_results = []
    chunk_size = 20 # Smaller chunks to ensure AI doesn't skip words
    chunks = [word_list[i:i + chunk_size] for i in range(0, len(word_list), chunk_size)]
    
    progress_bar = st.progress(0, text="Generating Master Curriculum... Please wait.")
    
    for i, chunk in enumerate(chunks):
        # Stricter prompt to force usage of EVERY word while maintaining logic
        prompt = f"Words: {chunk}. Group these words into logical pairs and write a meaningful sentence for each pair. You MUST use EVERY word from the list at least once. Remember to use helper words (like boy/girl) if two words don't naturally fit together. Format: Word1, Word2 | Sentence."
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": KIDS_AI_INSTRUCTIONS},
                          {"role": "user", "content": prompt}],
                temperature=0.1
            )
            raw_lines = response.choices[0].message.content.strip().split('\n')
            all_results.extend([line.strip() for line in raw_lines if "|" in line])
        except Exception as e:
            logging.error(f"Generation error on chunk {i}: {e}")
            continue
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
if "view_mode" not in st.session_state: st.session_state.view_mode = "Practice"
if "practice_queue" not in st.session_state: st.session_state.practice_queue = []

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
    st.title("📚 Teachers' Meaningful Sentence Guide")
    if st.button("🔄 Regenerate List"):
        st.cache_data.clear()
        st.session_state.practice_queue = [] # Clear the queue if regenerating
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
    # 1. Timer logic
    if st.session_state.current_pair:
        elapsed = time.time() - st.session_state.display_start_time
        remaining = max(0, 15 - int(elapsed))
        st.markdown(f"<div class='timer-container'>Next set in: {remaining}s</div>", unsafe_allow_html=True)
        
        # Show progress to kids/parents
        queue_left = len(st.session_state.practice_queue)
        st.markdown(f"<div class='queue-counter'>Remaining in this cycle: {queue_left}</div>", unsafe_allow_html=True)
        
        if elapsed >= 15:
            st.session_state.current_pair = None
            st.rerun()

    # 2. Game Display Engine (Queue Based)
    if st.session_state.current_pair is None:
        
        # If queue is empty, load the master list, parse, shuffle, and fill the queue
        if len(st.session_state.practice_queue) == 0:
            with st.spinner("Preparing deck..."):
                raw_pairs = generate_all_combinations(valid_names)
                parsed_items = []
                for p in raw_pairs:
                    if "|" in p:
                        parts = p.split("|")
                        if len(parts) == 2:
                            words_raw = parts[0].strip()
                            sentence = parts[1].strip()
                            words = [w.strip().lower() for w in words_raw.split(",")]
                            # Validate words actually exist in our image library
                            confirmed = [w for w in words if w in valid_names]
                            if len(confirmed) >= 2:
                                parsed_items.append({"words": confirmed, "sentence": sentence})
                
                # Shuffle the deck so it's random every full cycle
                random.shuffle(parsed_items)
                st.session_state.practice_queue = parsed_items
                
                # Failsafe
                if not st.session_state.practice_queue:
                    st.error("Could not load sentences. Please check Teacher's Guide.")
                    st.stop()
        
        # Pop the next item from the queue
        next_item = st.session_state.practice_queue.pop(0)
        st.session_state.current_pair = next_item["words"]
        st.session_state.current_sentence = next_item["sentence"]
        st.session_state.display_start_time = time.time()
        st.rerun()
        
    else:
        # 3. Display meaningful sentence
        st.markdown(f"<div class='tamil-sentence-box'>{st.session_state.current_sentence}</div>", unsafe_allow_html=True)
        
        # Display Images with English Words
        words = st.session_state.current_pair
        cols = st.columns(len(words))
        for idx, w in enumerate(words):
            if w in image_map:
                img_path = os.path.join(IMAGE_PATH, image_map[w])
                with open(img_path, "rb") as f:
                    cols[idx].image(f.read(), caption=w.upper(), use_container_width=True)
        
        time.sleep(1)
        st.rerun()