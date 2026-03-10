import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. THE PLAYBOOK ---
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Include your full playbook text here inside these triple quotes)

--- CITATION RULE ---
For every finding, you MUST include the page number using this exact tag: :page[X]
Example: "The roof is 15 years old :page[18]."
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# CSS for the "No-New-Tab" Inline Links and Suggestion Bubbles
st.markdown("""
    <style>
    /* Inline Page Links */
    div.stButton > button {
        border: none !important;
        padding: 0px 1px !important;
        background-color: transparent !important;
        color: #007bff !important;
        text-decoration: underline !important;
        font-size: inherit !important;
        display: inline !important;
        min-height: 0px !important;
        height: auto !important;
        vertical-align: baseline !important;
    }
    div.stButton > button:hover { color: #0056b3 !important; }

    /* Suggestion Bubbles Styling */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background-color: #ffffff !important;
        color: #2563eb !important;
        border: 1px solid #2563eb !important;
        text-decoration: none !important;
        border-radius: 12px !important;
        padding: 8px 12px !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        transition: 0.3s;
    }
    div[data-testid="column"] .stButton > button[key^="sugg_"]:hover {
        background-color: #2563eb !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "target_page" not in st.session_state:
    st.session_state.target_page = None 
if "suggestions" not in st.session_state:
    # Default initial suggestions
    st.session_state.suggestions = ["Highlight the biggest risks", "Check for unpermitted work", "Summarize NHD hazards"]

# --- 4. API SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 5. UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    col_pdf, col_chat = st.columns([1.3, 1], gap="large")

    with col_pdf:
        st.subheader("📄 Disclosure Document")
        if st.session_state.target_page:
            st.info(f"Focusing on Page {st.session_state.target_page}")
            pdf_viewer(input=pdf_bytes, height=850, pages_to_render=[st.session_state.target_page])
            if st.button("⬅️ Back to Full Document", key="back_btn"):
                st.session_state.target_page = None
                st.rerun()
        else:
            pdf_viewer(input=pdf_bytes, height=850)

    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        chat_container = st.container(height=600)
        
        with chat_container:
            for m_idx, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    # Handle text + inline links
                    parts = re.split(r'(:page\[\d+\])', msg["content"])
                    for p_idx, part in enumerate(parts):
                        match = re.match(r':page\[(\d+)\]', part)
                        if match:
                            page_num = int(match.group(1))
                            if st.button(f"Page {page_num}", key=f"lk_{m_idx}_{p_idx}_{page_num}"):
                                st.session_state.target_page = page_num
                                st.rerun()
                        else:
                            if part.strip(): st.markdown(part)

        # RENDER DYNAMIC SUGGESTION BUBBLES
        st.write("---")
        st.caption("Suggested follow-ups:")
        s_cols = st.columns(len(st.session_state.suggestions))
        for idx, suggestion in enumerate(st.session_state.suggestions):
            if s_cols[idx].button(suggestion, key=f"sugg_{idx}"):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                st.rerun()

        if prompt := st.chat_input("Ask a question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    # --- 6. AI CONTEXTUAL LOGIC ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with col_chat:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    try:
                        # CALL 1: The Main Audit
                        response = client.models.generate_content(
                            model="gemini-3-flash",
                            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                            contents=[
                                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                                *[types.Content(role="model" if m["role"] == "assistant" else "user", 
                                                parts=[types.Part.from_text(text=m["content"])]) 
                                  for m in st.session_state.messages]
                            ]
                        )
                        st.session_state.messages.append({"role": "assistant", "content": response.text})

                        # CALL 2: The Contextual Suggestions
                        # We ask Gemini to look at the last interaction and suggest what a smart buyer would ask next.
                        s_prompt = f"""
                        Based on this finding: "{response.text}", 
                        what are 3 logical, short follow-up questions (4-6 words each) 
                        a homebuyer should ask? 
                        Output ONLY the questions separated by the | character. 
                        Example: Question 1 | Question 2 | Question 3
                        """
                        sugg_response = client.models.generate_content(model="gemini-3-flash", contents=[s_prompt])
                        
                        # Update session state with new suggestions
                        new_suggs = sugg_response.text.strip().split('|')
                        st.session_state.suggestions = [s.strip() for s in new_suggs][:3]
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
