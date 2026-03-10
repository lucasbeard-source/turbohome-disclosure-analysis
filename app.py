import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE PLAYBOOK
# =========================================================
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
(Include your full multi-doc playbook here...)

--- CITATION RULE ---
For every finding, you MUST include the document name and page number.
Format: [Document Name] :page[X]
Example: "[Home Inspection] :page[18]: The HVAC unit is 22 years old."
"""

# =========================================================
# 2. PAGE CONFIG & STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Disclosure Analysis", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    /* Compact SaaS Styling */
    html, body, [class*="css"] { font-size: 13.5px; font-family: 'Inter', sans-serif; }
    .th-hero { background: #0f172a; color: white; padding: 15px 20px; border-radius: 12px; margin-bottom: 12px; }
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 15px; height: 100%; }
    
    /* Inline Link Buttons */
    div.stButton > button {
        border: none !important; padding: 0px 2px !important; background-color: transparent !important;
        color: #2563eb !important; text-decoration: underline !important; font-size: inherit !important;
        min-height: 0px !important; height: auto !important; vertical-align: baseline !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} # {Filename: Bytes}
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "target_page" not in st.session_state: st.session_state.target_page = None
if "suggestions" not in st.session_state: 
    st.session_state.suggestions = ["Summarize all risks", "Find structural issues", "Compare inspections"]

# =========================================================
# 4. SIDEBAR - FILE UPLOAD
# =========================================================
with st.sidebar:
    st.title("📂 Document Room")
    new_files = st.file_uploader("Upload Disclosure Packet", type=["pdf"], accept_multiple_files=True)
    
    if new_files:
        for f in new_files:
            if f.name not in st.session_state.pdf_library:
                st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

    if st.session_state.pdf_library:
        st.write("---")
        st.caption("Active Documents")
        for doc_name in list(st.session_state.pdf_library.keys()):
            col_name, col_del = st.columns([4, 1])
            col_name.text(f"📄 {doc_name[:20]}...")
            if col_del.button("X", key=f"del_{doc_name}"):
                del st.session_state.pdf_library[doc_name]
                if st.session_state.viewing_doc == doc_name:
                    st.session_state.viewing_doc = None
                st.rerun()

# =========================================================
# 5. MAIN UI
# =========================================================
st.markdown('<div class="th-hero"><h3>TurboHome Disclosure Analysis</h3></div>', unsafe_allow_html=True)

if not st.session_state.pdf_library:
    st.info("Upload your disclosure PDFs in the sidebar to begin the analysis.")
    st.stop()

col_pdf, col_chat = st.columns([1.3, 1], gap="medium")

# --- LEFT: DYNAMIC PDF VIEWER ---
with col_pdf:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    
    # DOCUMENT SELECTOR
    doc_options = list(st.session_state.pdf_library.keys())
    selected_doc = st.selectbox(
        "Current Document:", 
        doc_options, 
        index=doc_options.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_options else 0,
        key="doc_selector"
    )
    st.session_state.viewing_doc = selected_doc

    # VIEWER LOGIC
    doc_bytes = st.session_state.pdf_library[selected_doc]
    
    if st.session_state.target_page:
        st.caption(f"Targeting Page {st.session_state.target_page}")
        pdf_viewer(input=doc_bytes, height=800, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full Scroll", key="reset_view"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=doc_bytes, height=800)
    st.markdown('</div>', unsafe_allow_html=True)

# --- RIGHT: INTERACTIVE AUDITOR ---
with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    chat_box = st.container(height=600)
    
    with chat_box:
        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                parts = re.split(r'(:page\[\d+\])', msg["content"])
                for p_idx, part in enumerate(parts):
                    match = re.match(r':page\[(\d+)\]', part)
                    if match:
                        page_num = int(match.group(1))
                        if st.button(f"p.{page_num}", key=f"lk_{m_idx}_{p_idx}_{page_num}"):
                            st.session_state.target_page = page_num
                            st.rerun()
                    else:
                        st.markdown(part)

    # Contextual Suggestions
    st.write("---")
    st.caption("Suggested Follow-ups:")
    s_cols = st.columns(len(st.session_state.suggestions))
    for i, sugg in enumerate(st.session_state.suggestions):
        if s_cols[i].button(sugg, key=f"sugg_{i}"):
            st.session_state.messages.append({"role": "user", "content": sugg})
            st.rerun()

    if prompt := st.chat_input("Analyze these documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. AI CONTEXTUAL ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    
    with st.spinner("Reviewing across all files..."):
        try:
            # Send all PDFs together for cross-document intelligence
            all_pdfs = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            chat_history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                            parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]

            # Primary Audit
            response = client.models.generate_content(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=all_pdfs + chat_history
            )
            st.session_state.messages.append({"role": "assistant", "content": response.text})

            # Shadow Call for Contextual Suggestions
            s_prompt = f"Based on: '{response.text}', suggest 3 logical follow-ups (3-5 words) for a buyer. Output ONLY text separated by |."
            s_res = client.models.generate_content(model=MODEL_NAME, contents=[s_prompt])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            
            st.rerun()
        except Exception as e:
            st.error(f"Audit Error: {e}")
