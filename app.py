import streamlit as st
import base64
from google import genai
from google.genai import types

# --- 1. PLAYBOOK (SYSTEM INSTRUCTIONS) ---
# Ensure your full "Disclosure Review Playbook" text is pasted here.
SYSTEM_PROMPT = """
Disclosure Review Playbook
General Instructions...
(Paste your full playbook text from the previous message here)
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="TurboHome Auditor",
    page_icon="🏠",
    layout="wide"  # Needed for side-by-side view
)

# Custom CSS to force the PDF viewer to fill the vertical space
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    /* This targets the iframe to make it full height */
    iframe {
        width: 100%;
        height: 85vh; /* 85% of the viewport height */
        border: 1px solid #ddd;
        border-radius: 8px;
    }
    /* Style for the chat container to keep it aligned */
    .chat-container {
        height: 75vh;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. API SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Missing GOOGLE_API_KEY. Please add it to Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- 5. TOP BAR & FILE UPLOADER ---
st.title("🏠 TurboHome Interactive Auditor")

uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    # --- PDF PREVIEW LOGIC ---
    # We read the file once for the UI and then seek(0) for the AI
    pdf_bytes = uploaded_file.read()
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # We use 'data:application/pdf' with '#toolbar=1' to ensure the user can flip pages
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=1&navpanes=1&scrollbar=1" type="application/pdf"></iframe>'
    
    # --- LAYOUT: LEFT (PDF) | RIGHT (CHAT) ---
    col_pdf, col_chat = st.columns([1.2, 1], gap="large")

    with col_pdf:
        st.subheader("📄 Disclosure Document")
        st.markdown(pdf_display, unsafe_allow_html=True)
        st.caption("Use the toolbar above to zoom, rotate, or flip through pages.")

    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        # Container for chat messages
        chat_placeholder = st.container()
        
        with chat_placeholder:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Chat Input
        if prompt := st.chat_input("Ask a question about these disclosures..."):
            # 1. Show user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_placeholder:
                with st.chat_message("user"):
                    st.markdown(prompt)

            # 2. Generate AI response
            with chat_placeholder:
                with st.chat_message("assistant"):
                    response_text_area = st.empty()
                    with st.spinner("Analyzing..."):
                        try:
                            # We send the playbook, the PDF bytes, and the full chat history
                            response = client.models.generate_content(
                                model="gemini-3-flash-preview",
                                config=types.GenerateContentConfig(
                                    system_instruction=SYSTEM_PROMPT,
                                    temperature=0.0
                                ),
                                contents=[
                                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                                    # Add the full chat history for context
                                    *[types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) 
                                      for m in st.session_state.messages]
                                ]
                            )
                            
                            ai_response = response.text
                            response_text_area.markdown(ai_response)
                            st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        
                        except Exception as e:
                            st.error(f"AI Error: {str(e)}")
else:
    st.info("👋 Welcome to TurboHome. Please upload a PDF disclosure package to begin your audit.")
