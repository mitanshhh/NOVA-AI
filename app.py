import streamlit as st

st.set_page_config(layout="wide")

pages = [
    st.Page("main_chat.py", title="Chat", icon="🤖"),
    st.Page("quiz_summary.py", title="Summary & Quiz", icon="🧠"),
    st.Page("ai_learning_path.py", title="AI Roadmap", icon="🧭"),
    st.Page("configure_setting.py", title="Setting", icon=":material/settings:"),
]


pg = st.navigation(pages, position="top")
pg.run()
