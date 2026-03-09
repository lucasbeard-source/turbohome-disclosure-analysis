import streamlit as st
import os
from google import genai
from google.genai import types

# --- 1. SYSTEM INSTRUCTIONS (The "Soul" of your Gem) ---
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

# Branding CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #FF4B4B; color: white; border-radius: 8px; font-weight: bold; }
    .main { background-color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏠 TurboHome Disclosure Analysis")
st.write("Professional-grade AI audit for real estate disclosures.")

# --- 3. API SETUP ---
# Fetching from Streamlit Secrets (TOML format)
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("Missing API Key! Please add GOOGLE_API_KEY to your Streamlit Secrets.")
    st.stop()

# Initialize the 2026 Client
client = genai.Client(api_key=api_key)

# --- 4. FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Disclosure PDF", type=['pdf'])

if uploaded_file:
    # Display file name for confirmation
    st.info(f"📄 Document Loaded: {uploaded_file.name}")
    
    if st.button("🔍 Run Disclosure Audit"):
        with st.spinner("Gemini 3 is auditing your document..."):
            try:
                # 1. Read the PDF bytes directly from the uploader
                file_bytes = uploaded_file.read()
                
                # 2. Call the NEW Gemini 3 Flash model
                # Note: 'gemini-3-flash-preview' is the stable choice for March 2026
                response = client.models.generate_content(
                    model="gemini-3-flash-preview", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,  # Keep it precise for auditing
                    ),
                    contents=[
                        types.Part.from_bytes(
                            data=file_bytes,
                            mime_type="application/pdf"
                        ),
                        "Perform a complete risk audit on this disclosure document."
                    ]
                )

                # 3. Display Results
                st.success("Audit Complete")
                st.markdown("---")
                st.markdown(response.text)

            except Exception as e:
                # Specific error handling for model mismatches
                if "404" in str(e):
                    st.error("Model Error: It looks like that model version was just retired. Try changing the model name to 'gemini-3-flash'.")
                else:
                    st.error(f"Analysis failed: {e}")

st.divider()
st.caption("TurboHome Analysis is an AI tool. Always verify findings with a human professional.")
