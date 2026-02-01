import streamlit as st
import pandas as pd
import os
import random
import time
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
IMAGE_FOLDER = "images"
EXCEL_PATH = "TT2026-Word-List-Theni-1_2_3_4_Extracted.xlsx"
PAIRS_PER_SESSION = 20
SECONDS_PER_CARD = 15

st.set_page_config(page_title="Tamil Theni Practice", layout="wide")

# --- DATA LOADING & VALIDATION ---
@st.cache_data
def get_available_data():
    """Loads Excel and matches words with existing image files."""
    try:
        # 1. Load Excel
        if not os.path.exists(EXCEL_PATH):
            return None, "Excel file not found."
        
        df = pd.read_excel(EXCEL_PATH, engine='openpyxl')
        # Using columns 1 and 6 as per your specific file structure
        words_col1 = df.iloc[:, 1].dropna().astype(str).tolist()
        words_col6 = df.iloc[:, 6].dropna().astype(str).tolist()
        all_excel_words = list(set([w.strip().lower() for w in (words_col1 + words_col6)]))

        # 2. Map Images
        if not os.path.exists(IMAGE_FOLDER):
            return None, f"Folder '{IMAGE_FOLDER}' not found."
        
        files = os.listdir(IMAGE_FOLDER)
        image_map = {}
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                name_key = os.path.splitext(f)[0].strip().lower()
                image_map[name_key] = f
        
        # 3. Intersection: Only words that have both Excel entries and Images
        valid_words = [w for w in all_excel_words if w in image_map]
        
        return {"valid_words": valid_words, "image_map": image_map}, None
    
    except Exception as e:
        return None, f"Error: {str(e)}"

# --- SESSION STATE INITIALIZATION ---
if "practice_active" not in st.session_state:
    st.session_state.practice_active = False
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "session_pairs" not in st.session_state:
    st.session_state.session_pairs = []

# --- APP LOGIC ---
data, error = get_available_data()

if error:
    st.error(error)
    st.stop()

valid_words = data["valid_words"]
image_map = data["image_map"]

# --- UI: START PAGE ---
if not st.session_state.practice_active:
    st.title("🐘 Tamil Theni: Word-Image Practice")
    st.write(f"Loaded **{len(valid_words)}** words with matching images.")
    
    if len(valid_words) < 40:
        st.warning(f"Found only {len(valid_words)} images. You need at least 40 for a full session.")
    
    if st.button("🚀 Start New Practice (20 Pairs)", type="primary"):
        # Generate 20 random pairs (40 words total)
        needed = min(len(valid_words), 40)
        selected_words = random.sample(valid_words, needed)
        
        # Create list of tuples: [(w1, w2), (w3, w4)...]
        st.session_state.session_pairs = [
            (selected_words[i], selected_words[i+1]) 
            for i in range(0, len(selected_words) - 1, 2)
        ]
        st.session_state.current_index = 0
        st.session_state.practice_active = True
        st.rerun()

# --- UI: ACTIVE PRACTICE ---
else:
    # Check if we reached the end
    if st.session_state.current_index >= len(st.session_state.session_pairs):
        st.balloons()
        st.title("✅ Practice Complete!")
        st.write("You have successfully viewed all 20 pairs.")
        if st.button("🔄 Start New Practice"):
            st.session_state.practice_active = False
            st.rerun()
        st.stop()

    # Setup the Auto-Refresh (Timer)
    st_autorefresh(interval=SECONDS_PER_CARD * 1000, key="practice_timer")

    # Display Progress
    current_pair = st.session_state.session_pairs[st.session_state.current_index]
    w1, w2 = current_pair
    
    st.progress((st.session_state.current_index + 1) / len(st.session_state.session_pairs))
    st.write(f"Pair {st.session_state.current_index + 1} of {len(st.session_state.session_pairs)}")

    # Centered Layout
    container = st.container()
    with container:
        col1, col2 = st.columns(2)
        
        # Display Images using the map to handle original extensions (png/jpg)
        with col1:
            st.image(os.path.join(IMAGE_FOLDER, image_map[w1]), use_container_width=True)
            st.markdown(f"<h2 style='text-align: center;'>{w1.upper()}</h2>", unsafe_allow_html=True)
            
        with col2:
            st.image(os.path.join(IMAGE_FOLDER, image_map[w2]), use_container_width=True)
            st.markdown(f"<h2 style='text-align:center;'>{w2.upper()}</h2>", unsafe_allow_html=True)

        # Placeholder for Tamil Sentence Logic
        # (Assuming you want a placeholder until you integrate the AI logic back in)
        st.markdown(f"""
            <div style='background-color: #fdfd96; padding: 20px; border-radius: 15px; text-align: center; margin-top: 20px;'>
                <h1 style='color: #333;'>Practice these words together.</h1>
            </div>
        """, unsafe_allow_html=True)

    # Manual Next Button (Optional)
    if st.sidebar.button("➡️ Skip to Next"):
        st.session_state.current_index += 1
        st.rerun()

    if st.sidebar.button("⏹ End Session"):
        st.session_state.practice_active = False
        st.rerun()

    # Advance the index for the next timer cycle
    st.session_state.current_index += 1