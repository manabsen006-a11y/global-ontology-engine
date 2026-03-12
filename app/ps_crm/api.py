import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.ps_crm.ai_triage import process_complaint_text
from app.ps_crm.neo4j_service import create_complaint_node

logger = logging.getLogger(__name__)

router = APIRouter()

# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------
class ComplaintIntakeRequest(BaseModel):
    citizen_phone: str = Field(..., description="The phone number of the citizen reporting.")
    raw_text: str = Field(..., description="The unstructured text of the complaint.")
    latitude: float = Field(..., description="GPS Latitude of the reporter/issue.")
    longitude: float = Field(..., description="GPS Longitude of the reporter/issue.")

class IntakeResponse(BaseModel):
    status: str
    complaint_id: str
    message: str
    triage_result: Optional[Dict[str, Any]] = None

# -----------------------------------------------------------------------------
# Kafka Mock Setup
# -----------------------------------------------------------------------------
class MockKafkaProducer:
    def send(self, topic: str, value: Dict[str, Any]):
        logger.info(f"[KAFKA MOCK] Pushing to topic '{topic}': {value}")
        
    def flush(self):
        pass

kafka_producer = MockKafkaProducer()
KAFKA_TOPIC = "civic_complaints_ingestion"

# -----------------------------------------------------------------------------
# Webhook Endpoint
# -----------------------------------------------------------------------------
@router.post("/api/v1/complaints/intake", response_model=IntakeResponse, tags=["PS-CRM Intake"])
async def receive_complaint_webhook(payload: ComplaintIntakeRequest, background_tasks: BackgroundTasks):
    """
    Lightweight webhook for the Citizen Frontend / SMS gateway.
    Receives raw text & coordinates, triages with AI, pushes to Kafka, and saves to Neo4j.
    """
    logger.info(f"Received new complaint from {payload.citizen_phone}")
    
    complaint_id = f"CMP-{uuid.uuid4().hex[:8].upper()}"
    
    try:
        # 1. AI Triage Pipeline (Step 2 Implementation)
        # Parse category, severity, extract location desc, and summarize.
        triage_output = process_complaint_text(payload.raw_text)
        
        # 2. Build structured payload
        structured_event = {
            "complaint_id": complaint_id,
            "citizen_phone": payload.citizen_phone,
            "original_text": payload.raw_text,
            "coordinates": {
                "latitude": payload.latitude,
                "longitude": payload.longitude
            },
            "timestamp": datetime.utcnow().isoformat(),
            **triage_output
        }
        
        # 3. Push to Apache Kafka Topic (Immediate downstream trigger)
        kafka_producer.send(KAFKA_TOPIC, value=structured_event)
        kafka_producer.flush()
        
        # 4. Save to Graph Architecture (Neo4j) asynchronously as part of intake processing
        # Alternatively, Kafka consumers usually handle this part. We include it here for the scope of Step 1.
        background_tasks.add_task(
            create_complaint_node,
            complaint_id=complaint_id,
            citizen_phone=payload.citizen_phone,
            text=payload.raw_text,
            category=triage_output.get("category", "Unknown"),
            severity=triage_output.get("severity_score", 5),
            latitude=payload.latitude,
            longitude=payload.longitude,
            summary=triage_output.get("summary", "")
        )
        
        return IntakeResponse(
            status="success",
            complaint_id=complaint_id,
            message="Complaint received, triaged, and dispatched.",
            triage_result=triage_output
        )

    except Exception as e:
        logger.error(f"Error processing complaint intake: {e}", exc_info=True)
        # We don't want to drop the user's issue if the AI or DB fails entirely,
        # fallback is to push raw payload to a dead-letter queue or basic DB.
        raise HTTPException(status_code=500, detail="Internal server error processing complaint.")
