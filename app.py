import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE MULTI-DOC PLAYBOOK
# =========================================================
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
(Your full playbook text here...)

--- CITATION RULE ---
Wrap issue descriptions in this tag: :jump[Description]{doc="Name" page=X}
Example: ":jump[Roof has significant granular loss]{doc="Roof Report" page=2}."
"""

# =========================================================
# 2. COCKPIT STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 13px; font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    .block-container { max-width: 1750px; padding-top: 1rem; }
    
    .th-hero { background: #0f172a; color: white; padding: 10px 20px; border-radius: 12px; margin-bottom: 12px; }
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 16px; height: 100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .th-card-title { font-weight: 800; font-size: 1.1rem; margin-bottom: 12px; color: #0f172a; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }

    /* Inline Link Buttons */
    div.stButton > button {
        border: none !important; padding: 0px !important; background-color: transparent !important;
        color: #2563eb !important; text-decoration: underline !important; font-size: inherit !important;
        font-weight: 700 !important; display: inline !important; vertical-align: baseline !important;
    }

    /* Suggestion Bubbles - Short & Punchy */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background: #ffffff !important;
        color: #2563eb !important;
        border: 1px solid #e2e8f0 !important;
        text-decoration: none !important;
        border-radius: 10px !important;
        padding: 6px 10px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        width: 100% !important;
        line-height: 1.2 !important;
    }
    div[data-testid="column"] .stButton > button[key^="sugg_"]:hover {
        border-color: #2563eb !important;
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
if "suggestions" not in st.session_state: 
    st.session_state.suggestions = ["Summarize risks", "Check permit status", "Compare hazard reports"]

# =========================================================
# 4. RENDERING & JUMP LOGIC
# =========================================================
def render_jump_text(text, key_prefix):
    pattern = r'(:jump\[[^\]]+\]\{doc="[^"]+"\s+page=\d+\})'
    parts = re.split(pattern, text)
    for idx, part in enumerate(parts):
        match = re.match(r':jump\[(?P<txt>[^\]]+)\]\{doc="(?P<doc>[^"]+)"\s+page=(?P<pg>\d+)\}', part)
        if match:
            issue_text, doc_name, page_num = match.group('txt'), match.group('doc'), int(match.group('pg'))
            if st.button(issue_text, key=f"{key_prefix}_{idx}"):
                st.session_state.viewing_doc = doc_name
                st.session_state.target_page = page_num
                st.rerun()
        else:
            if part.strip(): st.markdown(part, unsafe_allow_html=True)

# =========================================================
# 5. UI LAYOUT
# =========================================================
st.markdown('<div class="th-hero"><strong>TurboHome Auditor Cockpit</strong></div>', unsafe_allow_html=True)

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

# TOP ROW: VIEWER & CHAT
col_pdf, col_chat = st.columns([1.3, 1], gap="medium")

with col_pdf:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    doc_list = list(st.session_state.pdf_library.keys())
    cur_idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    selected_doc = st.selectbox("Select Doc", doc_list, index=cur_idx, label_visibility="collapsed")
    st.session_state.viewing_doc = selected_doc

    if st.session_state.target_page:
        st.success(f"Viewing p.{st.session_state.target_page} in {selected_doc}")
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full View"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    chat_box = st.container(height=450)
    with chat_box:
        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                render_jump_text(msg["content"], f"chat_{m_idx}")

    # DYNAMIC SUGGESTIONS
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

# BOTTOM ROW: FINDINGS RAIL
st.markdown('<div class="th-card" style="margin-top: 15px;">', unsafe_allow_html=True)
st.markdown('<div class="th-card-title">📋 Integrated Findings Rail</div>', unsafe_allow_html=True)
last_analysis = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")
if last_analysis: render_jump_text(last_analysis, "rail")
else: st.caption("Analysis will appear here.")
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. AI CONTEXTUAL ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    
    with st.spinner("Analyzing..."):
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

            # Shadow Call for Dynamic, Context-Dependent Questions (Under 7 Words)
            s_prompt = f"""
            Based on this analysis: '{res.text}', generate 3 follow-up questions for a homebuyer.
            RULES:
            1. Under 7 words each.
            2. High impact (risk-focused).
            3. Output ONLY questions separated by | (e.g. Question 1 | Question 2 | Question 3)
            """
            sugg_res = client.models.generate_content(model=MODEL_NAME, contents=[s_prompt])
            st.session_state.suggestions = [s.strip() for s in sugg_res.text.split('|')][:3]
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
