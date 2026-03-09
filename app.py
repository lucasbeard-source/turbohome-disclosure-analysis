import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer
import streamlit.components.v1 as components

# --- 1. THE PLAYBOOK ---
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Include your full playbook here...)

--- CITATION RULE ---
For every finding, you MUST include the page number using this exact format: <a href="javascript:void(0)" onclick="window.parent.postMessage({type: 'jump', page: X}, '*')">[Page X]</a>
Example: "The roof is 15 years old <a href='javascript:void(0)' onclick='window.parent.postMessage({type: \"jump\", page: 18}, \"*\")'>[Page 18]</a>."
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# --- 3. JAVASCRIPT BRIDGE ---
# This invisible component listens for the "jump" message from the chat links
components.html("""
<script>
window.addEventListener('message', function(event) {
    if (event.data.type === 'jump') {
        const url = new URL(window.parent.location);
        url.searchParams.set('page', event.data.page);
        window.parent.history.pushState({}, '', url);
        // Force Streamlit to notice the change by clicking a hidden refresh button
        window.parent.document.querySelector('.stApp').click();
    }
});
</script>
""", height=0)

# --- 4. STATE SYNC ---
params = st.query_params
if "page" in params:
    st.session_state.target_page = int(params["page"])
elif "target_page" not in st.session_state:
    st.session_state.target_page = None

# --- 5. UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    col_pdf, col_chat = st.columns([1.3, 1], gap="large")

    with col_pdf:
        st.subheader("📄 Disclosure Document")
        
        # Logical check to prevent NoneType iteration error
        if st.session_state.target_page:
            st.info(f"Viewing Page {st.session_state.target_page}")
            pdf_viewer(input=pdf_bytes, height=850, pages_to_render=[st.session_state.target_page])
            if st.button("⬅️ Back to Full Document"):
                st.query_params.clear()
                st.session_state.target_page = None
                st.rerun()
        else:
            pdf_viewer(input=pdf_bytes, height=850)

    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                # We use unsafe_allow_html=True to render our custom Javascript links
                st.markdown(msg["content"], unsafe_allow_html=True)

        if prompt := st.chat_input("Ask about the disclosures..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("Auditing..."):
                    try:
                        api_key = st.secrets["GOOGLE_API_KEY"]
                        client = genai.Client(api_key=api_key)
                        
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.0),
                            contents=[
                                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                                *[types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) 
                                  for m in st.session_state.messages]
                            ]
                        )
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
