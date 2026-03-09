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
For every finding, you MUST include the page number using this exact tag: :page[X]
Example: "The roof is 15 years old :page[18]."
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# CSS to clean up the inline link-buttons and chat spacing
st.markdown("""
    <style>
    /* Remove standard button styling for page links */
    div.stButton > button {
        border: none !important;
        padding: 0px 2px !important;
        background-color: transparent !important;
        color: #007bff !important;
        text-decoration: underline !important;
        font-size: inherit !important;
        display: inline !important;
        min-height: 0px !important;
        height: auto !important;
        vertical-align: baseline !important;
    }
    div.stButton > button:hover {
        color: #0056b3 !important;
        background-color: transparent !important;
    }
    /* Fixed height for the PDF container with internal scrolling */
    .pdf-viewer-container {
        height: 85vh;
        overflow-y: auto;
        border: 1px solid #ddd;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "jump_to_page" not in st.session_state:
    st.session_state.jump_to_page = 1

# --- 4. API SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 5. UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    
    col_pdf, col_chat = st.columns([1.3, 1], gap="large")

    # --- LEFT SIDE: CONTINUOUS PDF VIEWER ---
    with col_pdf:
        st.subheader("📄 Continuous Disclosure Document")
        # Continuous scroll: Remove 'pages_to_render' to show all pages
        # Use 'page_number' as a stateful controller for jumping
        pdf_viewer(
            input=pdf_bytes,
            height=850,
            page_number=st.session_state.jump_to_page,
            annotation_outline_size=2 # Optional: highlights areas if needed
        )

    # --- RIGHT SIDE: CHAT WITH INLINE JUMP-LINKS ---
    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        chat_container = st.container(height=650)
        
        with chat_container:
            for msg_idx, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    parts = re.split(r'(:page\[\d+\])', msg["content"])
                    
                    # Layout logic: We use st.write for text and st.button for links
                    # To keep it "inline", we'll render segments sequentially
                    for p_idx, part in enumerate(parts):
                        match = re.match(r':page\[(\d+)\]', part)
                        if match:
                            page_num = int(match.group(1))
                            if st.button(f"Page {page_num}", key=f"link_{msg_idx}_{p_idx}_{page_num}"):
                                st.session_state.jump_to_page = page_num
                                st.rerun()
                        else:
                            # Using st.markdown for text allows for bolding/headers
                            st.markdown(part, unsafe_allow_html=True)

        if prompt := st.chat_input("Ask a question about the disclosures..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    # --- AI ANALYSIS LOGIC ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with col_chat:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing document..."):
                    try:
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                temperature=0.0
                            ),
                            contents=[
                                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                                *[types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) 
                                  for m in st.session_state.messages]
                            ]
                        )
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Audit Error: {e}")
