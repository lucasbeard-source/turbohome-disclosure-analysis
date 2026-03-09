import streamlit as st
import google.generativeai as genai
import tempfile
import os

# --- 1. SYSTEM INSTRUCTIONS (Replicating your Gem) ---
SYSTEM_PROMPT = """
You are the 'TurboHome Disclosure Auditor'. You are an expert in real estate disclosures, 
compliance, and risk mitigation. 

Your goal is to analyze the uploaded PDF disclosure documents for a home sale and:
1. Identify missing information or incomplete sections.
2. Flag "Red Flag" items (e.g., mentions of mold, unpermitted work, foundation issues).
3. Check for missing signatures or dates where required.
4. Summarize key risks that a buyer should investigate further.

Tone: Professional, objective, and highly detailed. 
Formatting: Use bold headers, bullet points, and a 'Risk Level' summary at the top.
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="TurboHome Disclosure Analysis",
    page_icon="🏠",
    layout="centered"
)

# Custom CSS for Branding
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; }
    </style>
    """, unsafe_allow_value=True)

st.title("🏠 TurboHome Disclosure Analysis")
st.write("Upload a disclosure PDF to perform an instant AI-powered risk audit.")

# --- 3. API SETUP ---
# It's best to use st.secrets for GitHub/Deployment
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("Please add your GOOGLE_API_KEY to continue.")
    st.stop()

genai.configure(api_key=api_key)

# Initialize Model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Highly efficient for document parsing
    system_instruction=SYSTEM_PROMPT
)

# --- 4. FILE UPLOADER ---
uploaded_file = st.file_uploader("Choose a Disclosure PDF", type=['pdf'])

if uploaded_file:
    # Display file details
    st.info(f"File uploaded: {uploaded_file.name}")
    
    if st.button("Run Disclosure Audit"):
        with st.spinner("Analyzing document for risks and missing signatures..."):
            try:
                # Save to a temp file for Gemini's File API
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                # Upload to Google File API
                # This allows the model to "see" the PDF structure properly
                google_file = genai.upload_file(path=tmp_path, display_name=uploaded_file.name)
                
                # Generate Content
                # We pass the file and a prompt to trigger the system instructions
                response = model.generate_content([
                    google_file, 
                    "Please perform a full disclosure audit on this document."
                ])

                # Results UI
                st.success("Audit Complete!")
                st.markdown("---")
                st.markdown(response.text)
                
                # Cleanup
                os.remove(tmp_path)

            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")

# --- 5. FOOTER ---
st.markdown("---")
st.caption("TurboHome Analysis is an AI tool and should not replace professional legal or home inspection advice.")
