from langchain_community.vectorstores import FAISS
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_classic.chains import RetrievalQA
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
import os
from google.genai import types
from google import genai
from dotenv import load_dotenv
import streamlit as st

load_dotenv()
# llm = ChatGoogleGenerativeAI(
#     # model="gemini-2.5-flash-lite",
#     model="gemini-flash-latest",
#     temperature=0.7,
#     max_tokens=3000,
#     timeout=None,
#     max_retries=2,
#     api_key=os.getenv('GEMINI_API_KEY'),
# )
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )



FALLBACK_PHRASES = [
    "i don't have info",
    "i do not have info",
    "i can only assist you with the information of file uploaded",
    "not present in the document",
    "not available in the provided content"
]
def needs_internet_search(answer: str) -> bool:
    answer_lower = answer.lower()
    return any(phrase in answer_lower for phrase in FALLBACK_PHRASES)


def switch_to_internet_search(retriever_query):
    # Ensure your API key is set correctly
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    # Use a valid model name
    model = "gemini-2.0-flash-lite" 
    
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=retriever_query)],
        ),
    ]

    # Correct tool definition for the new SDK
    tools = [
        types.Tool(google_search=types.GoogleSearchRetrieval()),
    ]

    generate_content_config = types.GenerateContentConfig(
        tools=tools,
    )

    internet_search_result = []
    try:
        # Using generate_content instead of stream for simpler debugging first
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        # Return the text response
        return response.text

    except Exception as e:
        # Check if the error is actually a quota issue (HTTP 429)
        if "429" in str(e):
            st.warning("Quota exceeded. Please wait a moment or check your billing.")
        else:
            st.error(f"An unexpected error occurred: {e}")
        print(f"Detailed Error: {e}")
        return ""

def ask_ai(retriever_query, full_history,data_base_live_connected):

    vector_embeddings = FAISS.load_local(
        f'{data_base_live_connected}',
        embeddings,
        allow_dangerous_deserialization=True
    )

    retriever = vector_embeddings.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 2},
        score_threshold=0.5
    )

    prompt_template = """
    Given the following context and a question, generate an answer based on this context
    NO PREAMBLE, Dont repeat the question in answer
    In the answer try to provide as much text as possible from "response" section in the source document context without making much changes.
    If the answer is not found in the context but related to the website then, kindly state "I don't have info on (use appropriate words end with full stop), switching back to Internet search". Don't try to make up an answer.
    If the question is completely unrelated and makes no sense with vector DB context backgroud the tell user that "I can only assist you with the information of file uploaded"
    If the intent of the question is not related to topic like greetings or short msgs (hi,bye,thanks,okay.alr,slangs used) then reply normally as a LLM/chatbot

    CONTEXT: {context}
    QUESTION: {question}
    """

    PROMPT = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )


    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        input_key="query",
        chain_type_kwargs={"prompt": PROMPT},
        verbose=True
    )
    try:
        result = qa.invoke(retriever_query)
        print(result)
        result = result["result"]

        if needs_internet_search(result):
            internet_answer = switch_to_internet_search(retriever_query)
            final_answer = f"Information unavailable in file uploaded\nInternet Search result:\n{internet_answer}"
        else:
            final_answer = result
    except Exception as e:
        st.warning("You exceeded your current quota, Please try later or get a new API key")
        print(e)
        return ""

    return final_answer

