from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

# ASR Word model
class WordTimestamp(BaseModel):
    word: str = Field(..., description="The individual transcribed word")
    start: float = Field(..., description="Start time of the word in seconds from the beginning of audio")
    end: float = Field(..., description="End time of the word in seconds")
    probability: float = Field(..., description="Transcription confidence probability for the word (0.0 to 1.0)")

# Audio details
class AudioUploadResponse(BaseModel):
    session_id: UUID
    question_number: int
    status: str
    file_path: str
    audio_size_bytes: int
    recorded_duration: float

# Transcript representation
class TranscriptResponse(BaseModel):
    question_number: int
    transcript_text: str
    duration: float
    words: List[WordTimestamp]
    confidence: float
    language: Optional[str] = None
    language_probability: Optional[float] = None
    average_segment_confidence: Optional[float] = None

# Temporal details
class TemporalMetricsSchema(BaseModel):
    total_speech_duration: float
    average_response_duration: float
    words_per_minute: float
    pause_count: int
    longest_pause_seconds: float

# Linguistic details
class LinguisticMetricsSchema(BaseModel):
    word_count: int
    unique_word_count: int
    repeated_words: List[Dict[str, int]] = Field(default_factory=list, description="Repeated words list and counts")
    filler_words_count: int
    filler_words_breakdown: Dict[str, int] = Field(default_factory=dict, description="Occurrences per filler word")

# Combined Analytics
class AnalyticsContainer(BaseModel):
    temporal_metrics: TemporalMetricsSchema
    linguistic_metrics: LinguisticMetricsSchema

# Risk classification
class RiskAssessmentSchema(BaseModel):
    score: float = Field(..., description="Calculated risk value from 0.0 to 1.0")
    classification: str = Field(..., description="Risk class (Low Risk, Medium Risk, High Risk)")
    rationale: str = Field(..., description="Clinician readable details on calculation logic triggers")
    created_at: Optional[datetime] = None
    confidence: float = Field(1.0, description="ASR/Session Confidence score")
    contributing_factors: List[str] = Field(default_factory=list, description="Primary Contributing Factors")
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Visual breakdown score metrics")

# Completed Session Detail including analytics and transcripts
class SessionResultResponse(BaseModel):
    session_id: UUID
    status: str
    subject_reference: str
    clinician_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    transcriptions: List[TranscriptResponse]
    analytics: Optional[AnalyticsContainer] = None
    risk_assessment: Optional[RiskAssessmentSchema] = None

class UploadResponse(BaseModel):
    session_id: UUID
    status: str
    filename: str
    size: int

class TranscribeRequest(BaseModel):
    session_id: UUID

class TranscribeResponse(BaseModel):
    session_id: UUID
    language: str
    processing_time_seconds: float
    transcript: str

class RepeatedWord(BaseModel):
    word: str
    count: int

class AnalyzeRequest(BaseModel):
    session_id: UUID

class TemporalAnalyticsSchema(BaseModel):
    total_speech_duration: float
    average_response_duration: float
    words_per_minute: float
    pause_count: int
    longest_pause: float

class LinguisticAnalyticsSchema(BaseModel):
    word_count: int
    unique_word_count: int
    repeated_words: List[RepeatedWord]
    filler_words: Dict[str, int]

class AnalyzeResponse(BaseModel):
    session_id: UUID
    temporal_metrics: TemporalAnalyticsSchema
    linguistic_metrics: LinguisticAnalyticsSchema
