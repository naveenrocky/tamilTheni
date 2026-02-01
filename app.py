import streamlit as st
import pandas as pd
import random
import time
import os
import hmac
import base64
from openai import OpenAI
from gtts import gTTS
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. CONFIGURATION & SECRETS ---
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
APP_PASSWORD = st.secrets["STREAMLIT_PASSWORD"]

client = OpenAI(api_key=OPENAI_API_KEY)

# Ensure folder names match your GitHub repo exactly
IMAGE_PATH = "images" 
EXCEL_FILE_NAME = "TT2026-Word-List-Theni-1_2_3_4 conv.xlsx"

st.set_page_config(page_title="Tamil Theni - Level 2", page_icon="🐘", layout="wide")

# Custom CSS for clear Tamil fonts
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;700&display=swap');
        body, h1, h2, h3, p, div {
            font-family: 'Noto Sans Tamil', sans-serif !important;
            color: #333;
        }
        .stMarkdown h1 {
            font-size: 60px !important;
        }
    </style>
""", unsafe_allow_html=True)

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
        logging.warning(f"Vocabulary file not found: {file_path}")
        return fallback_vocab
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        all_words = df.iloc[:, [1, 6]].values.flatten()
        extracted = list(set([str(w).strip().lower() for w in all_words if len(str(w)) > 2]))
        logging.info(f"Loaded {len(extracted)} words from vocabulary")
        return extracted if len(extracted) > 0 else fallback_vocab
    except Exception as e:
        logging.exception("Error loading vocabulary")
        return fallback_vocab

def get_ai_pairing(valid_names):
    if len(valid_names) < 2:
        logging.warning("Fewer than 2 valid names available for pairing")
        return None
    sample = random.sample(valid_names, min(len(valid_names), 30))
    if len(sample) < 2:
        return None
    prompt = f"Pick 2 related words from {sample} that belong to similar categories (e.g., body parts, animals, colors, food, vehicles, nature, etc.). Choose words that can logically connect in a simple context for kids. Then, write a simple 4-word Tamil sentence using both words, teaching basic vocabulary or relations in an engaging way for children. Ensure the sentence is grammatically correct and easy to understand. Format: word1 | word2 | sentence"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a Tamil teacher for kids. Always pick similar category words and use pipe | separator."},
                      {"role": "user", "content": prompt}],
            timeout=10
        )
        content = response.choices[0].message.content
        logging.info(f"AI response: {content}")
        parts = [p.strip() for p in content.split("|")]
        if len(parts) == 3 and parts[0] in valid_names and parts[1] in valid_names:
            return parts
        else:
            logging.warning("Invalid AI response format or words not in valid names")
            return None
    except Exception as e:
        logging.exception("Error in AI pairing")
        return None

def speak_tamil(text):
    try:
        tts = gTTS(text=text, lang='ta')
        tts.save("temp_voice.mp3")
        with open("temp_voice.mp3", "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    except Exception as e:
        logging.exception("Error in speech synthesis")
        pass

def load_image_as_bytes(img_path):
    try:
        if os.path.exists(img_path):
            logging.info(f"Loading image: {img_path}")
            with open(img_path, "rb") as img_file:
                return img_file.read()
        else:
            logging.warning(f"Image path does not exist: {img_path}")
            return None
    except Exception as e:
        logging.exception(f"Error loading image {img_path}")
        return None

# --- 4. IMAGE SYNCING ---
if not os.path.exists(IMAGE_PATH):
    logging.error(f"Image folder not found: {IMAGE_PATH}")
    st.error(f"Folder '{IMAGE_PATH}' not found. Please check your GitHub repository.")
    st.stop()

# Get all files and map them (handling case sensitivity)
try:
    all_files = [f for f in os.listdir(IMAGE_PATH) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    image_map = {os.path.splitext(f)[0].strip().lower(): f for f in all_files}
    logging.info(f"Found {len(all_files)} image files: {all_files}")
except Exception as e:
    logging.exception("Error listing image files")
    st.error("Error accessing image folder.")
    st.stop()

# Load vocab from Excel if possible, else fallback to image base names
vocab = list(image_map.keys())  # Start with image names as base
if os.path.exists(EXCEL_FILE_NAME):
    excel_vocab = load_vocabulary(EXCEL_FILE_NAME)
    vocab = list(set(vocab + [v for v in excel_vocab if v in image_map]))  # Merge matching Excel words
else:
    logging.warning(f"Excel file not found: {EXCEL_FILE_NAME}. Using image names only.")

valid_names = list(set(vocab))  # Unique
logging.info(f"Valid names for pairing: {valid_names}")

if len(valid_names) == 0:
    logging.error("No valid images or matching vocabulary found.")
    st.error("No images or matching vocabulary found. Add images to 'images' folder.")
    st.stop()

# --- 5. UI & LESSON LOOP ---
if "running" not in st.session_state:
    st.session_state.running = False
if "paused" not in st.session_state:
    st.session_state.paused = False
if "retry_count" not in st.session_state:
    st.session_state.retry_count = 0
if "pair_count" not in st.session_state:
    st.session_state.pair_count = 0
if "session_valid_names" not in st.session_state:
    st.session_state.session_valid_names = []

with st.sidebar:
    st.title("🐘 Tamil Theni Settings")
    st.write(f"Total Images Linked: {len(valid_names)}")
    if st.session_state.running:
        if st.button("⏹ Stop Practice"):
            st.session_state.running = False
            st.session_state.paused = False
            st.session_state.retry_count = 0
            st.session_state.pair_count = 0
            st.session_state.session_valid_names = []
            st.rerun()
        if not st.session_state.paused:
            if st.button("⏸ Pause Practice"):
                st.session_state.paused = True
                st.rerun()
        else:
            if st.button("▶ Resume Practice"):
                st.session_state.paused = False
                st.rerun()

if not st.session_state.running:
    st.title("🐘 Tamil Theni - Level 2")
    if len(valid_names) < 2:
        st.error("Need at least 2 images or vocabulary words to start practice. Please add more to the 'images' folder or check your Excel file.")
    else:
        if st.button("🚀 Start 15s Practice"):
            st.session_state.running = True
            st.session_state.paused = False
            st.session_state.retry_count = 0
            st.session_state.pair_count = 0
            st.session_state.session_valid_names = random.sample(valid_names, len(valid_names))  # Shuffle for randomness
            st.rerun()
else:
    if st.session_state.paused:
        st.title("🐘 Tamil Theni - Level 2")
        st.info("Practice Paused. Use sidebar to resume or stop.")
        st.stop()

    if st.session_state.pair_count >= 20:
        st.session_state.running = False
        st.session_state.pair_count = 0
        st.session_state.session_valid_names = []
        st.success("Completed 20 sets! Start a new practice.")
        st.rerun()

    # Get AI Result
    with st.spinner("AI is pairing items..."):
        ai_result = get_ai_pairing(st.session_state.session_valid_names)

    if ai_result:
        st.session_state.retry_count = 0  # Reset on success
        w1, w2, sentence = ai_result
        
        # Verification: Only display if both images truly exist in our map
        if w1 not in image_map or w2 not in image_map:
            logging.warning(f"AI selected non-existent images: {w1}, {w2}")
            st.rerun()  # Rerun if mismatch
        
        # Remove used words for no repetition in session
        if w1 in st.session_state.session_valid_names:
            st.session_state.session_valid_names.remove(w1)
        if w2 in st.session_state.session_valid_names:
            st.session_state.session_valid_names.remove(w2)
        
        card_placeholder = st.empty()
        
        # Load images as bytes once
        img1_path = os.path.join(IMAGE_PATH, image_map[w1])
        img2_path = os.path.join(IMAGE_PATH, image_map[w2])
        img1_bytes = load_image_as_bytes(img1_path)
        img2_bytes = load_image_as_bytes(img2_path)
        
        # PHASE 1: Stateful 15-second Preview
        if "phase" not in st.session_state or st.session_state.phase != "preview":
            st.session_state.phase = "preview"
            st.session_state.countdown = 15
        
        while st.session_state.countdown > 0 and not st.session_state.paused:
            with card_placeholder.container():
                st.markdown(f"<h3 style='text-align: center;'>Next Lesson in {st.session_state.countdown}s...</h3>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                if img1_bytes:
                    col1.image(img1_bytes, caption=w1.upper(), use_container_width=True)
                else:
                    col1.text(f"Image not found: {w1}")
                if img2_bytes:
                    col2.image(img2_bytes, caption=w2.upper(), use_container_width=True)
                else:
                    col2.text(f"Image not found: {w2}")
            
            time.sleep(1)
            st.session_state.countdown -= 1
            if st.session_state.countdown > 0:
                st.rerun()
        
        if st.session_state.paused:
            st.rerun()  # Handle pause
        
        # PHASE 2: Stateful 5-second Audio Lesson
        st.session_state.phase = "audio"
        st.session_state.countdown = 5
        
        with card_placeholder.container():
            st.markdown(f"""
                <div style='background-color: #fdfd96; padding: 40px; border-radius: 20px; text-align: center; border: 5px solid #FFD700;'>
                    <h1 style='font-size: 60px; color: #333;'>{sentence}</h1>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            if img1_bytes:
                col1.image(img1_bytes, use_container_width=True)
            else:
                col1.text(f"Image not found: {w1}")
            if img2_bytes:
                col2.image(img2_bytes, use_container_width=True)
            else:
                col2.text(f"Image not found: {w2}")
            
            speak_tamil(sentence)
        
        while st.session_state.countdown > 0 and not st.session_state.paused:
            time.sleep(1)
            st.session_state.countdown -= 1
            if st.session_state.countdown > 0:
                st.rerun()
        
        if st.session_state.paused:
            st.rerun()  # Handle pause
        
        # Increment pair count after full cycle
        st.session_state.pair_count += 1
        del st.session_state.phase  # Reset phase
        st.rerun()
    else:
        st.session_state.retry_count += 1
        if st.session_state.retry_count > 10:
            st.session_state.running = False
            st.session_state.retry_count = 0
            st.session_state.pair_count = 0
            st.session_state.session_valid_names = []
            st.error("Too many failed attempts to find a valid pair. Please check logs for details, add more images, or verify vocabulary matches image names (without extensions).")
        else:
            st.warning("AI had trouble finding a pair. Retrying...")
            time.sleep(2)
            st.rerun()