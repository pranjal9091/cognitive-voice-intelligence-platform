from uuid import UUID
from typing import List, Dict
from pydantic import BaseModel, Field

class ScoreRequest(BaseModel):
    session_id: UUID = Field(..., description="The unique session identifier to score")

class ScoreResponse(BaseModel):
    session_id: UUID = Field(..., description="The unique session identifier associated with this score")
    risk_level: str = Field(..., description="The evaluated cognitive risk level (LOW_RISK, MEDIUM_RISK, or HIGH_RISK)")
    score: float = Field(..., description="The numeric risk score on a scale of 0.0 to 100.0")
    explanation: str = Field(..., description="Detailed explanation of the risk assessment triggers and medical disclaimers")
    confidence: float = Field(1.0, description="Assessment Confidence score")
    contributing_factors: List[str] = Field(default_factory=list, description="Primary Contributing Factors")
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Visual breakdown score metrics")
