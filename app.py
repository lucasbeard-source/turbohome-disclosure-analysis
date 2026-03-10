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
End every response with a 'DATA_START' and 'DATA_END' block for the Summary Table.
Format each line exactly as: [Severity] | [Issue Name] | [Text to Click] | [Doc Name] | [Page X] | [Min Cost] | [Max Cost]
Severities: High, Medium, Low.

Example:
DATA_START
High | Structural Movement | Large cracks in crawlspace | Home Inspection | 14 | 15000 | 25000
Medium | Electrical Hazard | Live knob and tube wiring | Home Inspection | 22 | 8000 | 12000
DATA_END
"""

# =========================================================
# 2. PAGE CONFIG & MODERN STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 4.5rem !important; max-width: 1750px; }
    .stApp { background: #fcfdfe; }
    .th-header { background: #0f172a; color: white; padding: 12px 24px; border-radius: 12px; margin-bottom: 20px; }
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .th-card-title { font-weight: 800; font-size: 1.1rem; margin-bottom: 12px; color: #0f172a; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }

    /* The Hyperlink Citation Button Styling */
    div.stButton > button[key^="link_"] {
        color: #2563eb !important; text-decoration: underline !important; font-weight: 700 !important;
        border: none !important; background: none !important; padding: 0 !important; text-align: left !important;
        font-size: 13px !important;
    }

    /* Suggestion Bubbles */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background: #f1f5f9 !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important;
        font-size: 11px !important; padding: 6px 10px !important; width: 100% !important; color: #1e293b !important;
    }

    /* Table Badges */
    .sev-badge { padding: 2px 8px; border-radius: 999px; font-weight: 800; font-size: 10px; }
    .sev-high { background: #fee2e2; color: #b91c1c; }
    .sev-medium { background: #fef3c7; color: #b45309; }
    .sev-low { background: #f1f5f9; color: #475569; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE & HELPERS
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "target_page" not in st.session_state: st.session_state.target_page = None
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "suggestions" not in st.session_state: 
    st.session_state.suggestions = ["Highlight risks", "Check for conflicts", "Analyze permits"]

def parse_data_block(text):
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if match:
        lines = match.group(1).strip().split('\n')
        parsed = []
        for l in lines:
            parts = [p.strip() for p in l.split('|')]
            if len(parts) == 7:
                parsed.append({
                    "sev": parts[0], "name": parts[1], "txt": parts[2], 
                    "doc": parts[3], "pg": parts[4], "min": parts[5], "max": parts[6]
                })
        return parsed
    return []

# =========================================================
# 4. TOP UI & SIDEBAR
# =========================================================
st.markdown('<div class="th-header"><strong>TurboHome Disclosure Analysis</strong></div>', unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Files")
    files = st.file_uploader("Upload Disclosure Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("Upload documents in the sidebar to begin the audit.")
    st.stop()

# =========================================================
# 5. THE COCKPIT: VIEWER & CHAT
# =========================================================
col_view, col_chat = st.columns([1.2, 1], gap="medium")

with col_view:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">📄 Evidence Viewer</div>', unsafe_allow_html=True)
    
    docs = list(st.session_state.pdf_library.keys())
    idx = docs.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in docs else 0
    st.session_state.viewing_doc = st.selectbox("Current Doc", docs, index=idx, label_visibility="collapsed")
    
    if st.session_state.target_page is not None:
        try:
            page_val = int(st.session_state.target_page)
            st.success(f"Focused on p.{page_val} in {st.session_state.viewing_doc}")
            pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600, pages_to_render=[page_val])
            if st.button("⬅ Back to Full Scroll"):
                st.session_state.target_page = None
                st.rerun()
        except: pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600)
    else:
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=600)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">💬 TurboHome Analysis Chat</div>', unsafe_allow_html=True)
    chat_box = st.container(height=450)
    with chat_box:
        if not st.session_state.messages:
            st.write("Welcome. Upload documents and ask about risks, discrepancies, or costs.")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(re.sub(r"DATA_START.*?DATA_END", "", m["content"], flags=re.DOTALL))

    # Suggestions
    s_cols = st.columns(len(st.session_state.suggestions))
    for i, sugg in enumerate(st.session_state.suggestions):
        if s_cols[i].button(sugg, key=f"sugg_{i}"):
            st.session_state.messages.append({"role": "user", "content": sugg})
            st.rerun()

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. SUMMARY TABLE (FIXED)
# =========================================================
st.markdown('<div class="th-card">', unsafe_allow_html=True)
st.markdown('<div class="th-card-title">📊 Summary Table</div>', unsafe_allow_html=True)

last_assistant = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")
if last_assistant:
    rows = parse_data_block(last_assistant)
    if rows:
        c1, c2, c3, c4 = st.columns([0.4, 1, 2, 0.4])
        c1.caption("**SEVERITY**"); c2.caption("**ISSUE**"); c3.caption("**HYPERLINK CITATION (CLICK TO JUMP)**"); c4.caption("**EST COST**")
        
        for i, r in enumerate(rows):
            c1, c2, c3, c4 = st.columns([0.4, 1, 2, 0.4])
            sev_class = f"sev-{r['sev'].lower()}"
            c1.markdown(f'<span class="sev-badge {sev_class}">{r["sev"].upper()}</span>', unsafe_allow_html=True)
            c2.write(f"**{r['name']}**")
            
            if c3.button(r['txt'], key=f"link_{i}"):
                if r['doc'] in st.session_state.pdf_library:
                    st.session_state.viewing_doc = r['doc']
                    st.session_state.target_page = int(r['pg'])
                    st.rerun()
                else: st.error("Citing missing document.")
            
            # --- FIX: SANITIZE NUMBERS BEFORE FORMATTING ---
            try:
                # Strip commas/dollar signs and convert to int for clean formatting
                clean_min = int(re.sub(r'[^\d]', '', str(r['min'])))
                clean_max = int(re.sub(r'[^\d]', '', str(r['max'])))
                c4.write(f"${clean_min:,} - ${clean_max:,}")
            except:
                # Fallback: Just show the raw string if parsing fails
                c4.write(f"${r['min']} - ${r['max']}")
    else: st.caption("No structured data found.")
else: st.caption("Audit results will appear here.")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 7. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing risk & cross-referencing files..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            
            res = client.models.generate_content(
                model=MODEL_NAME, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})

            # Shadow Call for Suggestions
            s_res = client.models.generate_content(model=MODEL_NAME, 
                contents=[f"Based on: '{res.text}', suggest 3 logical follow-ups (under 7 words). Output text separated by |."])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
