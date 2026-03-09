import streamlit as st
import os
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. THE DISCLOSURE REVIEW PLAYBOOK (SYSTEM INSTRUCTIONS) ---
# Note: I have included your full text here to ensure the AI follows every specific rule.
SYSTEM_PROMPT = """
Disclosure Review Playbook
General Instructions
The purpose of this playbook is to provide the AI model with general instructions to analyze Disclosure Packets for residential real estate acquisitions. The purpose of the disclosure packets is for the buyer to get a qualitative understanding of the property. It informs the buyer about the history and condition of the property. For any note you make in the client report, concisely explain its implication to the buyer. 
Order of Documents to feed the AI Model:
1. TDS
2. SPQ
3. NHD 
4. Pest Inspection Report
5. Roof Inspection Report
6. Home Inspection Report
7. Preliminary Title Report
8. AVID
Don’t repeat items that have already been noted from previous reports. For example, if damage to the roof is noted in the report from reviewing the Roof Inspection Report, don’t repeat this note in the report if the same issue is noted in the Home Inspection Report or the AVID. 
Ignore the following documents: Electronic Signature Advisory, Property Details, As is Addendums, Notice of Supplemental Property Tax Bill, Homeowner’s Guide to Earthquake Safety & Environmental Hazards (Combined Hazard Book), Statewide Buyer and Seller Advisory (SBSA), Contra Costa County Disclosure and Disclaimers Advisory, Coversheet, Mold Disclosures, Buyer’s Investigation Elections (BIE), Seller’s Affidavit of Nonforeign Status (FIRPTA), Water-Conserving Plumbing Fixtures and Carbon Monoxide Detector Advisory, Carbon Monoxide Detector Notice, Wildfire Disaster Advisory (WFDA), Market Conditions Advisory (MCA), Hazard Booklet Receipt, Homeowner’s Combined Information Guides, Water Heater and Smoke Alarm Statement of Compliance, San Mateo/Santa Clara Counties Advisory, Use of Non-Standard Forms Advisory, Property Visit and Open House Advisory, Non-Contingent Offer Advisory, Lead-Based Paint and Lead-Based Paint Hazards Disclosure, California Consumer Privacy Act Advisory, Disclosure and Notice, Buyer’s Inspection Waver (BIW), Broker Compensation Advisory, Square Footage and Lot Size Disclosure and Advisory, Residential Earthquake Hazards Report, Residential Book Acknowledgement, Disclosure Regarding Real Estate Agency Relationship, Megan’s Law Data Base Disclosure, Solar Advisory and Questionnaire, Alameda County Disclosures and Disclaimers Advisory, Disclosure Information Advisory, Representative Capacity Signature Disclosure, Trust Advisory, Receipt for Links to Booklets, General Information For Buyers and Sellers of Residential Real Property in San Francisco (Disclosures and Disclaimers Advisory), Flood Map Advisory and Disclosure, Parking and Storage Disclosure, Fair Appraisal Act Addendum, Seller Notifiaction to Buyer of Hazardous Wastes in Soil, Wire Fraiud and Electronic Funds Transfer Advisory, San Francisco Adjacent Industrial Uses Disclosure and Affidavit, Acknowledgement of Receipt of Booklets by Buyer and/or Seller, Fair Housing and Discrimnation Advisory, Possible Representation of More Than One Buyer or Seller - Disclosure and Consent, Buyer Homeowners’ Insurance Advisory, Seller Notification to Buyer of Hazardous Wastes in Soil, Fire Hardening and Defensible Space Disclosure and Addendum, Residential Energy and Water Conservation Requirements, General Information For Buyers and Sellers of Residential Real Property in San Francisco (disclosures and disclaimers advisory), California Water Restrictions, Shortages and Conservation Advisory, Buyer’s Investigation Advisory, Advisory Regarding Completing Documents Electronically, Affiliated Business Arrangement Disclosure Statement

--- DOCUMENT SPECIFIC INSTRUCTIONS ---

[Real Estate Transfer Disclosure Statement (TDS)]
Look for issues in Section C (pg. 2). 
- Elevated: Environmental hazards (sub 1), Non-compliant alterations (sub 5), Fill (sub 6), Flooding/Drainage (sub 8), Zoning violations (sub 9), Lawsuits (sub 16). Note 'Yes' boxes and provide context.
- Moderate: Settling.
- Low/Informational: Roof type/age (pg 1), Common features (sub 2), Encroachments (sub 3 - note prelim for more), CC&Rs (sub 12).

[Seller Property Questionnaire (SPQ)]
- Elevated: Death on property (6A), Meth contamination (6B), Illegal substances (6C), Insurance claims (6H), Title matters (6I), Ownership interest (15A), Leases/Options (15B), Rent control/Restrictions (17B).
- Moderate: System defects (Sec 8A), Historic designation (Sec 8A).
- Low/Informational: Repairs/Remodels (7B), Pre-1978 lead paint (7E), Solar system (8B), Septic (8D), CC&Rs (14F), Common features (15D).

[Natural Hazards Disclosure (NHD)]
Focus: "Property Disclosure Summary", "Property Tax Disclosure", "Environmental Zones". Note Ad Valorem Tax Rate and Total Direct Assessments.
- Elevated: Special Flood Hazard, High Fire Zone, Earthquake Fault Zone, Liquefaction/Landslide (statutory), Superfund/RCRA (1 mile).
- Moderate: Liquefaction/Landslide (county), Dam Inundation, Mello-Roos/1915 Bond Act, PACE, SRA Fire Fee, SLIC list (1 mile).

[Preliminary Title Report]
Ignore current owner's mortgage.
- Elevated: Pending litigation, Liens, Unpaid taxes.
- Moderate: Easements, Encroachments.
- Low: CC&Rs (summarize limitations), Mello-Roos boundaries.

[Pest Inspection Report]
- Note Section 1, Section 2, and Further Inspection Items.
- Elevated: Repairs >$5k, Fumigation required.
- Moderate: Repairs $1k - $5k, Termites (no fumigation).

[Roof Inspection Report]
- Summary: 1-line item with Type, Life expectancy, Estimated age, Remaining life, Overall condition, # of corrective actions, Recommendation.
- Elevated: Replacement recommended, Repairs >$10k.

[Home Inspection Report]
Review AFTER others. Do not repeat items.
- Foundation: Summary of condition or notes on difficulty of evaluation.
- Elevated: Water heater/HVAC failure or end-of-life, Foundation cracks >1/8th inch, Interior leaks, Cracked attic truss, Open drain pipes, Asbestos, Sloped floors, Uncapped gas lines.

[HOA/Solar]
- HOA Elevated: Reserves <50% funded, Litigation.
- Solar: Summarize ownership, transferability, financial details, condition, and production.

Disregard missing signatures or dates.
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="TurboHome Auditor", page_icon="🏠", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { width: 100%; background-color: #FF4B4B; color: white; border-radius: 8px; font-weight: bold; }
    /* Container for the PDF to ensure scrollability */
    .pdf-container { height: 85vh; overflow-y: scroll; border: 1px solid #eee; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. API SETUP ---
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Missing GOOGLE_API_KEY in Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- 5. UI LAYOUT ---
st.title("🏠 TurboHome Interactive Auditor")
uploaded_file = st.file_uploader("Upload Disclosure Package (PDF)", type=['pdf'])

if uploaded_file:
    # Read bytes for both viewer and AI
    pdf_bytes = uploaded_file.read()

    col_pdf, col_chat = st.columns([1.2, 1], gap="large")

    # LEFT SIDE: PRO PDF VIEWER
    with col_pdf:
        st.subheader("📄 Disclosure Document")
        with st.container(border=True):
            # This component renders the PDF page-by-page, avoiding the Base64 limit
            pdf_viewer(input=pdf_bytes, height=800)

    # RIGHT SIDE: INTERACTIVE CHAT
    with col_chat:
        st.subheader("🤖 TurboHome Auditor")
        
        chat_placeholder = st.container(height=650)
        
        with chat_placeholder:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Ask about the disclosures (e.g., 'Any foundation issues?')"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_placeholder:
                with st.chat_message("user"):
                    st.markdown(prompt)

            with chat_placeholder:
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing disclosures..."):
                        try:
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
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")
else:
    st.info("👋 Upload a residential disclosure package to begin your professional audit.")

st.divider()
st.caption("TurboHome is an AI-powered tool. All findings should be verified by licensed professionals.")
