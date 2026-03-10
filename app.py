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
You are a professional real estate auditor. You are analyzing multiple PDF documents for a homebuyer.

--- CORE CATEGORIES ---
Organize your internal analysis into these 5 sections:
1. Cross-Document Conflicts: (e.g., Seller says "No leaks" in TDS, but Inspector found a leak).
2. Inspection Findings: (From Home, Pest, or Roof reports).
3. Seller Disclosures: (From TDS or SPQ).
4. Hazard Disclosures: (From NHD reports).
5. Follow-up Questions: (Items requiring more info from the seller).

--- CITATION RULE (STRICT) ---
Every finding MUST include the document name and page number in this exact format:
:doc[Document Name]:page[X]
Example: "Evidence of active termites found in subarea :doc[Pest Report]:page[12]."
"""

# =========================================================
# 2. PAGE CONFIG & COMPACT STYLES
# =========================================================
st.set_page_config(page_title="TurboHome Disclosure Analysis", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 13px; font-family: 'Inter', sans-serif; }
    .stApp { background: #f8fafc; }
    .block-container { max-width: 1650px; padding-top: 1rem; }
    
    /* Hero & Containers */
    .th-hero { background: #0f172a; color: white; padding: 12px 20px; border-radius: 12px; margin-bottom: 10px; }
    .th-card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; height: 100%; }

    /* Citation Link Styling */
    div.stButton > button {
        border: none !important; padding: 0px 2px !important; background-color: transparent !important;
        color: #2563eb !important; text-decoration: underline !important; font-size: inherit !important;
        min-height: 0px !important; height: auto !important; vertical-align: baseline !important; font-weight: 700 !important;
    }

    /* Findings Rail Styling */
    .finding-section-header { font-weight: 800; text-transform: uppercase; font-size: 10px; color: #64748b; margin: 10px 0 5px 0; letter-spacing: 0.05em; }
    .finding-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px 10px; margin-bottom: 8px; border-left: 4px solid #cbd5e1; }
    .finding-card.conflict { border-left-color: #ef4444; background: #fff1f2; }
    .finding-card.inspection { border-left-color: #f59e0b; }
    .finding-card.seller { border-left-color: #3b82f6; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None
if "target_page" not in st.session_state: st.session_state.target_page = None
if "suggestions" not in st.session_state: st.session_state.suggestions = ["Run full audit", "Check for conflicts", "Summarize NHD"]

# =========================================================
# 4. HELPERS
# =========================================================
def jump_to(doc_name, page_num):
    st.session_state.viewing_doc = doc_name
    st.session_state.target_page = page_num
    st.rerun()

def render_content_with_citations(text, key_prefix):
    """Parses text for :doc[Name]:page[X] and creates jump buttons."""
    # Pattern to find :doc[Any Name]:page[Number]
    pattern = r'(:doc\[[^\]]+\]:page\[\d+\])'
    parts = re.split(pattern, text)
    
    for idx, part in enumerate(parts):
        match = re.match(r':doc\[(?P<doc>[^\]]+)\]:page\[(?P<page>\d+)\]', part)
        if match:
            d_name = match.group('doc')
            p_num = int(match.group('page'))
            if st.button(f"Jump to {d_name} p.{p_num}", key=f"{key_prefix}_{idx}"):
                jump_to(d_name, p_num)
        else:
            if part.strip(): st.markdown(part)

# =========================================================
# 5. SIDEBAR
# =========================================================
with st.sidebar:
    st.title("📂 Document Room")
    files = st.file_uploader("Upload Disclosure PDFs", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library:
                st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

# =========================================================
# 6. MAIN UI
# =========================================================
st.markdown('<div class="th-hero"><div class="th-hero-title">TurboHome Disclosure Analysis</div></div>', unsafe_allow_html=True)

if not st.session_state.pdf_library:
    st.info("Upload PDF documents in the sidebar to begin.")
    st.stop()

# THREE COLUMN LAYOUT: Viewer | Findings | Chat
col_view, col_findings, col_chat = st.columns([1.2, 0.8, 1], gap="small")

# --- COLUMN 1: PDF VIEWER ---
with col_view:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    doc_options = list(st.session_state.pdf_library.keys())
    
    # Selection must match the state if triggered by a jump
    current_idx = doc_options.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_options else 0
    selected_doc = st.selectbox("Document", doc_options, index=current_idx, label_visibility="collapsed")
    st.session_state.viewing_doc = selected_doc

    if st.session_state.target_page:
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=800, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full View", key="reset_v"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=800)
    st.markdown('</div>', unsafe_allow_html=True)

# --- COLUMN 2: FINDINGS RAIL ---
with col_findings:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown("<strong>📋 Structured Findings</strong>", unsafe_allow_html=True)
    
    # We parse the last assistant message to populate the rail
    last_msg = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    
    if last_msg:
        # Simple parsing logic for the 5 categories
        categories = {
            "Conflicts": "Cross-Document Conflicts",
            "Inspection": "Inspection Findings",
            "Seller": "Seller Disclosures",
            "Hazards": "Hazard Disclosures"
        }
        for key, title in categories.items():
            st.markdown(f'<div class="finding-section-header">{title}</div>', unsafe_allow_html=True)
            # Find lines belonging to this section (using basic regex or markers)
            # For this demo, we'll render relevant snippets
            render_content_with_citations(last_msg, f"rail_{key}")
    else:
        st.caption("Findings will appear here after the first audit.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- COLUMN 3: INTERACTIVE CHAT ---
with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    chat_box = st.container(height=600)
    with chat_box:
        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                render_content_with_citations(msg["content"], f"chat_{m_idx}")

    # Suggestions
    st.write("---")
    s_cols = st.columns(3)
    for i, sugg in enumerate(st.session_state.suggestions):
        if s_cols[i].button(sugg, key=f"sugg_{i}"):
            st.session_state.messages.append({"role": "user", "content": sugg})
            st.rerun()

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 7. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing cross-doc evidence..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]

            res = client.models.generate_content(
                model="gemini-3-flash-preview",
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})

            # Contextual Suggestions
            s_res = client.models.generate_content(model="gemini-3-flash-preview", 
                contents=[f"Based on: '{res.text}', suggest 3 short buyer follow-up questions. Output text separated by |."])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
