import html
import re

import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================
# 1. THE PLAYBOOK
# =========================
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Include your full playbook here...)

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
# 3. STYLING
# =========================
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

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        h1, h2, h3 {
            color: var(--th-ink);
            letter-spacing: -0.02em;
        }

        /* Main shell cards */
        .th-shell {
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(226,232,240,0.9);
            border-radius: 24px;
            padding: 1rem 1rem 0.25rem 1rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
            backdrop-filter: blur(6px);
        }

        .th-hero {
            background:
                linear-gradient(135deg, rgba(37,99,235,0.12), rgba(255,255,255,0.92) 55%),
                #ffffff;
            border: 1px solid rgba(37,99,235,0.12);
            border-radius: 28px;
            padding: 1.35rem 1.5rem;
            box-shadow: 0 14px 36px rgba(37, 99, 235, 0.08);
            margin-bottom: 1rem;
        }

        .th-eyebrow {
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--th-blue-dark);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.5rem;
        }

        .th-hero-title {
            font-size: 2rem;
            font-weight: 800;
            color: var(--th-ink);
            line-height: 1.05;
            margin-bottom: 0.4rem;
        }

        .th-hero-copy {
            font-size: 1rem;
            color: var(--th-text);
            margin-bottom: 1rem;
            max-width: 70ch;
        }

        .th-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.2rem;
        }

        .th-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            border: 1px solid rgba(37,99,235,0.12);
            background: #ffffff;
            color: var(--th-ink);
            border-radius: 999px;
            padding: 0.48rem 0.72rem;
            font-size: 0.86rem;
            font-weight: 600;
        }

        .th-badge-dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--th-success);
            display: inline-block;
        }

        .th-stat-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.9rem 0 0.25rem 0;
        }

        .th-stat {
            background: rgba(255,255,255,0.96);
            border: 1px solid var(--th-line);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
        }

        .th-stat-label {
            font-size: 0.78rem;
            color: var(--th-muted);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.2rem;
        }

        .th-stat-value {
            font-size: 1.15rem;
            font-weight: 800;
            color: var(--th-ink);
        }

        .th-panel {
            background: var(--th-card);
            border: 1px solid var(--th-line);
            border-radius: 22px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            padding: 1rem;
        }

        .th-panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }

        .th-panel-title {
            font-size: 1.02rem;
            font-weight: 800;
            color: var(--th-ink);
        }

        .th-panel-subtitle {
            font-size: 0.9rem;
            color: var(--th-muted);
        }

        .th-doc-meta {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--th-blue-dark);
            background: rgba(37,99,235,0.08);
            border: 1px solid rgba(37,99,235,0.12);
            border-radius: 999px;
            padding: 0.42rem 0.7rem;
        }

        .th-chat-wrap {
            background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
            border: 1px solid var(--th-line);
            border-radius: 22px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            padding: 0.75rem;
        }

        .th-section-note {
            font-size: 0.92rem;
            color: var(--th-muted);
            margin-top: -0.1rem;
            margin-bottom: 0.6rem;
        }

        /* Inputs */
        .stFileUploader {
            background: rgba(255,255,255,0.88);
            border: 1px dashed rgba(37,99,235,0.35);
            border-radius: 20px;
            padding: 0.5rem;
        }

        /* Primary buttons */
        .stButton > button {
            border-radius: 999px !important;
            border: 1px solid transparent !important;
            background: linear-gradient(180deg, var(--th-blue), var(--th-blue-dark)) !important;
            color: white !important;
            font-weight: 700 !important;
            padding: 0.55rem 1rem !important;
            box-shadow: 0 8px 20px rgba(37,99,235,0.18) !important;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 24px rgba(37,99,235,0.22) !important;
        }

        /* Chat input */
        [data-testid="stChatInput"] {
            border-radius: 18px;
        }

        /* Streamlit message bubble polish */
        [data-testid="stChatMessage"] {
            background: transparent;
        }

        [data-testid="stChatMessageContent"] {
            border-radius: 18px;
            padding: 0.9rem 1rem !important;
            border: 1px solid var(--th-line);
            background: #ffffff;
        }

        /* Inline citation links */
        .page-link {
            display: inline;
            color: var(--th-blue);
            text-decoration: underline;
            font-weight: 700;
            white-space: nowrap;
        }

        .page-link:hover {
            color: var(--th-blue-dark);
            text-decoration: none;
        }

        .msg-rich {
            color: var(--th-text);
            line-height: 1.7;
            font-size: 0.98rem;
        }

        .msg-rich p {
            margin: 0 0 0.8rem 0;
        }

        .msg-rich ul, .msg-rich ol {
            margin-top: 0.4rem;
            margin-bottom: 0.8rem;
        }

        .th-info {
            border: 1px solid rgba(37,99,235,0.15);
            background: rgba(37,99,235,0.06);
            color: var(--th-blue-dark);
            border-radius: 16px;
            padding: 0.7rem 0.85rem;
            font-size: 0.92rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }

        /* Divider cleanup */
        hr {
            border: none;
            height: 1px;
            background: var(--th-line);
            margin: 0.75rem 0 1rem 0;
        }

        @media (max-width: 1100px) {
            .th-stat-grid {
                grid-template-columns: 1fr;
            }
            .th-hero-title {
                font-size: 1.6rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# 4. SESSION STATE
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "target_page" not in st.session_state:
    st.session_state.target_page = None

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = None

if "last_page_clicked" not in st.session_state:
    st.session_state.last_page_clicked = None

# Handle inline page links from query params
query_params = st.query_params
page_from_url = query_params.get("page", None)

if page_from_url is not None:
    try:
        page_num = int(page_from_url)
        if st.session_state.last_page_clicked != page_num:
            st.session_state.target_page = page_num
            st.session_state.last_page_clicked = page_num
    except Exception:
        pass


# =========================
# 5. HELPERS
# =========================
def clear_page_query_param():
    try:
        if "page" in st.query_params:
            del st.query_params["page"]
    except Exception:
        pass


def set_page_query_param(page_num: int):
    st.query_params["page"] = str(page_num)


def render_message_with_inline_page_links(content: str):
    """
    Converts :page[X] tags into true inline links.
    Keeps text readable and preserves simple line breaks.
    """
    safe = html.escape(content)

    def replace_page_tag(match):
        page_num = match.group(1)
        return f'<a class="page-link" href="?page={page_num}">Page {page_num}</a>'

    safe = re.sub(r":page\[(\d+)\]", replace_page_tag, safe)
    safe = safe.replace("\n", "<br>")
    st.markdown(f'<div class="msg-rich">{safe}</div>', unsafe_allow_html=True)


def estimate_page_count(pdf_bytes: bytes) -> str:
    # Lightweight heuristic; avoid adding more deps.
    # This is just a display nicety, not critical logic.
    try:
        text = pdf_bytes[:200000].decode("latin-1", errors="ignore")
        matches = re.findall(r"/Type\s*/Page\b", text)
        if matches:
            return str(len(matches))
    except Exception:
        pass
    return "PDF loaded"


# =========================
# 6. API SETUP
# =========================
api_key = st.secrets.get("GOOGLE_API_KEY", None)
client = genai.Client(api_key=api_key) if api_key else None


# =========================
# 7. HEADER / HERO
# =========================
st.markdown(
    """
    <div class="th-hero">
        <div class="th-eyebrow">TurboHome Disclosure Intelligence</div>
        <div class="th-hero-title">Review faster. Catch more. Jump straight to the page.</div>
        <div class="th-hero-copy">
            Upload a disclosure package, ask a question, and get grounded findings with inline page citations
            that open the exact page in the PDF viewer.
        </div>

        <div class="th-badges">
            <span class="th-badge"><span class="th-badge-dot"></span> Inline page citations</span>
            <span class="th-badge"><span class="th-badge-dot"></span> Disclosure-focused analysis</span>
            <span class="th-badge"><span class="th-badge-dot"></span> Fast PDF navigation</span>
        </div>

        <div class="th-stat-grid">
            <div class="th-stat">
                <div class="th-stat-label">Workflow</div>
                <div class="th-stat-value">Upload → Ask → Audit</div>
            </div>
            <div class="th-stat">
                <div class="th-stat-label">Output</div>
                <div class="th-stat-value">Findings with :page[X]</div>
            </div>
            <div class="th-stat">
                <div class="th-stat-label">Viewer</div>
                <div class="th-stat-value">Focus any cited page instantly</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload Disclosure Package (PDF)",
    type=["pdf"],
    help="Add the full seller disclosure packet, inspection materials, HOA docs, or related PDFs.",
)

if uploaded_file is not None:
    st.session_state.pdf_bytes = uploaded_file.read()
    st.session_state.pdf_name = uploaded_file.name

pdf_bytes = st.session_state.pdf_bytes


# =========================
# 8. MAIN APP
# =========================
if pdf_bytes:
    col_pdf, col_chat = st.columns([1.25, 1], gap="large")

    # -------------------------
    # LEFT: DOCUMENT VIEWER
    # -------------------------
    with col_pdf:
        st.markdown('<div class="th-shell">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="th-panel">
                <div class="th-panel-header">
                    <div>
                        <div class="th-panel-title">📄 Disclosure Document</div>
                        <div class="th-panel-subtitle">
                            Review the full package or jump directly from a cited finding.
                        </div>
                    </div>
                    <div class="th-doc-meta">
                        {html.escape(st.session_state.pdf_name or "Disclosure Package")} · {estimate_page_count(pdf_bytes)}
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.target_page:
            st.markdown(
                f"""
                <div class="th-info">
                    Focused on page {st.session_state.target_page}. Use “Back to full document” to return to the continuous view.
                </div>
                """,
                unsafe_allow_html=True,
            )
            pdf_viewer(
                input=pdf_bytes,
                height=860,
                pages_to_render=[st.session_state.target_page],
            )

            if st.button("Back to full document", key="back_to_full_doc"):
                st.session_state.target_page = None
                st.session_state.last_page_clicked = None
                clear_page_query_param()
                st.rerun()
        else:
            pdf_viewer(
                input=pdf_bytes,
                height=860,
            )

        st.markdown("</div></div>", unsafe_allow_html=True)

    # -------------------------
    # RIGHT: CHAT
    # -------------------------
    with col_chat:
        st.markdown(
            """
            <div class="th-shell">
                <div class="th-chat-wrap">
                    <div class="th-panel-header" style="margin-bottom:0.4rem;">
                        <div>
                            <div class="th-panel-title">🤖 TurboHome Auditor</div>
                            <div class="th-panel-subtitle">Ask about risk, repairs, disclosures, HOA, permits, or negotiation leverage.</div>
                        </div>
                    </div>
                    <div class="th-section-note">
                        Citations appear inline as clickable page links.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        chat_container = st.container(height=640)

        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    render_message_with_inline_page_links(msg["content"])

        prompt = st.chat_input("Ask a question about the disclosure package...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    # -------------------------
    # AI RESPONSE
    # -------------------------
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with col_chat:
            with st.chat_message("assistant"):
                with st.spinner("Auditing disclosure package..."):
                    if not api_key or not client:
                        st.error("Missing GOOGLE_API_KEY in Streamlit secrets.")
                    else:
                        try:
                            contents = [
                                types.Part.from_bytes(
                                    data=pdf_bytes,
                                    mime_type="application/pdf",
                                )
                            ]

                            for m in st.session_state.messages:
                                role = "model" if m["role"] == "assistant" else "user"
                                contents.append(
                                    types.Content(
                                        role=role,
                                        parts=[types.Part.from_text(text=m["content"])],
                                    )
                                )

                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                config=types.GenerateContentConfig(
                                    system_instruction=SYSTEM_PROMPT,
                                    temperature=0.0,
                                ),
                                contents=contents,
                            )

                            answer = getattr(response, "text", None) or "I couldn't generate a response."
                            st.session_state.messages.append(
                                {"role": "assistant", "content": answer}
                            )
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error: {e}")

else:
    st.markdown(
        """
        <div class="th-shell">
            <div class="th-panel">
                <div class="th-panel-title">Get started</div>
                <div class="th-section-note" style="margin-top:0.4rem;">
                    Upload a disclosure PDF to launch the auditor and begin asking questions.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
