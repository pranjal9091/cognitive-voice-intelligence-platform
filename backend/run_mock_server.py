import sys
import os
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.main import app

class MockDbSession:
    def __init__(self):
        self.mock_session_id = uuid.UUID("80775d6c-41db-42d6-956c-d228d4700187")
        
    def add(self, instance):
        pass

    async def delete(self, instance):
        pass

    async def commit(self):
        pass

    async def execute(self, query, *args, **kwargs):
        query_str = str(query)
        mock_result = MagicMock()
        
        # Import models
        from database.models.session import Session as DbSession
        from database.models.audio import AudioMetadata as DbAudioMetadata, Transcript as DbTranscript
        from database.models.analytics import TemporalMetrics as DbTemporalMetrics, LinguisticMetrics as DbLinguisticMetrics
        from database.models.risk import RiskScore as DbRiskScore
        
        mock_session = DbSession(
            session_id=self.mock_session_id,
            subject_reference="ANON_UPLOAD",
            status="scored",
            created_at=datetime.utcnow()
        )
        mock_audio = DbAudioMetadata(
            audio_id=uuid.uuid4(),
            session_id=self.mock_session_id,
            question_number=1,
            file_path="mock_path.wav",
            duration_seconds=10.0,
            file_size_bytes=1024,
            created_at=datetime.utcnow()
        )
        mock_transcript = DbTranscript(
            session_id=self.mock_session_id,
            question_number=1,
            full_text="I woke up like actually um matlab like toh at six am.",
            words_json=[
                {"word": "I", "start": 0.1, "end": 0.5, "probability": 0.99},
                {"word": "like", "start": 0.6, "end": 1.0, "probability": 0.98},
                {"word": "actually", "start": 1.2, "end": 1.8, "probability": 0.95},
                {"word": "um", "start": 2.2, "end": 2.6, "probability": 0.97},
                {"word": "matlab", "start": 3.0, "end": 3.6, "probability": 0.96},
                {"word": "like", "start": 4.0, "end": 4.4, "probability": 0.99},
                {"word": "toh", "start": 4.8, "end": 5.2, "probability": 0.95}
            ],
            confidence=0.98,
            language="en",
            processing_time_seconds=1.24,
            created_at=datetime.utcnow()
        )
        mock_temporal = DbTemporalMetrics(
            temporal_id=uuid.uuid4(),
            audio_id=mock_audio.audio_id,
            speech_duration_seconds=10.0,
            words_per_minute=120.0,
            pause_count=1,
            longest_pause_seconds=0.5,
            speech_rate_ratio=0.95
        )
        mock_linguistic = DbLinguisticMetrics(
            linguistic_id=uuid.uuid4(),
            audio_id=mock_audio.audio_id,
            word_count=20,
            unique_word_count=18,
            repeated_words_json={"like": 2},
            filler_words_json={"like": 2, "actually": 1, "um": 1, "matlab": 1, "toh": 1},
            lexical_density=0.9
        )
        mock_risk = DbRiskScore(
            risk_id=uuid.uuid4(),
            session_id=self.mock_session_id,
            score=35.0,
            classification="MEDIUM_RISK",
            rationale="Cognitive risk indicators identified: Moderate slow speech detected (avg WPM is 75.0); Moderate single pause of 3.5s detected; Elevated filler word frequency (10.0% of total words). DISCLAIMER: This assessment is an engineering demonstration of voice analysis parameters and does NOT constitute a clinical or medical diagnosis. Please consult a qualified healthcare professional for formal medical evaluations."
        )

        if "temporal_metrics" in query_str and "linguistic_metrics" in query_str:
            mock_result.all.return_value = [(mock_audio, mock_temporal, mock_linguistic)]
        elif "sessions" in query_str:
            mock_result.scalars.return_value.first.return_value = mock_session
        elif "transcripts" in query_str:
            mock_result.scalars.return_value.first.return_value = mock_transcript
            mock_result.scalars.return_value.all.return_value = [mock_transcript]
        elif "audio_metadata" in query_str:
            mock_result.scalars.return_value.first.return_value = mock_audio
            mock_result.scalars.return_value.all.return_value = [mock_audio, mock_audio, mock_audio]
        elif "risk_scores" in query_str:
            mock_result.scalars.return_value.first.return_value = mock_risk
        else:
            mock_result.scalars.return_value.first.return_value = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            
        return mock_result

    async def rollback(self):
        pass

    async def close(self):
        pass

active_db_session = MockDbSession()

async def override_get_db():
    yield active_db_session

app.dependency_overrides[get_db] = override_get_db

# Patch health checks and external services globally
patchers = [
    patch("app.main.verify_connection", return_value=True),
    patch("app.main.TranscriptionService.transcribe", return_value=(
        "I woke up like actually um matlab like toh at six am.",
        "en",
        0.98,
        1.24,
        [
            {"word": "I", "start": 0.1, "end": 0.5, "probability": 0.99},
            {"word": "like", "start": 0.6, "end": 1.0, "probability": 0.98},
            {"word": "actually", "start": 1.2, "end": 1.8, "probability": 0.95},
            {"word": "um", "start": 2.2, "end": 2.6, "probability": 0.97},
            {"word": "matlab", "start": 3.0, "end": 3.6, "probability": 0.96},
            {"word": "like", "start": 4.0, "end": 4.4, "probability": 0.99},
            {"word": "toh", "start": 4.8, "end": 5.2, "probability": 0.95}
        ]
    )),
    patch("app.services.analytics_service.AnalyticsService.estimate_pauses_from_audio", return_value=(2, 1.2)),
    patch("os.path.exists", return_value=True),
]

for p in patchers:
    p.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("run_mock_server:app", host="127.0.0.1", port=8000, reload=False)
