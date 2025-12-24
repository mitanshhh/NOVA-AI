import streamlit as st
import json
import re
import os
import io
import uuid
import requests
from dotenv import load_dotenv

# ================= ENV & PAGE CONFIG =================
load_dotenv()
st.set_page_config(page_title="RAG Quiz Assistant", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.st-emotion-cache-467cry p,
.st-emotion-cache-467cry li { color: rgb(255 255 255); }
.st-emotion-cache-13veyas {
    opacity: 1 !important; 
    visibility: visible !important;
}
.st-emotion-cache-13veyas:hover {
    opacity: 1 !important; 
    visibility: visible !important;
}
</style>
""", unsafe_allow_html=True)

# ================= CONFIGURATION =================
DOCS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbw1Jew58JG48DYdKIVMrCt-7m-g4slyLmDfH8AgNDIdFQqgEXRmS8owx8sYkMxfe2yPgQ/exec"

# ================= CACHED RESOURCES =================
@st.cache_resource
def get_gemini_model():
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY not found in environment variables.")
        return None
        
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        "gemini-2.5-flash-lite",
        generation_config={"temperature": 0.7, "top_p": 0.9}
    )

# ================= EFFICIENT FILE LOADING =================
@st.cache_data(show_spinner="Reading file...")
def load_file_text(file_bytes: bytes, file_name: str) -> str:
    try:
        if file_name.endswith(".pdf"):
            import pypdf
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        else:
            return file_bytes.decode("utf-8").strip()
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return ""

# ================= PROMPTS =================
QUIZ_PROMPT = """
CRITICAL RULES:
- NO PREAMBLE
- ONLY JSON OUTPUT
- USE ONLY PROVIDED TEXT
- EXACTLY 5 QUESTIONS
- RANDOMIZE CORRECT ANSWERS (Do not always make 'A' the answer)

TEXT:
{context}

JSON SCHEMA:
{{
  "questions": [
    {{
      "question": "string",
      "options": {{
        "A": "string",
        "B": "string",
        "C": "string",
        "D": "string"
      }},
      "answer": "A|B|C|D",
      "reason": "string",
      "type": "True/False | Numerical | Theory | MCQ",
      "difficulty": "Easy | Medium | Hard"
    }}
  ]
}}
"""

SUMMARY_PROMPT = "Summarize the following content in simple, student-friendly language:\n\n{context}"

# ================= GENERATION FUNCTIONS =================
def generate_summary(text: str):
    model = get_gemini_model()
    if not model or not text: return None
    
    try:
        response = model.generate_content(SUMMARY_PROMPT.format(context=text[:25000]))
        return response.text.strip()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def generate_quiz(text: str, current_questions):
    model = get_gemini_model()
    if not model or not text: return None

    avoid_text = "\n".join(current_questions)
    prompt = f"DO NOT repeat these questions:\n{avoid_text}\n\n{QUIZ_PROMPT.format(context=text[:25000])}"

    try:
        response = model.generate_content(prompt)
        raw = re.sub(r"```json|```", "", response.text.strip())
        return json.loads(raw)
    except Exception as e:
        st.error(f"Quiz Generation Error: {e}")
        return None

def save_to_google_docs(title, summary=None, quiz_results=None):
    payload = {"title": title}
    if summary:
        payload["summary"] = summary
    if quiz_results:
        payload["quiz_results"] = quiz_results
    
    try:
        requests.post(DOCS_WEBHOOK_URL, json=payload)
        return True
    except Exception as e:
        print(f"Error saving to docs: {e}")
        return False

# ================= SESSION STATE =================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.text = None
    st.session_state.summary = None
    st.session_state.quiz = None
    st.session_state.asked_questions = []
    st.session_state.checked_status = {}
    
if "historical_score" not in st.session_state:
    st.session_state.historical_score = 0
if "historical_total" not in st.session_state:
    st.session_state.historical_total = 0

# ================= LOGIC HANDLERS =================
def reset_quiz_state():
    """Resets everything for a brand new quiz session (new file or hard reset)"""
    # st.session_state.summary = None
    st.session_state.quiz = None
    st.session_state.asked_questions = []
    st.session_state.checked_status = {}
    st.session_state.historical_score = 0
    st.session_state.historical_total = 0

def load_new_batch():
    """Generates the next batch of questions"""
    if st.session_state.text:
        with st.spinner("Generating next batch..."):
            quiz_data = generate_quiz(st.session_state.text, st.session_state.asked_questions)
            if quiz_data:
                st.session_state.quiz = quiz_data
                st.session_state.checked_status = {}
                # Record these questions so we don't repeat them
                for q in quiz_data.get("questions", []):
                    st.session_state.asked_questions.append(q["question"])

def on_next_click():
    """Calculates score for current batch and loads the next one"""
    # 1. Calculate Score for current batch before it disappears
    if st.session_state.quiz:
        current_batch_score = 0
        current_batch_total = len(st.session_state.quiz.get("questions", []))
        
        
        for i, q in enumerate(st.session_state.quiz.get("questions", [])):
            q_key = f"q_{i}_{len(st.session_state.asked_questions)}"
            user_answer = st.session_state.get(q_key)
            if user_answer == q["answer"]:
                current_batch_score += 1
        
        st.session_state.historical_score += current_batch_score
        st.session_state.historical_total += current_batch_total
    
    # 2. Load Next Batch
    load_new_batch()

# ================= SIDEBAR =================
with st.sidebar:
    st.title("📘 Controls")
    uploaded_file = st.file_uploader("Upload file", type=["pdf", "txt"])

    if uploaded_file:
        file_key = f"file_{uploaded_file.name}"
        if file_key != st.session_state.get("last_loaded_file"):
            text = load_file_text(uploaded_file.getvalue(), uploaded_file.name)
            st.session_state.text = text
            st.session_state.last_loaded_file = file_key
            reset_quiz_state()
            st.success("File Processed!")

    if st.button("📌 Generate Summary"):
        if st.session_state.text:
            with st.spinner("Summarizing..."):
                st.session_state.summary = generate_summary(st.session_state.text)
        else:
            st.warning("Please upload a file first.")

    # Modified: Explicitly resets history when starting a fresh quiz
    if st.button("🧠 Start New Quiz"):
        if st.session_state.text:
            reset_quiz_state() # Clear previous history
            load_new_batch()
        else:
            st.warning("Please upload a file first.")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:left; font-size: 16px; color: white;'>"
        "Made by <a href='https://www.linkedin.com/in/mitanshjadhav/' style='color: white; text-decoration: none;'>pym1t</a>"
        "<br>"
        "Feedback form <a href='https://docs.google.com/forms/d/e/1FAIpQLScwmjzNArCIg1m89IL8Z-tsQSaOcE_6sgxad3LSj83dHDsg8Q/viewform?usp=header' style='color: #ff8d8d; text-decoration: none;'> Click here</a>"
        "</div>",
        unsafe_allow_html=True,
    )

# ================= MAIN UI =================
st.header("📄 Content Analysis")

if st.session_state.summary:
    with st.expander("📌 Summary", expanded=True):
        st.write(st.session_state.summary)

if st.session_state.quiz:
    st.subheader("📝 Quiz")
    
    questions = st.session_state.quiz.get("questions", [])
    current_score = 0
    total_checked = 0

    for i, q in enumerate(questions):
        st.markdown(f"**Q{i+1}. {q['question']}**")
        
        # Unique key using current length of asked_questions to distinguish batches
        q_key = f"q_{i}_{len(st.session_state.asked_questions)}"
        
        user_choice = st.radio(
            f"Select answer for Q{i+1}",
            options=q["options"].keys(),
            format_func=lambda x: f"{x}. {q['options'][x]}",
            key=q_key,
            index=None,
            label_visibility="collapsed"
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button(f"Check", key=f"btn_{q_key}"):
                st.session_state.checked_status[q_key] = True

        if st.session_state.checked_status.get(q_key):
            total_checked += 1
            if user_choice == q["answer"]:
                st.success(f"Correct! Reason: {q['reason']}")
                current_score += 1
            else:
                st.error(f"Wrong. The correct answer was {q['answer']}. \nReason: {q['reason']}")
                
        st.markdown("---")

    # Metrics Display
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Current Batch Score", f"{current_score} / {len(questions)}")
    with m2:
        total_s = st.session_state.historical_score + current_score
        total_q = st.session_state.historical_total + total_checked
        st.metric("Total Session Score", f"{total_s} / {total_q}")

    # NEXT BUTTON
    st.button("➡️ Next 5 Questions", on_click=on_next_click, use_container_width=True)

# ================= SAVE TO GOOGLE DOCS =================
if st.session_state.summary or st.session_state.quiz:
    st.divider()
    st.subheader("💾 Save to Google Docs")
    
    col1, col2, col3 = st.columns(3)
    
    # Harvest current quiz results
    current_results = []
    if st.session_state.quiz:
        for i, q in enumerate(st.session_state.quiz.get("questions", [])):
            q_key = f"q_{i}_{len(st.session_state.asked_questions)}"
            user_ans_key = st.session_state.get(q_key)
            
            if user_ans_key:
                current_results.append({
                    "question": q["question"],
                    "user_answer": q["options"].get(user_ans_key),
                    "correct_answer": q["options"].get(q["answer"])
                })

    with col1:
        if st.session_state.summary:
            if st.button("Save Summary"):
                if save_to_google_docs("AI Tutor - Summary", summary=st.session_state.summary):
                    st.success("Summary saved!")
                else:
                    st.error("Save failed.")

    with col2:
        if current_results:
            if st.button("Save Quiz"):
                if save_to_google_docs("AI Tutor - Quiz Attempt", quiz_results=current_results):
                    st.success("Quiz saved!")
                else:
                    st.error("Save failed.")

    with col3:
        if st.session_state.summary and current_results:
            if st.button("Save Both"):
                if save_to_google_docs("AI Tutor - Full Session", summary=st.session_state.summary, quiz_results=current_results):
                    st.success("Full session saved!")
                else:
                    st.error("Save failed.")