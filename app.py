import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. THE PLAYBOOK ---
# (Using your existing multi-line playbook logic)
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Paste your full playbook text here...)

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

# --- 3. THE BRANDED STYLES (TurboHome "Warm Lifestyle" Palette) ---
st.markdown("""
<style>
    :root {
        --th-orange: #FF5A35;
        --th-orange-dark: #E14627;
        --th-cream: #FEFAF4;
        --th-navy: #0F172A;
        --th-text: #334155;
        --th-card-bg: #FFFFFF;
        --th-border: #F1F5F9;
    }

    .stApp {
        background-color: var(--th-cream);
        color: var(--th-navy);
    }

    .block-container {
        padding-top: 1.5rem;
        max-width: 1600px;
    }

    /* TurboHome Hero Header */
    .th-hero {
        background: white;
        padding: 40px;
        border-radius: 30px;
        box-shadow: 0 10px 40px rgba(255, 90, 53, 0.05);
        margin-bottom: 24px;
        border: 1px solid var(--th-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .th-brand-logo {
        font-size: 2.2rem;
        font-weight: 900;
        color: var(--th-navy);
        letter-spacing: -1px;
    }

    .th-brand-logo span {
        color: var(--th-orange);
    }

    .th-hero-text h1 {
        font-size: 2.5rem;
        font-weight: 800;
        color: var(--th-navy);
        line-height: 1.1;
        margin-bottom: 12px;
    }

    /* Cards & Panels */
    .th-card {
        background: white;
        border-radius: 28px;
        padding: 24px;
        border: 1px solid var(--th-border);
        box-shadow: 0 8px 30px rgba(0,0,0,0.03);
    }

    .th-card-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: var(--th-navy);
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* Primary Action Buttons (Orange) */
    div.stButton > button:not([key^="sugg_"]):not([key^="lk_"]) {
        background: linear-gradient(135deg, var(--th-orange), var(--th-orange-dark)) !important;
        color: white !important;
        border: none !important;
        border-radius: 999px !important;
        padding: 12px 28px !important;
        font-weight: 700 !important;
        box-shadow: 0 10px 20px rgba(255, 90, 53, 0.2) !important;
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 14px 24px rgba(255, 90, 53, 0.3) !important;
    }

    /* Inline Page Link Buttons */
    div.stButton > button[key^="lk_"] {
        color: var(--th-orange) !important;
        text-decoration: underline !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        font-size: inherit !important;
        font-weight: 700 !important;
    }

    /* Suggestion Bubbles (Light Cream/Orange) */
    div.stButton > button[key^="sugg_"] {
        background: white !important;
        color: var(--th-navy) !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        padding: 10px 16px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.02) !important;
    }

    div.stButton > button[key^="sugg_"]:hover {
        border-color: var(--th-orange) !important;
        color: var(--th-orange) !important;
    }

    /* Findings UI */
    .finding-item {
        background: #F8FAFC;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 5px solid #CBD5E1;
    }
    .finding-item.high { border-left-color: #EF4444; background: #FEF2F2; }
    .finding-item.medium { border-left-color: #F59E0B; background: #FFFBEB; }
    .finding-item.low { border-left-color: #3B82F6; background: #EFF6FF; }

</style>
""", unsafe_allow_html=True)

# --- 4. HEADER ---
st.markdown(f"""
<div class="th-hero">
    <div class="th-hero-text">
        <div class="th-brand-logo">turbo<span>home</span></div>
        <h1>Disclosure Auditor</h1>
        <p style="color: #64748B; font-size: 1.1rem;">Review faster. Catch more. Get your rebate.</p>
    </div>
    <div style="text-align: right;">
        <span class="th-badge" style="background: #FFF1F0; color: #FF5A35; padding: 10px 20px; border-radius: 999px; font-weight: 700;">
            🏠 Pro Auditor Active
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 5. SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "target_page" not in st.session_state: st.session_state.target_page = None
if "suggestions" not in st.session_state: st.session_state.suggestions = ["Summarize TDS risks", "Find structural red flags", "Check NHD hazard zones"]

# --- 6. FILE UPLOADER ---
uploaded_file = st.file_uploader("Drop your disclosure PDF here", type=["pdf"])

if not uploaded_file:
    st.markdown("""
    <div style="text-align: center; padding: 60px; background: white; border-radius: 30px; border: 2px dashed #E2E8F0; margin-top: 20px;">
        <h3 style="color: #0F172A;">Ready to audit?</h3>
        <p style="color: #64748B;">Upload your seller disclosures or inspection reports to begin.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- 7. MAIN INTERFACE ---
pdf_bytes = uploaded_file.read()
col_pdf, col_workspace = st.columns([1.2, 1], gap="large")

with col_pdf:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">📄 Property Disclosures</div>', unsafe_allow_html=True)
    
    if st.session_state.target_page:
        st.info(f"📍 Viewing Page {st.session_state.target_page}")
        pdf_viewer(input=pdf_bytes, height=800, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back to Full document", key="back_btn"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=pdf_bytes, height=800)
    st.markdown('</div>', unsafe_allow_html=True)

with col_workspace:
    st.markdown('<div class="th-card" style="height: 870px; display: flex; flex-direction: column;">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-title">🤖 AI Assistant</div>', unsafe_allow_html=True)
    
    chat_container = st.container(height=600)
    with chat_container:
        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                # Rendering text with the inline orange link buttons
                parts = re.split(r'(:page\[\d+\])', msg["content"])
                for p_idx, part in enumerate(parts):
                    match = re.match(r':page\[(\d+)\]', part)
                    if match:
                        page_num = int(match.group(1))
                        if st.button(f"Page {page_num}", key=f"lk_{m_idx}_{p_idx}"):
                            st.session_state.target_page = page_num
                            st.rerun()
                    else:
                        st.markdown(part)

    # Dynamic Suggestion Bubbles
    st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
    s_cols = st.columns(3)
    for idx, suggestion in enumerate(st.session_state.suggestions):
        if s_cols[idx].button(suggestion, key=f"sugg_{idx}"):
            st.session_state.messages.append({"role": "user", "content": suggestion})
            st.rerun()

    # Chat Input
    if prompt := st.chat_input("Ask TurboHome about this property..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 8. AI LOGIC ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    api_key = st.secrets["GOOGLE_API_KEY"]
    client = genai.Client(api_key=api_key)
    
    with st.spinner("TurboHome is reviewing..."):
        try:
            # Audit Response
            res = client.models.generate_content(
                model="gemini-3-flash-preview",
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                contents=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    *[types.Content(role="model" if m["role"] == "assistant" else "user", 
                                    parts=[types.Part.from_text(text=m["content"])]) 
                      for m in st.session_state.messages]
                ]
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})

            # Contextual Suggestions
            s_prompt = f"Based on: '{res.text}', suggest 3 short follow-up questions for a buyer. Output ONLY text separated by |."
            s_res = client.models.generate_content(model="gemini-3-flash-preview", contents=[s_prompt])
            st.session_state.suggestions = [s.strip() for s in s_res.text.split('|')][:3]
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
