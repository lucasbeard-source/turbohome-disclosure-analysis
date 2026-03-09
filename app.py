import streamlit as st
import os
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. ENHANCED PLAYBOOK ---
# I added a instruction at the bottom to force the AI to cite page numbers
SYSTEM_PROMPT = """
Disclosure Review Playbook
(Include all your previous instructions here...)

--- CITATION RULE ---
For every finding you identify, you MUST include the page number in brackets at the end of the sentence, 
e.g., "The roof is 15 years old [Page 4]". 
Only cite the page number where the information was actually found in the PDF.
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_page" not in st.session_state:
    st.session_state.current_page = 1  # Default to page 1

# --- 4. API SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 5. UI ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    
    col_pdf, col_chat = st.columns([1.2, 1], gap="large")

    # LEFT SIDE: PDF VIEWER WITH STATEFUL PAGE JUMPING
    with col_pdf:
        st.subheader(f"📄 Disclosure Document (Viewing Page {st.session_state.current_page})")
        
        # We pass the current_page from session_state here
        pdf_viewer(
            input=pdf_bytes, 
            height=800, 
            pages_to_render=[st.session_state.current_page] # This focuses the viewer
        )

    # RIGHT SIDE: CHAT & CLICKABLE LINKS
    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        chat_placeholder = st.container(height=600)
        
        with chat_placeholder:
            for i, message in enumerate(st.session_state.messages):
                with st.chat_message(message["role"]):
                    # LOGIC: Find [Page X] in the text and turn it into a button
                    content = message["content"]
                    pages_found = re.findall(r"\[Page (\d+)\]", content)
                    
                    st.markdown(content)
                    
                    # Create small buttons for each page found in this specific message
                    if pages_found:
                        cols = st.columns(len(pages_found))
                        for idx, p in enumerate(pages_found):
                            if cols[idx].button(f"Go to Page {p}", key=f"btn_{i}_{p}"):
                                st.session_state.current_page = int(p)
                                st.rerun() # Refresh to update the PDF viewer

        if prompt := st.chat_input("Ask about the disclosures..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_placeholder:
                with st.chat_message("user"):
                    st.markdown(prompt)

            with chat_placeholder:
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing..."):
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
                        st.rerun() # Ensure buttons appear immediately
