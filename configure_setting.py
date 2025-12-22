import streamlit as st
import os
from pathlib import Path


st.set_page_config(page_title="Settings", page_icon="⚙️",layout="wide")

st.title("⚙️ Settings & Configuration")

# This ensures the key is private to the current user's browser session
if "USER_GEMINI_API_KEY" not in st.session_state:
    # Fallback order: 1. App Secrets (Developer's key) | 2. Empty string
    st.session_state["USER_GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

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
# We use session_state to track what the user has saved
current_key = st.session_state["USER_GEMINI_API_KEY"]
masked_key = f"{current_key[:4]}...{current_key[-4:]}" if len(current_key) > 8 else "Not Set"

col1, col2 = st.columns([3, 1])
with col1:
    api_key_input = st.text_input(
        "Enter API Key",
        value=current_key,
        type="password",
        placeholder="AIzaSy...",
        help="This key is stored only in your current browser session for privacy."
    )

if st.button("💾 Save API Key", type="primary"):
    if len(api_key_input) < 30 and len(api_key_input) > 0:
        st.error("Invalid API Key format. It should be longer.")
    else:
        # SAVE TO SESSION STATE ONLY (Private to this user)
        st.session_state["USER_GEMINI_API_KEY"] = api_key_input.strip()
        
        # Also update os.environ for the duration of this specific user's run
        os.environ["GEMINI_API_KEY"] = api_key_input.strip()
        
        st.success("✅ API Key applied to this session!")
        st.rerun()

# Show current status
if st.session_state["USER_GEMINI_API_KEY"]:
    st.caption(f"✅ Active Key for this session: `{masked_key}`")
else:
    st.caption("❌ No API Key found for this session.")

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