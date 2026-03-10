import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. THE PLAYBOOK ---
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Your full playbook text here)

--- CITATION RULE ---
For every finding, you MUST include the page number using this exact tag: :page[X]
Example: "The roof is 15 years old :page[18]."
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="TurboHome Auditor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 3. STYLES ---
st.markdown("""
<style>
    /* App background */
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 28%),
            radial-gradient(circle at top right, rgba(16, 185, 129, 0.08), transparent 24%),
            linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
    }

    /* Global typography */
    html, body, [class*="css"]  {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #0f172a;
    }

    /* Main block spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* Hero */
    .th-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #2563eb 100%);
        color: white;
        padding: 28px 30px;
        border-radius: 22px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18);
        margin-bottom: 18px;
        border: 1px solid rgba(255,255,255,0.10);
    }

    .th-hero-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }

    .th-hero-subtitle {
        font-size: 1rem;
        line-height: 1.6;
        color: rgba(255,255,255,0.82);
        max-width: 760px;
    }

    .th-badge-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 16px;
    }

    .th-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.16);
        color: white;
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 0.86rem;
        font-weight: 600;
        backdrop-filter: blur(6px);
    }

    /* Section cards */
    .th-card {
        background: rgba(255,255,255,0.76);
        border: 1px solid rgba(255,255,255,0.70);
        border-radius: 22px;
        padding: 18px 18px 10px 18px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        backdrop-filter: blur(10px);
    }

    .th-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        gap: 12px;
    }

    .th-card-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #0f172a;
    }

    .th-card-subtitle {
        font-size: 0.88rem;
        color: #64748b;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.82);
        border: 1px dashed #93c5fd;
        border-radius: 18px;
        padding: 12px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }

    /* Chat area */
    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.86);
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 4px 6px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        margin-bottom: 10px;
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        background: rgba(255,255,255,0.90);
        border-radius: 16px;
    }

    /* Divider */
    .th-divider {
        height: 1px;
        width: 100%;
        background: linear-gradient(90deg, transparent, #cbd5e1, transparent);
        margin: 14px 0 16px 0;
    }

    /* Inline page citation buttons */
    div.stButton > button {
        border: none !important;
        padding: 0px 2px !important;
        background-color: transparent !important;
        color: #2563eb !important;
        text-decoration: underline !important;
        font-size: inherit !important;
        display: inline !important;
        min-height: 0px !important;
        height: auto !important;
        vertical-align: baseline !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }

    /* Suggestion pills */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
        color: #1d4ed8 !important;
        border: 1px solid #bfdbfe !important;
        text-decoration: none !important;
        border-radius: 999px !important;
        padding: 10px 14px !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08) !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="column"] .stButton > button[key^="sugg_"]:hover {
        border-color: #60a5fa !important;
        color: #1e40af !important;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.14) !important;
    }

    /* Back button */
    div.stButton > button[key="back_btn"] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        border: 1px solid #cbd5e1 !important;
        background: white !important;
        text-decoration: none !important;
        color: #0f172a !important;
        font-weight: 600 !important;
        min-height: 40px !important;
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.06) !important;
    }

    /* Info / alert boxes */
    [data-testid="stInfo"] {
        border-radius: 14px;
        background: rgba(219, 234, 254, 0.65);
        border: 1px solid #bfdbfe;
    }

    /* Hide streamlit default anchor hover clutter a bit */
    .stMarkdown a {
        color: #2563eb;
    }

    /* Subtle metric strip */
    .th-metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 10px 0 18px 0;
    }

    .th-metric {
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(255,255,255,0.70);
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }

    .th-metric-label {
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 4px;
        font-weight: 600;
    }

    .th-metric-value {
        font-size: 1.15rem;
        color: #0f172a;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    /* Empty state */
    .th-empty {
        background: rgba(255,255,255,0.78);
        border: 1px solid #dbeafe;
        border-radius: 20px;
        padding: 28px;
        text-align: center;
        color: #334155;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
    }

    .th-empty-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 6px;
        color: #0f172a;
    }

    .th-empty-subtitle {
        font-size: 0.95rem;
        color: #64748b;
        max-width: 540px;
        margin: 0 auto;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "target_page" not in st.session_state:
    st.session_state.target_page = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = [
        "Biggest disclosure risks",
        "Check unpermitted work",
        "Summarize NHD hazards"
    ]

# --- 5. API SETUP ---
MODEL_NAME = "gemini-3-flash-preview"

api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 6. HEADER / HERO ---
st.markdown("""
<div class="th-hero">
    <div class="th-hero-title">TurboHome Auditor</div>
    <div class="th-hero-subtitle">
        AI-powered disclosure review for modern homebuyers. Upload a disclosure package,
        surface material risks, and jump directly to cited pages for faster due diligence.
    </div>
    <div class="th-badge-row">
        <div class="th-badge">⚡ Fast risk triage</div>
        <div class="th-badge">📎 Page-linked citations</div>
        <div class="th-badge">🧠 Buyer-friendly explanations</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="th-metrics">
    <div class="th-metric">
        <div class="th-metric-label">Workflow</div>
        <div class="th-metric-value">Upload → Review → Investigate</div>
    </div>
    <div class="th-metric">
        <div class="th-metric-label">Output Style</div>
        <div class="th-metric-value">Actionable + cited</div>
    </div>
    <div class="th-metric">
        <div class="th-metric-label">Built For</div>
        <div class="th-metric-value">TurboHome buyers</div>
    </div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload Disclosure Package (PDF)",
    type=["pdf"],
    help="Supported format: PDF"
)

