import sys
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root directory is on python search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.core.config import settings

from database.models import (
    Session as DbSession,
    AudioMetadata as DbAudioMetadata,
    Transcript as DbTranscript,
    TemporalMetrics as DbTemporalMetrics,
    LinguisticMetrics as DbLinguisticMetrics,
    RiskScore as DbRiskScore
)

# 1. Create a Mock Database Session representing SQLAlchemy AsyncSession
class MockDbSession:
    def __init__(self, session_exists=True, audio_exists=True, transcript_exists=True):
        self.session_exists = session_exists
        self.audio_exists = audio_exists
        self.transcript_exists = transcript_exists
        self.metrics_exists = True
        self.mock_session_id = uuid.uuid4()
        
        self.mock_session = DbSession(
            session_id=self.mock_session_id,
            subject_reference="ANON_UPLOAD",
            status="transcribed",
            created_at=datetime.utcnow()
        )
        self.mock_audio = DbAudioMetadata(
            audio_id=uuid.uuid4(),
            session_id=self.mock_session_id,
            question_number=1,
            file_path="mock_path.wav",
            duration_seconds=10.0,
            file_size_bytes=1024,
            created_at=datetime.utcnow()
        )
        self.mock_transcript = DbTranscript(
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
            language_probability=0.95,
            average_segment_confidence=0.97,
            processing_time_seconds=1.24,
            created_at=datetime.utcnow()
        )
        self.mock_temporal = DbTemporalMetrics(
            temporal_id=uuid.uuid4(),
            audio_id=self.mock_audio.audio_id,
            speech_duration_seconds=10.0,
            words_per_minute=120.0,
            pause_count=1,
            longest_pause_seconds=0.5,
            speech_rate_ratio=0.95
        )
        self.mock_linguistic = DbLinguisticMetrics(
            linguistic_id=uuid.uuid4(),
            audio_id=self.mock_audio.audio_id,
            word_count=20,
            unique_word_count=18,
            repeated_words_json={},
            filler_words_json={},
            lexical_density=0.9
        )

    def add(self, instance):
        pass

    async def delete(self, instance):
        pass

    async def commit(self):
        pass

    async def execute(self, query, *args, **kwargs):
        query_str = str(query)
        mock_result = MagicMock()
        
        # Check for multi-table join query in /score
        if "temporal_metrics" in query_str and "linguistic_metrics" in query_str:
            mock_result.all.return_value = [(self.mock_audio, self.mock_temporal, self.mock_linguistic)] if self.metrics_exists else []
        elif "sessions" in query_str:
            mock_result.scalars.return_value.first.return_value = self.mock_session if self.session_exists else None
        elif "transcripts" in query_str:
            mock_result.scalars.return_value.first.return_value = self.mock_transcript if self.transcript_exists else None
            mock_result.scalars.return_value.all.return_value = [self.mock_transcript] if self.transcript_exists else []
        elif "audio_metadata" in query_str:
            mock_result.scalars.return_value.first.return_value = self.mock_audio if self.audio_exists else None
            mock_result.scalars.return_value.all.return_value = [self.mock_audio] if self.audio_exists else []
        else:
            mock_result.scalars.return_value.first.return_value = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            
        return mock_result

    async def rollback(self):
        pass

    async def close(self):
        pass

# Contextual dependencies override helpers
active_db_session = MockDbSession()

async def override_get_db():
    yield active_db_session

app.dependency_overrides[get_db] = override_get_db

