import re
import os
import math
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. CORE CONFIG & PLAYBOOK
# =========================================================
MODEL_NAME = "gemini-3-flash-preview"  # UPDATED: Production-stable 2026 model

SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
You are a professional real estate auditor. Analyze all documents for material risks.

--- DATA BLOCK RULE ---
Format: [Severity] | [Issue Name] | [Short Citation Text] | [Doc Name] | [Page X] | [Min Cost $] | [Max Cost $]
Wrap rows between DATA_START and DATA_END tags.

--- SUGGESTIONS BLOCK ---
Output exactly 3 concise EDUCATIONAL follow-up questions.
Format: SUGGESTIONS_START | Q1 | Q2 | Q3 | SUGGESTIONS_END
"""

# =========================================================
# 2. SESSION STATE & HELPERS
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "summary_table" not in st.session_state: st.session_state.summary_table = []
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "target_page" not in st.session_state: st.session_state.target_page = None
if "suggestions" not in st.session_state: 
    st.session_state.suggestions = ["What are the biggest red flags?", "Explain foundation risks", "How does this affect my offer?"]

def find_best_doc_match(ai_doc_name):
    if not ai_doc_name: return None
    docs = list(st.session_state.pdf_library.keys())
    for d in docs:
        if ai_doc_name.lower() in d.lower() or d.lower() in ai_doc_name.lower():
            return d
    return None

def parse_and_store_data(text):
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if not match: return
    lines = [l.strip() for l in match.group(1).strip().split('\n') if '|' in l]
    new_rows = []
    for l in lines:
        p = [i.strip() for i in l.split('|')]
        if len(p) >= 7:
            new_rows.append({
                "sev": p[0], "name": p[1], "txt": p[2], "doc": p[3], "pg": p[4],
                "min": int(re.sub(r'\D', '', p[5])), "max": int(re.sub(r'\D', '', p[6]))
            })
    if new_rows: st.session_state.summary_table = new_rows

# =========================================================
# 3. PAGE UI (DM SERIF & MODERN STYLES)
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&family=DM+Serif+Display&display=swap');
html, body, .stApp { font-family: 'DM Sans', sans-serif; background: #f8f7f4; }
.th-header { background: #0f1923; color: white; padding: 18px 24px; border-radius: 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
.th-brand { font-family: 'DM Serif Display', serif; font-size: 24px; }
.th-card { background: white; border: 1px solid #e8e4dc; border-radius: 18px; padding: 24px; margin-bottom: 1.25rem; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
.risk-score-number { font-family: 'DM Serif Display', serif; font-size: 52px; line-height: 1; color: #ea580c; }
div.stButton > button[key^="link_"] { color: #2563eb !important; text-decoration: underline !important; font-weight: 700 !important; border: none !important; background: none !important; padding: 0 !important; text-align: left !important; }
</style>
""", unsafe_allow_html=True)

# --- HEADER & SIDEBAR ---
st.markdown('<div class="th-header"><div class="th-brand">Turbo<span style="color:#f97316;">Home</span> Auditor</div><div style="font-size:12px;opacity:0.7;">2026 PREMIUM EDITION</div></div>', unsafe_allow_html=True)

with st.sidebar:
    files = st.file_uploader("Upload Disclosure Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("Upload documents in the sidebar to begin.")
    st.stop()

# =========================================================
# 4. THE COCKPIT
# =========================================================
col_view, col_chat = st.columns([1.2, 1], gap="medium")

with col_view:
    st.markdown('<div class="th-card"><strong>📄 Evidence Viewer</strong>', unsafe_allow_html=True)
    docs = list(st.session_state.pdf_library.keys())
    idx = docs.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in docs else 0
    st.session_state.viewing_doc = st.selectbox("Current Doc", docs, index=idx, label_visibility="collapsed")
    
    if st.session_state.target_page:
        p_val = int(re.sub(r'\D', '', str(st.session_state.target_page)))
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600, pages_to_render=[p_val])
        if st.button("⬅ Back"): st.session_state.target_page = None; st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card"><strong>💬 Analysis Chat</strong>', unsafe_allow_html=True)
    chat_box = st.container(height=450)
    with chat_box:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(re.sub(r"(DATA|SUGGESTIONS)_(START|END).*?", "", m["content"], flags=re.DOTALL))

    if not st.session_state.messages:
        if st.button("🔍 Run Priority Risk Analysis", type="primary", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "List top issues by priority with costs."})
            st.rerun()
    else:
        s_cols = st.columns(len(st.session_state.suggestions))
        for i, sugg in enumerate(st.session_state.suggestions):
            if s_cols[i].button(sugg, key=f"sugg_{i}"):
                st.session_state.messages.append({"role": "user", "content": sugg}); st.rerun()

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt}); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 5. SUMMARY TABLE & SCORE
# =========================================================
if st.session_state.summary_table:
    rows = st.session_state.summary_table
    t_min, t_max = sum(r["min"] for r in rows), sum(r["max"] for r in rows)
    
    st.markdown(f'<div class="th-card" style="background:#fff7ed; border:1px solid #fed7aa;"><div style="display:flex; justify-content:space-between; align-items:center;"><div><div class="risk-score-number">{len(rows)}</div><div style="font-size:12px; font-weight:700;">TOTAL RISKS</div></div><div style="text-align:right;"><div style="font-size:11px; color:#94a3b8;">EST. REPAIR LIABILITY</div><div style="font-family:\'DM Serif Display\',serif; font-size:32px;">${t_min:,} – ${t_max:,}</div></div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="th-card"><strong>📊 Summary Table</strong>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([0.4, 1, 2, 0.6])
    c1.caption("**SEV**"); c2.caption("**ISSUE**"); c3.caption("**HYPERLINK CITATION**"); c4.caption("**COST**")
    for i, r in enumerate(rows):
        c1, c2, c3, c4 = st.columns([0.4, 1, 2, 0.6])
        c1.write(f"**{r['sev']}**")
        c2.write(r['name'])
        if c3.button(r['txt'], key=f"link_{i}"):
            match = find_best_doc_match(r['doc'])
            if match:
                st.session_state.viewing_doc, st.session_state.target_page = match, r['pg']
                st.rerun()
        c4.write(f"${r['min']:,}")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            res = client.models.generate_content(model=MODEL_NAME, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0), contents=pdf_parts + history)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            parse_and_store_data(res.text)
            
            s_match = re.search(r"SUGGESTIONS_START\s*\|(.*?)\|\s*SUGGESTIONS_END", res.text, re.DOTALL)
            if s_match: st.session_state.suggestions = [s.strip() for s in s_match.group(1).split('|')][:3]
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")
