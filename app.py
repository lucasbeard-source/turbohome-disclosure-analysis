import re
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# =========================================================
# 1. THE PLAYBOOK (STRICT TABLE FORMATTING)
# =========================================================
def get_system_prompt(is_financial_mode):
    prompt = """
    TurboHome Disclosure Analysis Playbook
    Analyze the uploaded PDFs and find all material risks.
    
    --- OUTPUT FORMAT ---
    You MUST end every response with a 'DATA_START' and 'DATA_END' block containing a 
    structured summary for the findings rail.
    
    Format each line as:
    [Severity] | [Issue Name] | :jump[Issue Text]{doc="DocName" page=X} | [Est Cost]
    
    Severities: High, Medium, Low.
    Example: High | Cracked Foundation | :jump[Main slab has 1/4 inch crack]{doc="Home Inspection" page=14} | $15,000
    """
    if is_financial_mode:
        prompt += "\nInclude realistic 2026 repair costs for the [Est Cost] column."
    else:
        prompt += "\nUse 'N/A' for the [Est Cost] column."
    return prompt

# =========================================================
# 2. PAGE CONFIG & STYLING
# =========================================================
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 4.5rem !important; max-width: 1750px; }
    .stApp { background: #fcfdfe; }
    .th-header { background: #0f172a; color: white; padding: 10px 20px; border-radius: 12px; margin-bottom: 12px; }
    
    /* Styled DataFrame Table */
    [data-testid="stDataFrame"] { border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE & PARSING
# =========================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_library" not in st.session_state: st.session_state.pdf_library = {} 
if "target_page" not in st.session_state: st.session_state.target_page = None
if "viewing_doc" not in st.session_state: st.session_state.viewing_doc = None

def parse_table_data(text):
    """Extracts rows between DATA_START and DATA_END."""
    results = []
    # Find the block
    match = re.search(r"DATA_START(.*?)DATA_END", text, re.DOTALL)
    if match:
        lines = match.group(1).strip().split('\n')
        for line in lines:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) == 4:
                results.append({
                    "Severity": parts[0],
                    "Issue Name": parts[1],
                    "Citation": parts[2],
                    "Estimated Cost": parts[3]
                })
    return results

# =========================================================
# 4. TOP BAR & CONTROLS
# =========================================================
h_col1, h_col2 = st.columns([3, 1])
with h_col1:
    st.markdown('<div class="th-header"><strong>TurboHome Disclosure Analysis</strong></div>', unsafe_allow_html=True)
with h_col2:
    financial_mode = st.toggle("💰 Financial Estimation Mode", value=False)

# =========================================================
# 5. SIDEBAR
# =========================================================
with st.sidebar:
    st.title("📂 Files")
    files = st.file_uploader("Upload PDF Packet", type=["pdf"], accept_multiple_files=True)
    if files:
        for f in files:
            if f.name not in st.session_state.pdf_library: st.session_state.pdf_library[f.name] = f.read()
        if not st.session_state.viewing_doc and st.session_state.pdf_library:
            st.session_state.viewing_doc = list(st.session_state.pdf_library.keys())[0]

if not st.session_state.pdf_library:
    st.info("Upload documents to start.")
    st.stop()

# =========================================================
# 6. MAIN COCKPIT
# =========================================================
col_pdf, col_chat = st.columns([1.2, 1], gap="medium")

with col_pdf:
    st.subheader("📄 Evidence Viewer")
    doc_list = list(st.session_state.pdf_library.keys())
    cur_idx = doc_list.index(st.session_state.viewing_doc) if st.session_state.viewing_doc in doc_list else 0
    selected_doc = st.selectbox("Select Doc", doc_list, index=cur_idx, label_visibility="collapsed")
    st.session_state.viewing_doc = selected_doc

    if st.session_state.target_page:
        st.success(f"Viewing p.{st.session_state.target_page}")
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600, pages_to_render=[st.session_state.target_page])
        if st.button("⬅ Back"): st.session_state.target_page = None; st.rerun()
    else:
        pdf_viewer(input=st.session_state.pdf_library[selected_doc], height=600)

with col_chat:
    st.subheader("🤖 Auditor Chat")
    chat_box = st.container(height=520)
    with chat_box:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                # Clean the text of the DATA block for the user
                clean_text = re.sub(r"DATA_START.*?DATA_END", "", m["content"], flags=re.DOTALL)
                st.markdown(clean_text)

    if prompt := st.chat_input("Ask Auditor..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

# =========================================================
# 7. BOTTOM RAIL: SORTABLE TABLE
# =========================================================
st.write("---")
st.subheader("📋 Integrated Findings Rail")

last_assistant = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")

if last_assistant:
    table_data = parse_table_data(last_assistant)
    if table_data:
        df = pd.DataFrame(table_data)
        
        # Color coding severity for the user
        def color_severity(val):
            color = '#fee2e2' if val == 'High' else '#fef3c7' if val == 'Medium' else '#f1f5f9'
            return f'background-color: {color}'

        # Render Sortable Table
        st.dataframe(
            df.style.applymap(color_severity, subset=['Severity']),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Severity": st.column_config.TextColumn("Severity", width="small"),
                "Issue Name": st.column_config.TextColumn("Issue Name", width="medium"),
                "Citation": st.column_config.TextColumn("Citation / Jump Link", width="large"),
                "Estimated Cost": st.column_config.TextColumn("Estimated Cost (2026)", width="small"),
            }
        )
        st.caption("💡 Click any column header to sort.")
    else:
        st.caption("Waiting for AI to generate structured data...")
else:
    st.caption("Perform an audit to populate the findings table.")

# =========================================================
# 8. AI ENGINE
# =========================================================
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    MODEL_NAME = "gemini-3-flash-preview"
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    with st.spinner("Analyzing..."):
        try:
            pdf_parts = [types.Part.from_bytes(data=b, mime_type="application/pdf") for b in st.session_state.pdf_library.values()]
            history = [types.Content(role="model" if m["role"] == "assistant" else "user", 
                       parts=[types.Part.from_text(text=m["content"])]) for m in st.session_state.messages]
            
            res = client.models.generate_content(
                model=MODEL_NAME, 
                config=types.GenerateContentConfig(system_instruction=get_system_prompt(financial_mode), temperature=0.0),
                contents=pdf_parts + history
            )
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()
        except Exception as e:
            st.error(f"Audit Error: {e}")
