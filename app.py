import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. PLAYBOOK (No changes to your prompt) ---
SYSTEM_PROMPT = """
(Include your full playbook here...)
--- CITATION RULE ---
For every finding, you MUST include the page number using this exact tag: :page[X]
Example: "The roof is 15 years old :page[18]."
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# Updated CSS to force inline display and remove vertical margins
st.markdown("""
    <style>
    /* Remove vertical padding from chat messages */
    .stChatMessage { padding: 0.5rem 1rem !important; }
    
    /* Style the buttons to look like hyperlinked text */
    div.inline-button > div {
        display: inline-block;
        vertical-align: baseline;
    }
    button[kind="secondary"] {
        border: none !important;
        padding: 0px 2px !important;
        background-color: transparent !important;
        color: #007bff !important;
        text-decoration: underline !important;
        font-size: inherit !important;
        min-height: 0px !important;
        height: auto !important;
        line-height: inherit !important;
    }
    button[kind="secondary"]:hover {
        color: #0056b3 !important;
        text-decoration: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

# --- 4. API SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 5. UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    col_pdf, col_chat = st.columns([1.2, 1], gap="large")

    with col_pdf:
        st.subheader("📄 Disclosure Document")
        pdf_viewer(input=pdf_bytes, height=850, pages_to_render=[st.session_state.current_page])

    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        chat_container = st.container(height=650)
        
        with chat_container:
            for msg_idx, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    # We split the text into chunks of normal text and :page[X] tags
                    parts = re.split(r'(:page\[\d+\])', msg["content"])
                    
                    # We use a container to wrap the parts so we can control spacing
                    # Note: We avoid st.write here because it adds margins. 
                    # We use st.markdown with an inline-container trick.
                    html_content = ""
                    for part_idx, part in enumerate(parts):
                        match = re.match(r':page\[(\d+)\]', part)
                        if match:
                            # Render current html_content accumulated so far
                            if html_content:
                                st.markdown(f'<span style="display:inline;">{html_content}</span>', unsafe_allow_html=True)
                                html_content = ""
                            
                            page_num = int(match.group(1))
                            # We use a column trick to put button immediately after text
                            if st.button(f"Page {page_num}", key=f"btn_{msg_idx}_{part_idx}_{page_num}"):
                                st.session_state.current_page = page_num
                                st.rerun()
                        else:
                            # Clean up the text part for HTML display
                            # Replace newlines with <br> to keep formatting
                            clean_text = part.replace("\n", "<br>")
                            html_content += clean_text
                    
                    # Final text chunk
                    if html_content:
                        st.markdown(f'<span style="display:inline;">{html_content}</span>', unsafe_allow_html=True)

        if prompt := st.chat_input("Ask about the disclosures..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    # --- CHAT LOGIC ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with col_chat:
            with st.chat_message("assistant"):
                with st.spinner("Auditing..."):
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
