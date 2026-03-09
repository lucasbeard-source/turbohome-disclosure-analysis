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
    --th-blue: #2f5bff;
    --th-blue-dark: #2147db;
    --th-navy: #13203b;
    --th-text: #41516b;
    --th-muted: #74829a;
    --th-line: #dfe7f4;
    --th-bg: #f5f8ff;
    --th-card: #ffffff;
    --th-green: #13b981;
    --th-shadow: 0 18px 45px rgba(23, 37, 84, 0.08);
    --th-radius-xl: 28px;
    --th-radius-lg: 22px;
    --th-radius-md: 16px;
}

html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(47, 91, 255, 0.10), transparent 28%),
        linear-gradient(180deg, #f8fbff 0%, #f3f7ff 100%);
}

.block-container {
    max-width: 1500px;
    padding-top: 1.6rem;
    padding-bottom: 2rem;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header {visibility: hidden;}

/* Hero */
.th-hero {
    background:
        linear-gradient(135deg, rgba(47,91,255,0.10) 0%, rgba(255,255,255,0.95) 52%, rgba(245,248,255,1) 100%);
    border: 1px solid rgba(47, 91, 255, 0.12);
    border-radius: 30px;
    padding: 28px 28px 24px 28px;
    box-shadow: var(--th-shadow);
    margin-bottom: 18px;
}

.th-eyebrow {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--th-blue-dark);
    margin-bottom: 10px;
}

.th-title {
    font-size: 28px;
    line-height: 1.08;
    font-weight: 850;
    letter-spacing: -0.03em;
    color: var(--th-navy);
    margin-bottom: 10px;
}

.th-copy {
    max-width: 760px;
    color: var(--th-text);
    font-size: 18px;
    line-height: 1.6;
    margin-bottom: 18px;
}

.th-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 18px;
}

.th-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.9);
    color: var(--th-navy);
    border: 1px solid rgba(47, 91, 255, 0.14);
    border-radius: 999px;
    padding: 10px 14px;
    font-size: 14px;
    font-weight: 700;
}

.th-badge-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--th-green);
    display: inline-block;
}

.th-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}

.th-stat {
    background: rgba(255,255,255,0.82);
    border: 1px solid var(--th-line);
    border-radius: 20px;
    padding: 16px 18px;
}

.th-stat-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 800;
    color: var(--th-muted);
    margin-bottom: 6px;
}

.th-stat-value {
    color: var(--th-navy);
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.02em;
}

/* Shell / cards */
.th-shell {
    background: rgba(255,255,255,0.72);
    border: 1px solid rgba(223,231,244,0.9);
    border-radius: var(--th-radius-xl);
    padding: 14px;
    box-shadow: var(--th-shadow);
}

