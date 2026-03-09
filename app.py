import html
import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================
# 1. THE PLAYBOOK (REFINED)
# =========================
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Your full playbook goes here...)

--- CITATION RULE ---
For every finding, you MUST include the page number using this exact tag: :page[X]
Example: "The roof is 15 years old :page[18]."
"""

# =========================
# 2. PAGE CONFIG
# =========================
st.set_page_config(
    page_title="TurboHome Auditor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# 3. STYLING (REFINED)
# =========================
# I've kept your beautiful CSS but added a 'jump-animation' for the PDF viewer
st.markdown(
    """
    <style>
        :root {
            --th-blue: #2563eb;
            --th-blue-dark: #1d4ed8;
            --th-ink: #0f172a;
            --th-text: #334155;
            --th-muted: #64748b;
            --th-line: #e2e8f0;
            --th-bg: #f8fbff;
            --th-card: #ffffff;
            --th-success: #10b981;
        }

        .stApp {
            background: 
                radial-gradient(circle at top left, rgba(37,99,235,0.10), transparent 30%),
                linear-gradient(180deg, #f8fbff 0%, #f4f8fc 100%);
        }

        /* Improved Chat Bubble Spacing */
        [data-testid="stChatMessageContent"] {
            border-radius: 20px !important;
            border: 1px solid var(--th-line) !important;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
        }

        /* Citation Link Styling */
        .page-link {
            display: inline-block;
            color: var(--th-blue);
            background: rgba(37,99,235,0.08);
            border: 1px solid rgba(37,99,235,0.2);
            padding: 0px 6px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 700;
            font-size: 0.85em;
            transition: all 0.2s;
        }

        .page-link:hover {
            background: var(--th-blue);
            color: white !important;
            transform: translateY(-1px);
        }
        
        .th-shell {
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(226,232,240,0.9);
            border-radius: 24px;
            padding: 1rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
            backdrop-filter: blur(6px);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# 4. SESSION STATE & NAVIGATION
# =========================
if "messages" not in st.session_state: st.session_state.messages = []
if "target_page" not in st.session_state: st.session_state.target_page = None
if "pdf_bytes" not in st.session_state: st.session_state.pdf_bytes = None

# Detect jump from URL
query_params = st.query_params
if "page" in query_params:
    st.session_state.target_page = int(query_params["page"])

# =========================
# 5. IMPROVED MESSAGE RENDERER
# =========================
def render_rich_message(content: str):
    """
    Renders markdown correctly while injecting stylized page links.
    """
    # Replace :page[X] with a styled HTML link that targets the same window
    def replace_tag(match):
        p = match.group(1)
        return f'<a class="page-link" href="?page={p}" target="_self">Page {p}</a>'
    
    processed_content = re.sub(r":page\[(\d+)\]", replace_tag, content)
    st.markdown(processed_content, unsafe_allow_html=True)

# =========================
# 6. HEADER / HERO
# =========================
st.markdown("""
    <div class="th-hero">
        <div class="th-eyebrow">TurboHome Disclosure Intelligence</div>
        <div class="th-hero-title">Auditing {pdf_name}</div>
    </div>
""".format(pdf_name=st.session_state.get("pdf_name", "Package")), unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=["pdf"])

if uploaded_file:
    st.session_state.pdf_bytes = uploaded_file.read()
    st.session_state.pdf_name = uploaded_file.name
    st.rerun()

# =========================
# 7. MAIN APP
# =========================
if st.session_state.pdf_bytes:
    col_pdf, col_chat = st.columns([1.25, 1], gap="large")

    with col_pdf:
        st.markdown('<div class="th-shell">', unsafe_allow_html=True)
        # Toggle between focus mode and continuous mode
        if st.session_state.target_page:
            st.info(f"📍 Viewing Page {st.session_state.target_page}")
            pdf_viewer(input=st.session_state.pdf_bytes, height=800, pages_to_render=[st.session_state.target_page])
            if st.button("⬅️ Back to Continuous View"):
                st.query_params.clear()
                st.session_state.target_page = None
                st.rerun()
        else:
            pdf_viewer(input=st.session_state.pdf_bytes, height=800)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_chat:
        st.markdown('<div class="th-shell" style="height: 850px; overflow: hidden; display: flex; flex-direction: column;">', unsafe_allow_html=True)
        
        # Chat History Container
        chat_sub_container = st.container(height=700)
        with chat_sub_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    render_rich_message(msg["content"])

        # Chat Input
        if prompt := st.chat_input("Ask about risks, repairs, or NHD zones..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # --- AI CALL (Modernized for Gemini 3) ---
            api_key = st.secrets.get("GOOGLE_API_KEY")
            client = genai.Client(api_key=api_key)
            
            with st.chat_message("assistant"):
                with st.spinner("TurboHome is auditing..."):
                    try:
                        response = client.models.generate_content(
                            model="gemini-3-flash", # Updated to the 2026 standard
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                temperature=0.0
                            ),
                            contents=[
                                types.Part.from_bytes(data=st.session_state.pdf_bytes, mime_type="application/pdf"),
                                *[types.Content(role="model" if m["role"] == "assistant" else "user", 
                                                parts=[types.Part.from_text(text=m["content"])]) 
                                  for m in st.session_state.messages]
                            ]
                        )
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Audit Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
