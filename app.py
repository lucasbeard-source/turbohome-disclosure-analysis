import re
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE PLAYBOOK
# =========================================================
def get_system_prompt(is_financial_mode):
    return f"""
    TurboHome Disclosure Analysis Playbook
    Analyze all PDFs and find material risks.
    
    --- DATA BLOCK RULE ---
    End every response with a 'DATA_START' and 'DATA_END' block.
    Format each line as: [Severity] | [Issue Name] | [Text to Click] | [Doc Name] | [Page X] | [Est Cost]
    Severities: High, Medium, Low.
    
    Example:
    DATA_START
    High | Structural Movement | Large cracks in crawlspace | Home Inspection | 14 | $25,000
    DATA_END
    """

# =========================================================
# 2. PAGE CONFIG & STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 4.5rem !important; max-width: 1750px; }
    .stApp { background: #fcfdfe; }
    
    /* Custom Interactive Table Styling */
    .rail-table { width: 100%; border-collapse: collapse; font-size: 13px; background: white; border-radius: 12px; overflow: hidden; }
    .rail-table th { background: #f8fafc; text-align: left; padding: 12px; border-bottom: 2px solid #e2e8f0; color: #64748b; text-transform: uppercase; font-size: 11px; }
    .rail-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
    
    .sev-badge { padding: 4px 8px; border-radius: 999px; font-weight: 700; font-size: 11px; }
    .sev-high { background: #fee2e2; color: #b91c1c; }
    .sev-medium { background: #fef3c7; color: #b45309; }
    .sev-low { background: #f1f5f9; color: #475569; }

    .jump-link { color: #2563eb !important; text-decoration: underline !important; font-weight: 600; cursor: pointer; border:none; background:none; padding:0; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE & NAVIGATION
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "target_page" not in st.session_state: st.session_state.target_page = None
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "suggestions" not in st.session_state: st.session_state.suggestions = ["Highlight risks", "Check permits", "Compare docs"]

def parse_table_data(text):
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if match:
        lines = match.group(1).strip().split('\n')
        parsed = []
        for l in lines:
            parts = [p.strip() for p in l.split('|')]
            if len(parts) == 6:
                parsed.append({
                    "sev": parts[0], "name": parts[1], "txt": parts[2], 
                    "doc": parts[3], "pg": parts[4], "cost": parts[5]
                })
        return parsed
    return []

# =========================================================
# 4. TOP BAR & SIDEBAR (Skipping for brevity, same as before)
# =========================================================
h_col1, h_col2 = st.columns([3, 1])
with h_col1:
    st.markdown('<div style="background:#0f172a; color:white; padding:10px 20px; border-radius:12px;"><strong>TurboHome Disclosure Analysis</strong></div>', unsafe_allow_html=True)
with h_col2:
    financial_mode = st.toggle("💰 Financial Mode", value=True)

with st.sidebar:
    files = st.file_uploader("Upload PDF Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.stop()

# =========================================================
# 5. COCKPIT (VIEWER & CHAT)
# =========================================================
col_pdf, col_chat = st.columns([1.2, 1], gap="medium")

with col_pdf:
    st.subheader("📄 Evidence Viewer")
    doc_list = list(st.session_state.pdf_library.keys())
    cur_idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    st.session_state.viewing_doc = st.selectbox("Doc", doc_list, index=cur_idx, label_visibility="collapsed")
    
    if st.session_state.target_page:
        st.success(f"Focus: p.{st.session_state.target_page}")
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back"): st.session_state.target_page = None; st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600)

with col_chat:
    st.subheader("🤖 Auditor Chat")
    chat_box = st.container(height=550)
    with chat_box:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(re.sub(r"DATA_START.*?DATA_END", "", m["content"], flags=re.DOTALL))

# =========================================================
# 6. BOTTOM RAIL: INTERACTIVE HTML TABLE
# =========================================================
st.write("---")
st.subheader("📋 Integrated Findings Rail")

last_assistant = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")

if last_assistant:
    rows = parse_table_data(last_assistant)
    if rows:
        # We use st.button trick for the links in a loop
        # For a truly clean table with jumps, we render columns
        c1, c2, c3, c4 = st.columns([0.5, 1, 2, 0.5])
        c1.write("**Severity**")
        c2.write("**Issue Name**")
        c3.write("**Citation / Jump Link**")
        c4.write("**Est. Cost**")
        
        for i, r in enumerate(rows):
            c1, c2, c3, c4 = st.columns([0.5, 1, 2, 0.5])
            sev_class = f"sev-{r['sev'].lower()}"
            c1.markdown(f'<span class="sev-badge {sev_class}">{r["sev"].upper()}</span>', unsafe_allow_html=True)
            c2.write(r['name'])
            
            # THE FIX: We use a real Streamlit button styled as a link inside the column
            if c3.button(r['txt'], key=f"rail_jump_{i}"):
                st.session_state.viewing_doc = r['doc']
                st.session_state.target_page = int(r['pg'])
                st.rerun()
            
            c4.write(r['cost'])
    else:
        st.caption("No structured data.")
