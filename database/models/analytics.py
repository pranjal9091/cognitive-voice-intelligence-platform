import uuid
from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database.models.base import Base

class TemporalMetrics(Base):
    __tablename__ = "temporal_metrics"

    temporal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audio_id = Column(UUID(as_uuid=True), ForeignKey("audio_metadata.audio_id", ondelete="CASCADE"), nullable=False, unique=True)
    speech_duration_seconds = Column(Float, nullable=False)
    words_per_minute = Column(Float, nullable=False)
    pause_count = Column(Integer, nullable=False)
    longest_pause_seconds = Column(Float, nullable=False)
    speech_rate_ratio = Column(Float, nullable=False)

    # Relationships
    audio = relationship("AudioMetadata", back_populates="temporal_metrics")

    def __repr__(self) -> str:
        return f"<TemporalMetrics(temporal_id={self.temporal_id}, wpm={self.words_per_minute})>"


class LinguisticMetrics(Base):
    __tablename__ = "linguistic_metrics"

    linguistic_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audio_id = Column(UUID(as_uuid=True), ForeignKey("audio_metadata.audio_id", ondelete="CASCADE"), nullable=False, unique=True)
    word_count = Column(Integer, nullable=False)
    unique_word_count = Column(Integer, nullable=False)
    repeated_words_json = Column(JSONB, nullable=False)  # {"word": count}
    filler_words_json = Column(JSONB, nullable=False)    # {"filler": count}
    lexical_density = Column(Float, nullable=False)

    # Relationships
    audio = relationship("AudioMetadata", back_populates="linguistic_metrics")

    def __repr__(self) -> str:
        return f"<LinguisticMetrics(linguistic_id={self.linguistic_id}, word_count={self.word_count})>"
