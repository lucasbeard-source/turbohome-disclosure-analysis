import streamlit as st
import re
from google import genai
from google.genai import types
from streamlit_pdf_viewer import pdf_viewer

# --- 1. THE PLAYBOOK ---
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
Documents
Real Estate Transfer Disclosure Statement
Overview
The TDS is a disclosure that provides the buyer with greater visibility into the history of the property. It provides the buyer with straightforward yes/no information regarding pertinent issues like known substances on the property, zoning violations, roof age, etc. 
The primary purpose of the TDS is to ensure that buyers have transparent and accurate information about the property’s condition before finalizing the purchase. Some key areas covered in this document: 
Lists appliances, utilities, and structural components present in the home. 
Environmental & Legal Concerns – Discloses hazards, unpermitted work, easements, zoning violations, lawsuits, and neighborhood nuisances.
Roof age
TDS does not replace a home inspection report, but it provides a baseline for buyers to assess risks
Instructions
Look for the issues noted in the sections below. If any of the issues listed below are found in the report, note them and concisely explain implication to the buyer. If any issues listed below are not found in the report, do not note that said issue was not found in the report. Simply leave it out. 
Elevated
Substances, materials, or products which may be an environmental hazard such as, but not limited to, asbestos, formaldehyde, radon gas, lead-based paint, mold, fuel or chemical storage tanks, and contaminated soil or water on the subject property.
Location: pg. 2 Section C subquestion 1 of document
Instructions: 
If yes box is checked make a note
if no box is checked, ignore/don’t make a note 
Note if any additions, structural modifications, or other alterations or repairs were made without necessary permits or are not in compliance with building code.
Location: pg. 2 Section C subquestion 5 of document
Instructions: 
If yes box is checked make a note and provide context
if no box is checked, ignore/don’t make a note 
Note if there’s fill on the property.
Location: pg. 2 Section C subquestion 6 of document
Instructions: 
If yes box is checked make a note and provide context
if no box is checked, ignore/don’t make a note 
Note if there’s flooding, drainage or grading problems.
Location: pg. 2 Section C subquestion 8 of document
Instructions: 
If yes box is checked make a note and provide context
if no box is checked, ignore/don’t make a note 
Note any zoning violations, nonconforming uses, violations of “setback” requirements that pertain to property.
Location: pg. 2 Section C subquestion 9 of document
Instructions: 
If yes box is checked make a note and provide context
if no box is checked, ignore/don’t make a note 
Note if there are any lawsuits by or against the Seller threatening to or affecting the real property.
Location: pg. 2 Section C subquestion 16 of document
Instructions: 
If yes box is checked make a note and provide context
if no box is checked, ignore/don’t make a note 
Moderate
Note if there’s settling on property.
Low / Informational
Note roof type and age.
Location: lower half of pg. 1
Note if features of the property share in common with adjoining landowners, such as walls, fences, and driveways, whose use or responsibility for maintenance may affect subject property.
Location: pg. 2 Section C subquestion 2 of document
Instructions: 
If yes box is checked make a note and implication to potential homeowner
if no box is checked, ignore/don’t make a note 
Note any encroachments, easements or similar matters that relate to property (informational item for now, provide more detail in preliminary title report).
Location: pg. 2 Section C subquestion 3 of document
Instructions: 
If yes box is checked make a note and explain that further information will be provided from the preliminary title report
if no box is checked, ignore/don’t make a note  
Note if there are CC&Rs or other deed restrictions or obligations that relate to property.
Location: pg. 2 Section C subquestion 12 of document
Instructions: 
If yes box is checked make a note and implication to potential homeowner
if no box is checked, ignore/don’t make a note 
Seller Property Questionnaire
Overview
The SPQ supplements the TDS by providing additional details about the property’s condition, history, and known material issues. Some key areas covered in the SPQ: property conditions & repairs, environmental & legal issues (hazards, insurance claims, title disputes, lawsuits), water & structural concerns (leaks, mold, flooding, foundation stability), shared property & title issues (easements, boundary disputes), previous deaths on property. Similar to TDS the SPQ does not replace a home inspection report. 
Instructions
Look for the issues noted in the sections below. If any of the issues listed below are found in the report, note them and concisely explain implication to the buyer. If any issues listed below are not found in the report, do not note in the report that said issue was not found in the report. Simply leave it out. 
Elevated
Within the last 3 years, the death of an occupant of the property upon the property (include note at bottom of section).
Location: pg. 1 Section 6 subsection A of document
Instructions: 
If yes box is checked, include a note regarding the death that took place at the property. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if no box is checked, ignore/don’t make a note 
An Order from a government health official identifying the property as being contaminated by methamphetamine.
Location: pg. 1 Section 6 subsection B of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note 
The release of an illegal controlled substance on or beneath the Property.
Location: pg. 1 Section 6 subsection C of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note 
Insurance claims affecting the property in the past 5 years.
Location: pg. 1 Section 6 subsection H of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Matters affecting title of the Property.
Location: pg. 1 Section 6 subsection I of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Note if there are any other people or entities with ownership interest in subject property that are not listed on the agreement.
Location: pg. 3 Section 15 subsection A of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Note if there are any leases, options or claims affecting the property. 
Location: pg. 3 Section 15 subsection B of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document. If the seller notes in-place leases, look for further attachment of lease and summarize that information. 
if “no” box is checked, ignore/don’t make a note
Note any encroachments, easements, boundary disputes (see Preliminary Title Report Section of playbook for more detail).
Note if there’s existence of rent control, occupancy restrictions, or improvement restrictions that could affect the property.
Location: pg. 4 Section 17 subsection B of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Moderate
Note defects in any of the following systems: heating, air conditioning, electrical, plumbing, sewer, waste disposal, septic system, sump pumps,. Well, roof, gutters, chimney, fireplace foundation, crawl space, attic, soil, grading, drainage, retaining walls, interior or exterior doors, windows, walls, ceilings, floors or appliances. 
Location: pg. 2 Section 8 subsection A of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Note if subject property is historically designated or falls within proposed historic district
Location: pg. 2 Section 8 subsection A of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Low / Informational
Note if there are any leases, options or claims affecting or relating to title or use of property
Location: pg. 3 Section 15 subsection B of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection H or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Note any alterations, modifications, improvements, remodels, and repairs made to the property
Location: pg. 2 Section 7 subsection B of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection F or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Note if the property was built before 1978. If yes, note if lead-based paint surfaces were removed
Location: pg. 2 Section 7 subsection E of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection 6L or on an “overflow” document
if “no” box is checked, ignore/don’t make a note
Note if there’s a solar system (if yes, look for a solar disclosure report and provide more information… see solar disclosure review section of playbook)
Location: pg. 2 Section 8 subsection B of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection E or on an “overflow” document. If solar system exists look to analyze further the solar system disclosure document
if “no” box is checked, ignore/don’t make a note
Note if there’s an alternative septic system serving the property 
Location: pg. 2 Section 8 subsection D of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. This information will be located either at the bottom of the section after subsection E or on an “overflow” document. 
if “no” box is checked, ignore/don’t make a note
Note if there are CC&Rs or other deed restrictions related to the property. If yes, see CC&R section of playbook and add detailed notes when you come across specific documents. 
Location: pg. 3 Section 14 subsection F of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. 
if “no” box is checked, ignore/don’t make a note
Note if there features of the property shared in common with adjoining neighbors
Location: pg. 3 Section 15 subsection D of document
Instructions: 
If “yes” box is checked, include a note providing context for this matter. 
if “no” box is checked, ignore/don’t make a note
Natural Hazards Disclosure
Overview 
The NHD report informs buyers if a property is located in a designated hazard zone that may pose risks to its safety, insurability, and long-term value. This report helps buyers assess potential environmental risks before purchasing a property. 
Instructions
Look for the issues noted in the sections below. If any of the issues listed below are found in the report, note them and concisely explain implication to the buyer. If any issues listed below are not found in the report, do not note in the report that said issue was not found in the report. Simply leave it out. 
Only analyze the following sections of the document: “Property Disclosure Summary” Section,  “Property Tax Disclosure Report” Section, “Environmental Zones”
For every property, note the ad valorem tax rate and Total Direct Assessments (information can be found under “Property Tax Estimator” section
Only make a note in report if it applies to property. For example, it is not necessary to note that the property is not in a special flood hazard area. 
Elevated
Property is located within a “Special Flood Hazard Area”
Location: can be found under the “Property Disclosure Summary Section”
Property is located within a “High or Very High Fire Hazard Zone”
Location: can be found under the “Property Disclosure Summary Section”
Property is located in an “Earthquake Fault Zone” 
(provide more information regarding fault and proximity to fault)
Location: can be found under the “Property Disclosure Summary Section”
Property is located within a liquefaction zone (statutory)
Location: can be found under the “Property Disclosure Summary Section”
Property is located within a landslide zone (statutory)
Location: can be found under the “Property Disclosure Summary Section”
Property is located within one mile of a Superfund or RCRA Corrective Action Site
Location: can be found under the “Environmental Zones Section"
Moderate
Property is located within a liquefaction zone (county level)
Location: can be found under the “Property Disclosure Summary Section”
Property is located within a landslide zone (county level)
Location: can be found under the “Property Disclosure Summary Section”
Property is located in an “Area of Potential Flooding” or in an area of potential dam inundation
Location: can be found under the “Property Disclosure Summary Section”
Property is located in a Mello-Roos Special Tax District
Explain what special tax applies to the property and note the annual tax amount
Location: can be found under the “Property Disclosure Summary Section” and/or “Property Tax Disclosure Report”
Property is located in 1915 Bond Act District 
Location: can be found under the “Property Disclosure Summary Section” and/or “Property Tax Disclosure Report”
Property is subject to a PACE contract
Location: can be found under the “Property Disclosure Summary Section” and/or “Property Tax Disclosure Report”
Property is subject to the State Responsibility Area Fire Prevention Fee 
Location: can be found under the “Property Disclosure Summary Section” and/or “Property Tax Disclosure Report”
This property is located within 1 mile of known sites on the California Spills, Leaks, Investigation and Cleanup (SLIC) List. 
Location: can be found under the “Environmental Zones Section"
Low / Informational
Property is located within one-quarter mile of a known leaking underground storage tank (LUST)
Location: can be found under the “Environmental Zones Section"
Property is within 2,000 feet of a gas transmission or hazardous liquid pipeline depicted in the National Pipeline Mapping system
Location: can be found under the “Environmental Zones Section"
Note estimated Ad Valorem Tax Rate
Location: can be found under the “Property Tax Estimator” section
Note Direct Additional Direct Assessment tax amounts
Location: can be found under the “Property Tax Estimator” section
Property is located in an “airport influence area”
Location: can be found under the “Property Disclosure Summary Section”
Preliminary Title Report
Overview
This document provides a snapshot of the legal status of the property’s title, listing any recorded liens, encumbrances, ownership details, and any potential issues that could affect the transfer of clear title to the buyer
Key areas covered in the Prelim: ownership details, legal description (official lot, tract, and parcel description), liens & encumbrances (outstanding mortgages, tax obligations, Mello-Roos assessments, HOA dues, mechanics’ liens), easements & restrictions (recorded access rights, utility easements, and zoning restrictions), exceptions to coverage
Instructions
Look for the issues noted in the sections below. If any of the issues listed below are found in the report, note them and concisely explain implication to the buyer. If any issues listed below are not found in the report, do not note in the report that said issue was not found in the report. Simply leave it out. 
Do not note liens in regards to the current owner’s mortgage as this lien does not concern the buyer
Elevated
Identify and summarize any pending litigation involving the property.
Identify and describe any liens on the property, including the type and amount owed.
Identify and describe any unpaid property taxes or assessments on the property.
Moderate
Identify and describe any easements affecting the property, including their purpose and location.
Identify and describe any encroachments on the property, detailing the nature and extent.
Low / Informational
Note if there are CC&Rs that may limit the subject property
If there are, note limitations / restrictions
Note if the property lies within the boundaries of a Mello-Roos Community Facilities District
Pest Inspection Report
Overview
This document assesses a property for active infestations, structural damages and conditions that could lead to future pest issues. It identifies the presence of termites, fungus, dry rot, and other-wood destroying organisms categorizing findings into two sections: 
Section 1 – Identifies active infestations, damage, or conditions that require immediate treatment or repair.
Section 2 – Highlights risk factors, such as moisture buildup or structural vulnerabilities, that could lead to future infestations.
Unlike the Home Inspection Report, it includes cost estimates for necessary treatments and repairs, allowing buyers to understand the financial impact of addressing these issues before purchasing. If certain areas were inaccessible during the inspection, the report will recommend further evaluation.
Instructions 
Note every item from this report (“Section 1 Items”, “Section 2 Items” and “Further Inspection Items”
If there are no items noted in the report, explain there are no action items and that the property is in good condition.
Note certifications regarding termites, fungus, and dry-rot.
Elevated
Any item that costs more than $5,000 to repair
Termites that require fumigation to remediate. 
Moderate
Any line item that costs more than $1k to remediate and less than $5k 
Termites noted that do not require fumigation to remediate. 
Low / Informational
Any line item noted in report costing less than $5k to remediate
Roof Inspection Report
Overview 
This document evaluates the condition of a property’s roof, identifying any existing damage, wear, or structural deficiencies that may affect its longevity and ability to shed water. The report assesses the roof condition, estimates remaining lifespan, recommends repairs, and provides cost estimates. 
Instructions 
Summarize the condition of the roof in one line item. 
Information to include in summary
Roof type
Typical life expectancy of said roof type
Estimated life of existing roof
Estimated remaining serviceable life expectancy of existing roof
Overall condition of existing roof
# of corrective recommended actions
Inspectors recommendation (repair roof, replace roof, or no work needed)
Listing the actual corrective recommendations is not vital. It is only important to list the number of corrective actions and estimated total cost of all the recommended corrective actions. 
It is vital to include whether or not the inspector recommends replacing the roof. 
Example Summary of Roof Inspection Report. 
“The roof is made of concrete tile which typically have a life expectancy of 40-50 years. The inspector notes this roof shows the characteristics of being approximately 8 years old. The overall condition of the roof is good however the inspector notes 3 action corrective action items that will cost an estimated $395 to repair.”
Elevated
Roof needs to be replaced.
Total estimated roof repair >$10k.
Moderate
$1k < Total estimated roof repair  < $10k.
Low / Informational
Total estimated roof repair < $1k.
Home Inspection Report
Overview: 
The Home Inspection Report provides a comprehensive assessment of a property's overall condition, evaluating structural integrity, major systems, and potential safety concerns. Conducted as a non-invasive, visual examination, it helps buyers understand maintenance needs before purchasing. The report covers the foundation, framing, roof, electrical, plumbing, HVAC, and insulation, identifying deficiencies and recommending repairs or ongoing maintenance. Notably, this report offers the most detailed insights into the foundation, highlighting cracks, settlement issues, and drainage concerns that could affect the property's stability. Unlike specialized reports such as pest or roof inspections, which provide cost estimates for specific issues, the home inspection report is broader in scope, identifying a wide range of potential defects without guaranteeing the absence of hidden problems.
Instructions: 
Review Home Inspection report after all other inspection reports.
Do not repeat issues noted from other reports. 
Provide a summary of the foundation. Note the condition of the foundation. Summarize any problems or action items. If there are no notes regarding the foundation, note that there are no notes. Oftentimes the design of the foundation makes it difficult for the home inspector to evaluate the foundation. If the report notes this, convey that information in the report.  
Note every “immediate improvement recommendation item”. Often times “!” at the beginning of the note signifies it is an immediate improvement recommendation item
Elevated
Water heater is not responding properly
HVAC system is not responding properly 
The water heater is beyond or nearing the end of its useful life. 
HVAC system is beyond or nearing the end of its useful life. 
Horizontal cracking in foundation walls is > 1/8th inch. Horizontal cracks often indicate external pressure, such as soil pressure, water pressure, or frost, pushing against the wall. This type of crack can suggest the wall is bowing or is structurally compromised.
Vertical cracking in foundation walls is > 1/8th inch. Vertical cracks are usually caused by normal settling of the house or minor shrinkage of the concrete as it cures. Typically less likely to compromise the structural integrity of the foundation.
Any leak on the interior of the house.
Truss in the attic is cracked and/or damaged. 
Open drain pipes anywhere on the property. This is a potential health hazard. 
Any asbestos on the interior of the property. This is a potential health hazard. 
Sloped interior floors. 
Uncapped gas line noted anywhere on the interior of the building. 
Moderate
Water heater is not properly strapped / braced.
Any leak noted on the exterior of the house.
Horizontal cracking in foundation walls < 1/8th inch. Horizontal cracks often indicate external pressure, such as soil pressure, water pressure, or frost, pushing against the wall. This type of crack can suggest the wall is bowing or is structurally compromised. 
Cracking in foundation walls < 1/8th inch. Vertical cracks are usually caused by normal settling of the house or minor shrinkage of the concrete as it cures. Typically less likely to compromise the structural integrity of the foundation. 
Note any ungrounded outlets that require upgrading to GFCI standard.
Significant cracking and/or damage to siding of the house.
Evidence of Vermin activity in the structure. Describe location and nature of severity of the structure.
Damage to barge rafter (the outside rafter at the end of the roof).
Deterioration noted to roof beams.
Cracked glass in a window.
Loose or cracked toilet (which can lead to leaking)
Leaks noted outdoors (for example at downspouts and/or gutters)
Cracked, deteriorated and/or missing grout and/or caulk in the bathroom 
Low / Informational
Auto door closer between garage and house does not function properly
Water heater tank has been strapped improperly and/or with improper material 
The home does not have enough smoke detectors installed
The home does not have sufficient carbon monoxide detectors
 Individual loose, cracked, or chipped tiles on the roof 
“Minor” cracking in foundation. Explain the nature of cracks. 
Minor cracking and/or damage to siding of the house.
Gaps between railing bars on the stairs are larger than 4 inches. While this was standard when the home was built, it is considered a safety hazard according to modern standards. 
Property lacks carbon monoxide detectors. 
Outdoor cracks and/or vegetation on walkways outside of the house.
Note corrosion to any sink.
Grading is sloped toward structure. Negative grading can promote water accumulation near the building, as well as possible erosion and water penetration into crawl spaces and/or basements. 
Stains on the interior of the building that indicate a previous leak that has been repaired. 
Cracking on garage floor. 
Missing drain stops at bathroom wash basins.
Missing, compressed, or uneven insulation.
Earth to wood contact noted
Malfunctioning door
Electrical equipment that is known to have safety issues 
Localized damage and/or stucco cracks at the exterior 


Things to Ignore from Home Inspection report
Debris noted on the roof
Doors that don’t hinge or latch properly 
Appliance vent flashing loose
Evidence of moss on ground, sidewalk, or roof
Gate latch mechanism needs repair
Heating system air filters are dirty
Ceiling showing evidence of patching 
Missing or damaged window screens
Interior wall or ceiling blemishes
Dishwasher lacks an air gap 
Unstable railing
Steps or railing don’t meet today’s standard
Missing catch pan under washing machine
Dryer vent or washing machine does not meet current standards 
Any trip hazard noted by an inspector
Missing electric outlet protected cover
Air filter is dirty
Agent Visual Inspection Disclosure Report (AVID)
Overview
Required disclosure that documents the listing agent’s observations from a high level visual inspection of the property. It is a non-invasive inspection, meaning the agent does not move furniture, test systems, or provide any analysis of potential issues. The AVID is primarily a liability protection measure for the listing agent, ensuring they have disclosed any obvious material defects they observe. However, the information provided in this report is typically redundant, as more thorough inspections (such as the home, roof, and pest inspections) will already document property conditions in greater detail.
Instructions
HOA Documents
Overview 
Instructions 
Summarize key HOA rules and regulations, particularly those that could affect the buyer’s intended use of the property.
Elevated
HOA reserve account is less than 50% funded.
Note any ongoing or past litigation involving the HOA that could affect future dues or property values.
Moderate
50% < HOA reserve fund < 75% funded.
Low / Informational
HOA reserve fund > 75% funded.
Identify and describe any significant controls or restrictions the HOA has over property owners.
Note the current monthly HOA dues and any scheduled increases.
Solar System Disclosure 

Summarize the report and incorporate the following information:
Ownership Status: Identify if the system is owned outright, financed, or leased.
Transferability: Note the transferability conditions of the system.
Transfer Action Items: Outline necessary steps to transfer ownership based on the system's status (owned, financed, or leased).
Financial Details: If financed or leased, provide monthly payment details, interest rate, and remaining payments.
System Condition/Warranty: Note the condition of the system and any remaining warranty period.
Energy Production: Summarize the system’s energy production performance, if available.


--- CITATION RULE ---
For every finding, you MUST include the page number using this exact tag: :page[X]
Example: "The roof is 15 years old :page[18]."
"""

# --- 2. PAGE CONFIG ---
st.set_page_config(
    page_title="TurboHome Auditor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 3. STYLES ---
st.markdown("""
<style>
    /* App background */
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 28%),
            radial-gradient(circle at top right, rgba(16, 185, 129, 0.08), transparent 24%),
            linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
    }

    /* Global typography */
    html, body, [class*="css"]  {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #0f172a;
    }

    /* Main block spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* Hero */
    .th-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #2563eb 100%);
        color: white;
        padding: 28px 30px;
        border-radius: 22px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18);
        margin-bottom: 18px;
        border: 1px solid rgba(255,255,255,0.10);
    }

    .th-hero-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }

    .th-hero-subtitle {
        font-size: 1rem;
        line-height: 1.6;
        color: rgba(255,255,255,0.82);
        max-width: 760px;
    }

    .th-badge-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 16px;
    }

    .th-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.16);
        color: white;
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 0.86rem;
        font-weight: 600;
        backdrop-filter: blur(6px);
    }

    /* Section cards */
    .th-card {
        background: rgba(255,255,255,0.76);
        border: 1px solid rgba(255,255,255,0.70);
        border-radius: 22px;
        padding: 18px 18px 10px 18px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        backdrop-filter: blur(10px);
    }

    .th-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        gap: 12px;
    }

    .th-card-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #0f172a;
    }

    .th-card-subtitle {
        font-size: 0.88rem;
        color: #64748b;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.82);
        border: 1px dashed #93c5fd;
        border-radius: 18px;
        padding: 12px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }

    /* Chat area */
    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.86);
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 4px 6px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        margin-bottom: 10px;
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        background: rgba(255,255,255,0.90);
        border-radius: 16px;
    }

    /* Divider */
    .th-divider {
        height: 1px;
        width: 100%;
        background: linear-gradient(90deg, transparent, #cbd5e1, transparent);
        margin: 14px 0 16px 0;
    }

    /* Inline page citation buttons */
    div.stButton > button {
        border: none !important;
        padding: 0px 2px !important;
        background-color: transparent !important;
        color: #2563eb !important;
        text-decoration: underline !important;
        font-size: inherit !important;
        display: inline !important;
        min-height: 0px !important;
        height: auto !important;
        vertical-align: baseline !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }

    /* Suggestion pills */
    div[data-testid="column"] .stButton > button[key^="sugg_"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
        color: #1d4ed8 !important;
        border: 1px solid #bfdbfe !important;
        text-decoration: none !important;
        border-radius: 999px !important;
        padding: 10px 14px !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08) !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="column"] .stButton > button[key^="sugg_"]:hover {
        border-color: #60a5fa !important;
        color: #1e40af !important;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.14) !important;
    }

    /* Back button */
    div.stButton > button[key="back_btn"] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        border: 1px solid #cbd5e1 !important;
        background: white !important;
        text-decoration: none !important;
        color: #0f172a !important;
        font-weight: 600 !important;
        min-height: 40px !important;
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.06) !important;
    }

    /* Info / alert boxes */
    [data-testid="stInfo"] {
        border-radius: 14px;
        background: rgba(219, 234, 254, 0.65);
        border: 1px solid #bfdbfe;
    }

    /* Hide streamlit default anchor hover clutter a bit */
    .stMarkdown a {
        color: #2563eb;
    }

    /* Subtle metric strip */
    .th-metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 10px 0 18px 0;
    }

    .th-metric {
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(255,255,255,0.70);
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }

    .th-metric-label {
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 4px;
        font-weight: 600;
    }

    .th-metric-value {
        font-size: 1.15rem;
        color: #0f172a;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    /* Empty state */
    .th-empty {
        background: rgba(255,255,255,0.78);
        border: 1px solid #dbeafe;
        border-radius: 20px;
        padding: 28px;
        text-align: center;
        color: #334155;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
    }

    .th-empty-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 6px;
        color: #0f172a;
    }

    .th-empty-subtitle {
        font-size: 0.95rem;
        color: #64748b;
        max-width: 540px;
        margin: 0 auto;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "target_page" not in st.session_state:
    st.session_state.target_page = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = [
        "Biggest disclosure risks",
        "Check unpermitted work",
        "Summarize NHD hazards"
    ]

# --- 5. API SETUP ---
MODEL_NAME = "gemini-3-flash-preview"

api_key = st.secrets.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# --- 6. HEADER / HERO ---
st.markdown("""
<div class="th-hero">
    <div class="th-hero-title">TurboHome Auditor</div>
    <div class="th-hero-subtitle">
        AI-powered disclosure review for modern homebuyers. Upload a disclosure package,
        surface material risks, and jump directly to cited pages for faster due diligence.
    </div>
    <div class="th-badge-row">
        <div class="th-badge">⚡ Fast risk triage</div>
        <div class="th-badge">📎 Page-linked citations</div>
        <div class="th-badge">🧠 Buyer-friendly explanations</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="th-metrics">
    <div class="th-metric">
        <div class="th-metric-label">Workflow</div>
        <div class="th-metric-value">Upload → Review → Investigate</div>
    </div>
    <div class="th-metric">
        <div class="th-metric-label">Output Style</div>
        <div class="th-metric-value">Actionable + cited</div>
    </div>
    <div class="th-metric">
        <div class="th-metric-label">Built For</div>
        <div class="th-metric-value">TurboHome buyers</div>
    </div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload Disclosure Package (PDF)",
    type=["pdf"],
    help="Supported format: PDF"
)

# --- 7. EMPTY STATE ---
if not uploaded_file:
    st.markdown("""
    <div class="th-empty">
        <div class="th-empty-title">Start with a disclosure package</div>
        <div class="th-empty-subtitle">
            Upload a PDF to analyze seller disclosures, inspection notes, and hazard reports.
            The auditor will cite every finding with clickable page references.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- 8. FILE LOADED ---
pdf_bytes = uploaded_file.read()

col_pdf, col_chat = st.columns([1.35, 1], gap="large")

with col_pdf:
    st.markdown("""
    <div class="th-card">
        <div class="th-card-header">
            <div>
                <div class="th-card-title">Disclosure Document</div>
                <div class="th-card-subtitle">View the full file or jump to cited pages</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.target_page:
        st.info(f"Focused on page {st.session_state.target_page}")
        pdf_viewer(
            input=pdf_bytes,
            height=860,
            pages_to_render=[st.session_state.target_page]
        )
        if st.button("⬅ Back to Full Document", key="back_btn"):
            st.session_state.target_page = None
            st.rerun()
    else:
        pdf_viewer(input=pdf_bytes, height=860)

    st.markdown("</div>", unsafe_allow_html=True)

with col_chat:
    st.markdown("""
    <div class="th-card">
        <div class="th-card-header">
            <div>
                <div class="th-card-title">AI Auditor</div>
                <div class="th-card-subtitle">Ask questions, inspect risks, and follow citations</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    chat_container = st.container(height=600)

    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div class="th-empty" style="padding:22px;">
                <div class="th-empty-title">No analysis yet</div>
                <div class="th-empty-subtitle">
                    Try a suggested prompt below or ask something like
                    “What are the biggest risks in this package?”
                </div>
            </div>
            """, unsafe_allow_html=True)

        for m_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                parts = re.split(r'(:page\[\d+\])', msg["content"])
                for p_idx, part in enumerate(parts):
                    match = re.match(r':page\[(\d+)\]', part)
                    if match:
                        page_num = int(match.group(1))
                        if st.button(f"Page {page_num}", key=f"lk_{m_idx}_{p_idx}_{page_num}"):
                            st.session_state.target_page = page_num
                            st.rerun()
                    else:
                        if part.strip():
                            st.markdown(part)

    st.markdown('<div class="th-divider"></div>', unsafe_allow_html=True)

    if st.session_state.suggestions:
        s_cols = st.columns(len(st.session_state.suggestions))
        for idx, suggestion in enumerate(st.session_state.suggestions):
            if s_cols[idx].button(suggestion, key=f"sugg_{idx}"):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                st.rerun()

    if prompt := st.chat_input("Ask about risks, permits, hazards, repairs, or red flags..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# --- 9. AI CONTEXTUAL LOGIC ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with col_chat:
        with st.chat_message("assistant"):
            with st.spinner("Reviewing disclosure package..."):
                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.0
                        ),
                        contents=[
                            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                            *[
                                types.Content(
                                    role="model" if m["role"] == "assistant" else "user",
                                    parts=[types.Part.from_text(text=m["content"])]
                                )
                                for m in st.session_state.messages
                            ]
                        ]
                    )

                    assistant_text = response.text if response and response.text else "I couldn't generate a response for this document."
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_text
                    })

                    s_prompt = (
                        f"Based on: '{assistant_text}', suggest 3 short follow-up questions "
                        f"(3-5 words) for a buyer. Output ONLY the questions separated by |."
                    )

                    sugg_res = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[s_prompt]
                    )

                    if sugg_res and sugg_res.text:
                        st.session_state.suggestions = [
                            s.strip() for s in sugg_res.text.split("|") if s.strip()
                        ][:3]

                    st.rerun()

                except Exception as e:
                    st.error(f"Audit Error: {e}")
