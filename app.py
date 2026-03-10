import re
import html
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE DYNAMIC PLAYBOOK
# =========================================================
def get_system_prompt(is_financial_mode):
    base_prompt = """
    TurboHome Disclosure Analysis Playbook
    You are a professional real estate auditor. You are analyzing multiple PDF documents for a homebuyer.

    --- CORE CATEGORIES ---
    Organize your findings into these sections:
    1. Cross-Document Conflicts: (e.g., Seller says "No leaks", but Inspector found a leak).
    2. Inspection Findings: (From Home, Pest, or Roof reports).
    3. Seller Disclosures: (From TDS or SPQ).
    4. Hazard Disclosures: (From NHD reports).
    5. Follow-up Questions: (Items requiring more info from the seller).

    --- CITATION RULE ---
    Instead of separate citations, wrap the SPECIFIC issue text in this tag:
    :jump[Description of the issue]{doc="Document Name" page=X}
    Example: "The :jump[water heater is reaching the end of its useful life]{doc="Home Inspection" page=18} and requires replacement."
    """
    
    financial_addon = """
    --- FINANCIAL ESTIMATION MODE (ACTIVE) ---
    For every physical defect found, you MUST provide a "TurboHome Repair Estimate."
    1. Use 2026 California/National construction averages for labor and materials.
    2. Format as: :jump[Issue Description]{doc="Name" page=X} | Est: $Min-$Max.
    3. At the end of your response, provide a 'TOTAL ESTIMATED LIABILITY' range.
    """
    
    return base_prompt + (financial_addon if is_financial_mode else "")

