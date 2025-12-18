import streamlit as st
from langchain_community.vectorstores import FAISS
import tempfile
from pathlib import Path
import os
import re
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv
from supabase import create_client, Client
from gemini_agent import ask_ai,switch_to_internet_search
from langchain_vector_conversion import convert_to_vector_db
from supabase_db import save_vector_db_to_supabase,load_vector_db_from_supabase

# ----------------- Supabase client setup -----------------

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "vector-db")

if SUPABASE_URL is None or SUPABASE_KEY is None:
    raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set in environment")


# ========================= CACHE ADDITIONS =========================

@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = get_supabase_client()



@st.cache_resource
def load_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )

embeddings = load_embeddings()


@st.cache_data
def cached_convert_to_vector_db(uploaded_file, file_type_by_user):
    return convert_to_vector_db(uploaded_file, file_type_by_user)


@st.cache_resource
def load_faiss_local(path, _embeddings):
    return FAISS.load_local(
        path,
        _embeddings,
        allow_dangerous_deserialization=True
    )


@st.cache_resource
def cached_load_vector_db_from_supabase(db_id, _embeddings):
    return load_vector_db_from_supabase(db_id, _embeddings)




# --------------------------------------- PAGE CONFIG --------------------------------------
st.set_page_config(
    page_title="AI RAG Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown("""
<style>
.st-emotion-cache-13veyas {
    opacity: 1 !important; 
    visibility: visible !important;
}
.st-emotion-cache-13veyas:hover {
    opacity: 1 !important; 
    visibility: visible !important;
}
.st-emotion-cache-px2xcf h3 {
    font-size: 17px;
    font-weight: 600;
    padding: 0.75rem 0px 1rem;
}
.st-aq {
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)


# ---------- SESSION STATE ----------
if "active_db_id" not in st.session_state:
    st.session_state.active_db_id = None

if "topic_name" not in st.session_state:
    st.session_state.topic_name = "Your Knowledge. Powered by AI"

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Ask me anything"}
    ]


def clear_chat_history():
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Ask me anything"}
    ]
    st.session_state.active_db_id = None


# ============================================================================================
# ================================= SIDEBAR ================================================
# ============================================================================================
with st.sidebar:

    st.markdown("## Pym1t Assistant")
    st.markdown("### 🗪  Chat Controls")

    mode = st.radio(
        "Choose an action:",
        ("Upload a new file","Search file by ID"),
        key="db_mode",
    )

    st.write("")

    if mode == "Search file by ID":
        search_id = st.text_input(
            "Search file by ID",
            placeholder="Enter Database ID"
        )

        if st.button("Load Database", type="primary", use_container_width=True):
            if search_id:
                cached_load_vector_db_from_supabase(search_id, embeddings)
                st.session_state.active_db_id = search_id
                st.success(f'Loaded chat with id {search_id}')
            else:
                st.warning("Please enter a valid ID.")

    else:
        uploaded_file = st.file_uploader(
            "Upload a new file",
            type=["pdf", "txt", "docx"],
        )

        if st.button("Upload", type="primary", use_container_width=True):
            if uploaded_file is None:
                st.warning("Please upload a file first.")
            else:
                if uploaded_file.name.endswith(".pdf") and uploaded_file.type == "application/pdf":
                    file_type_by_user = "pdf"
                elif uploaded_file.name.endswith(".txt") and uploaded_file.type == "text/plain":
                    file_type_by_user = "text"
                elif uploaded_file.name.endswith(".docx") or uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    file_type_by_user = "docx"
                DATABASE = cached_convert_to_vector_db(uploaded_file, file_type_by_user)

                db = load_faiss_local(
                    f"{uploaded_file.name}_DB",
                    embeddings
                )

                database_saved_with_id = save_vector_db_to_supabase(db)

                st.session_state.active_db_id = database_saved_with_id

                st.success("File converted to vector DB successfully!")
                st.markdown("##### Your Unique Database ID")
                st.text_input(
                    label="",
                    value=database_saved_with_id,
                    key="generated_id_display",
                )
                st.caption("Use this ID later with *Search file by ID*.")

    st.markdown("---")
    st.button("🗑️ Clear Chat History", on_click=clear_chat_history, use_container_width=True)
    st.markdown("---")

    st.markdown(
        "<div style='text-align:left; font-size: 16px; color: white;'>"
        "Made by <a href='https://www.linkedin.com/in/mitanshjadhav/' style='color: white; text-decoration: none;'>pym1t</a>"
        "<br>"
        "Feedback form <a href='https://docs.google.com/forms/d/e/1FAIpQLScwmjzNArCIg1m89IL8Z-tsQSaOcE_6sgxad3LSj83dHDsg8Q/viewform?usp=header' style='color: #ff8d8d; text-decoration: none;'> Click here</a>"
        "</div>",
        unsafe_allow_html=True,
    )


# ================================= MAIN CHAT ==============================================

st.subheader(st.session_state.topic_name)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if retriever_query := st.chat_input("Ask a question"):
    if st.session_state.active_db_id:
        st.session_state.messages.append({"role": "user", "content": retriever_query})

        with st.chat_message("user"):
            st.markdown(retriever_query)
            
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                full_history = [(m['role'], m['content']) for m in st.session_state.messages]

                if mode == "Search file by ID":

                    def save_faiss_to_temp(vectorstore):
                        temp_dir = Path(tempfile.mkdtemp())
                        vectorstore.save_local(str(temp_dir))
                        return temp_dir

                    response_data = ask_ai(
                        retriever_query,
                        full_history,
                        str(
                            save_faiss_to_temp(
                                cached_load_vector_db_from_supabase(search_id, embeddings)
                            )
                        )
                    )
                else:
                    response_data = ask_ai(
                        retriever_query,
                        full_history,
                        f"{uploaded_file.name}_DB"
                    )

                answer_text = response_data

                def normalize_llm_math(text: str) -> str:
                    text = re.sub(r"\[\s*(.*?)\s*\]", r"$$\n\1\n$$", text, flags=re.DOTALL)
                    text = re.sub(r"\$\$\s*(.*?)\s*\$\$", r"$$\n\1\n$$", text, flags=re.DOTALL)
                    text = re.sub(r"^\s*\\\s*$", "", text, flags=re.MULTILINE)
                    text = text.replace(r"\$", "$")
                    text = re.sub(r"\\\((.*?)\\\)", r"$\1$", text)
                    lines = text.splitlines()
                    cleaned = []
                    for line in lines:
                        if line.strip() == "$$":
                            cleaned.append("$$")
                        else:
                            cleaned.append(line.rstrip())
                    return "\n".join(cleaned)

            st.markdown(
                normalize_llm_math(answer_text).replace("\n", "  \n")
            )

            st.session_state.messages.append(
                {"role": "assistant", "content": answer_text}
            )
    else:
        st.session_state.messages.append({"role": "user", "content": retriever_query})

        with st.chat_message("user"):
            st.markdown(retriever_query)
            
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                llm_reply_without_db = switch_to_internet_search(retriever_query)
                st.markdown(llm_reply_without_db)
            st.session_state.messages.append(
                {"role": "assistant", "content": llm_reply_without_db}
            )

