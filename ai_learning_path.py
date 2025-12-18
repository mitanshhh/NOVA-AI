import streamlit as st
import time
import requests
import os

API_KEY = os.getenv('GEMINI_API_KEY')
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"


st.markdown("""
<style>
.st-emotion-cache-467cry p,
.st-emotion-cache-467cry li { color: rgb(255 255 255); }
.st-emotion-cache-13veyas { opacity: 1 !important; visibility: visible !important; }
.st-emotion-cache-13veyas:hover { opacity: 1 !important; visibility: visible !important; }
</style>
""", unsafe_allow_html=True)




def call_gemini_api(prompt, use_search=True):
    """
    Calls the Gemini API with exponential backoff and Google Search grounding.
    Returns the generated text and a list of source links.
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{
                "text": (
                    "You are an expert Educational Consultant and Study Architect. "
                    "Your goal is to create highly structured, realistic, and actionable learning paths. "
                    "Always provide a structured schedule (e.g., Week 1, Week 2)"
                    "include verified external links for study materials with Header as (Relevant Links: link.xyz) which should open when clicked"
                    "Format the output in clear Markdown."
                )
            }]
        }
    }

    # Enable Google Search grounding to get real links
    if use_search:
        payload["tools"] = [{"google_search": {}}]

    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            result = response.json()

            # Extract text content
            try:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                text = "Error: No content generated. Please try again."

            # Extract grounding sources (links)
            links = []
            try:
                grounding_metadata = result["candidates"][0].get("groundingMetadata", {})
                if "groundingAttributions" in grounding_metadata:
                    for attr in grounding_metadata["groundingAttributions"]:
                        web = attr.get("web", {})
                        if web.get("uri") and web.get("title"):
                            links.append({"title": web["title"], "url": web["uri"]})
            except (KeyError, IndexError):
                pass # No links found, just continue

            return text, links

        except requests.exceptions.RequestException as e:
            if i < max_retries - 1:
                time.sleep(2**i)
                continue
            else:
                return f"Error communicating with API: {str(e)}", []
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}", []

    return "Failed to generate content after multiple retries.", []

# --- Streamlit UI ---

st.set_page_config(page_title="AI Learning Path Generator", page_icon="🎓", layout="wide")

st.title("🎓 AI Learning Path Generator")
st.markdown("""
This app generates a personalized study schedule tailored to your goals and time availability.
It uses AI to find the best resources and structure your learning journey.
""")

# Input Section
with st.sidebar:
    st.header("Your Goals")

    subject = st.text_input("Broad Subject", placeholder="e.g. CS, Science, Biology")
    topic = st.text_input("Specific Topic", placeholder="e.g. React.js, Maxwell Theory, Genetics")

    current_knowledge = st.selectbox(
        "Current Knowledge Level",
        ["Absolute Beginner", "Beginner with some basics", "Intermediate", "Advanced"]
    )

    duration = st.selectbox(
        "Learning Duration",
        ["1 Week (Crash Course)", "2 Weeks", "4 Weeks (1 Month)", "8 Weeks (2 Months)", "12 Weeks (3 Months)", "6 Months","1 Year"]
    )

    hours_per_week = st.slider("Hours per week available", 1, 50, 10)

    generate_btn = st.button("Generate Learning Path", type="primary")
    st.markdown("---")
    st.markdown(
        "<div style='text-align:left; font-size: 16px; color: white;'>"
        "Made by <a href='https://www.linkedin.com/in/mitanshjadhav/' style='color: white; text-decoration: none;'>pym1t</a>"
        "<br>"
        "Feedback form <a href='https://docs.google.com/forms/d/e/1FAIpQLScwmjzNArCIg1m89IL8Z-tsQSaOcE_6sgxad3LSj83dHDsg8Q/viewform?usp=header' style='color: #ff8d8d; text-decoration: none;'> Click here</a>"
        "</div>",
        unsafe_allow_html=True,
    )

# Main Content Area
if generate_btn:
    if not subject or not topic:
        st.error("Please enter both a Subject and a Specific Topic.")
    else:
        with st.spinner("Consulting the AI Study Architect... this may take a moment..."):

            # Construct a detailed prompt
            prompt = f"""
            Create a detailed, step-by-step learning path for a student wanting to learn '{topic}' within the subject of '{subject}'.

            User Profile:
            - Current Knowledge: {current_knowledge}
            - Total Duration: {duration}
            - Time Commitment: {hours_per_week} hours per week.

            Requirements:
            1. Break down the timeline into Weeks (e.g., Week 1, Week 2...).
            2. For each week, define specific Learning Objectives and Topics to cover.
            3. Provide a list of high-quality, free online resources (URLs to documentation, video tutorials, courses) for each topic.
            4. Include a "Practical Exercise" or "Project" for each week to reinforce learning.
            5. Structure the response clearly using Markdown headings and bullet points.
            6. The links should be visible and not embedded into any text
            """

            # Call API
            generated_text, source_links = call_gemini_api(prompt)

            # Display Results
            st.markdown("### 📅 Your Personalized Learning Schedule")
            st.markdown("---")
            st.markdown(generated_text)

            # Display collected sources in an expander if available
            if source_links:
                with st.expander("📚 Verified Source Links & References"):
                    st.write("The AI used these sources to build your path:")
                    for link in source_links:
                        st.markdown(f"- [{link['title']}]({link['url']})")
            

else:
    # Empty state placeholder
    st.info("👈 Enter your details in the sidebar and click 'Generate' to start!")

    st.markdown("### Example Inputs")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**User A**\n* Computer Science\n* Python for Data Science\n* Beginner\n* 1 Year")
    with col2:
        st.markdown("**User B**\n* Engineering Mechanics\n* Robotics\n* Intermediate\n* 2 Weeks")