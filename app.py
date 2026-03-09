import streamlit as st
import os
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. UPDATED PLAYBOOK WITH INLINE LINK INSTRUCTION ---
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Include your full playbook here...)

--- CITATION RULE ---
For every finding you identify, you MUST include the page number as a hyperlink at the end of the sentence.
Use exactly this format: [[Page X]](/?page=X)
Example: "The roof is made of concrete tile [Page 8](/?page=8)."
Only cite the page number where the information was actually found.
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# --- 3. SYNC PAGE STATE WITH URL ---
# Check if the URL has a ?page=X parameter and update the state
query_params = st.query_params
if "page" in query_params:
    st.session_state.current_page = int(query_params["page"])
elif "current_page" not in st.session_state:
    st.session_state.current_page = 1

# --- 4. UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    
    col_pdf, col_chat = st.columns([1.2, 1], gap="large")

    # LEFT SIDE: PDF VIEWER (Listens to st.session_state.current_page)
    with col_pdf:
        st.subheader(f"📄 Disclosure Document")
        # Ensure we use the current page from our state
        pdf_viewer(
            input=pdf_bytes, 
            height=850, 
            pages_to_render=[st.session_state.current_page] 
        )

    # RIGHT SIDE: CHAT WITH INLINE LINKS
    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        chat_placeholder = st.container(height=650)
        
        with chat_placeholder:
            if "messages" not in st.session_state:
                st.session_state.messages = []
            
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Ask about the disclosures..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_placeholder:
                with st.chat_message("user"):
                    st.markdown(prompt)

            with chat_placeholder:
                with st.chat_message("assistant"):
                    try:
                        api_key = st.secrets["GOOGLE_API_KEY"]
                        client = genai.Client(api_key=api_key)
                        
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                temperature=0.0
                            ),
                            contents=[
                                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                                *[types.Content(role=m["role"], parts=[types.Part.from_text(text=m["content"])]) 
                                  for m in st.session_state.messages]
                            ]
                        )
                        
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        st.rerun() # Refresh to ensure the links are active
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- 5. LOGIC TO DETECT LINK CLICKS ---
# This forces the app to acknowledge the query parameter change from the link
if "page" in query_params and int(query_params["page"]) != st.session_state.current_page:
    st.session_state.current_page = int(query_params["page"])
    st.rerun()
