import streamlit as st
import os
import tempfile
from google import genai
from google.genai import types

# --- 1. SYSTEM INSTRUCTIONS ---
SYSTEM_PROMPT = """
You are the 'TurboHome Disclosure Auditor'. 
Your goal is to analyze real estate disclosure PDFs and:
1. Identify missing information or incomplete sections.
2. Flag "Red Flag" items (mold, foundation issues, unpermitted work).
3. Check for missing signatures or dates.
4. Summarize key risks for the buyer.
"""

# --- 2. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="TurboHome Disclosure Analysis", page_icon="🏠")

st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #FF4B4B; color: white; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏠 TurboHome Disclosure Analysis")
st.write("Professional-grade AI audit for real estate disclosures.")

# --- 3. API SETUP ---
# Priority 1: Streamlit Secrets (for Deployment)
# Priority 2: Sidebar Input (for Local Testing)
api_key = st.secrets.get("GOOGLE_API_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.info("Please add your Google API Key to the sidebar or Streamlit secrets to begin.")
    st.stop()

# Initialize the modern 2026 Client
client = genai.Client(api_key=api_key)

# --- 4. FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Disclosure PDF", type=['pdf'])

if uploaded_file:
    if st.button("🔍 Run Disclosure Audit"):
        with st.spinner("Analyzing document structure and content..."):
            try:
                # 1. Read the PDF bytes directly
                file_bytes = uploaded_file.read()
                
                # 2. Call Gemini 3 Flash (fast & cheap for document parsing)
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2, # Lower temperature for factual auditing
                    ),
                    contents=[
                        types.Part.from_bytes(
                            data=file_bytes,
                            mime_type="application/pdf"
                        ),
                        "Perform a complete risk audit on this document."
                    ]
                )

                # 3. Display Results
                st.success("Audit Complete")
                st.markdown("### 📋 Audit Findings")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"Analysis failed: {e}")

st.divider()
st.caption("TurboHome is an AI assistant. Always verify findings with a licensed professional.")