def run_integration_tests():
    print("======================================================================")
    print("🧪 Starting Backend Milestone 4 Verification Tests (Analytics Engine)")
    print("======================================================================\n")

    # Patch verify_connection helper to return True (simulating active DB connection)
    with patch("app.main.verify_connection", return_value=True):
        client = TestClient(app)
        
        # Test Case 1: GET /health with active database connection
        print("👉 Running Test 1: GET /health (Database Connected)")
        response = client.get("/health")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["database"] == "connected"
        print("   ✅ Test 1 Passed!\n")

        # Test Case 2: GET /api/v1/session/test to verify database session injection
        print("👉 Running Test 2: GET /api/v1/session/test (Database Injection)")
        response = client.get("/api/v1/session/test")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.json()}")
        assert response.status_code == 200
        assert response.json()["message"] == "session service operational"
        print("   ✅ Test 2 Passed!\n")

        # Test Case 3: POST /upload with a valid WAV audio file
        print("👉 Running Test 3: POST /upload (Valid Audio File)")
        import io
        import wave
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b'\x00' * 16000)  # 0.5 seconds of silence
        file_content = wav_io.getvalue()
        response = client.post(
            "/upload",
            files={"audio_file": ("sample.wav", file_content, "audio/wav")}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.json()}")
        assert response.status_code == 200
        assert "session_id" in response.json()
        assert response.json()["status"] == "uploaded"
        print("   ✅ Test 3 Passed!\n")

        # Test Case 4: POST /transcribe (Successful Mock Transcription)
        print("👉 Running Test 4: POST /transcribe (Successful)")
        mock_transcribe_result = (
            "This is a mock speech transcription result.",
            "en",
            0.96,
            1.24,
            [{"word": "This", "start": 0.1, "end": 0.4, "probability": 0.99}]
        )
        with patch("app.main.TranscriptionService.transcribe", return_value=mock_transcribe_result), \
             patch("os.path.exists", return_value=True):
            
            test_session_id = str(active_db_session.mock_session_id)
            response = client.post(
                "/transcribe",
                json={"session_id": test_session_id}
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Body: {response.json()}")
            assert response.status_code == 200
            assert response.json()["session_id"] == test_session_id
            print("   ✅ Test 4 Passed!\n")

        # Test Case 5: POST /analyze (Successful Metrics Calculation)
        print("👉 Running Test 5: POST /analyze (Successful)")
        # We patch estimate_pauses_from_audio to return (2, 1.2) representing acoustic pause analysis results
        # We also patch os.path.exists to True so validation passes
        with patch("app.services.analytics_service.AnalyticsService.estimate_pauses_from_audio", return_value=(2, 1.2)), \
             patch("os.path.exists", return_value=True):
            
            test_session_id = str(active_db_session.mock_session_id)
            response = client.post(
                "/analyze",
                json={"session_id": test_session_id}
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Body: {response.json()}")
            assert response.status_code == 200
            
            # Check Temporal Metrics
            temporal = response.json()["temporal_metrics"]
            assert temporal["total_speech_duration"] == 10.0
            assert temporal["words_per_minute"] > 0.0
            assert temporal["pause_count"] == 2
            assert temporal["longest_pause"] == 1.2
            
            # Check Linguistic Metrics
            linguistic = response.json()["linguistic_metrics"]
            # Transcript text: "I woke up like actually um matlab like toh at six am." (12 words)
            assert linguistic["word_count"] == 12
            assert linguistic["unique_word_count"] == 11  # 'like' repeated, all others unique
            assert len(linguistic["repeated_words"]) == 1
            assert linguistic["repeated_words"][0]["word"] == "like"
            assert linguistic["repeated_words"][0]["count"] == 2
            
            # Filler word frequencies
            fillers = linguistic["filler_words"]
            assert fillers["like"] == 2
            assert fillers["actually"] == 1
            assert fillers["um"] == 1
            assert fillers["matlab"] == 1
            assert fillers["toh"] == 1
            
            print("   ✅ Test 5 Passed!\n")

        # Test Case 6: POST /analyze with missing transcript (400 Bad Request)
        print("👉 Running Test 6: POST /analyze (Missing Transcript)")
        active_db_session.transcript_exists = False
        try:
            response = client.post(
                "/analyze",
                json={"session_id": str(active_db_session.mock_session_id)}
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Body: {response.json()}")
            assert response.status_code == 400
            assert "no transcript found" in response.json()["detail"].lower()
            print("   ✅ Test 6 Passed!\n")
        finally:
            active_db_session.transcript_exists = True

        # Test Case 7: POST /score (Successful - Low Risk Profile)
        print("👉 Running Test 7: POST /score (Low Risk)")
        active_db_session.mock_temporal.words_per_minute = 120.0
        active_db_session.mock_temporal.pause_count = 1
        active_db_session.mock_temporal.longest_pause_seconds = 0.5
        active_db_session.mock_audio.duration_seconds = 10.0
        active_db_session.mock_linguistic.word_count = 20
        active_db_session.mock_linguistic.unique_word_count = 18
        active_db_session.mock_linguistic.repeated_words_json = {}
        active_db_session.mock_linguistic.filler_words_json = {}
        
        response = client.post(
            "/score",
            json={"session_id": str(active_db_session.mock_session_id)}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.json()}")
        assert response.status_code == 200
        assert response.json()["risk_level"] == "LOW_RISK"
        assert response.json()["score"] == 0.0
        assert "disclaimer" in response.json()["explanation"].lower()
        print("   ✅ Test 7 Passed!\n")

        # Test Case 8: POST /score (Successful - Medium Risk Profile)
        print("👉 Running Test 8: POST /score (Medium Risk)")
        # WPM = 75.0 (+15)
        # longest pause = 3.5 (+10)
        # filler words = 2/20 = 10% (+10)
        # Expected score: 35.0
        active_db_session.mock_temporal.words_per_minute = 75.0
        active_db_session.mock_temporal.pause_count = 4
        active_db_session.mock_temporal.longest_pause_seconds = 3.5
        active_db_session.mock_audio.duration_seconds = 10.0
        active_db_session.mock_linguistic.word_count = 20
        active_db_session.mock_linguistic.unique_word_count = 18
        active_db_session.mock_linguistic.repeated_words_json = {}
        active_db_session.mock_linguistic.filler_words_json = {"like": 2}
        
        response = client.post(
            "/score",
            json={"session_id": str(active_db_session.mock_session_id)}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.json()}")
        assert response.status_code == 200
        assert response.json()["risk_level"] == "MEDIUM_RISK"
        assert response.json()["score"] == 35.0
        print("   ✅ Test 8 Passed!\n")

        # Test Case 9: POST /score (Successful - High Risk Profile)
        print("👉 Running Test 9: POST /score (High Risk)")
        # WPM = 45.0 (+25)
        # longest pause = 5.5 (+20)
        # filler words = 4/20 = 20% (+20)
        # repeated words = 5/20 = 25% (+15)
        # Expected score: 80.0
        active_db_session.mock_temporal.words_per_minute = 45.0
        active_db_session.mock_temporal.pause_count = 8
        active_db_session.mock_temporal.longest_pause_seconds = 5.5
        active_db_session.mock_audio.duration_seconds = 10.0
        active_db_session.mock_linguistic.word_count = 20
        active_db_session.mock_linguistic.unique_word_count = 12
        active_db_session.mock_linguistic.repeated_words_json = {"like": 5}
        active_db_session.mock_linguistic.filler_words_json = {"um": 4}
        
        response = client.post(
            "/score",
            json={"session_id": str(active_db_session.mock_session_id)}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.json()}")
        assert response.status_code == 200
        assert response.json()["risk_level"] == "HIGH_RISK"
        assert response.json()["score"] == 80.0
        print("   ✅ Test 9 Passed!\n")

        # Test Case 10: POST /score (Missing Analytics - 400 Bad Request)
        print("👉 Running Test 10: POST /score (Missing Analytics)")
        active_db_session.metrics_exists = False
        try:
            response = client.post(
                "/score",
                json={"session_id": str(active_db_session.mock_session_id)}
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Body: {response.json()}")
            assert response.status_code == 400
            assert "no analytics metrics found" in response.json()["detail"].lower()
            print("   ✅ Test 10 Passed!\n")
        finally:
            active_db_session.metrics_exists = True

    print("======================================================================")
    print("🎉 All Speech Analytics & Cognitive Risk Scoring Tests Passed!")
    print("======================================================================")

if __name__ == "__main__":
    run_integration_tests()
