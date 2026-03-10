import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE MULTI-DOC PLAYBOOK (HYPERLINK EDITION)
# =========================================================
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
You are a professional auditor. Analyze all documents and find discrepancies.

--- CORE CATEGORIES ---
1. Cross-Document Conflicts
2. Inspection Findings
3. Seller Disclosures
4. Hazard Disclosures
5. Follow-up Questions

--- CITATION RULE ---
Instead of a separate citation, wrap the specific text describing the issue in this tag: 
:jump[Description of the issue]{doc="Document Name" page=X}

Example: "The :jump[water heater is reaching the end of its useful life]{doc="Home Inspection" page=18} and requires replacement."
"""

# =========================================================
# 2. PAGE CONFIG & COMPACT STYLES
# =========================================================
st.set_page_config(page_title="TurboHome Disclosure Analysis", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 13px; font-family: 'Inter', sans-serif; }
    .stApp { background: #fcfdfe; }
    .block-container { max-width: 1700px; padding-top: 1rem; }
    
    .th-hero { background: #0f172a; color: white; padding: 10px 20px; border-radius: 12px; margin-bottom: 10px; }
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; height: 100%; }

    /* THE INLINE "ISSUE" LINK STYLING */
    div.stButton > button {
        border: none !important;
        padding: 0px !important;
        background-color: transparent !important;
        color: #2563eb !important;
        text-decoration: underline !important;
        font-size: inherit !important;
        font-weight: 700 !important;
        display: inline !important;
        min-height: 0px !important;
        height: auto !important;
        vertical-align: baseline !important;
        line-height: inherit !important;
    }
    div.stButton > button:hover { color: #1d4ed8 !important; background-color: transparent !important; }

    /* RAIL STYLING */
    .rail-header { font-weight: 800; font-size: 10px; color: #64748b; margin-top: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
    .finding-block { margin-bottom: 12px; line-height: 1.5; color: #334155; }
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
    st.session_state.suggestions = ["Run full audit", "Check for conflicts", "Summarize NHD"]

# =========================================================
# 4. RENDERING ENGINE (The "Magic" Linker)
# =========================================================
def render_hyperlinked_text(text, key_prefix):
    """
    Parses :jump[text]{doc="name" page=X} tags and turns them into 
    inline buttons that look like standard links.
    """
    # Regex to catch the text, the doc name, and the page number
    pattern = r'(:jump\[[^\]]+\]\{doc="[^"]+"\s+page=\d+\})'
    parts = re.split(pattern, text)
    
    for idx, part in enumerate(parts):
        # Check if the part is a jump tag
        match = re.match(r':jump\[(?P<txt>[^\]]+)\]\{doc="(?P<doc>[^"]+)"\s+page=(?P<pg>\d+)\}', part)
        if match:
            issue_text = match.group('txt')
            doc_name = match.group('doc')
            page_num = int(match.group('pg'))
            
            # This creates a button that looks like hyperlinked text
            if st.button(issue_text, key=f"{key_prefix}_{idx}"):
                st.session_state.viewing_doc = doc_name
                st.session_state.target_page = page_num
                st.rerun()
        else:
            # Standard text around the link
            if part.strip():
                st.markdown(part, unsafe_allow_html=True)

# =========================================================
# 5. UI LAYOUT
# =========================================================
st.markdown('<div class="th-hero"><strong>TurboHome Disclosure Analysis</strong></div>', unsafe_allow_html=True)

# Sidebar for file management
with st.sidebar:
    st.title("📂 Files")
    files = st.file_uploader("Upload PDF Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library:
                st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("Upload documents in the sidebar to begin.")
    st.stop()

# Layout: Viewer | Findings Rail | Chat
col_view, col_rail, col_chat = st.columns([1.2, 0.8, 1], gap="small")

with col_view:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    doc_list = list(st.session_state.pdf_library.keys())
    # Sync selector with session state for jumping across docs
    idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    selected = st.selectbox("Select Doc", doc_list, index=idx, label_visibility="collapsed")
    st.session_state.viewing_doc = selected

    if st.session_state.target_page:
        pdf_viewer(input=st.session_state.pdf_library[selected], height=800, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full Scroll", key="reset"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[selected], height=800)
    st.markdown('</div>', unsafe_allow_html=True)

with col_rail:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown("<strong>📋 Structured Findings</strong>", unsafe_allow_html=True)
    
    last_assistant_msg = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    
    if last_assistant_msg:
        # We render the last message here, but specifically the parts that are jump-linked
        st.markdown('<div class="rail-header">Key Audited Items</div>', unsafe_allow_html=True)
        render_hyperlinked_text(last_assistant_msg, "rail")
    else:
        st.caption("Audited items will appear here.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    chat_box = st.container(height=600)
    with chat_box:
        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                render_hyperlinked_text(msg["content"], f"chat_{m_idx}")

    # Suggestions
    st.write("---")
    s_cols = st.columns(3)
    for idx, sugg in enumerate(st.session_state.suggestions):
        if s_cols[idx].button(sugg, key=f"sugg_{idx}"):
            st.session_state.messages.append({"role": "user", "content": sugg})
            st.rerun()

    if prompt := st.chat_input("Ask Auditor..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. AI CONTEXTUAL ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    
    with st.spinner("Reviewing documents..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]

            res = client.models.generate_content(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})

            # Suggestion shadow call
            s_res = client.models.generate_content(model=MODEL_NAME, 
                contents=[f"Based on: '{res.text}', suggest 3 logical follow-up questions for a buyer. Output text separated by |."])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
