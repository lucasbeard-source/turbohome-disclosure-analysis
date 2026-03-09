import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. PLAYBOOK ---
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Include your full playbook here...)

--- CITATION RULE ---
You MUST include page citations as inline Markdown links.
Format: [Page X](/?jump=X)
Example: "The foundation has cracks [Page 14](/?jump=14)."
This is crucial for the interactive viewer.
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# Custom CSS to make the links look native
st.markdown("""
    <style>
    .stChatMessage a {
        color: #007bff !important;
        text-decoration: underline !important;
        font-weight: bold;
    }
    .stChatMessage a:hover {
        color: #0056b3 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. STATE & URL SYNC ---
# Detect if the user clicked a jump link in the URL
params = st.query_params
if "jump" in params:
    st.session_state.target_page = int(params["jump"])
elif "target_page" not in st.session_state:
    st.session_state.target_page = None

# --- 4. UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    col_pdf, col_chat = st.columns([1.3, 1], gap="large")

    with col_pdf:
        st.subheader("📄 Disclosure Document")
        
        # Use target_page for jump or None for continuous
        pg = [st.session_state.target_page] if st.session_state.target_page else None
        
        # The key= is important to force refresh when target_page changes
        pdf_viewer(input=pdf_bytes, height=850, pages_to_render=pg)
        
        if st.session_state.target_page:
            if st.button("⬅️ Back to Full Document"):
                st.query_params.clear() # Clear the URL
                st.session_state.target_page = None
                st.rerun()

    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # RENDER CHAT: Everything is now in a single clean markdown block per message
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask about the disclosures..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # AI Logic
            api_key = st.secrets["GOOGLE_API_KEY"]
            client = genai.Client(api_key=api_key)
            
            try:
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                    contents=[
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                        *[types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) 
                          for m in st.session_state.messages]
                    ]
                )
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
