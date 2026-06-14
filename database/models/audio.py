import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database.models.base import Base

class AudioMetadata(Base):
    __tablename__ = "audio_metadata"

    audio_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint("session_id", "question_number", name="unique_session_question_num"),
    )

    # Relationships
    session = relationship("Session", back_populates="audio_records")
    temporal_metrics = relationship("TemporalMetrics", back_populates="audio", uselist=False, cascade="all, delete-orphan")
    linguistic_metrics = relationship("LinguisticMetrics", back_populates="audio", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AudioMetadata(audio_id={self.audio_id}, session_id={self.session_id}, question_number={self.question_number})>"


class Transcript(Base):
    __tablename__ = "transcripts"

    transcript_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False)
    full_text = Column(Text, nullable=False)
    words_json = Column(JSONB, nullable=False)  # [{word, start, end, probability}]
    confidence = Column(Float, nullable=False)
    language = Column(String(10), nullable=True)
    language_probability = Column(Float, nullable=True)
    average_segment_confidence = Column(Float, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint("session_id", "question_number", name="unique_session_transcript_num"),
    )

    # Relationships
    session = relationship("Session", back_populates="transcripts")

    def __repr__(self) -> str:
        return f"<Transcript(transcript_id={self.transcript_id}, question_number={self.question_number})>"
