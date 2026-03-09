import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. THE REFINED PLAYBOOK ---
# Instructing the AI to use a unique tag for page citations
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Include your full playbook here...)

--- CITATION RULE ---
For every finding, you MUST include the page number using this exact tag: :page[X]
Example: "The roof is 15 years old :page[18]."
This allows the user to click the number to jump to that page in the viewer.
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# Custom CSS to make the "Page Links" look like blue inline text instead of bulky buttons
st.markdown("""
    <style>
    div.stButton > button {
        border: none;
        padding: 0px 2px;
        background-color: transparent;
        color: #007bff;
        text-decoration: underline;
        font-size: inherit;
        display: inline;
        vertical-align: baseline;
    }
    div.stButton > button:hover {
        color: #0056b3;
        background-color: transparent;
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

# --- 5. APP UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    
    col_pdf, col_chat = st.columns([1.2, 1], gap="large")

    # --- LEFT SIDE: THE PDF VIEWER ---
    with col_pdf:
        st.subheader(f"📄 Disclosure Document")
        # Renders ONLY the page the user clicked on for maximum speed
        pdf_viewer(
            input=pdf_bytes, 
            height=850, 
            pages_to_render=[st.session_state.current_page]
        )

    # --- RIGHT SIDE: THE CHAT WITH INLINE JUMP-LINKS ---
    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        chat_container = st.container(height=650)
        
        with chat_container:
            for i, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    # We split the AI text to find our :page[X] tags
                    parts = re.split(r'(:page\[\d+\])', msg["content"])
                    
                    # Create a horizontal flow of text and "link buttons"
                    for part in parts:
                        match = re.match(r':page\[(\d+)\]', part)
                        if match:
                            page_num = int(match.group(1))
                            # This button looks like a link thanks to our CSS
                            if st.button(f"Page {page_num}", key=f"link_{i}_{page_num}_{msg['role']}"):
                                st.session_state.current_page = page_num
                                st.rerun()
                        else:
                            st.write(part, unsafe_allow_html=True)

        if prompt := st.chat_input("Ask about the disclosures..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    # --- CHAT LOGIC ---
    # We trigger the AI only if the last message was from the user
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with col_chat:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing PDF..."):
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
                        st.error(f"Error: {e}")
