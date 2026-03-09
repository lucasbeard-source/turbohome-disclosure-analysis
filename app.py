import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. THE PLAYBOOK ---
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Include your full playbook here...)

--- CITATION RULE ---
You MUST include page citations as inline Markdown links.
Format: [Page X](/?jump=X)
Example: "The foundation has cracks [Page 14](/?jump=14)."
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# CSS to make chat links pop and look professional
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
params = st.query_params
if "jump" in params:
    st.session_state.target_page = int(params["jump"])
elif "target_page" not in st.session_state:
    st.session_state.target_page = None

# --- 4. API SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 5. UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    col_pdf, col_chat = st.columns([1.3, 1], gap="large")

    # LEFT SIDE: PDF VIEWER
    with col_pdf:
        st.subheader("📄 Disclosure Document")
        
        # BULLETPROOF LOGIC: 
        # We split the function call so we never pass None to pages_to_render
        if st.session_state.target_page:
            st.info(f"Focusing on Page {st.session_state.target_page}")
            pdf_viewer(
                input=pdf_bytes, 
                height=850, 
                pages_to_render=[st.session_state.target_page]
            )
            if st.button("⬅️ Back to Full Document"):
                st.query_params.clear() 
                st.session_state.target_page = None
                st.rerun()
        else:
            # Renders all pages in a continuous scroll
            pdf_viewer(input=pdf_bytes, height=850)

    # RIGHT SIDE: CHAT
    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask a question about the disclosures..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
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
