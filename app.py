import re
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE PLAYBOOK (STRICT DATA STRUCTURE)
# =========================================================
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
Analyze all PDFs for material risks. End with a DATA block.

--- DATA BLOCK RULE ---
End every response with a 'DATA_START' and 'DATA_END' block.
Format: [Severity] | [Issue Name] | [Text to Click] | [Doc Name] | [Page X] | [Min Cost] | [Max Cost]
Severities: High, Medium, Low.
Example: High | Foundation | Slab cracks | Home Inspection | 14 | 15000 | 25000
"""

# =========================================================
# 2. PAGE CONFIG & STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 4.5rem !important; max-width: 1750px; }
    .stApp { background: #fcfdfe; }
    
    /* Styled Header */
    .th-header { background: #0f172a; color: white; padding: 12px 24px; border-radius: 12px; margin-bottom: 20px; }
    
    /* Cost Range Pills */
    .cost-pill {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 2px 8px;
        font-family: monospace;
        font-weight: 600;
        color: #1e293b;
    }
    .cost-min { color: #16a34a; }

    /* Rail Link */
    div.stButton > button[key^="rail_jump_"] {
        color: #2563eb !important; text-decoration: underline !important; font-weight: 700 !important;
        border: none !important; background: none !important; padding: 0 !important; text-align: left !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "target_page" not in st.session_state: st.session_state.target_page = None
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "suggestions" not in st.session_state: st.session_state.suggestions = ["Highlight risks", "Check permits"]

def parse_rail_data(text):
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if match:
        lines = match.group(1).strip().split('\n')
        parsed = []
        for l in lines:
            p = [i.strip() for i in l.split('|')]
            if len(p) == 7:
                parsed.append({
                    "sev": p[0], "name": p[1], "txt": p[2], 
                    "doc": p[3], "pg": p[4], "min": int(p[5]), "max": int(p[6])
                })
        return parsed
    return []

# =========================================================
# 4. TOP UI
# =========================================================
st.markdown('<div class="th-header"><strong>TurboHome Disclosure Analysis</strong></div>', unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Files")
    files = st.file_uploader("Upload PDF Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("Upload documents to begin.")
    st.stop()

# =========================================================
# 5. COCKPIT
# =========================================================
col_pdf, col_chat = st.columns([1.2, 1], gap="medium")

with col_pdf:
    st.markdown('<div class="th-card" style="background:white; padding:15px; border-radius:12px; border:1px solid #e2e8f0;">', unsafe_allow_html=True)
    doc_list = list(st.session_state.pdf_library.keys())
    idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    st.session_state.viewing_doc = st.selectbox("Switch View", doc_list, index=idx)
    
    pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], 
               height=650, 
               pages_to_render=[st.session_state.target_page] if st.session_state.target_page else None)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    chat_container = st.container(height=520)
    with chat_container:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(re.sub(r"DATA_START.*?DATA_END", "", m["content"], flags=re.DOTALL))

    # Suggestions
    s_cols = st.columns(len(st.session_state.suggestions))
    for i, sugg in enumerate(st.session_state.suggestions):
        if s_cols[i].button(sugg, key=f"sugg_{i}"):
            st.session_state.messages.append({"role": "user", "content": sugg})
            st.rerun()

    if prompt := st.chat_input("Analyze..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

# =========================================================
# 6. SORTABLE FINDINGS TABLE (THE FIX)
# =========================================================
st.write("---")
st.subheader("📋 Integrated Findings Rail")

last_assistant = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")

if last_assistant:
    rows = parse_rail_data(last_assistant)
    if rows:
        df = pd.DataFrame(rows)
        # Convert costs to display ranges but keep raw numbers for sorting
        df['Display Cost'] = df.apply(lambda r: f"${r['min']:,} - {r['max']:,}", axis=1)
        
        # We use a real dataframe for SORTABILITY
        st.dataframe(
            df[['sev', 'name', 'txt', 'Display Cost']], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "sev": "Severity",
                "name": "Issue",
                "txt": "Description",
                "Display Cost": "Est. Cost (2026)"
            }
        )
        
        # Quick-jump buttons below the table for interactivity
        st.caption("📍 Click a description link in chat or use these quick-jumps:")
        jump_cols = st.columns(min(len(rows), 4))
        for i, r in enumerate(rows[:4]):
            if jump_cols[i].button(f"🔍 {r['name']}", key=f"rail_jump_{i}"):
                st.session_state.viewing_doc, st.session_state.target_page = r['doc'], int(r['pg'])
                st.rerun()
    else: st.caption("No data found.")

# =========================================================
# 7. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            
            res = client.models.generate_content(
                model="gemini-3-flash-preview", 
                config=types.GenerateContentConfig(system_instruction=get_system_prompt(True), temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            # Contextual Suggestions
            s_res = client.models.generate_content(model="gemini-3-flash-preview", 
                contents=[f"Based on: '{res.text}', suggest 3 logical buyer follow-ups (under 7 words). Output text separated by |."])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