# =========================================================
# 2. PAGE CONFIG & ADVANCED COCKPIT STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Disclosure Analysis", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    /* FIX: Standard Streamlit Header Spacing */
    .block-container {
        padding-top: 4.5rem !important;
        max-width: 1750px;
    }

    /* THE AUDITOR COCKPIT THEME */
    html, body, [class*="css"] { font-size: 13.5px; font-family: 'Inter', sans-serif; color: #1e293b; }
    .stApp { background: #f8fafc; }
    
    /* Header & Dashboard */
    .th-header { background: #0f172a; color: white; padding: 12px 20px; border-radius: 12px; margin-bottom: 12px; }
    .cost-dashboard { 
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
        color: #38bdf8; padding: 15px; border-radius: 16px; margin-bottom: 15px; border: 1px solid #334155; 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .cost-val { font-size: 1.6rem; font-weight: 800; color: #f8fafc; }

    /* Cockpit Panels */
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 16px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .th-card-title { font-weight: 800; font-size: 1.1rem; margin-bottom: 12px; color: #0f172a; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }

    /* Inline Link Buttons (Jump-Links) */
    div.stButton > button {
        border: none !important; padding: 0px !important; background-color: transparent !important;
        color: #2563eb !important; text-decoration: underline !important; font-size: inherit !important;
        font-weight: 700 !important; display: inline !important; vertical-align: baseline !important;
    }
    div.stButton > button:hover { color: #1d4ed8 !important; }

    /* Dynamic Suggestion Bubbles */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background: #ffffff !important; color: #334155 !important; border: 1px solid #e2e8f0 !important;
        text-decoration: none !important; border-radius: 10px !important; padding: 6px 10px !important;
        font-size: 12px !important; font-weight: 600 !important; width: 100% !important; line-height: 1.2 !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "target_page" not in st.session_state: st.session_state.target_page = None
if "suggestions" not in st.session_state: st.session_state.suggestions = ["Highlight risks", "Check permits", "Compare docs"]
if "est_min" not in st.session_state: st.session_state.est_min = 0
if "est_max" not in st.session_state: st.session_state.est_max = 0

# =========================================================
# 4. RENDERING ENGINE (JUMP-LINK PARSER)
# =========================================================
def render_jump_text(text, key_prefix):
    pattern = r'(:jump\[[^\]]+\]\{doc="[^"]+"\s+page=\d+\})'
    parts = re.split(pattern, text)
    for idx, part in enumerate(parts):
        match = re.match(r':jump\[(?P<txt>[^\]]+)\]\{doc="(?P<doc>[^"]+)"\s+page=(?P<pg>\d+)\}', part)
        if match:
            issue_text, doc_name, page_num = match.group('txt'), match.group('doc'), int(match.group('pg'))
            if st.button(issue_text, key=f"{key_prefix}_{idx}_{page_num}"):
                st.session_state.viewing_doc = doc_name
                st.session_state.target_page = page_num
                st.rerun()
        else:
            if part.strip(): st.markdown(part, unsafe_allow_html=True)

# =========================================================
# 5. TOP CONTROLS & HEADER
# =========================================================
header_col1, header_col2 = st.columns([2.5, 1])

with header_col1:
    st.markdown('<div class="th-header"><strong>TurboHome Disclosure Analysis</strong></div>', unsafe_allow_html=True)

with header_col2:
    financial_mode = st.toggle("💰 Repair Cost Estimator", value=False)

if financial_mode:
    st.markdown(f"""
    <div class="cost-dashboard">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div><small>MIN REPAIR LIABILITY</small><br><span class="cost-val">${st.session_state.est_min:,}</span></div>
            <div><small>MAX REPAIR LIABILITY</small><br><span class="cost-val">${st.session_state.est_max:,}</span></div>
            <div><small>NEGOTIATION LEVERAGE</small><br><span class="cost-val">HIGH</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# 6. SIDEBAR & FILE LOADING
# =========================================================
with st.sidebar:
    st.title("📂 Document Room")
    files = st.file_uploader("Upload Disclosure Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("👋 Welcome. Please upload disclosure PDFs in the sidebar to enter the cockpit.")
    st.stop()

# =========================================================
# 7. MAIN COCKPIT: TOP ROW (VIEWER & CHAT)
# =========================================================
col_pdf, col_chat = st.columns([1.3, 1], gap="medium")

with col_pdf:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">📄 Evidence Viewer</div>', unsafe_allow_html=True)
    
    doc_list = list(st.session_state.pdf_library.keys())
    cur_idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    selected_doc = st.selectbox("Select Doc", doc_list, index=cur_idx, label_visibility="collapsed")
    st.session_state.viewing_doc = selected_doc

    if st.session_state.target_page:
        st.success(f"Focusing on p.{st.session_state.target_page} in {selected_doc}")
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full View", key="reset_pdf"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">🤖 Auditor Chat</div>', unsafe_allow_html=True)
    
    chat_box = st.container(height=480)
    with chat_box:
        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                render_jump_text(msg["content"], f"chat_{m_idx}")

    # SUGGESTION BUBBLES
    st.write("---")
    s_cols = st.columns(len(st.session_state.suggestions))
    for i, sugg in enumerate(st.session_state.suggestions):
        if s_cols[i].button(sugg, key=f"sugg_{i}"):
            st.session_state.messages.append({"role": "user", "content": sugg})
            st.rerun()

    if prompt := st.chat_input("Ask Auditor..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 8. MAIN COCKPIT: BOTTOM ROW (FINDINGS RAIL)
# =========================================================
st.markdown('<div class="th-card" style="margin-top: 15px;">', unsafe_allow_html=True)
st.markdown('<div class="th-card-title">📋 Integrated Findings Rail</div>', unsafe_allow_html=True)

last_assistant = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")
if last_assistant:
    render_jump_text(last_assistant, "rail")
else:
    st.caption("Perform an audit to populate the findings rail.")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 9. AI ENGINE (DUAL-CONTEXT CALL)
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    
    with st.spinner("TurboHome is cross-referencing documents..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            
            # Primary Generation
            res = client.models.generate_content(
                model=MODEL_NAME, 
                config=types.GenerateContentConfig(system_instruction=get_system_prompt(financial_mode), temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})

            # Cost Parsing (If Financial Mode Active)
            if financial_mode:
                prices = re.findall(r'\$(\d{1,3}(?:,\d{3})*)', res.text)
                if len(prices) >= 2:
                    st.session_state.est_min = int(prices[-2].replace(',', ''))
                    st.session_state.est_max = int(prices[-1].replace(',', ''))

            # Shadow Suggestion Call
            s_prompt = f"Based on: '{res.text}', suggest 3 logical follow-ups (under 7 words each). Output ONLY text separated by |."
            s_res = client.models.generate_content(model=MODEL_NAME, contents=[s_prompt])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            
            st.rerun()
        except Exception as e:
            st.error(f"Audit Error: {e}")