# --- 7. EMPTY STATE ---
if not uploaded_file:
    st.markdown("""
    <div class="th-empty">
        <div class="th-empty-title">Start with a disclosure package</div>
        <div class="th-empty-subtitle">
            Upload a PDF to analyze seller disclosures, inspection notes, and hazard reports.
            The auditor will cite every finding with clickable page references.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- 8. FILE LOADED ---
pdf_bytes = uploaded_file.read()

col_pdf, col_chat = st.columns([1.35, 1], gap="large")

with col_pdf:
    st.markdown("""
    <div class="th-card">
        <div class="th-card-header">
            <div>
                <div class="th-card-title">Disclosure Document</div>
                <div class="th-card-subtitle">View the full file or jump to cited pages</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.target_page:
        st.info(f"Focused on page {st.session_state.target_page}")
        pdf_viewer(
            input=pdf_bytes,
            height=860,
            pages_to_render=[st.session_state.target_page]
        )
        if st.button("⬅ Back to Full Document", key="back_btn"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=pdf_bytes, height=860)

    st.markdown("</div>", unsafe_allow_html=True)

with col_chat:
    st.markdown("""
    <div class="th-card">
        <div class="th-card-header">
            <div>
                <div class="th-card-title">AI Auditor</div>
                <div class="th-card-subtitle">Ask questions, inspect risks, and follow citations</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    chat_container = st.container(height=600)

    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div class="th-empty" style="padding:22px;">
                <div class="th-empty-title">No analysis yet</div>
                <div class="th-empty-subtitle">
                    Try a suggested prompt below or ask something like
                    “What are the biggest risks in this package?”
                </div>
            </div>
            """, unsafe_allow_html=True)

        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                parts = re.split(r'(:page\[\d+\])', msg["content"])
                for p_idx, part in enumerate(parts):
                    match = re.match(r':page\[(\d+)\]', part)
                    if match:
                        page_num = int(match.group(1))
                        if st.button(f"Page {page_num}", key=f"lk_{m_idx}_{p_idx}_{page_num}"):
                            st.session_state.target_page = page_num
                            st.rerun()
                    else:
                        if part.strip():
                            st.markdown(part)

    st.markdown('<div class="th-divider"></div>', unsafe_allow_html=True)

    if st.session_state.suggestions:
        s_cols = st.columns(len(st.session_state.suggestions))
        for idx, suggestion in enumerate(st.session_state.suggestions):
            if s_cols[idx].button(suggestion, key=f"sugg_{idx}"):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                st.rerun()

    if prompt := st.chat_input("Ask about risks, permits, hazards, repairs, or red flags..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# --- 9. AI CONTEXTUAL LOGIC ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with col_chat:
        with st.chat_message("assistant"):
            with st.spinner("Reviewing disclosure package..."):
                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.0
                        ),
                        contents=[
                            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                            *[
                                types.Content(
                                    role="model" if m["role"] == "assistant" else "user",
                                    parts=[types.Part.from_text(text=m["content"])]
                                )
                                for m in st.session_state.messages
                            ]
                        ]
                    )

                    assistant_text = response.text if response and response.text else "I couldn't generate a response for this document."
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_text
                    })

                    s_prompt = (
                        f"Based on: '{assistant_text}', suggest 3 short follow-up questions "
                        f"(3-5 words) for a buyer. Output ONLY the questions separated by |."
                    )

                    sugg_res = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[s_prompt]
                    )

                    if sugg_res and sugg_res.text:
                        st.session_state.suggestions = [
                            s.strip() for s in sugg_res.text.split("|") if s.strip()
                        ][:3]

                    st.rerun()

                except Exception as e:
                    st.error(f"Audit Error: {e}")
