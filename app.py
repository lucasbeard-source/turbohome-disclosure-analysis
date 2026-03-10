import re
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE AUDITOR PLAYBOOK
# =========================================================
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
You are a professional real estate auditor. Analyze all documents for material risks.

--- DATA BLOCK RULE ---
ONLY include a 'DATA_START' block if you are identifying NEW or UPDATED risks.
Format: [Severity] | [Issue Name] | [Text to Click] | [Doc Name] | [Page X] | [Min Cost] | [Max Cost]
Severities: High, Medium, Low. 
"""

# =========================================================
# 2. PAGE CONFIG & STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 4.5rem !important; max-width: 1750px; }
    .stApp { background: #fcfdfe; }
    .th-header { background: #0f172a; color: white; padding: 12px 24px; border-radius: 12px; margin-bottom: 20px; }
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 20px; }
    
    /* Standard Suggestion Bubbles */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background: #f1f5f9 !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important;
        font-size: 11px !important; padding: 6px 10px !important; width: 100% !important; color: #1e293b !important;
    }

    /* ORANGE PRIORITY BUTTON */
    div.stButton > button[key="priority_btn"] {
        background-color: #f97316 !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        padding: 15px 25px !important;
        border: none !important;
        width: 100% !important;
        font-size: 14px !important;
        box-shadow: 0 4px 14px 0 rgba(249, 115, 22, 0.39) !important;
    }

    /* Jump-Links */
    div.stButton > button[key^="link_"] {
        color: #2563eb !important; text-decoration: underline !important; font-weight: 700 !important;
        border: none !important; background: none !important; padding: 0 !important; text-align: left !important;
    }

    .sev-badge { padding: 4px 10px; border-radius: 999px; font-weight: 800; font-size: 10px; }
    .sev-high { background: #fee2e2; color: #b91c1c; }
    .sev-medium { background: #fef3c7; color: #b45309; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "target_page" not in st.session_state: st.session_state.target_page = None
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "summary_table" not in st.session_state: st.session_state.summary_table = []
if "suggestions" not in st.session_state: 
    st.session_state.suggestions = ["List top issues by priority", "Learn about wiring risks", "Explain foundation hazards"]

def find_best_doc_match(ai_doc_name):
    if not ai_doc_name: return None
    uploaded_files = list(st.session_state.pdf_library.keys())
    for real_name in uploaded_files:
        if ai_doc_name.lower() in real_name.lower() or real_name.lower() in ai_doc_name.lower():
            return real_name
    return None

def parse_and_store_data(text):
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if match:
        lines = [l.strip() for l in match.group(1).strip().split('\n') if '|' in l]
        new_rows = []
        for l in lines:
            p = [i.strip() for i in l.split('|')]
            if len(p) >= 6:
                new_rows.append({"sev": p[0], "name": p[1], "txt": p[2], "doc": p[3], "pg": p[4], "min": p[5], "max": p[6] if len(p)>6 else p[5]})
        st.session_state.summary_table = new_rows

# =========================================================
# 4. TOP UI
# =========================================================
st.markdown('<div class="th-header"><strong>TurboHome Disclosure Analysis</strong></div>', unsafe_allow_html=True)

with st.sidebar:
    files = st.file_uploader("Upload Disclosure Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.stop()

# =========================================================
# 5. COCKPIT
# =========================================================
col_view, col_chat = st.columns([1.2, 1], gap="medium")

with col_view:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    docs = list(st.session_state.pdf_library.keys())
    idx = docs.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in docs else 0
    st.session_state.viewing_doc = st.selectbox("Doc", docs, index=idx, label_visibility="collapsed")
    
    if st.session_state.target_page:
        try:
            p_val = int(re.sub(r'[^\d]', '', str(st.session_state.target_page)))
            pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600, pages_to_render=[p_val])
            if st.button("⬅ Back"): st.session_state.target_page = None; st.rerun()
        except: pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600)
    else:
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown("<strong>💬 TurboHome Analysis Chat</strong>", unsafe_allow_html=True)
    chat_box = st.container(height=420)
    with chat_box:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(re.sub(r"DATA_START.*?DATA_END", "", m["content"], flags=re.DOTALL))

    # --- THE SUGGESTION LOGIC FIX ---
    if not st.session_state.messages:
        # Step 1: Initial State - Only show Orange Button
        if st.button("List top issues by priority", key="priority_btn"):
            st.session_state.messages.append({"role": "user", "content": "List top issues by priority"})
            st.rerun()
    else:
        # Step 2: Normal 3x Suggestions after first interaction
        st.write("---")
        s_cols = st.columns(len(st.session_state.suggestions))
        for i, sugg in enumerate(st.session_state.suggestions):
            if s_cols[i].button(sugg, key=f"sugg_{i}"):
                st.session_state.messages.append({"role": "user", "content": sugg})
                st.rerun()

    if prompt := st.chat_input("Ask about risks..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. SUMMARY TABLE (PERSISTENT)
# =========================================================
st.markdown('<div class="th-card">', unsafe_allow_html=True)
st.markdown("<strong>📊 Summary Table</strong>", unsafe_allow_html=True)
if st.session_state.summary_table:
    rows = st.session_state.summary_table
    c1, c2, c3, c4 = st.columns([0.4, 1, 2, 0.6])
    c1.caption("**SEVERITY**"); c2.caption("**ISSUE**"); c3.caption("**HYPERLINK CITATION**"); c4.caption("**EST COST**")
    for i, r in enumerate(rows):
        c1, c2, c3, c4 = st.columns([0.4, 1, 2, 0.6])
        c1.markdown(f'<span class="sev-badge sev-{r["sev"].lower()}">{r["sev"].upper()}</span>', unsafe_allow_html=True)
        c2.write(f"**{r['name']}**")
        if c3.button(r['txt'], key=f"link_{i}"):
            match = find_best_doc_match(r['doc'])
            if match:
                st.session_state.viewing_doc, st.session_state.target_page = match, r['pg']
                st.rerun()
        try:
            min_c, max_c = int(re.sub(r'[^\d]', '', str(r['min']))), int(re.sub(r'[^\d]', '', str(r['max'])))
            c4.markdown(f"**${min_c:,} - {max_c:,}**")
        except: c4.write(f"{r['min']} - {r['max']}")
else:
    st.info("No audit data. Click the orange button above to begin.")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 7. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            res = client.models.generate_content(
                model=MODEL_NAME, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            parse_and_store_data(res.text)
            
            # Update suggestions for Step 2
            ed_prompt = f"Based on: '{res.text}', suggest 3 EDUCATIONAL follow-ups (under 7 words). Format: Q1 | Q2 | Q3"
            s_res = client.models.generate_content(model=MODEL_NAME, contents=[ed_prompt])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")
