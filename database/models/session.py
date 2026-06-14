import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database.models.base import Base

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_reference = Column(String(100), nullable=False, index=True)
    clinician_id = Column(String(100), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="initialized")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    audio_records = relationship("AudioMetadata", back_populates="session", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="session", cascade="all, delete-orphan")
    risk_score = relationship("RiskScore", back_populates="session", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Session(session_id={self.session_id}, status={self.status})>"
