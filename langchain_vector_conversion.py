from langchain_community.document_loaders import TextLoader,PyPDFLoader,Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import tempfile
import os
import random
import streamlit as st

def convert_to_vector_db(filename,mode_of_file):
    if mode_of_file == "pdf":
        suffix = ".pdf"
    elif mode_of_file == "text":
        suffix = ".txt"
    elif mode_of_file == "docx":
        suffix = ".docx"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(filename.getvalue())  # write bytes
        tmp.flush()
        tmp.close()
        tmp_path = tmp.name
        if mode_of_file == "pdf":
            loader = UnstructuredPDFLoader(tmp_path)
        elif mode_of_file == "text":
            loader = TextLoader(tmp_path,encoding="utf-8")
        elif mode_of_file == "docx":
            loader = Docx2txtLoader(tmp_path)
        else:
            raise ValueError(f"Unsupported file type")
        documents = loader.load()
        unique_id_to_store_text = random.randint(1,2000)
        text_in_file_uploaded = f"raw_text_of_file_uploaded_{unique_id_to_store_text}.txt"
        with open(text_in_file_uploaded,"a",encoding='utf-8') as f:
            f.write(documents[0].page_content)
        st.session_state["raw_text_file_path"] = text_in_file_uploaded

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size =500,
            chunk_overlap  = 0,
            length_function = len,
        )

        docs = text_splitter.split_documents(documents)

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

        vector_embeddings = FAISS.from_documents(docs,embeddings)
        vector_embeddings.save_local(f"{filename.name}_DB")
        return vector_embeddings
    finally:
            # 5) Clean up temp file (safe after loader.load())
            try:
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)
            except Exception:
                pass

