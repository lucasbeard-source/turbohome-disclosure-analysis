import streamlit as st
import base64
from google import genai
from google.genai import types

# --- 1. PLAYBOOK (SYSTEM INSTRUCTIONS) ---
# (Keeping your full instructions from the previous turn)
SYSTEM_PROMPT = """
Disclosure Review Playbook
General Instructions: Analyze Disclosure Packets for residential real estate acquisitions...
(Full Playbook text here)
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="TurboHome Auditor",
    page_icon="🏠",
    layout="wide"  # Crucial for the side-by-side experience
)

# Custom CSS to make the PDF and Chat fill the height
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    iframe { width: 100%; height: 85vh; border-radius: 10px; }
    .stChatFloatingInputContainer { bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_ref" not in st.session_state:
    st.session_state.pdf_ref = None

# --- 4. API SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY") or st.sidebar.text_input("Gemini API Key", type="password")
if not api_key:
    st.info("Please provide an API Key to start.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- 5. TOP BAR / FILE UPLOADER ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    # Convert PDF to Base64 for viewing
    base64_pdf = base64.b64encode(uploaded_file.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" type="application/pdf"></iframe>'
    
    # Store the bytes for the AI to read (resetting pointer)
    uploaded_file.seek(0)
    pdf_bytes = uploaded_file.read()

    # Create Side-by-Side Layout
    col_pdf, col_chat = st.columns([1, 1], gap="medium")

    # --- LEFT SIDE: PDF VIEW ---
    with col_pdf:
        st.subheader("📄 Disclosure Document")
        st.markdown(pdf_display, unsafe_allow_html=True)

    # --- RIGHT SIDE: CONVERSATION ---
    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat Input
        if prompt := st.chat_input("Ask about the disclosures (e.g., 'What are the roof issues?')"):
            # Add user message to UI
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate AI Response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                try:
                    # Send Playbook + PDF + Chat History
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
                    
                    full_response = response.text
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                except Exception as e:
                    st.error(f"Error: {e}")

else:
    st.warning("Please upload a PDF to begin the analysis.")
