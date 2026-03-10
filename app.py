import re
import os
import math
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE AUDITOR PLAYBOOK
# =========================================================
SYSTEM_PROMPT = """
TurboHome Disclosure Analysis Playbook
You are a professional real estate auditor trained to analyze disclosure packets, inspection reports, and HOA documents for material risks that affect a buyer's decision or negotiation.

Your job:
- Identify ALL material risks: structural, electrical, plumbing, environmental, legal/title, HOA, permits, and financial.
- Be specific. Always cite the document name and page number.
- Provide realistic cost estimates based on Bay Area / California contractor rates.
- Be direct and useful. Buyers are making a $1M+ decision.

--- DATA BLOCK RULE ---
ONLY include a DATA_START block if you are identifying NEW or UPDATED risks.
Never repeat risks already in the conversation history unless explicitly asked.

Format (one risk per line):
[Severity] | [Issue Name] | [Short Citation Text] | [Doc Name] | [Page X] | [Min Cost $] | [Max Cost $]

Severities: High, Medium, Low
Cost format: integers only, no symbols (e.g. 5000 | 25000)

Wrap ALL risk rows between DATA_START and DATA_END tags.

--- SUGGESTIONS BLOCK ---
After your main response, always output exactly 3 concise follow-up question suggestions (under 8 words each).
Format: SUGGESTIONS_START
Q1 text | Q2 text | Q3 text
SUGGESTIONS_END

--- TONE ---
Speak like a sharp, experienced agent who is 100% on the buyer's side. Be clear, not alarming. Translate jargon. If something is truly not an issue, say so plainly.
"""

