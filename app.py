import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. THE PLAYBOOK ---
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
(Your full playbook here...)

--- CITATION RULE ---
Wrap the issue description in this tag: :jump[Description]{doc="Name" page=X}
Example: "The :jump[foundation has vertical cracking]{doc="Home Inspection" page=14}..."
"""

# --- 2. PAGE CONFIG & LINEAR STYLING ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="centered")

st.markdown("""
<style>
    /* Clean, modern typography and background */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1e293b; background: #fdfdfd; }
    .block-container { max-width: 900px; padding-top: 2rem; }
    
    /* Header styling */
    .th-logo { color: #0f172a; font-size: 1.5rem; font-weight: 800; margin-bottom: 2rem; }
    .th-logo span { color: #2563eb; }

    /* Linear Section Cards */
    .th-section { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .th-section-title { font-size: 1.1rem; font-weight: 700; color: #0f172a; margin-bottom: 1rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }

    /* The Inline Link */
    div.stButton > button {
        border: none !important; padding: 0px !important; background-color: transparent !important;
        color: #2563eb !important; text-decoration: underline !important; font-size: inherit !important;
        font-weight: 700 !important; display: inline !important; vertical-align: baseline !important;
    }
    
    /* Document selection tray */
    .doc-tray { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {}
if "target_page" not in st.session_state: st.session_state.target_page = None
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None

# --- 4. HEADER ---
st.markdown('<div class="th-logo">Turbo<span>Home</span> Disclosure Analysis</div>', unsafe_allow_html=True)

# --- 5. SIDEBAR (Keeping file management out of the way) ---
with st.sidebar:
    st.title("Files")
    files = st.file_uploader("Upload PDF Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library:
                st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("👋 Welcome! Upload your disclosure documents in the sidebar to begin your audit.")
    st.stop()

# --- 6. SECTION 1: THE INTELLIGENCE (Findings & Chat) ---
st.markdown('<div class="th-section">', unsafe_allow_html=True)
st.markdown('<div class="th-section-title">🔍 Analysis & Findings</div>', unsafe_allow_html=True)

# Function to render hyperlinked text (re-using the logic we built)
def render_jump_text(text, key_prefix):
    pattern = r'(:jump\[[^\]]+\]\{doc="[^"]+"\s+page=\d+\})'
    parts = re.split(pattern, text)
    for idx, part in enumerate(parts):
        match = re.match(r':jump\[(?P<txt>[^\]]+)\]\{doc="(?P<doc>[^"]+)"\s+page=(?P<pg>\d+)\}', part)
        if match:
            issue_text = match.group('txt')
            doc_name = match.group('doc')
            page_num = int(match.group('pg'))
            if st.button(issue_text, key=f"{key_prefix}_{idx}"):
                st.session_state.viewing_doc = doc_name
                st.session_state.target_page = page_num
                st.rerun()
        else:
            if part.strip(): st.markdown(part, unsafe_allow_html=True)

# Render only the latest analysis for a clean "Summary" view
last_analysis = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
if last_analysis:
    render_jump_text(last_analysis, "summary")
else:
    st.caption("No findings yet. Ask a question below to start.")

if prompt := st.chat_input("Ask a follow-up question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 7. SECTION 2: THE EVIDENCE (PDF Viewer) ---
st.markdown('<div class="th-section">', unsafe_allow_html=True)
st.markdown('<div class="th-section-title">📄 Document Verification</div>', unsafe_allow_html=True)

doc_list = list(st.session_state.pdf_library.keys())
idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
selected = st.selectbox("Select document to view", doc_list, index=idx)
st.session_state.viewing_doc = selected

if st.session_state.target_page:
    st.success(f"Focused on Page {st.session_state.target_page} of {selected}")
    pdf_viewer(input=st.session_state.pdf_library[selected], height=800, pages_to_render=[st.session_state.target_page])
    if st.button("Close Page Focus"):
        st.session_state.target_page = None
        st.rerun()
else:
    pdf_viewer(input=st.session_state.pdf_library[selected], height=800)
st.markdown('</div>', unsafe_allow_html=True)

# --- 8. AI ENGINE ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("TurboHome is cross-referencing all documents..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            res = client.models.generate_content(
                model=MODEL_NAME, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
