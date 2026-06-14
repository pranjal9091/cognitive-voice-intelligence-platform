import uuid
from datetime import datetime
from sqlalchemy import Column, Float, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database.models.base import Base

class RiskScore(Base):
    __tablename__ = "risk_scores"

    risk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, unique=True)
    score = Column(Float, nullable=False)
    classification = Column(String(20), nullable=False)
    rationale = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="risk_score")

    def __repr__(self) -> str:
        return f"<RiskScore(risk_id={self.risk_id}, classification={self.classification}, score={self.score})>"