.th-panel {
    background: var(--th-card);
    border: 1px solid var(--th-line);
    border-radius: var(--th-radius-lg);
    padding: 16px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.th-panel-header {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 10px;
}

.th-panel-title {
    color: var(--th-navy);
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.th-panel-subtitle {
    color: var(--th-muted);
    font-size: 14px;
    line-height: 1.5;
    margin-top: 3px;
}

.th-doc-meta {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
    border-radius: 999px;
    padding: 9px 12px;
    background: rgba(47, 91, 255, 0.08);
    border: 1px solid rgba(47, 91, 255, 0.14);
    color: var(--th-blue-dark);
    font-size: 13px;
    font-weight: 800;
}

.th-info {
    background: rgba(47, 91, 255, 0.06);
    border: 1px solid rgba(47, 91, 255, 0.12);
    color: var(--th-blue-dark);
    border-radius: 16px;
    padding: 12px 14px;
    margin-bottom: 12px;
    font-size: 14px;
    font-weight: 700;
}

/* Uploader */
.stFileUploader {
    background: rgba(255,255,255,0.78);
    border: 1px dashed rgba(47,91,255,0.35);
    border-radius: 22px;
    padding: 6px;
}

/* Buttons */
.stButton > button {
    border-radius: 999px !important;
    border: 1px solid transparent !important;
    background: linear-gradient(180deg, var(--th-blue), var(--th-blue-dark)) !important;
    color: white !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    padding: 0.60rem 1rem !important;
    box-shadow: 0 10px 24px rgba(47,91,255,0.18) !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
}

/* Chat */
[data-testid="stChatMessage"] {
    background: transparent !important;
}
[data-testid="stChatMessageContent"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}
.th-chat-wrap {
    background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    border: 1px solid var(--th-line);
    border-radius: var(--th-radius-lg);
    padding: 10px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.th-message {
    border: 1px solid var(--th-line);
    background: #ffffff;
    border-radius: 18px;
    padding: 14px 16px;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.03);
}

.th-message-user {
    background: linear-gradient(180deg, #f7f9ff 0%, #ffffff 100%);
}

.th-message-assistant {
    background: #ffffff;
}

.th-message-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 800;
    color: var(--th-muted);
    margin-bottom: 8px;
}

.msg-rich {
    color: var(--th-text);
    font-size: 15.5px;
    line-height: 1.72;
    word-wrap: break-word;
}
.msg-rich p {
    margin: 0 0 0.8rem 0;
}
.msg-rich p:last-child {
    margin-bottom: 0;
}

/* Next-level inline citation pills */
.page-cite {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    vertical-align: baseline;
    margin: 0 2px;
    padding: 2px 9px;
    border-radius: 999px;
    border: 1px solid rgba(47, 91, 255, 0.16);
    background: rgba(47, 91, 255, 0.08);
    color: var(--th-blue-dark);
    text-decoration: none !important;
    font-size: 0.92em;
    font-weight: 800;
    white-space: nowrap;
    transition: all 0.16s ease;
}
.page-cite:hover {
    background: rgba(47, 91, 255, 0.14);
    border-color: rgba(47, 91, 255, 0.28);
    color: var(--th-blue-dark);
    transform: translateY(-1px);
}
.page-cite-dot {
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: var(--th-blue);
    display: inline-block;
}

/* Chat input */
[data-testid="stChatInput"] {
    border-radius: 18px;
}

/* Responsive */
@media (max-width: 1100px) {
    .th-stats {
        grid-template-columns: 1fr;
    }
    .th-title {
        font-size: 24px;
    }
    .th-copy {
        font-size: 16px;
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

# Same-window navigation using query params
query_params = st.query_params
page_from_url = query_params.get("page", None)
if page_from_url is not None:
    try:
        st.session_state.target_page = int(page_from_url)
    except Exception:
        pass

# =========================
# 5. HELPERS
# =========================
def clear_page_param():
    try:
        if "page" in st.query_params:
            del st.query_params["page"]
    except Exception:
        pass


def estimate_page_count(pdf_bytes: bytes) -> str:
    try:
        text = pdf_bytes[:250000].decode("latin-1", errors="ignore")
        matches = re.findall(r"/Type\s*/Page\b", text)
        if matches:
            return f"{len(matches)} pages"
    except Exception:
        pass
    return "PDF loaded"


def render_message_with_inline_page_links(content: str):
    """
    Replaces :page[X] with same-window clickable citation pills.
    """
    safe = html.escape(content)

    def replace_page_tag(match):
        page_num = match.group(1)
        js = (
            "window.parent.history.replaceState({}, '', '?page="
            + page_num
            + "'); window.parent.location.search='?page="
            + page_num
            + "'; return false;"
        )
        return (
            f'<a class="page-cite" href="?page={page_num}" onclick="{js}">'
            f'<span class="page-cite-dot"></span>p.{page_num}</a>'
        )

    safe = re.sub(r":page\[(\d+)\]", replace_page_tag, safe)

    paragraphs = [p for p in safe.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [safe]

    body = "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)
    st.markdown(f'<div class="msg-rich">{body}</div>', unsafe_allow_html=True)


def render_chat_message(role: str, content: str):
    label = "You" if role == "user" else "TurboHome Auditor"
    role_class = "th-message-user" if role == "user" else "th-message-assistant"
    st.markdown(
        f"""
        <div class="th-message {role_class}">
            <div class="th-message-label">{label}</div>
        """,
        unsafe_allow_html=True,
    )
    render_message_with_inline_page_links(content)
    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# 6. API SETUP
# =========================
api_key = st.secrets.get("GOOGLE_API_KEY", None)
client = genai.Client(api_key=api_key) if api_key else None

# =========================
# 7. HERO
# =========================
st.markdown(
    """
<div class="th-hero">
    <div class="th-eyebrow">TurboHome Disclosure Intelligence</div>
    <div class="th-title">Review faster. Catch more. Jump straight to the page.</div>
    <div class="th-copy">
        Upload a disclosure package, ask a question, and get grounded findings with inline page citations
        that take you directly to the exact page in the PDF viewer.
    </div>

    <div class="th-badges">
        <span class="th-badge"><span class="th-badge-dot"></span>Inline page citations</span>
        <span class="th-badge"><span class="th-badge-dot"></span>Disclosure-focused analysis</span>
        <span class="th-badge"><span class="th-badge-dot"></span>Fast PDF navigation</span>
    </div>

    <div class="th-stats">
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

# =========================
# 8. FILE UPLOAD
# =========================
uploaded_file = st.file_uploader(
    "Upload Disclosure Package (PDF)",
    type=["pdf"],
    help="Upload seller disclosures, inspection reports, HOA docs, or any related packet.",
)

if uploaded_file is not None:
    st.session_state.pdf_bytes = uploaded_file.read()
    st.session_state.pdf_name = uploaded_file.name

pdf_bytes = st.session_state.pdf_bytes

# =========================
# 9. MAIN APP
# =========================
if pdf_bytes:
    col_pdf, col_chat = st.columns([1.25, 1], gap="large")

    # LEFT: PDF VIEWER
    with col_pdf:
        st.markdown('<div class="th-shell">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="th-panel">
                <div class="th-panel-header">
                    <div>
                        <div class="th-panel-title">📄 Disclosure Document</div>
                        <div class="th-panel-subtitle">
                            Review the full package or jump directly from any cited finding.
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
                    Focused on page {st.session_state.target_page}. Click “Back to full document” to return to continuous view.
                </div>
                """,
                unsafe_allow_html=True,
            )

            pdf_viewer(
                input=pdf_bytes,
                height=860,
                pages_to_render=[st.session_state.target_page],
            )

            if st.button("Back to full document", key="back_to_full_document"):
                st.session_state.target_page = None
                clear_page_param()
                st.rerun()
        else:
            pdf_viewer(
                input=pdf_bytes,
                height=860,
            )

        st.markdown("</div></div>", unsafe_allow_html=True)

    # RIGHT: CHAT
    with col_chat:
        st.markdown(
            """
            <div class="th-shell">
                <div class="th-chat-wrap">
                    <div class="th-panel-header" style="margin-bottom: 4px;">
                        <div>
                            <div class="th-panel-title">🤖 TurboHome Auditor</div>
                            <div class="th-panel-subtitle">
                                Ask about risk, repairs, disclosures, permits, HOA, negotiation leverage, or missing items.
                            </div>
                        </div>
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
                    render_chat_message(msg["role"], msg["content"])

        prompt = st.chat_input("Ask a question about the disclosure package...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    # AI RESPONSE
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with col_chat:
            with st.chat_message("assistant"):
                st.markdown(
                    '<div class="th-message th-message-assistant"><div class="th-message-label">TurboHome Auditor</div>',
                    unsafe_allow_html=True,
                )
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
                            render_message_with_inline_page_links(answer)
                            st.session_state.messages.append({"role": "assistant", "content": answer})
                            st.markdown("</div>", unsafe_allow_html=True)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error: {e}")
                            st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown(
        """
        <div class="th-shell">
            <div class="th-panel">
                <div class="th-panel-title">Get started</div>
                <div class="th-panel-subtitle" style="margin-top: 8px;">
                    Upload a disclosure PDF to launch the auditor and begin asking questions.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
