import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. MULTI-DOC PLAYBOOK
# =========================================================
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
You are a professional real estate auditor. You have been provided with multiple disclosure documents.

--- CORE INSTRUCTIONS ---
1. Analyze ALL provided documents simultaneously.
2. Cross-reference info: If the Home Inspection notes a crack but the TDS says 'No foundation issues', flag this conflict.
3. Concisely explain implications for the buyer for every finding.

--- CITATION RULE ---
For every finding, you MUST cite the document and page. 
Format: [Document Name] :page[X]
Example: "[Pest Report] :page[12]: Termite activity found in subarea."
"""

# =========================================================
# 2. PAGE CONFIG & COMPACT STYLING
# =========================================================
st.set_page_config(
    page_title="TurboHome Disclosure Analysis",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 13px; font-family: 'Inter', sans-serif; color: #0f172a; }
    .block-container { max-width: 1600px; padding-top: 1rem; }
    
    /* COMPACT HERO */
    .th-hero { background: #0f172a; color: white; padding: 10px 20px; border-radius: 12px; margin-bottom: 10px; }
    .th-hero-title { font-size: 1.3rem; font-weight: 800; margin: 0; }
    
    /* MULTI-DOC TABS */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 4px 12px; font-size: 12px; 
    }

    /* COMPACT CARDS */
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; height: 100%; }
    
    /* BUTTONS TO LINKS */
    div.stButton > button {
        border: none !important; padding: 0px 2px !important; background-color: transparent !important;
        color: #2563eb !important; text-decoration: underline !important; font-size: inherit !important;
        min-height: 0px !important; height: auto !important; vertical-align: baseline !important; font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_docs" not in st.session_state: st.session_state.pdf_docs = {} # Name: Bytes
if "active_doc" not in st.session_state: st.session_state.active_doc = None
if "target_page" not in st.session_state: st.session_state.target_page = 1

# =========================================================
# 4. SIDEBAR - FILE MANAGEMENT
# =========================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/home.png", width=40)
    st.title("Admin")
    uploaded_files = st.file_uploader(
        "Upload Disclosures", 
        type=["pdf"], 
        accept_multiple_files=True,
        help="Upload TDS, SPQ, NHD, and Inspection reports together."
    )
    
    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.pdf_docs:
                st.session_state.pdf_docs[f.name] = f.read()
        
    if st.session_state.pdf_docs:
        st.write("---")
        st.caption("Manage Documents")
        for name in list(st.session_state.pdf_docs.keys()):
            col1, col2 = st.columns([4, 1])
            col1.text(f"📄 {name[:20]}...")
            if col2.button("X", key=f"del_{name}"):
                del st.session_state.pdf_docs[name]
                st.rerun()

# =========================================================
# 5. MAIN UI LAYOUT
# =========================================================
st.markdown('<div class="th-hero"><div class="th-hero-title">TurboHome Disclosure Analysis</div></div>', unsafe_allow_html=True)

if not st.session_state.pdf_docs:
    st.info("Please upload one or more disclosure PDFs in the sidebar to begin.")
    st.stop()

col_viewer, col_chat = st.columns([1.2, 1], gap="small")

# --- LEFT: MULTI-PDF VIEWER ---
with col_viewer:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    # Selection tabs for which PDF to view
    doc_names = list(st.session_state.pdf_docs.keys())
    active_tab = st.selectbox("Select document to view:", doc_names, label_visibility="collapsed")
    
    st.session_state.active_doc = active_tab
    
    if st.session_state.target_page and st.session_state.target_page > 0:
        st.caption(f"Viewing {active_tab} - Page {st.session_state.target_page}")
        pdf_viewer(
            input=st.session_state.pdf_docs[active_tab], 
            height=800, 
            pages_to_render=[st.session_state.target_page]
        )
        if st.button("Back to full scroll", key="reset_view"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_docs[active_tab], height=800)
    st.markdown('</div>', unsafe_allow_html=True)

# --- RIGHT: CROSS-DOC CHAT ---
with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    chat_container = st.container(height=650)
    
    with chat_container:
        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                # Rendering logic with page jump buttons
                parts = re.split(r"(:page\[\d+\])", msg["content"])
                for p_idx, part in enumerate(parts):
                    match = re.match(r":page\[(\d+)\]", part)
                    if match:
                        page_num = int(match.group(1))
                        if st.button(f"p.{page_num}", key=f"jump_{idx}_{p_idx}"):
                            st.session_state.target_page = page_num
                            st.rerun()
                    else:
                        st.markdown(part)

    if prompt := st.chat_input("Ask about these documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # AI Logic
        api_key = st.secrets.get("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)
        
        with st.spinner("Analyzing across documents..."):
            try:
                # Prepare all PDFs as parts for the AI
                pdf_parts = [
                    types.Part.from_bytes(data=content, mime_type="application/pdf")
                    for name, content in st.session_state.pdf_docs.items()
                ]
                
                # Prepare chat history
                history = [
                    types.Content(
                        role="model" if m["role"] == "assistant" else "user",
                        parts=[types.Part.from_text(text=m["content"])]
                    ) for m in st.session_state.messages
                ]

                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                    contents=pdf_parts + history
                )
                
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"Audit Error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)