# =========================================================
# 2. PAGE CONFIG & STYLING
# =========================================================
st.set_page_config(
    page_title="TurboHome · Disclosure Auditor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Serif+Display:ital@0;1&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp { font-family: 'DM Sans', sans-serif; background: #f8f7f4 !important; }
.block-container { padding: 1.5rem 2rem 3rem !important; max-width: 1800px !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Top Header Bar ── */
.th-topbar {
    display: flex; align-items: center; justify-content: space-between;
    background: #0f1923; color: white;
    padding: 14px 28px; border-radius: 16px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.18);
}
.th-topbar-left { display: flex; align-items: center; gap: 14px; }
.th-logo-mark {
    width: 36px; height: 36px; background: #f97316;
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 18px; flex-shrink: 0;
}
.th-brand { font-family: 'DM Serif Display', serif; font-size: 20px; letter-spacing: -0.3px; }
.th-brand span { color: #f97316; }
.th-subtitle { font-size: 12px; color: #94a3b8; font-weight: 400; margin-top: 1px; }
.th-badge {
    background: rgba(249,115,22,0.15); color: #f97316;
    border: 1px solid rgba(249,115,22,0.3);
    padding: 5px 12px; border-radius: 999px; font-size: 11px; font-weight: 600;
    letter-spacing: 0.5px;
}

/* ── Cards ── */
.th-card {
    background: white; border: 1px solid #e8e4dc;
    border-radius: 18px; padding: 22px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    margin-bottom: 1.25rem;
}
.th-card-header {
    font-size: 13px; font-weight: 600; color: #475569;
    text-transform: uppercase; letter-spacing: 0.8px;
    margin-bottom: 14px; display: flex; align-items: center; gap: 8px;
}

/* ── Risk Score Widget ── */
.risk-score-wrap {
    display: flex; align-items: center; gap: 20px;
    padding: 16px 20px; border-radius: 14px;
    background: linear-gradient(135deg, #fff7ed 0%, #fff 100%);
    border: 1px solid #fed7aa;
    margin-bottom: 1.25rem;
}
.risk-score-number {
    font-family: 'DM Serif Display', serif;
    font-size: 52px; line-height: 1; color: #ea580c;
}
.risk-score-label { font-size: 13px; color: #92400e; font-weight: 500; }
.risk-score-detail { font-size: 11px; color: #b45309; margin-top: 3px; }

/* ── Severity Badges ── */
.sev-badge { padding: 3px 10px; border-radius: 999px; font-weight: 700; font-size: 10px; letter-spacing: 0.4px; text-transform: uppercase; white-space: nowrap; }
.sev-high   { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.sev-medium { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
.sev-low    { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }

/* ── Summary Table ── */
.table-header-row {
    display: grid; grid-template-columns: 80px 160px 1fr 140px 110px;
    gap: 10px; padding: 8px 12px;
    font-size: 10px; font-weight: 700; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.8px;
    border-bottom: 1px solid #f1f5f9; margin-bottom: 4px;
}
.table-data-row {
    display: grid; grid-template-columns: 80px 160px 1fr 140px 110px;
    gap: 10px; padding: 10px 12px; align-items: center;
    border-radius: 10px; transition: background 0.15s;
}
.table-data-row:hover { background: #f8fafc; }
.issue-name { font-weight: 600; font-size: 13px; color: #1e293b; }
.cost-range { font-weight: 700; font-size: 13px; color: #0f172a; font-family: 'DM Serif Display', serif; }
.cost-totals {
    background: #0f1923; color: white;
    padding: 14px 20px; border-radius: 12px; margin-top: 12px;
    display: flex; justify-content: space-between; align-items: center;
}
.cost-totals-label { font-size: 12px; color: #94a3b8; font-weight: 500; }
.cost-totals-value { font-family: 'DM Serif Display', serif; font-size: 24px; color: #f97316; }

/* ── Chat ── */
.chat-user-msg {
    background: #0f1923; color: white;
    padding: 12px 16px; border-radius: 14px 14px 4px 14px;
    font-size: 14px; margin: 8px 0; max-width: 85%; margin-left: auto;
}
.chat-ai-msg {
    background: #f1f5f9; color: #1e293b;
    padding: 12px 16px; border-radius: 4px 14px 14px 14px;
    font-size: 14px; margin: 8px 0; max-width: 92%; line-height: 1.6;
}
.chat-ai-label {
    font-size: 10px; font-weight: 700; color: #f97316;
    text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;
}

/* ── Suggestion Buttons ── */
.stButton > button[data-testid*="sugg"] {
    background: white !important; border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important; font-size: 12px !important;
    padding: 8px 12px !important; width: 100% !important;
    color: #334155 !important; text-align: left !important;
    transition: all 0.15s !important; font-family: 'DM Sans', sans-serif !important;
}
.stButton > button[data-testid*="sugg"]:hover {
    border-color: #f97316 !important; color: #f97316 !important;
    background: #fff7ed !important;
}

/* ── Primary CTA ── */
div.stButton > button.priority-btn {
    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;
    color: white !important; font-weight: 700 !important;
    border-radius: 14px !important; padding: 16px 28px !important;
    border: none !important; width: 100% !important; font-size: 15px !important;
    box-shadow: 0 6px 20px rgba(249,115,22,0.35) !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
}
div.stButton > button.priority-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 28px rgba(249,115,22,0.45) !important;
}

/* ── Citation Links ── */
div.stButton > button.link-btn {
    color: #2563eb !important; font-size: 12px !important;
    border: none !important; background: none !important;
    padding: 2px 0 !important; text-align: left !important;
    text-decoration: underline !important; text-underline-offset: 3px !important;
    white-space: normal !important; height: auto !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0f1923 !important; border-right: none !important;
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stFileUploader label { color: #94a3b8 !important; }
.sidebar-doc-item {
    padding: 8px 12px; border-radius: 8px; font-size: 12px;
    background: rgba(255,255,255,0.06); margin-bottom: 4px;
    border: 1px solid rgba(255,255,255,0.08); cursor: pointer;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    color: #cbd5e1 !important;
}
.sidebar-doc-item.active { background: rgba(249,115,22,0.2) !important; border-color: rgba(249,115,22,0.4) !important; color: #fdba74 !important; }

/* ── Empty State ── */
.empty-state {
    text-align: center; padding: 48px 24px; color: #94a3b8;
}
.empty-state-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state-title { font-size: 16px; font-weight: 600; color: #475569; margin-bottom: 6px; }
.empty-state-body { font-size: 13px; line-height: 1.6; }

/* ── Doc selector ── */
div[data-testid="stSelectbox"] > div > div {
    border-radius: 10px !important; border-color: #e2e8f0 !important;
    font-size: 13px !important;
}

/* ── Divider ── */
.th-divider { height: 1px; background: #f1f5f9; margin: 12px 0; }

/* ── Progress bar ── */
.analysis-progress {
    background: #f1f5f9; border-radius: 8px; overflow: hidden;
    height: 6px; margin-top: 8px;
}
.analysis-progress-bar {
    height: 100%; width: 60%;
    background: linear-gradient(90deg, #f97316, #ea580c);
    border-radius: 8px;
    animation: pulse-bar 1.5s ease-in-out infinite;
}
@keyframes pulse-bar {
    0%, 100% { opacity: 1; } 50% { opacity: 0.6; }
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE
# =========================================================
def init_state():
    defaults = {
        "messages": [],
        "pdf_library": {},
        "target_page": None,
        "viewing_doc": None,
        "summary_table": [],
        "suggestions": [
            "What are the biggest red flags?",
            "Explain the foundation risks",
            "How does this affect my offer?"
        ],
        "is_analyzing": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =========================================================
# 4. HELPERS
# =========================================================
def find_best_doc_match(ai_doc_name):
    if not ai_doc_name:
        return None
    for real_name in st.session_state.pdf_library:
        if ai_doc_name.lower() in real_name.lower() or real_name.lower() in ai_doc_name.lower():
            return real_name
    return None

def parse_page_number(pg_str):
    """Safely extract a page number from strings like 'Page 12', '12', 'p.12'."""
    match = re.search(r'\b(\d+)\b', str(pg_str))
    return int(match.group(1)) if match else None

def parse_cost(cost_str):
    """Extract integer from cost string."""
    cleaned = re.sub(r'[^\d]', '', str(cost_str))
    return int(cleaned) if cleaned else 0

def parse_and_store_data(text):
    """Parse DATA_START...DATA_END block and update summary table."""
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if not match:
        return
    lines = [l.strip() for l in match.group(1).strip().split('\n') if '|' in l]
    new_rows = []
    for l in lines:
        parts = [p.strip() for p in l.split('|')]
        if len(parts) >= 6:
            new_rows.append({
                "sev":  parts[0].capitalize(),
                "name": parts[1],
                "txt":  parts[2],
                "doc":  parts[3],
                "pg":   parts[4],
                "min":  parse_cost(parts[5]),
                "max":  parse_cost(parts[6]) if len(parts) > 6 else parse_cost(parts[5]),
            })
    if new_rows:
        # Merge: avoid exact-name duplicates
        existing_names = {r["name"] for r in st.session_state.summary_table}
        for row in new_rows:
            if row["name"] not in existing_names:
                st.session_state.summary_table.append(row)
                existing_names.add(row["name"])

def parse_suggestions(text):
    """Parse SUGGESTIONS_START...SUGGESTIONS_END block."""
    match = re.search(r"SUGGESTIONS_START\s*(.*?)\s*SUGGESTIONS_END", text, re.DOTALL)
    if match:
        suggestions = [s.strip() for s in match.group(1).split('|')]
        clean = [s for s in suggestions if s and not s.startswith('Q')]
        if len(clean) >= 3:
            return clean[:3]
    return None

def strip_data_blocks(text):
    """Remove DATA and SUGGESTIONS blocks from displayed text."""
    text = re.sub(r"DATA_START.*?DATA_END", "", text, flags=re.DOTALL)
    text = re.sub(r"SUGGESTIONS_START.*?SUGGESTIONS_END", "", text, flags=re.DOTALL)
    return text.strip()

def compute_risk_score(rows):
    """Compute a 0–10 risk score from issue list."""
    if not rows:
        return None, None, {}
    weights = {"High": 3, "Medium": 1.5, "Low": 0.5}
    score = sum(weights.get(r["sev"], 0) for r in rows)
    counts = {"High": 0, "Medium": 0, "Low": 0}
    for r in rows:
        counts[r["sev"]] = counts.get(r["sev"], 0) + 1
    # Normalize to 10, cap at 10
    normalized = min(round(math.log1p(score) * 2.5, 1), 10.0)
    if normalized >= 7:
        label = "High Risk"
    elif normalized >= 4:
        label = "Moderate Risk"
    else:
        label = "Low Risk"
    return normalized, label, counts

def reset_session():
    for key in ["messages", "pdf_library", "target_page", "viewing_doc", "summary_table"]:
        st.session_state[key] = [] if key in ["messages", "summary_table"] else (None if key in ["target_page", "viewing_doc"] else {})
    st.session_state.suggestions = [
        "What are the biggest red flags?",
        "Explain the foundation risks",
        "How does this affect my offer?"
    ]

# =========================================================
# 5. SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="padding: 8px 0 20px;">
            <div style="font-family: 'DM Serif Display', serif; font-size: 22px; color: white;">
                Turbo<span style="color: #f97316;">Home</span>
            </div>
            <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Disclosure Auditor</div>
        </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload Disclosure Packet",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload PDFs: disclosure, inspection report, HOA docs, etc."
    )

    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.pdf_library:
                st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

    if st.session_state.pdf_library:
        st.markdown('<div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin: 16px 0 8px; font-weight: 600;">Documents</div>', unsafe_allow_html=True)
        for doc_name in st.session_state.pdf_library:
            is_active = doc_name == st.session_state.viewing_doc
            css_class = "sidebar-doc-item active" if is_active else "sidebar-doc-item"
            short_name = doc_name[:38] + "…" if len(doc_name) > 40 else doc_name
            st.markdown(f'<div class="{css_class}">📄 {short_name}</div>', unsafe_allow_html=True)

        st.markdown('<div style="margin-top: 24px;"></div>', unsafe_allow_html=True)
        if st.button("🔄 Start New Audit", use_container_width=True):
            reset_session()
            st.rerun()

    st.markdown("""
        <div style="position: fixed; bottom: 24px; font-size: 11px; color: #334155; line-height: 1.5;">
            <strong style="color: #64748b;">TurboHome</strong> · AI-assisted audit<br>
            <span style="color: #475569;">Not a substitute for legal advice</span>
        </div>
    """, unsafe_allow_html=True)

# =========================================================
# 6. HEADER
# =========================================================
st.markdown("""
<div class="th-topbar">
    <div class="th-topbar-left">
        <div class="th-logo-mark">🏠</div>
        <div>
            <div class="th-brand">Turbo<span>Home</span> Disclosure Auditor</div>
            <div class="th-subtitle">AI-powered property risk analysis · Built for buyers</div>
        </div>
    </div>
    <div class="th-badge">BETA</div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 7. UPLOAD EMPTY STATE
# =========================================================
if not st.session_state.pdf_library:
    st.markdown("""
    <div class="th-card">
        <div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <div class="empty-state-title">No documents uploaded yet</div>
            <div class="empty-state-body">
                Upload your disclosure packet, inspection report, HOA documents, or any property-related PDFs
                using the sidebar on the left.<br><br>
                TurboHome will analyze them for material risks, flag issues by severity, and estimate repair costs —
                so you can negotiate with confidence.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# =========================================================
# 8. MAIN COCKPIT — PDF Viewer + Chat
# =========================================================
col_view, col_chat = st.columns([1.15, 1], gap="large")

# ── PDF VIEWER ──────────────────────────────────────────
with col_view:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-header">📄 Document Viewer</div>', unsafe_allow_html=True)

    docs = list(st.session_state.pdf_library.keys())
    curr_idx = docs.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in docs else 0
    selected_doc = st.selectbox("Select document", docs, index=curr_idx, label_visibility="collapsed")
    if selected_doc != st.session_state.viewing_doc:
        st.session_state.viewing_doc = selected_doc
        st.session_state.target_page = None

    pdf_bytes = st.session_state.pdf_library[st.session_state.viewing_doc]

    if st.session_state.target_page:
        page_num = parse_page_number(st.session_state.target_page)
        col_back, col_pginfo = st.columns([1, 3])
        with col_back:
            if st.button("← All pages"):
                st.session_state.target_page = None
                st.rerun()
        with col_pginfo:
            st.markdown(f'<span style="font-size:12px; color:#64748b;">Jumping to page {page_num}</span>', unsafe_allow_html=True)

        try:
            if page_num:
                pdf_viewer(input=pdf_bytes, height=580, pages_to_render=[page_num])
            else:
                pdf_viewer(input=pdf_bytes, height=580)
        except Exception:
            pdf_viewer(input=pdf_bytes, height=580)
    else:
        pdf_viewer(input=pdf_bytes, height=580)

    st.markdown('</div>', unsafe_allow_html=True)

# ── CHAT ────────────────────────────────────────────────
with col_chat:
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-header">💬 Analysis Chat</div>', unsafe_allow_html=True)

    chat_container = st.container(height=430)
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center; padding: 32px 16px; color: #94a3b8;">
                <div style="font-size: 32px; margin-bottom: 10px;">🔍</div>
                <div style="font-size: 14px; font-weight: 600; color: #475569; margin-bottom: 6px;">Ready to audit</div>
                <div style="font-size: 12px; line-height: 1.6;">
                    Click the button below to run your first<br>automated risk analysis.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.messages:
                clean_content = strip_data_blocks(msg["content"])
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-user-msg">{clean_content}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-ai-label">🏠 TurboHome AI</div><div class="chat-ai-msg">{clean_content}</div>', unsafe_allow_html=True)

    # ── CTA / Suggestions
    if not st.session_state.messages:
        if st.button("🔍 Run Priority Risk Analysis", key="priority_btn", type="primary", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "List all issues by priority. Be thorough — include severity, document source, page number, and estimated repair costs for each issue."})
            st.rerun()
    else:
        st.markdown('<div class="th-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 11px; color: #94a3b8; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px;">Suggested follow-ups</div>', unsafe_allow_html=True)
        s_cols = st.columns(3)
        for i, sugg in enumerate(st.session_state.suggestions[:3]):
            if s_cols[i].button(sugg, key=f"sugg_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sugg})
                st.rerun()

    if prompt := st.chat_input("Ask anything about these documents…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 9. RISK SCORE + SUMMARY TABLE
# =========================================================
rows = st.session_state.summary_table

if rows:
    score, score_label, counts = compute_risk_score(rows)
    total_min = sum(r["min"] for r in rows)
    total_max = sum(r["max"] for r in rows)

    # ── Risk Score Widget
    score_color = "#dc2626" if score and score >= 7 else ("#d97706" if score and score >= 4 else "#16a34a")
    high_c = counts.get("High", 0)
    med_c = counts.get("Medium", 0)
    low_c = counts.get("Low", 0)

    st.markdown(f"""
    <div class="risk-score-wrap">
        <div style="text-align:center; flex-shrink:0;">
            <div class="risk-score-number" style="color:{score_color};">{score}</div>
            <div style="font-size: 10px; color: #92400e; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px;">/ 10</div>
        </div>
        <div>
            <div style="font-size: 18px; font-weight: 700; color: #1e293b; font-family: 'DM Serif Display', serif;">{score_label}</div>
            <div class="risk-score-detail">
                <span class="sev-badge sev-high">{high_c} High</span>&nbsp;
                <span class="sev-badge sev-medium">{med_c} Medium</span>&nbsp;
                <span class="sev-badge sev-low">{low_c} Low</span>
            </div>
        </div>
        <div style="margin-left:auto; text-align:right;">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 500;">TOTAL EST. REPAIR COST</div>
            <div style="font-family: 'DM Serif Display', serif; font-size: 26px; color: #0f172a;">${total_min:,} – ${total_max:,}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Issues Table
    st.markdown('<div class="th-card">', unsafe_allow_html=True)
    st.markdown('<div class="th-card-header">📊 Issues Summary</div>', unsafe_allow_html=True)

    # Header row
    h_cols = st.columns([0.5, 1, 2.2, 1, 0.8])
    for col, label in zip(h_cols, ["SEV", "ISSUE", "CITATION", "DOCUMENT", "EST. COST"]):
        col.markdown(f'<div style="font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.8px;">{label}</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

    # Sort: High → Medium → Low
    order = {"High": 0, "Medium": 1, "Low": 2}
    sorted_rows = sorted(rows, key=lambda r: order.get(r["sev"], 3))

    for i, r in enumerate(sorted_rows):
        c1, c2, c3, c4, c5 = st.columns([0.5, 1, 2.2, 1, 0.8])
        sev_lower = r["sev"].lower()
        c1.markdown(f'<span class="sev-badge sev-{sev_lower}">{r["sev"].upper()}</span>', unsafe_allow_html=True)
        c2.markdown(f'<div class="issue-name">{r["name"]}</div>', unsafe_allow_html=True)

        # Citation link
        citation_text = r["txt"][:65] + "…" if len(r["txt"]) > 67 else r["txt"]
        if c3.button(f'🔗 {citation_text}', key=f"link_{i}"):
            match = find_best_doc_match(r["doc"])
            if match:
                st.session_state.viewing_doc = match
                st.session_state.target_page = r["pg"]
                st.rerun()
            else:
                st.warning(f'Could not locate document: "{r["doc"]}"')

        # Doc name (short)
        doc_short = r["doc"][:22] + "…" if len(r["doc"]) > 24 else r["doc"]
        c4.markdown(f'<div style="font-size:11px; color:#64748b;">{doc_short}<br><span style="color:#94a3b8;">{r["pg"]}</span></div>', unsafe_allow_html=True)

        if r["min"] and r["max"]:
            c5.markdown(f'<div class="cost-range">${r["min"]:,}–{r["max"]:,}</div>', unsafe_allow_html=True)
        else:
            c5.markdown('<div style="font-size:12px; color:#94a3b8;">TBD</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="th-card">
        <div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <div class="empty-state-title">No issues identified yet</div>
            <div class="empty-state-body">
                Click "Run Priority Risk Analysis" above to begin.<br>
                Issues will appear here with severity ratings, citations, and estimated repair costs.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# 10. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-2.5-flash-preview-04-17"
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.error("Missing GOOGLE_API_KEY. Add it to .streamlit/secrets.toml or set as environment variable.")
        st.stop()

    client = genai.Client(api_key=api_key)

    with col_chat:
        with st.container():
            st.markdown("""
            <div style="padding: 10px 0 4px;">
                <div style="font-size: 12px; color: #f97316; font-weight: 600;">🏠 TurboHome AI &nbsp;·&nbsp; <span style="color: #94a3b8; font-weight: 400;">Analyzing documents…</span></div>
                <div class="analysis-progress"><div class="analysis-progress-bar"></div></div>
            </div>
            """, unsafe_allow_html=True)

    try:
        # Build PDF parts
        pdf_parts = [
            types.Part.from_bytes(data=b, mime_type="application/pdf")
            for b in st.session_state.pdf_library.values()
        ]

        # Cap history to last 10 messages to manage token window
        recent_history = st.session_state.messages[-10:]
        history_parts = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part.from_text(text=m["content"])]
            )
            for m in recent_history
        ]

        response = client.models.generate_content(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.0,
            ),
            contents=pdf_parts + history_parts
        )

        reply_text = response.text
        st.session_state.messages.append({"role": "assistant", "content": reply_text})

        # Parse structured data
        parse_and_store_data(reply_text)

        # Parse suggestions (embedded in response — no second API call)
        new_suggestions = parse_suggestions(reply_text)
        if new_suggestions:
            st.session_state.suggestions = new_suggestions

        st.rerun()

    except Exception as e:
        st.error(f"Analysis error: {str(e)}")
        st.info("Check your GOOGLE_API_KEY and that you have access to the Gemini API.")
