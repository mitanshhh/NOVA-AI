import streamlit as st
import os
from dotenv import load_dotenv, set_key
from pathlib import Path

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Settings", page_icon="⚙️")

st.title("⚙️ Settings & Configuration")

#Path to your .env file
env_file_path = Path(".env")

# ================= API KEY SECTION =================
st.header("🔑 Gemini API Setup")

st.info("To use the AI features, you need a Google Gemini API Key.")

# Instructions
with st.expander("📝 **How to get your API Key (Step-by-Step)**", expanded=True):
    st.markdown("""
    1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
    2. Log in with your Google Account.
    3. Click on the blue **"Create API key"** button.
    4. Select "Create key in new project" (or an existing one).
    5. **Copy** the generated key string (it starts with `AIza...`).
    6. Paste it in the box below and click **Save**.
    """)

# Input Form
current_key = os.getenv("GEMINI_API_KEY", "")
masked_key = f"{current_key[:4]}...{current_key[-4:]}" if current_key and len(current_key) > 8 else ""

col1, col2 = st.columns([3, 1])
with col1:
    api_key_input = st.text_input(
        "Enter API Key",
        value=current_key if current_key else "",
        type="password",
        placeholder="AIzaSy...",
        help="This key will be stored securely in your local .env file"
    )

if st.button("💾 Save API Key", type="primary"):
    if len(api_key_input) < 30:
        st.error("Invalid API Key format. It should be longer.")
    else:
        try:
            # Ensure .env exists
            if not env_file_path.exists():
                env_file_path.touch()
            
            # Write to .env
            set_key(env_file_path, "GEMINI_API_KEY", api_key_input.strip())
            
            # Update current session
            os.environ["GEMINI_API_KEY"] = api_key_input.strip()
            
            st.success("✅ API Key saved successfully! You can now use the app.")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving key: {e}")

# Show current status
if os.getenv("GEMINI_API_KEY"):
    st.caption(f"✅ Active Key: `{masked_key}`")
else:
    st.caption("❌ No API Key found.")

st.markdown("---")

# ================= CONTACT SECTION =================
st.header("📬 Contact Developer")
st.write("Have questions or feedback? Reach out to me!")

c1, c2, c3 = st.columns([1,1,2])

# LinkedIn Button Style
with c1:
    st.markdown("""
    <a href="https://www.linkedin.com/in/mitanshjadhav/" target="_blank" style="text-decoration:none;">
        <div style="
            background-color: #0077b5;
            color: white;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: 0.3s;
        ">
            LinkedIn
        </div>
    </a>
    """, unsafe_allow_html=True)

# Instagram Button Style
with c2:
    st.markdown("""
    <a href="https://www.instagram.com/mitanshhh.__/" target="_blank" style="text-decoration:none;">
        <div style="
            background: linear-gradient(45deg, #f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%);
            color: white;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        ">
            Instagram
        </div>
    </a>
    """, unsafe_allow_html=True)

st.markdown("---")
