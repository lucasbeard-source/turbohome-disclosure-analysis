import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE MULTI-DOC PLAYBOOK
# =========================================================
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
You are a professional auditor. Analyze all documents for discrepancies.

--- CORE CATEGORIES ---
1. Cross-Document Conflicts
2. Inspection Findings
3. Seller Disclosures
4. Hazard Disclosures
5. Follow-up Questions

--- CITATION RULE ---
Wrap every specific issue in this tag: :jump[Description of the issue]{doc="Document Name" page=X}
Example: "The :jump[water heater is reaching the end of its useful life]{doc="Home Inspection" page=18}."
"""

# =========================================================
# 2. PAGE CONFIG & COCKPIT STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 13px; font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    .block-container { max-width: 1750px; padding-top: 1rem; }
    
    /* Hero Header */
    .th-hero { background: #0f172a; color: white; padding: 10px 20px; border-radius: 12px; margin-bottom: 12px; }

    /* Cockpit Panels */
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 16px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .th-card-title { font-weight: 800; font-size: 1.1rem; margin-bottom: 12px; color: #0f172a; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }

    /* Inline Link Buttons */
    div.stButton > button {
        border: none !important; padding: 0px !important; background-color: transparent !important;
        color: #2563eb !important; text-decoration: underline !important; font-size: inherit !important;
        font-weight: 700 !important; display: inline !important; vertical-align: baseline !important;
    }

    /* Findings Rail (Bottom Third) */
    .rail-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 10px; }
    .rail-col { background: #ffffff; border-radius: 12px; padding: 12px; border: 1px solid #e2e8f0; min-height: 200px; }
    .rail-label { font-size: 10px; font-weight: 800; text-transform: uppercase; color: #64748b; margin-bottom: 8px; letter-spacing: 0.05em; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "target_page" not in st.session_state: st.session_state.target_page = None

# =========================================================
# 4. RENDERING ENGINE
# =========================================================
def render_jump_text(text, key_prefix):
    pattern = r'(:jump\[[^\]]+\]\{doc="[^"]+"\s+page=\d+\})'
    parts = re.split(pattern, text)
    for idx, part in enumerate(parts):
        match = re.match(r':jump\[(?P<txt>[^\]]+)\]\{doc="(?P<doc>[^"]+)"\s+page=(?P<pg>\d+)\}', part)
        if match:
            issue_text = match.group('txt')
            doc_name = match.group('doc')
            page_num = int(match.group('pg'))
            if st.button(issue_text, key=f"{key_prefix}_{idx}"):
                st.session_state.viewing_doc = doc_name
                st.session_state.target_page = page_num
                st.rerun()
        else:
            if part.strip(): st.markdown(part, unsafe_allow_html=True)

# =========================================================
# 5. UI: TOP ROW (VIEWER & CHAT)
# =========================================================
st.markdown('<div class="th-hero"><strong>TurboHome Auditor Cockpit</strong></div>', unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Files")
    files = st.file_uploader("Upload PDF Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library:
                st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("Upload documents in the sidebar to enter the cockpit.")
    st.stop()

# TOP ROW
col_pdf, col_chat = st.columns([1.3, 1], gap="medium")

with col_pdf:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">📄 Evidence Viewer</div>', unsafe_allow_html=True)
    
    doc_list = list(st.session_state.pdf_library.keys())
    cur_idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    selected_doc = st.selectbox("Select Doc", doc_list, index=cur_idx, label_visibility="collapsed")
    st.session_state.viewing_doc = selected_doc

    if st.session_state.target_page:
        st.success(f"Targeting p.{st.session_state.target_page} in {selected_doc}")
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full Scroll"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">🤖 Auditor Chat</div>', unsafe_allow_html=True)
    chat_box = st.container(height=520)
    with chat_box:
        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                render_jump_text(msg["content"], f"chat_{m_idx}")

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. UI: BOTTOM ROW (FINDINGS RAIL)
# =========================================================
st.markdown('<div class="th-card" style="margin-top: 15px;">', unsafe_allow_html=True)
st.markdown('<div class="th-card-title">📋 Integrated Findings Rail</div>', unsafe_allow_html=True)

last_analysis = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")

# This rail renders the most recent AI analysis across the full width
# You can use regex to split the 5 sections into the 5-column CSS grid below
if last_analysis:
    render_jump_text(last_analysis, "rail_summary")
else:
    st.caption("Perform an audit to populate the findings rail.")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 7. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    
    with st.spinner("Analyzing cross-document context..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            res = client.models.generate_content(
                model=MODEL_NAME, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
