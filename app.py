import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE PLAYBOOK
# =========================================================
def get_system_prompt(is_financial_mode):
    prompt = """
    TurboHome Disclosure Analysis Playbook
    Analyze all PDFs for material risks and discrepancies.
    
    --- DATA BLOCK RULE ---
    End every response with a 'DATA_START' and 'DATA_END' block.
    Format each line as: [Severity] | [Issue Name] | [Text to Click] | [Doc Name] | [Page X] | [Est Cost]
    """
    if is_financial_mode:
        prompt += "\nInclude 2026 repair costs for the [Est Cost] column."
    return prompt

# =========================================================
# 2. PAGE CONFIG & UI FIXES
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    /* Ensure the app content starts below the Streamlit header */
    .block-container { padding-top: 5rem !important; max-width: 1750px; }
    
    /* Panel Styling */
    .th-card { 
        background: white; 
        border: 1px solid #e2e8f0; 
        border-radius: 16px; 
        padding: 20px; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* Make Suggestion Bubbles look like small, clickable tags */
    div.stButton > button[key^="sugg_"] {
        background: #f1f5f9 !important;
        color: #1e293b !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        font-size: 11px !important;
        padding: 4px 8px !important;
        width: 100% !important;
    }

    /* Jump Link styling for the rail */
    div.stButton > button[key^="rail_jump_"] {
        color: #2563eb !important;
        text-decoration: underline !important;
        font-weight: 700 !important;
        border: none !important;
        background: none !important;
        text-align: left !important;
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
if "suggestions" not in st.session_state: st.session_state.suggestions = ["Highlight risks", "Check permits", "Compare documents"]

def parse_rail_data(text):
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if match:
        lines = match.group(1).strip().split('\n')
        return [dict(zip(["sev", "name", "txt", "doc", "pg", "cost"], [p.strip() for p in l.split('|')])) 
                for l in lines if len(l.split('|')) == 6]
    return []

# =========================================================
# 4. HEADER & SIDEBAR
# =========================================================
h1, h2 = st.columns([3, 1])
with h1: st.title("🏠 TurboHome Disclosure Analysis")
with h2: financial_mode = st.toggle("💰 Financial Mode", value=True)

with st.sidebar:
    st.title("📂 Files")
    files = st.file_uploader("Upload PDF Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("👈 Upload your documents in the sidebar to begin the audit.")
    st.stop()

# =========================================================
# 5. THE COCKPIT
# =========================================================
col_pdf, col_chat = st.columns([1.2, 1], gap="medium")

with col_pdf:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.subheader("📄 Evidence Viewer")
    docs = list(st.session_state.pdf_library.keys())
    cur_idx = docs.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in docs else 0
    st.session_state.viewing_doc = st.selectbox("Switch Document", docs, index=cur_idx)
    
    if st.session_state.target_page:
        st.caption(f"📍 Focusing on Page {st.session_state.target_page}")
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=700, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full View"): st.session_state.target_page = None; st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=700)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.subheader("🤖 Auditor Chat")
    
    # FIX: Explicit height and placement of the chat box
    chat_box = st.container(height=500)
    with chat_box:
        if not st.session_state.messages:
            st.write("Hello! I'm ready to audit your documents. Ask me anything or use a suggestion below.")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(re.sub(r"DATA_START.*?DATA_END", "", m["content"], flags=re.DOTALL))

    # SUGGESTION BUBBLES (Directly above input)
    s_cols = st.columns(len(st.session_state.suggestions))
    for i, sugg in enumerate(st.session_state.suggestions):
        if s_cols[i].button(sugg, key=f"sugg_{i}"):
            st.session_state.messages.append({"role": "user", "content": sugg})
            st.rerun()

    # FIX: Input field is now outside the container to ensure it stays visible
    if prompt := st.chat_input("Ask a question about the disclosures..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. THE RAIL (BOTTOM)
# =========================================================
st.markdown('<div class="th-card">', unsafe_allow_html=True)
st.subheader("📋 Integrated Findings Rail")
last_assistant = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")
if last_assistant:
    rows = parse_rail_data(last_assistant)
    if rows:
        c1, c2, c3, c4 = st.columns([0.4, 1, 2, 0.4])
        c1.caption("**SEVERITY**"); c2.caption("**ISSUE**"); c3.caption("**JUMP-LINK**"); c4.caption("**COST**")
        for i, r in enumerate(rows):
            c1, c2, c3, c4 = st.columns([0.4, 1, 2, 0.4])
            c1.markdown(f'**{r["sev"]}**')
            c2.write(r['name'])
            if c3.button(r['txt'], key=f"rail_jump_{i}"):
                if r['doc'] in st.session_state.pdf_library:
                    st.session_state.viewing_doc = r['doc']
                    st.session_state.target_page = int(r['pg'])
                    st.rerun()
            c4.write(r['cost'])
    else: st.caption("No issues found in last audit.")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 7. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing cross-doc context..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            
            res = client.models.generate_content(
                model="gemini-3-flash-preview", 
                config=types.GenerateContentConfig(system_instruction=get_system_prompt(financial_mode), temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})

            # Shadow Call for Contextual Suggestions
            s_res = client.models.generate_content(model="gemini-3-flash-preview", 
                contents=[f"Based on: '{res.text}', suggest 3 logical buyer follow-ups (under 7 words). Output text separated by |."])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            st.rerun()
        except Exception as e:
            st.error(f"Audit Error: {e}")
