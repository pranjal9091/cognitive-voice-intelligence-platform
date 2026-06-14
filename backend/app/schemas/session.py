from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class QuestionSchema(BaseModel):
    number: int = Field(..., description="Question prompt sequence number (1, 2, or 3)")
    prompt: str = Field(..., description="The textual question prompt presented to the user")
    status: str = Field("pending", description="Status of the recording attempt (pending, uploaded)")

class SessionCreate(BaseModel):
    subject_reference: str = Field(..., min_length=3, max_length=100, description="Anonymized subject patient reference code")
    clinician_id: Optional[str] = Field(None, max_length=100, description="ID of the clinician managing the session")

class SessionResponse(BaseModel):
    session_id: UUID
    status: str
    subject_reference: str
    clinician_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    questions: List[QuestionSchema]

    model_config = {
        "from_attributes": True
    }
