import os
import requests

# 1. SETUP: Create the folder on your Desktop
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "TamilTheni_Images")
if not os.path.exists(DESKTOP_PATH):
    os.makedirs(DESKTOP_PATH)

# 2. SOURCE: High-quality educational icons for children
# Using a consistent, kid-friendly icon library (OpenMoji / Flaticon style)
BASE_URL = "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/64x64/"

# Mapping words to specific high-quality icon IDs
word_map = {
    "ear": "1F442.png",
    "nose": "1F443.png",
    "head": "1F466.png",
    "eye": "1F441.png",
    "hand": "270B.png",
    "leg": "1F9B5.png",
    "body": "1F9CD.png"
}

def download_pro_set():
    print(f"🚀 Downloading professional educational set to: {DESKTOP_PATH}")
    
    for word, file_id in word_map.items():
        url = BASE_URL + file_id
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                save_path = os.path.join(DESKTOP_PATH, f"{word}.png")
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Saved professional {word}.png")
            else:
                print(f"❌ Failed {word} (Status: {response.status_code})")
        except Exception as e:
            print(f"⚠️ Error downloading {word}: {e}")

    print("\n✨ Download complete! Your app will now run with professional icons.")

if __name__ == "__main__":
    download_pro_set()