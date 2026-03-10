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
End every response with a 'DATA_START' and 'DATA_END' block for the findings rail.
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
    /* Spacing fix for Streamlit header */
    .block-container { padding-top: 4.5rem !important; max-width: 1750px; }
    .stApp { background: #fcfdfe; }
    
    /* Hero Header */
    .th-header { background: #0f172a; color: white; padding: 12px 24px; border-radius: 12px; margin-bottom: 20px; }

    /* Cockpit Panels */
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .th-card-title { font-weight: 800; font-size: 1.1rem; margin-bottom: 12px; color: #0f172a; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }

    /* Suggestion Bubbles */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background: #f1f5f9 !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important;
        font-size: 11px !important; padding: 6px 10px !important; width: 100% !important; color: #1e293b !important;
    }
    
    /* Jump Link Buttons below table */
    div.stButton > button[key^="rail_jump_"] {
        color: #2563eb !important; text-decoration: underline !important; font-weight: 700 !important;
        border: none !important; background: none !important; padding: 0 !important; text-align: left !important;
    }
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
    st.session_state.suggestions = ["Summarize key risks", "Check for conflicts", "Analyze permits"]

def parse_rail_data(text):
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if match:
        lines = match.group(1).strip().split('\n')
        parsed = []
        for l in lines:
            parts = [p.strip() for p in l.split('|')]
            if len(parts) == 7:
                parsed.append({
                    "sev": parts[0], "name": parts[1], "txt": parts[2], 
                    "doc": parts[3], "pg": parts[4], 
                    "min": int(parts[5]) if parts[5].isdigit() else 0,
                    "max": int(parts[6]) if parts[6].isdigit() else 0
                })
        return parsed
    return []

# =========================================================
# 4. TOP UI
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
# 5. THE COCKPIT: TOP ROW
# =========================================================
col_view, col_chat = st.columns([1.2, 1], gap="medium")

with col_view:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">📄 Evidence Viewer</div>', unsafe_allow_html=True)
    
    doc_list = list(st.session_state.pdf_library.keys())
    idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    st.session_state.viewing_doc = st.selectbox("Current Doc", doc_list, index=idx, label_visibility="collapsed")
    
    # FIX: Bulletproof Page Jumping
    if st.session_state.target_page is not None:
        try:
            page_to_show = int(st.session_state.target_page)
            st.success(f"Focused on p.{page_to_show} in {st.session_state.viewing_doc}")
            pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=650, pages_to_render=[page_to_show])
            if st.button("⬅ Back to Full Scroll"):
                st.session_state.target_page = None
                st.rerun()
        except (ValueError, TypeError):
            pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=650)
    else:
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=650)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">🤖 Auditor Chat</div>', unsafe_allow_html=True)
    chat_box = st.container(height=480)
    with chat_box:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(re.sub(r"DATA_START.*?DATA_END", "", m["content"], flags=re.DOTALL))

    # RESTORED SUGGESTIONS
    st.write("---")
    s_cols = st.columns(len(st.session_state.suggestions))
    for i, sugg in enumerate(st.session_state.suggestions):
        if s_cols[i].button(sugg, key=f"sugg_{i}"):
            st.session_state.messages.append({"role": "user", "content": sugg})
            st.rerun()

    if prompt := st.chat_input("Ask a question about risks or costs..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. BOTTOM RAIL: SORTABLE TABLE
# =========================================================
st.markdown('<div class="th-card" style="margin-top: 15px;">', unsafe_allow_html=True)
st.markdown('<div class="th-card-title">📋 Integrated Findings Rail</div>', unsafe_allow_html=True)

last_assistant = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")
if last_assistant:
    rows = parse_rail_data(last_assistant)
    if rows:
        df = pd.DataFrame(rows)
        # Create display cost range for clean sorting/viewing
        df['Est. Cost'] = df.apply(lambda r: f"${r['min']:,} - ${r['max']:,}", axis=1)
        
        # DISPLAY SORTABLE TABLE
        st.dataframe(
            df[['sev', 'name', 'Est. Cost']], 
            use_container_width=True, 
            hide_index=True,
            column_config={"sev": "Severity", "name": "Risk Item", "Est. Cost": "2026 Estimate"}
        )
        
        # INTERACTIVE JUMP BUTTONS BELOW TABLE
        st.caption("📍 Click an item below to view the evidence in the PDF:")
        jump_cols = st.columns(min(len(rows), 4))
        for i, r in enumerate(rows[:4]):
            if jump_cols[i].button(f"🔍 {r['name']}", key=f"rail_jump_{i}"):
                if r['doc'] in st.session_state.pdf_library:
                    st.session_state.viewing_doc, st.session_state.target_page = r['doc'], int(r['pg'])
                    st.rerun()
    else: st.caption("No data in last response.")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 7. AI ENGINE (HEARTBEAT)
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing cross-document context..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            
            # Primary Audit
            res = client.models.generate_content(
                model=MODEL_NAME, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})

            # Shadow Call for Suggestions (Under 7 Words)
            s_res = client.models.generate_content(model=MODEL_NAME, 
                contents=[f"Based on: '{res.text}', suggest 3 logical buyer follow-ups (under 7 words). Output text separated by |."])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            st.rerun()
        except Exception as e:
            st.error(f"Audit Error: {e}")
