import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. DYNAMIC PLAYBOOK (INCLUDES FINANCIAL LOGIC)
# =========================================================
def get_system_prompt(is_financial_mode):
    base_prompt = """
    TurboHome Disclosure Analysis Playbook
    You are a professional real estate auditor. Analyze all documents for discrepancies.
    
    --- CITATION RULE ---
    Wrap issue descriptions in this tag: :jump[Description of the issue]{doc="Document Name" page=X}
    """
    
    financial_addon = """
    --- FINANCIAL ESTIMATION MODE (ACTIVE) ---
    For every defect found, you MUST provide a "TurboHome Repair Estimate."
    1. Estimate costs based on 2026 California/National construction averages.
    2. Format as: :jump[Issue Description]{doc="Name" page=X} | Est: $Min-$Max.
    3. At the end of your response, provide a 'PROBABLE TOTAL LIABILITY' range.
    """
    
    return base_prompt + (financial_addon if is_financial_mode else "")

# =========================================================
# 2. COCKPIT STYLING (WITH FINANCIAL ACCENTS)
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 13px; font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    .block-container { max-width: 1750px; padding-top: 1rem; }
    
    /* Header & Toggle Area */
    .th-hero { background: #0f172a; color: white; padding: 12px 20px; border-radius: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
    
    /* Financial Dashboard */
    .cost-dashboard { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: #38bdf8; padding: 15px; border-radius: 16px; margin-bottom: 15px; border: 1px solid #334155; }
    .cost-val { font-size: 1.5rem; font-weight: 800; color: #f8fafc; }
    
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 16px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    
    /* Inline Link Buttons */
    div.stButton > button {
        border: none !important; padding: 0px !important; background-color: transparent !important;
        color: #2563eb !important; text-decoration: underline !important; font-size: inherit !important;
        font-weight: 700 !important; display: inline !important; vertical-align: baseline !important;
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
if "suggestions" not in st.session_state: st.session_state.suggestions = ["Summarize risks", "Check permits"]
if "est_min" not in st.session_state: st.session_state.est_min = 0
if "est_max" not in st.session_state: st.session_state.est_max = 0

# =========================================================
# 4. HEADER & FINANCIAL TOGGLE
# =========================================================
with st.container():
    col_logo, col_toggle = st.columns([2, 1])
    with col_logo:
        st.markdown('<div class="th-hero"><strong>TurboHome Auditor Cockpit</strong></div>', unsafe_allow_html=True)
    with col_toggle:
        financial_mode = st.toggle("💰 Activate Repair Cost Estimator", value=False, help="Uses AI to predict 2026 repair costs and negotiation leverage.")

# =========================================================
# 5. UI: TOP ROW (VIEWER & CHAT)
# =========================================================
with st.sidebar:
    st.title("📂 Files")
    files = st.file_uploader("Upload PDF Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("Upload documents to start.")
    st.stop()

# IF FINANCIAL MODE: Show Dashboard
if financial_mode:
    
    with st.container():
        st.markdown(f"""
        <div class="cost-dashboard">
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div><small>MIN EST. LIABILITY</small><br><span class="cost-val">${st.session_state.est_min:,}</span></div>
                <div><small>MAX EST. LIABILITY</small><br><span class="cost-val">${st.session_state.est_max:,}</span></div>
                <div><small>NEGOTIATION LEVERAGE</small><br><span class="cost-val">HIGH</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

col_pdf, col_chat = st.columns([1.3, 1], gap="medium")

with col_pdf:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    doc_list = list(st.session_state.pdf_library.keys())
    cur_idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    selected_doc = st.selectbox("Select Doc", doc_list, index=cur_idx, label_visibility="collapsed")
    st.session_state.viewing_doc = selected_doc

    if st.session_state.target_page:
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full View"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    # (Chat container logic remains same as previous turn)
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    # ... [Chat Rendering & Input Logic]
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. AI ENGINE
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
                config=types.GenerateContentConfig(system_instruction=get_system_prompt(financial_mode), temperature=0.0),
                contents=pdf_parts + history
            )
            
            # PARSING LOGIC: Extract totals for the dashboard
            if financial_mode:
                # Simple regex to find $ amounts in the AI's "Total Liability" section
                prices = re.findall(r'\$(\d{1,3}(?:,\d{3})*)', res.text)
                if len(prices) >= 2:
                    st.session_state.est_min = int(prices[-2].replace(',', ''))
                    st.session_state.est_max = int(prices[-1].replace(',', ''))

            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
