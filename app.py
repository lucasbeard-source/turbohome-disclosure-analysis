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
Focus on EDUCATIONAL/LEARNING questions (e.g., "Learn about [Topic]" or "Explain [Topic]").
Format: SUGGESTIONS_START
Q1 text | Q2 text | Q3 text
SUGGESTIONS_END

--- TONE ---
Speak like a sharp, experienced agent who is 100% on the buyer's side. Be clear, not alarming. Translate jargon. 
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

/* ── Summary Table Row Logic ── */
.issue-name { font-weight: 600; font-size: 13px; color: #1e293b; }
.cost-range { font-weight: 700; font-size: 13px; color: #0f172a; font-family: 'DM Serif Display', serif; }

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
section[data-testid="stSidebar"] { background: #0f1923 !important; border-right: none !important; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.sidebar-doc-item {
    padding: 8px 12px; border-radius: 8px; font-size: 12px;
    background: rgba(255,255,255,0.06); margin-bottom: 4px;
    border: 1px solid rgba(255,255,255,0.08); cursor: pointer;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    color: #cbd5e1 !important;
}

/* ── Progress bar ── */
.analysis-progress { background: #f1f5f9; border-radius: 8px; overflow: hidden; height: 6px; margin-top: 8px; }
.analysis-progress-bar {
    height: 100%; width: 60%;
    background: linear-gradient(90deg, #f97316, #ea580c);
    border-radius: 8px; animation: pulse-bar 1.5s ease-in-out infinite;
}
@keyframes pulse-bar { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
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
        "suggestions": ["What are the biggest red flags?", "Explain foundation risks", "How does this affect my offer?"],
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

# =========================================================
# 4. HELPERS
# =========================================================
def find_best_doc_match(ai_doc_name):
    if not ai_doc_name: return None
    docs = list(st.session_state.pdf_library.keys())
    for real_name in docs:
        if ai_doc_name.lower() in real_name.lower() or real_name.lower() in ai_doc_name.lower():
            return real_name
    return None

def parse_page_number(pg_str):
    match = re.search(r'\b(\d+)\b', str(pg_str))
    return int(match.group(1)) if match else None

def parse_cost(cost_str):
    cleaned = re.sub(r'[^\d]', '', str(cost_str))
    return int(cleaned) if cleaned else 0

def parse_and_store_data(text):
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if not match: return
    lines = [l.strip() for l in match.group(1).strip().split('\n') if '|' in l]
    new_rows = []
    for l in lines:
        parts = [p.strip() for p in l.split('|')]
        if len(parts) >= 6:
            new_rows.append({
                "sev": parts[0].capitalize(), "name": parts[1], "txt": parts[2],
                "doc": parts[3], "pg": parts[4], "min": parse_cost(parts[5]),
                "max": parse_cost(parts[6]) if len(parts) > 6 else parse_cost(parts[5]),
            })
    if new_rows:
        existing_names = {r["name"] for r in st.session_state.summary_table}
        for row in new_rows:
            if row["name"] not in existing_names:
                st.session_state.summary_table.append(row)
                existing_names.add(row["name"])

def parse_suggestions(text):
    match = re.search(r"SUGGESTIONS_START\s*(.*?)\s*SUGGESTIONS_END", text, re.DOTALL)
    if match:
        suggestions = [s.strip() for s in match.group(1).split('|')]
        return suggestions[:3]
    return None

def compute_risk_score(rows):
    if not rows: return 0, "No Data", {}
    weights = {"High": 3, "Medium": 1.5, "Low": 0.5}
    score = sum(weights.get(r["sev"], 0) for r in rows)
    counts = {"High": 0, "Medium": 0, "Low": 0}
    for r in rows: counts[r["sev"]] = counts.get(r["sev"], 0) + 1
    normalized = min(round(math.log1p(score) * 2.5, 1), 10.0)
    label = "High Risk" if normalized >= 7 else ("Moderate Risk" if normalized >= 4 else "Low Risk")
    return normalized, label, counts

# =========================================================
# 5. UI: SIDEBAR, HEADER, EMPTY STATE
# =========================================================
with st.sidebar:
    st.markdown('<div style="font-family:\'DM Serif Display\',serif;font-size:22px;color:white;">Turbo<span style="color:#f97316;">Home</span></div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload Disclosure Packet", type=["pdf"], accept_multiple_files=True)
    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

    if st.session_state.pdf_library:
        for doc_name in st.session_state.pdf_library:
            active = "active" if doc_name == st.session_state.viewing_doc else ""
            st.markdown(f'<div class="sidebar-doc-item {active}">📄 {doc_name[:35]}...</div>', unsafe_allow_html=True)
        if st.button("🔄 Reset Audit", use_container_width=True):
            for k in ["messages", "pdf_library", "summary_table"]: st.session_state[k] = [] if k != "pdf_library" else {}
            st.rerun()

st.markdown('<div class="th-topbar"><div class="th-topbar-left"><div class="th-logo-mark">🏠</div><div class="th-brand">Turbo<span>Home</span> Auditor</div></div><div class="th-badge">BETA</div></div>', unsafe_allow_html=True)

if not st.session_state.pdf_library:
    st.markdown('<div class="th-card"><div class="empty-state"><div class="empty-state-icon">📂</div><div class="empty-state-title">No documents uploaded</div><div class="empty-state-body">Upload PDFs in the sidebar to begin analysis.</div></div></div>', unsafe_allow_html=True)
    st.stop()

# =========================================================
# 6. MAIN COCKPIT
# =========================================================
col_view, col_chat = st.columns([1.15, 1], gap="large")

with col_view:
    st.markdown('<div class="th-card"><div class="th-card-header">📄 Document Viewer</div>', unsafe_allow_html=True)
    docs = list(st.session_state.pdf_library.keys())
    curr_idx = docs.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in docs else 0
    st.session_state.viewing_doc = st.selectbox("Select document", docs, index=curr_idx, label_visibility="collapsed")
    
    pg = parse_page_number(st.session_state.target_page) if st.session_state.target_page else None
    if pg:
        if st.button("← Show all pages", key="reset_pg"): st.session_state.target_page = None; st.rerun()
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=580, pages_to_render=[pg])
    else:
        pdf_viewer(input=st.session_state.pdf_library[st.session_state.viewing_doc], height=580)
    st.markdown('</div>', unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="th-card"><div class="th-card-header">💬 Analysis Chat</div>', unsafe_allow_html=True)
    chat_box = st.container(height=430)
    with chat_box:
        if not st.session_state.messages:
            st.markdown('<div style="text-align:center;padding:32px;color:#94a3b8;">Click the priority button to start.</div>', unsafe_allow_html=True)
        else:
            for m in st.session_state.messages:
                txt = re.sub(r"(DATA|SUGGESTIONS)_(START|END).*?", "", m["content"], flags=re.DOTALL)
                role_class = "chat-user-msg" if m["role"] == "user" else "chat-ai-msg"
                label = "" if m["role"] == "user" else '<div class="chat-ai-label">🏠 TurboHome AI</div>'
                st.markdown(f'{label}<div class="{role_class}">{txt}</div>', unsafe_allow_html=True)

    if not st.session_state.messages:
        if st.button("🔍 Run Priority Risk Analysis", key="priority_btn", type="primary", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "List all issues by priority with document source, page number, and costs."})
            st.rerun()
    else:
        s_cols = st.columns(3)
        for i, sugg in enumerate(st.session_state.suggestions[:3]):
            if s_cols[i].button(sugg, key=f"sugg_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sugg}); st.rerun()

    if prompt := st.chat_input("Ask about documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt}); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 7. SUMMARY RAIL
# =========================================================
rows = st.session_state.summary_table
if rows:
    score, label, counts = compute_risk_score(rows)
    score_color = "#dc2626" if score >= 7 else ("#d97706" if score >= 4 else "#16a34a")
    t_min, t_max = sum(r["min"] for r in rows), sum(r["max"] for r in rows)

    

    st.markdown(f'<div class="risk-score-wrap"><div style="text-align:center;"><div class="risk-score-number" style="color:{score_color};">{score}</div><div style="font-size:10px;font-weight:700;">/ 10</div></div><div><div style="font-size:18px;font-weight:700;font-family:\'DM Serif Display\',serif;">{label}</div><div class="risk-score-detail"><span class="sev-badge sev-high">{counts.get("High",0)} High</span> <span class="sev-badge sev-medium">{counts.get("Medium",0)} Med</span></div></div><div style="margin-left:auto;text-align:right;"><div style="font-size:11px;color:#94a3b8;">EST. REPAIR COST</div><div style="font-family:\'DM Serif Display\',serif;font-size:26px;">${t_min:,} – ${t_max:,}</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="th-card"><div class="th-card-header">📊 Issues Summary</div>', unsafe_allow_html=True)
    h_cols = st.columns([0.5, 1, 2.2, 1, 0.8])
    for col, lbl in zip(h_cols, ["SEV", "ISSUE", "CITATION", "DOCUMENT", "COST"]):
        col.markdown(f'<div style="font-size:10px;font-weight:700;color:#94a3b8;">{lbl}</div>', unsafe_allow_html=True)

    for i, r in enumerate(sorted(rows, key=lambda x: {"High":0,"Medium":1,"Low":2}.get(x["sev"],3))):
        c1, c2, c3, c4, c5 = st.columns([0.5, 1, 2.2, 1, 0.8])
        c1.markdown(f'<span class="sev-badge sev-{r["sev"].lower()}">{r["sev"]}</span>', unsafe_allow_html=True)
        c2.markdown(f'<div class="issue-name">{r["name"]}</div>', unsafe_allow_html=True)
        if c3.button(f"🔗 {r['txt'][:60]}...", key=f"link_{i}", help="Click to jump to page"):
            match = find_best_doc_match(r["doc"])
            if match: st.session_state.viewing_doc, st.session_state.target_page = match, r["pg"]; st.rerun()
        c4.markdown(f'<div style="font-size:11px;color:#64748b;">{r["doc"][:20]}...<br>pg.{r["pg"]}</div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="cost-range">${r["min"]:,}+</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 8. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with col_chat: st.markdown('<div class="analysis-progress"><div class="analysis-progress-bar"></div></div>', unsafe_allow_html=True)
    
    try:
        pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
        history = [types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages[-10:]]
        
        res = client.models.generate_content(model="gemini-2.0-flash-exp", config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0), contents=pdf_parts + history)
        
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        parse_and_store_data(res.text)
        suggs = parse_suggestions(res.text)
        if suggs: st.session_state.suggestions = suggs
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")
