import re
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. PLAYBOOK
# =========================================================
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Your full playbook text here)

When appropriate, organize findings using these sections:
- Critical Risks
- Repairs / Deferred Maintenance
- Permit / Compliance Issues
- Insurance / Hazard Concerns
- Follow-up Questions

--- CITATION RULE ---
For every finding, you MUST include the page number using this exact tag: :page[X]
Example: "The roof is 15 years old :page[18]."
"""

# =========================================================
# 2. PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="TurboHome Auditor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# 3. STYLES
# =========================================================
st.markdown(
    """
<style>
    :root {
        --bg: #f6f8fb;
        --panel: #ffffff;
        --panel-muted: #f8fafc;
        --border: #e5e7eb;
        --border-soft: #eef2f7;
        --text: #0f172a;
        --text-muted: #64748b;
        --blue: #2563eb;
        --blue-soft: #eff6ff;
        --red: #dc2626;
        --red-soft: #fef2f2;
        --amber: #d97706;
        --amber-soft: #fffbeb;
        --slate-soft: #f1f5f9;
        --shadow: 0 1px 2px rgba(16, 24, 40, 0.04), 0 8px 24px rgba(16, 24, 40, 0.04);
        --radius: 16px;
    }

    .stApp {
        background: linear-gradient(180deg, #f8fafc 0%, #f4f7fb 100%);
    }

    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text);
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    /* HERO */
    .th-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        color: white;
        padding: 24px 28px;
        border-radius: 20px;
        box-shadow: var(--shadow);
        margin-bottom: 16px;
    }

    .th-hero-title {
        font-size: 1.85rem;
        font-weight: 750;
        line-height: 1.1;
        margin-bottom: 6px;
        letter-spacing: -0.02em;
    }

    .th-hero-subtitle {
        font-size: 0.98rem;
        line-height: 1.55;
        color: rgba(255,255,255,0.82);
        max-width: 760px;
    }

    .th-badge-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 14px;
    }

    .th-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(255,255,255,0.10);
        border: 1px solid rgba(255,255,255,0.10);
        color: white;
        padding: 7px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* METRICS */
    .th-metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin: 0 0 16px 0;
    }

    .th-metric {
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--border-soft);
        border-radius: 14px;
        padding: 12px 14px;
    }

    .th-metric-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-bottom: 3px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .th-metric-value {
        font-size: 1rem;
        color: var(--text);
        font-weight: 700;
        letter-spacing: -0.01em;
    }

    /* PANELS */
    .th-card {
        background: rgba(255,255,255,0.90);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 16px;
        box-shadow: var(--shadow);
        height: 100%;
    }

    .th-card-header {
        margin-bottom: 12px;
    }

    .th-card-title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 2px;
    }

    .th-card-subtitle {
        font-size: 0.9rem;
        color: var(--text-muted);
    }

    /* FILE UPLOADER */
    [data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.92);
        border: 1px dashed #cbd5e1;
        border-radius: 14px;
        padding: 10px;
        box-shadow: none;
    }

    /* CHAT */
    [data-testid="stChatMessage"] {
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 0;
        margin-bottom: 10px;
    }

    [data-testid="stChatMessageContent"] {
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 12px 14px;
        box-shadow: 0 1px 2px rgba(16,24,40,0.03);
    }

    [data-testid="stChatInput"] {
        background: white;
        border-radius: 14px;
    }

    .th-divider {
        height: 1px;
        width: 100%;
        background: var(--border-soft);
        margin: 14px 0;
    }

    /* INLINE PAGE BUTTONS */
    div.stButton > button {
        border: none !important;
        padding: 0px 2px !important;
        background-color: transparent !important;
        color: var(--blue) !important;
        text-decoration: underline !important;
        font-size: inherit !important;
        display: inline !important;
        min-height: 0px !important;
        height: auto !important;
        vertical-align: baseline !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }

    /* Suggestion chips */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background: #fff !important;
        color: #334155 !important;
        border: 1px solid var(--border) !important;
        text-decoration: none !important;
        border-radius: 999px !important;
        padding: 8px 12px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        box-shadow: none !important;
    }

    div[data-testid="column"] .stButton > button[key^="sugg_"]:hover {
        border-color: #cbd5e1 !important;
        background: #f8fafc !important;
        color: #0f172a !important;
    }

    /* Back button */
    div.stButton > button[key="back_btn"] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 8px 12px !important;
        border-radius: 10px !important;
        border: 1px solid var(--border) !important;
        background: white !important;
        text-decoration: none !important;
        color: var(--text) !important;
        font-weight: 600 !important;
        min-height: 38px !important;
        box-shadow: none !important;
    }

    [data-testid="stInfo"] {
        border-radius: 12px;
        background: var(--blue-soft);
        border: 1px solid #bfdbfe;
    }

    /* EMPTY STATES */
    .th-empty {
        background: #ffffff;
        border: 1px dashed #dbe2ea;
        border-radius: 16px;
        padding: 22px;
        text-align: center;
        color: #334155;
    }

    .th-empty-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 6px;
        color: var(--text);
    }

    .th-empty-subtitle {
        font-size: 0.92rem;
        color: var(--text-muted);
        max-width: 540px;
        margin: 0 auto;
        line-height: 1.55;
    }

    /* FINDINGS */
    .findings-toolbar-label {
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 700;
        color: var(--text-muted);
        margin-bottom: 6px;
    }

    .finding-item {
        background: #ffffff;
        border: 1px solid var(--border-soft);
        border-radius: 12px;
        padding: 10px 12px;
        margin-top: 8px;
    }

    .finding-item.high {
        border-left: 3px solid var(--red);
    }

    .finding-item.medium {
        border-left: 3px solid var(--amber);
    }

    .finding-item.low {
        border-left: 3px solid #94a3b8;
    }

    .finding-top {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        margin-bottom: 6px;
    }

    .finding-badge {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 3px 8px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .finding-badge.high {
        background: var(--red-soft);
        color: var(--red);
    }

    .finding-badge.medium {
        background: var(--amber-soft);
        color: var(--amber);
    }

    .finding-badge.low {
        background: var(--slate-soft);
        color: #475569;
    }

    .finding-body {
        font-size: 0.92rem;
        color: #334155;
        line-height: 1.55;
    }

    .finding-rail-empty {
        background: #ffffff;
        border: 1px dashed #dbe2ea;
        border-radius: 14px;
        padding: 16px;
        color: var(--text-muted);
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* EXPANDERS */
    .streamlit-expanderHeader {
        font-weight: 650;
        color: var(--text);
        font-size: 0.95rem;
        border-radius: 10px;
    }

    [data-testid="stExpander"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        background: #fcfdff;
        overflow: hidden;
        margin-bottom: 10px;
    }

    /* MULTISELECT */
    [data-testid="stMultiSelect"] > div {
        background: #ffffff;
        border-radius: 12px;
    }

    [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background: #f8fafc !important;
        color: #334155 !important;
        border-radius: 999px !important;
        border: 1px solid #e2e8f0 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# 4. SESSION STATE
# =========================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "target_page" not in st.session_state:
    st.session_state.target_page = None

if "suggestions" not in st.session_state:
    st.session_state.suggestions = [
        "Biggest disclosure risks",
        "Check unpermitted work",
        "Summarize NHD hazards",
    ]

if "severity_filter" not in st.session_state:
    st.session_state.severity_filter = ["high", "medium", "low"]

# =========================================================
# 5. API SETUP
# =========================================================
MODEL_NAME = "gemini-3-flash-preview"
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# =========================================================
# 6. FINDINGS HELPERS
# =========================================================
SECTION_MAP = {
    "critical risks": "Critical Risks",
    "repairs / deferred maintenance": "Repairs / Deferred Maintenance",
    "repairs/deferred maintenance": "Repairs / Deferred Maintenance",
    "permit / compliance issues": "Permit / Compliance Issues",
    "permit/compliance issues": "Permit / Compliance Issues",
    "insurance / hazard concerns": "Insurance / Hazard Concerns",
    "insurance/hazard concerns": "Insurance / Hazard Concerns",
    "follow-up questions": "Follow-up Questions",
    "follow up questions": "Follow-up Questions",
}

DEFAULT_FINDINGS = {
    "Critical Risks": [],
    "Repairs / Deferred Maintenance": [],
    "Permit / Compliance Issues": [],
    "Insurance / Hazard Concerns": [],
    "Follow-up Questions": [],
}


def infer_severity(section_name: str) -> str:
    if section_name == "Critical Risks":
        return "high"
    if section_name in {
        "Repairs / Deferred Maintenance",
        "Permit / Compliance Issues",
        "Insurance / Hazard Concerns",
    }:
        return "medium"
    return "low"


def extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        clean = line.strip()
        if re.match(r"^[-*•]\s+", clean):
            bullets.append(re.sub(r"^[-*•]\s+", "", clean).strip())
        elif re.match(r"^\d+\.\s+", clean):
            bullets.append(re.sub(r"^\d+\.\s+", "", clean).strip())
    return bullets


def parse_findings(text: str) -> dict[str, list[str]]:
    findings = {k: [] for k in DEFAULT_FINDINGS.keys()}
    current_section = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = re.match(r"^#{1,6}\s*(.+)$", line)
        header_text = header_match.group(1).strip().lower() if header_match else None
        normalized = line.lower().strip(": ")

        if header_text and header_text in SECTION_MAP:
            current_section = SECTION_MAP[header_text]
            continue
        if normalized in SECTION_MAP:
            current_section = SECTION_MAP[normalized]
            continue

        bullet_match = re.match(r"^([-*•]|\d+\.)\s+(.*)$", line)
        if bullet_match and current_section:
            findings[current_section].append(bullet_match.group(2).strip())

    total_items = sum(len(v) for v in findings.values())
    if total_items == 0:
        fallback = extract_bullets(text)
        if fallback:
            findings["Critical Risks"] = fallback[:3]
            findings["Repairs / Deferred Maintenance"] = fallback[3:6]
        else:
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", text)
                if s.strip()
            ]
            findings["Critical Risks"] = sentences[:3]

    return findings


def latest_assistant_message() -> str | None:
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant":
            return msg["content"]
    return None


def filtered_findings(
    findings_dict: dict[str, list[str]],
    allowed_severities: list[str],
) -> dict[str, list[str]]:
    filtered: dict[str, list[str]] = {}
    for section_name, items in findings_dict.items():
        sev = infer_severity(section_name)
        filtered[section_name] = items if sev in allowed_severities else []
    return filtered


def render_text_with_page_buttons(text: str, prefix: str) -> None:
    parts = re.split(r"(:page\[\d+\])", text)
    for p_idx, part in enumerate(parts):
        match = re.match(r":page\[(\d+)\]", part)
        if match:
            page_num = int(match.group(1))
            if st.button(f"p. {page_num}", key=f"{prefix}_{p_idx}_{page_num}"):
                st.session_state.target_page = page_num
                st.rerun()
        else:
            if part.strip():
                st.markdown(part)


# =========================================================
# 7. HERO
# =========================================================
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload Disclosure Package (PDF)",
    type=["pdf"],
    help="Supported format: PDF",
)

if not uploaded_file:
    st.markdown(
        """
    <div class="th-empty">
        <div class="th-empty-title">Start with a disclosure package</div>
        <div class="th-empty-subtitle">
            Upload a PDF to analyze seller disclosures, inspection notes, and hazard reports.
            The auditor will cite every finding with clickable page references.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.stop()

# =========================================================
# 8. FILE LOADED
# =========================================================
pdf_bytes = uploaded_file.read()

col_pdf, col_workspace = st.columns([1.3, 1.15], gap="large")

with col_pdf:
    st.markdown(
        """
    <div class="th-card">
        <div class="th-card-header">
            <div class="th-card-title">Disclosure Document</div>
            <div class="th-card-subtitle">View the full file or jump to cited pages</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if st.session_state.target_page:
        st.info(f"Focused on page {st.session_state.target_page}")
        pdf_viewer(
            input=pdf_bytes,
            height=860,
            pages_to_render=[st.session_state.target_page],
        )
        if st.button("← Back to full document", key="back_btn"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=pdf_bytes, height=860)

    st.markdown("</div>", unsafe_allow_html=True)

with col_workspace:
    chat_col, findings_col = st.columns([1.15, 1.0], gap="medium")

    # =====================================================
    # CHAT PANEL
    # =====================================================
    with chat_col:
        st.markdown(
            """
        <div class="th-card">
            <div class="th-card-header">
                <div class="th-card-title">AI Auditor</div>
                <div class="th-card-subtitle">Ask questions, inspect risks, and follow citations</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        chat_container = st.container(height=620)

        with chat_container:
            if not st.session_state.messages:
                st.markdown(
                    """
                <div class="th-empty">
                    <div class="th-empty-title">No analysis yet</div>
                    <div class="th-empty-subtitle">
                        Try a suggested prompt below or ask, “What are the biggest risks in this package?”
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            for idx, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    render_text_with_page_buttons(msg["content"], prefix=f"chat_{idx}")

        st.markdown('<div class="th-divider"></div>', unsafe_allow_html=True)

        if st.session_state.suggestions:
            suggestion_cols = st.columns(len(st.session_state.suggestions))
            for idx, suggestion in enumerate(st.session_state.suggestions):
                if suggestion_cols[idx].button(suggestion, key=f"sugg_{idx}"):
                    st.session_state.messages.append(
                        {"role": "user", "content": suggestion}
                    )
                    st.rerun()

        prompt = st.chat_input(
            "Ask about risks, permits, hazards, repairs, or red flags..."
        )
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================
    # FINDINGS PANEL
    # =====================================================
    with findings_col:
        st.markdown(
            """
        <div class="th-card">
            <div class="th-card-header">
                <div class="th-card-title">Findings</div>
                <div class="th-card-subtitle">Structured due-diligence summary</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="findings-toolbar-label">Severity filter</div>',
            unsafe_allow_html=True,
        )

        selected_severities = st.multiselect(
            label="Severity",
            options=["high", "medium", "low"],
            default=st.session_state.severity_filter,
            key="severity_filter",
            label_visibility="collapsed",
            placeholder="Select severity",
        )

        latest_response = latest_assistant_message()

        if latest_response:
            findings = parse_findings(latest_response)
            findings = filtered_findings(findings, selected_severities)

            any_items = False
            for section_name, items in findings.items():
                if not items:
                    continue

                any_items = True
                sev = infer_severity(section_name)
                default_open = sev == "high"

                with st.expander(f"{section_name} ({len(items)})", expanded=default_open):
                    for idx, item in enumerate(items):
                        st.markdown(
                            f"""
                            <div class="finding-item {sev}">
                                <div class="finding-top">
                                    <div class="finding-badge {sev}">{sev.upper()}</div>
                                </div>
                                <div class="finding-body">
                            """,
                            unsafe_allow_html=True,
                        )
                        render_text_with_page_buttons(
                            item,
                            prefix=f"finding_{section_name}_{idx}",
                        )
                        st.markdown("</div></div>", unsafe_allow_html=True)

            if not any_items:
                st.markdown(
                    """
                <div class="finding-rail-empty">
                    No findings match the current severity filter. Try enabling more severity levels.
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                """
            <div class="finding-rail-empty">
                Findings will appear here after the first analysis. This rail is ideal for critical risks,
                deferred maintenance, compliance issues, hazard concerns, and buyer follow-up questions.
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 9. MODEL RUN
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with col_workspace:
        with st.chat_message("assistant"):
            with st.spinner("Reviewing disclosure package..."):
                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.0,
                        ),
                        contents=[
                            types.Part.from_bytes(
                                data=pdf_bytes,
                                mime_type="application/pdf",
                            ),
                            *[
                                types.Content(
                                    role="model" if m["role"] == "assistant" else "user",
                                    parts=[types.Part.from_text(text=m["content"])],
                                )
                                for m in st.session_state.messages
                            ],
                        ],
                    )

                    assistant_text = (
                        response.text
                        if response and getattr(response, "text", None)
                        else "I couldn't generate a response for this document."
                    )

                    st.session_state.messages.append(
                        {"role": "assistant", "content": assistant_text}
                    )

                    suggestion_prompt = (
                        f"Based on: '{assistant_text}', suggest 3 short follow-up questions "
                        f"(3-5 words) for a buyer. Output ONLY the questions separated by |."
                    )

                    sugg_res = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[suggestion_prompt],
                    )

                    if sugg_res and getattr(sugg_res, "text", None):
                        st.session_state.suggestions = [
                            s.strip()
                            for s in sugg_res.text.split("|")
                            if s.strip()
                        ][:3]

                    st.rerun()

                except Exception as e:
                    st.error(f"Audit Error: {e}")
