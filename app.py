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
MODEL_NAME = "gemini-3-flash-preview"

SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
You are a professional real estate auditor. Analyze the uploaded documents for the property address and calibrate your risk assessment to that specific market.

--- DATA BLOCK RULE ---
End every audit with a DATA_START block. Use the exact format:
[Severity] | [Urgency] | [Issue Name] | [Citation Text] | [Doc Name] | [Page X] | [Min $] | [Max $]

Urgency: Immediate (Safety/Insurance), Planned (1-2 years), Monitor (3+ years).
Severities: High, Medium, Low.
Cost: Integers only, no symbols (e.g., 5000 | 15000).
Wrap between DATA_START and DATA_END.

--- TONE ---
Professional, grounded, and conversational. Use bullet points in the chat. 
Frame repair costs in the context of the property location (e.g., Richmond, CA vs. Houston, TX).
"""

# =========================================================
# 2. SESSION STATE & PERSISTENT MEMORY
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "summary_table" not in st.session_state: st.session_state.summary_table = [] # PERSISTENT
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "target_page" not in st.session_state: st.session_state.target_page = None
if "suggestions" not in st.session_state: 
    st.session_state.suggestions = ["List top issues by priority", "Learn about wiring risks", "Explain foundation hazards"]

def find_best_doc_match(ai_doc_name):
    if not ai_doc_name: return None
    docs = list(st.session_state.pdf_library.keys())
    for d in docs:
        if ai_doc_name.lower() in d.lower() or d.lower() in ai_doc_name.lower():
            return d
    return None

def parse_and_store_data(text):
    """Updates the persistent table state by pulling structured data from the AI."""
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if not match: return
    lines = [l.strip() for l in match.group(1).strip().split('\n') if '|' in l]
    new_rows = []
    for l in lines:
        p = [i.strip() for i in l.split('|')]
        if len(p) >= 8:
            try:
                new_rows.append({
                    "sev": p[0].strip('[]'), "urg": p[1].strip('[]'), "name": p[2], 
                    "txt": p[3], "doc": p[4], "pg": p[5],
                    "min": int(re.sub(r'\D', '', p[6])), "max": int(re.sub(r'\D', '', p[7]))
                })
            except: continue
    if new_rows:
        st.session_state.summary_table = new_rows

def clean_chat_text(text):
    """Removes technical data blocks from the chat bubble for clean reading."""
    text = re.sub(r"DATA_START.*?DATA_END", "", text, flags=re.DOTALL)
    text = re.sub(r"SUGGESTIONS_START.*?SUGGESTIONS_END", "", text, flags=re.DOTALL)
    return text.strip()

# =========================================================
# 3. UI STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&family=DM+Serif+Display&display=swap');
html, body, .stApp { font-family: 'DM Sans', sans-serif; background: #f8f7f4; }
.th-header { background: #0f1923; color: white; padding: 18px 24px; border-radius: 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
.th-brand { font-family: 'DM Serif Display', serif; font-size: 24px; }
.th-card { background: white; border: 1px solid #e8e4dc; border-radius: 18px; padding: 24px; margin-bottom: 1.25rem; box-shadow: 0 2px 12px rgba(0,0,0,0.04); }
.urgency-tag { padding: 3px 10px; border-radius: 6px; font-size: 10px; font-weight: 700; text-transform: uppercase; border: 1px solid; }
.urg-immediate { background: #fff1f2; color: #be123c; border-color: #fecdd3; }
.urg-planned { background: #f0f9ff; color: #0369a1; border-color: #bae6fd; }
div.stButton > button[key^="link_"] { color: #2563eb !important; text-decoration: underline !important; font-weight: 700 !important; border: none !important; background: none !important; padding: 0 !important; text-align: left !important; }
div.stButton > button[key="priority_btn"] { background: #f97316 !important; color: white !important; font-weight: 700 !important; border-radius: 12px !important; border: none !important; padding: 12px !important;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="th-header"><div class="th-brand">Turbo<span style="color:#f97316;">Home</span> Auditor</div></div>', unsafe_allow_html=True)

with st.sidebar:
    files = st.file_uploader("Upload Disclosure Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]
    if st.button("Reset Session"):
        st.session_state.messages = []; st.session_state.summary_table = []; st.rerun()

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
        try:
            p_val = int(re.sub(r'\D', '', str(st.session_state.target_page)))
            pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600, pages_to_render=[p_val])
            if st.button("⬅ Back"): st.session_state.target_page = None; st.rerun()
        except: pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600)
    else:
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card"><strong>💬 Analysis Chat</strong>', unsafe_allow_html=True)
    chat_box = st.container(height=450)
    with chat_box:
        if not st.session_state.messages:
            st.write("Welcome. Use the orange button to start your audit.")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(clean_chat_text(m["content"]))

    if not st.session_state.messages:
        if st.button("List top issues by priority", key="priority_btn", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Analyze the property and list issues by priority, calibrating risks to the local property market found in the docs."})
            st.rerun()
    else:
        st.write("---")
        s_cols = st.columns(len(st.session_state.suggestions))
        for i, sugg in enumerate(st.session_state.suggestions):
            if s_cols[i].button(sugg, key=f"sugg_{i}"):
                st.session_state.messages.append({"role": "user", "content": sugg}); st.rerun()

    if prompt := st.chat_input("Ask about location risks..."):
        st.session_state.messages.append({"role": "user", "content": prompt}); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 5. THE SUMMARY TABLE (PERSISTENT MEMORY)
# =========================================================
if st.session_state.summary_table:
    rows = st.session_state.summary_table
    t_min, t_max = sum(r["min"] for r in rows), sum(r["max"] for r in rows)
    
    # Contextual image for home inspection and structural integrity
    
    st.markdown(f'<div class="th-card" style="background:#fff7ed; border:1px solid #fed7aa;"><div style="display:flex; justify-content:space-between; align-items:center;"><div><div style="font-family:\'DM Serif Display\',serif; font-size:42px; color:#ea580c;">{len(rows)}</div><div style="font-size:12px; font-weight:700; color:#92400e;">AUDITED RISKS</div></div><div style="text-align:right;"><div style="font-size:11px; color:#94a3b8;">EST. MARKET-ADJUSTED LIABILITY</div><div style="font-family:\'DM Serif Display\',serif; font-size:32px; color:#0f172a;">${t_min:,} – ${t_max:,}</div></div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="th-card"><strong>📊 Summary Table</strong>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([0.4, 0.6, 1, 1.8, 0.6])
    c1.caption("**SEV**"); c2.caption("**URGENCY**"); c3.caption("**ISSUE**"); c4.caption("**JUMP-LINK**"); c5.caption("**COST**")
    for i, r in enumerate(rows):
        c1, c2, c3, c4, c5 = st.columns([0.4, 0.6, 1, 1.8, 0.6])
        c1.write(f"**{r['sev']}**")
        urg_style = "urg-immediate" if "Immediate" in r['urg'] else "urg-planned"
        c2.markdown(f'<span class="urgency-tag {urg_style}">{r["urg"]}</span>', unsafe_allow_html=True)
        c3.write(r['name'])
        if c4.button(r['txt'], key=f"link_{i}"):
            match = find_best_doc_match(r['doc'])
            if match:
                st.session_state.viewing_doc, st.session_state.target_page = match, r['pg']
                st.rerun()
        c5.write(f"${r['min']:,}")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="th-card" style="text-align:center; color:#94a3b8;">Summary Table will appear here after the first audit.</div>', unsafe_allow_html=True)

# =========================================================
# 6. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing property context..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages[-10:]]
            res = client.models.generate_content(model=MODEL_NAME, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0), contents=pdf_parts + history)
            
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            parse_and_store_data(res.text) # Push data to session state
            
            s_match = re.search(r"SUGGESTIONS_START\s*\|(.*?)\|\s*SUGGESTIONS_END", res.text, re.DOTALL)
            if s_match: st.session_state.suggestions = [s.strip() for s in s_match.group(1).split('|')][:3]
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")
