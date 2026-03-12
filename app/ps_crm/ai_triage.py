import os
import json
import logging
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Optionally, enforce the output schema structure via Pydantic
class ComplaintExtraction(BaseModel):
    category: str = Field(description="The department category, e.g., 'Sanitation', 'Roads', 'Water', 'Electricity', 'Civil'")
    severity_score: int = Field(description="Severity score from 1 (minor) to 10 (emergency)")
    extracted_location: str = Field(description="The physical location extracted from the text.")
    summary: str = Field(description="A brief, professional 1-sentence summary of the issue.")

# Setup output parser
parser = JsonOutputParser(pydantic_object=ComplaintExtraction)

# Definition of the core prompt
triage_prompt = PromptTemplate(
    template="""You are an expert AI triage assistant for a municipality's Public Service CRM.
Your job is to analyze incoming raw text complaints from citizens and extract structured data.

Process the following complaint text and return a JSON object with the requested fields.
Do not include markdown blocks or any other text outside the JSON object.

Complaint Text: 
"{text}"

{format_instructions}
""",
    input_variables=["text"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# Initialize Gemini only if an API key is configured.
_gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if _gemini_key:
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)
        triage_chain = triage_prompt | llm | parser
    except Exception as e:
        logger.warning(f"Could not initialize Google GenAI model: {e}. Will use fallback.")
        triage_chain = None
else:
    logger.info("GOOGLE_API_KEY/GEMINI_API_KEY not set. AI triage will use local fallback logic.")
    triage_chain = None

def process_complaint_text(raw_text: str) -> Dict[str, Any]:
    """
    Processes a raw complaint text using the LangChain Gemini pipeline
    to extract category, severity, location, and summary.
    
    Includes robust error handling and fallback logic.
    """
    logger.info(f"Processing complaint via AI Triage: {raw_text[:50]}...")
    
    if not triage_chain:
        logger.warning("LLM Triage chain is unavailable. Using mock fallback logic.")
        return _apply_fallback_logic(raw_text)
    
    try:
        # Invoke the LangChain pipeline
        structured_output = triage_chain.invoke({"text": raw_text})
        
        # Additional validation (e.g. ensuring severity is 1-10)
        severity = structured_output.get("severity_score", 5)
        if not isinstance(severity, int) or severity < 1 or severity > 10:
             structured_output["severity_score"] = 5
             
        # Fallback if location is empty
        if not structured_output.get("extracted_location"):
            structured_output["extracted_location"] = "Location unknown/not provided"
            
        return structured_output
        
    except Exception as e:
        logger.error(f"AI Triage Pipeline failed: {e}. Applying fallback logic.")
        return _apply_fallback_logic(raw_text)

def _apply_fallback_logic(raw_text: str) -> Dict[str, Any]:
    """
    Fallback logic if the LLM fails to parse or the API is unavailable.
    Provides basic heuristic-based categorization.
    """
    text_lower = raw_text.lower()
    
    # Simple heuristics
    if any(keyword in text_lower for keyword in ["water", "sewer", "smell", "leak"]):
        category = "Water/Sanitation"
        severity = 7
    elif any(keyword in text_lower for keyword in ["road", "pothole", "street"]):
        category = "Roads"
        severity = 5
    elif any(keyword in text_lower for keyword in ["electricity", "power", "light"]):
        category = "Electricity"
        severity = 6
    else:
        category = "General/Uncategorized"
        severity = 5
        
    return {
        "category": category,
        "severity_score": severity,
        "extracted_location": "Location extraction failed (Fallback)",
        "summary": raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
    }
