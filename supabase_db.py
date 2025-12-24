import streamlit as st
import os
import uuid
import tempfile
import shutil
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_community.vectorstores import FAISS

# ----------------- Supabase client setup -----------------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "vector-db")

if SUPABASE_URL is None or SUPABASE_KEY is None:
    raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

from langchain_community.vectorstores import FAISS
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)


# ----------------- Save vector DB -----------------

def save_vector_db_to_supabase(vectordb: FAISS) -> str:
    """
    Save a FAISS vector DB to Supabase Storage.

    Returns:
        db_id (str): unique ID that you can give to the user.
                     Later you can use this id to load the vector DB again.
    """
    # 1. Save FAISS index to a temporary directory
    tmp_dir = tempfile.mkdtemp()
    zip_path = None

    try:
        # This will create index files in tmp_dir
        vectordb.save_local(tmp_dir)

        # 2. Zip the directory into one file
        zip_base = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
        zip_path = shutil.make_archive(zip_base, "zip", tmp_dir)  

        # 3. Generate a unique ID for this vector DB
        db_id = str(uuid.uuid4())

        # 4. Define storage path inside the bucket 
        storage_path = f"stores/{db_id}.zip"

        # 5. Upload the zip file to Supabase Storage
        with open(zip_path, "rb") as f:
            supabase.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=f,
    )

        # That db_id is all the user needs
        return db_id

    finally:
        # Cleanup temporary files and directory
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass


# ----------------- Load vector DB -----------------

def load_vector_db_from_supabase(db_id: str, embeddings) -> FAISS:

    # 1. Compute storage path from id 
    storage_path = f"stores/{db_id}.zip"

    # 2. Download zip from Supabase Storage
    try:
        file_bytes = supabase.storage.from_(BUCKET_NAME).download(storage_path)
    except Exception as e:
        st.error(f"Could not fetch file for id: {db_id}")
        st.error("Please Enter a valid ID or upload a file to get a new ID")
        return
        
        
    # 3. Write bytes to a temporary zip and extract
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, "index.zip")

    with open(zip_path, "wb") as f:
        f.write(file_bytes)

    shutil.unpack_archive(zip_path, tmp_dir)

    # 4. Load FAISS from the extracted folder
    vectordb = FAISS.load_local(
        tmp_dir,
        embeddings,
        allow_dangerous_deserialization=True,
    )
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return vectordb

