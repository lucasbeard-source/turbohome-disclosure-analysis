import streamlit as st
from google import genai  # Updated to the new 2026 standard library
import tempfile
import os

# --- 1. SYSTEM INSTRUCTIONS ---
SYSTEM_PROMPT = """
You are the 'TurboHome Disclosure Auditor'. You are an expert in real estate disclosures, 
compliance, and risk mitigation. 

Analyze the uploaded PDF and:
1. Identify missing information/incomplete sections.
2. Flag "Red Flag" items (mold, unpermitted work, foundation issues).
3. Check for missing signatures/dates.
4. Summarize key risks.
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="TurboHome Disclosure Analysis",
    page_icon="🏠",
    layout="centered"
)

# FIXED: Changed 'unsafe_allow_value' to 'unsafe_allow_html'
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏠 TurboHome Disclosure Analysis")

# --- 3. API SETUP ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("Please add your GOOGLE_API_KEY to continue.")
    st.stop()

# Updated Client Initialization for google-genai
client = genai.Client(api_key=api_key)

# --- 4. FILE UPLOADER ---
uploaded_file = st.file_uploader("Choose a Disclosure PDF", type=['pdf'])

if uploaded_file:
    st.info(f"File ready: {uploaded_file.name}")
    
    if st.button("Run Disclosure Audit"):
        with st.spinner("Analyzing document..."):
            try:
                # Save to a temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                # New 2026 way to generate content with a file
                with open(tmp_path, "rb") as f:
                    response = client.models.generate_content(
                        model="gemini-2.0-flash", # Using the latest stable Flash model
                        config={'system_instruction': SYSTEM_PROMPT},
                        contents=[
                            genai.types.Part.from_bytes(
                                data=f.read(),
                                mime_type="application/pdf"
                            ),
                            "Please perform a full disclosure audit on this document."
                        ]
                    )

                st.success("Audit Complete!")
                st.markdown("---")
                st.markdown(response.text)
                
                os.remove(tmp_path)

            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
