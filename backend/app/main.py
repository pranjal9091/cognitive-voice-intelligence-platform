import sys
import os
import subprocess
import time
import wave
# Dynamically add the monorepo root to sys.path to resolve 'database' imports
monorepo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(monorepo_root)

import logging
import uuid
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, UploadFile, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, verify_connection
from app.core.logging_config import setup_logging
from app.schemas.analytics import AudioUploadResponse, SessionResultResponse, UploadResponse, TranscribeRequest, TranscribeResponse, AnalyzeRequest, AnalyzeResponse, TemporalAnalyticsSchema, LinguisticAnalyticsSchema
from app.schemas.session import QuestionSchema, SessionCreate, SessionResponse
from app.services.transcription_service import TranscriptionService
from app.services.analytics_service import AnalyticsService
from app.schemas.risk import ScoreRequest, ScoreResponse
from app.services.risk_scoring_service import RiskScoringService

from database.models.session import Session as DbSession
from database.models.audio import AudioMetadata as DbAudioMetadata, Transcript as DbTranscript
from database.models.analytics import TemporalMetrics as DbTemporalMetrics, LinguisticMetrics as DbLinguisticMetrics
from database.models.risk import RiskScore as DbRiskScore

# 1. Initialize structured logging configuration immediately upon startup
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("app.main")

# 2. Modern context manager (lifespan) handling startup checks
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initiating Cognitive Voice Intelligence Platform backend startup sequence...")
    
    # Verify database connection robustness on startup
    logger.info("Verifying PostgreSQL database connection...")
    db_ok = await verify_connection()
    if not db_ok:
        logger.critical(
            "FATAL: Database connectivity check failed during startup verification. "
            "Please check DATABASE_URL configurations and verify PostgreSQL is running."
        )
        raise SystemExit(1)
        
    logger.info("PostgreSQL database connection verified successfully.")
    logger.info("FastAPI service initialization finished.")
    yield
    logger.info("Shutting down FastAPI service...")

# 3. Create FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Cognitive Voice Intelligence Platform REST API. Milestone 2 - Audio Upload Foundation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 4. CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from collections import defaultdict
import threading

class SessionTimingTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.timings = defaultdict(dict)

    def record(self, session_id: uuid.UUID, phase: str, duration: float):
        with self.lock:
            self.timings[session_id][phase] = self.timings[session_id].get(phase, 0.0) + duration

    def get(self, session_id: uuid.UUID, phase: str) -> float:
        with self.lock:
            return self.timings[session_id].get(phase, 0.0)

    def get_all(self, session_id: uuid.UUID) -> Dict[str, float]:
        with self.lock:
            return dict(self.timings[session_id])

    def print_breakdown(self, session_id: uuid.UUID):
        with self.lock:
            t = self.timings.get(session_id)
            if not t:
                logger.info(f"=== Timing Breakdown for Session: {session_id} ===\nNo timing data recorded.")
                return
            
            # Retrieve values or defaults
            up = t.get("upload_duration", 0.0)
            conv = t.get("audio_conversion_duration", 0.0)
            ml = t.get("model_load_duration", 0.0)
            trans = t.get("transcription_duration", 0.0)
            anal = t.get("analytics_duration", 0.0)
            score = t.get("scoring_duration", 0.0)
            
            total = up + conv + ml + trans + anal + score
            
            breakdown_str = (
                f"\n========================================================\n"
                f"⏱️  PERFORMANCE TIMING BREAKDOWN FOR SESSION: {session_id}\n"
                f"========================================================\n"
                f" 📂 Upload Phase:             {up:7.3f} seconds  ({(up/total*100) if total > 0 else 0:5.1f}%)\n"
                f" 🔄 Audio Conversion (FFmpeg): {conv:7.3f} seconds  ({(conv/total*100) if total > 0 else 0:5.1f}%)\n"
                f" 🧠 Model Loading (Whisper):   {ml:7.3f} seconds  ({(ml/total*100) if total > 0 else 0:5.1f}%)\n"
                f" 📝 Speech Transcription:     {trans:7.3f} seconds  ({(trans/total*100) if total > 0 else 0:5.1f}%)\n"
                f" 📊 Speech Analytics:         {anal:7.3f} seconds  ({(anal/total*100) if total > 0 else 0:5.1f}%)\n"
                f" 🎯 Risk Scoring:             {score:7.3f} seconds  ({(score/total*100) if total > 0 else 0:5.1f}%)\n"
                f"--------------------------------------------------------\n"
                f" 🚀 Total Processing Time:     {total:7.3f} seconds  (100.0%)\n"
                f"========================================================"
            )
            logger.info(breakdown_str)
            print(breakdown_str)
            logger.info(f"Raw timings for session {session_id}: {dict(t)}")

            # Structured performance logs for task 5
            structured_logs = (
                f"\n[UPLOAD] {up:.1f}s\n"
                f"[CONVERT] {conv:.1f}s\n"
                f"[MODEL_LOAD] {ml:.1f}s\n"
                f"[TRANSCRIBE] {trans:.1f}s\n"
                f"[ANALYZE] {anal:.1f}s\n"
                f"[SCORE] {score:.1f}s\n"
                f"[TOTAL] {total:.1f}s"
            )
            logger.info(structured_logs)
            print(structured_logs)

timing_tracker = SessionTimingTracker()

# Temporary in-memory fallback for testing endpoint parameters
MOCK_SESSIONS: Dict[uuid.UUID, Dict[str, Any]] = {}

# --- Operational / Health Endpoints ---

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Perform a live health assessment.
    Verifies that the API server is functional and the PostgreSQL database is reachable.
    """
    logger.info("Received request for endpoint: GET /health")
    db_connected = await verify_connection()
    if not db_connected:
        logger.error("Health check request failed: Database connection is unreachable.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "service": "cognitive-voice-platform",
                "database": "disconnected"
            }
        )
    return {
        "status": "healthy",
        "service": "cognitive-voice-platform",
        "database": "connected"
    }

@app.get("/api/v1/session/test", tags=["Sessions"])
async def test_session_endpoint(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Verify session routing and database session management.
    Executes a test query using the injected SQLAlchemy session.
    """
    logger.info("Received request for endpoint: GET /api/v1/session/test")
    try:
        await db.execute(text("SELECT 1"))
        logger.info("Database session transaction test query executed successfully.")
        return {"message": "session service operational"}
    except Exception as e:
        logger.error(f"Error in database session management inside test endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session service active but database execution failed."
        )

# --- Audio Upload Foundation Endpoint ---

@app.post("/upload", response_model=UploadResponse, tags=["Audio"])
async def upload_audio_file(
    audio_file: UploadFile = File(...),
    session_id: Optional[uuid.UUID] = Form(None),
    question_number: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
) -> UploadResponse:
    """
    Upload an audio file (WAV, MP3, WEBM, or M4A) up to 25MB.
    Links the recording to an existing session or generates a new one.
    Stores tracking metadata and writes files to disk.
    """
    logger.info("Audio upload sequence initiated...")
    
    # 1. Validate filename presence
    filename = audio_file.filename
    if not filename:
        logger.error("Upload failed: Missing filename.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing."
        )
        
    # 2. Validate file extension
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in settings.SUPPORTED_AUDIO_EXTENSIONS:
        logger.error(f"Upload failed: Unsupported file extension '.{ext}'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Supported formats: {', '.join(settings.SUPPORTED_AUDIO_EXTENSIONS)}"
        )
        
    # 3. Read content in chunks
    start_upload = time.time()
    total_bytes = 0
    chunks = []
    try:
        while True:
            chunk = await audio_file.read(65536)  # Read 64KB chunks
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > settings.MAX_AUDIO_FILE_SIZE_BYTES:
                logger.error(f"Upload failed: File exceeds maximum allowed size of 25MB.")
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File exceeds maximum allowed size of 25MB."
                )
            chunks.append(chunk)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read file data."
        )
        
    if total_bytes == 0:
        logger.error("Upload failed: Uploaded file is empty.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )
        
    contents = b"".join(chunks)
    
    # 4. Resolve session_id
    q_num = question_number if question_number is not None else 1
    db_session = None
    if session_id:
        session_stmt = select(DbSession).where(DbSession.session_id == session_id)
        result = await db.execute(session_stmt)
        db_session = result.scalars().first()
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found."
            )
    else:
        session_id = uuid.uuid4()
        
    file_path_temp = os.path.join(settings.UPLOAD_DIR, f"{session_id}_q{q_num}_temp.{ext}")
    file_path_wav = os.path.join(settings.UPLOAD_DIR, f"{session_id}_q{q_num}.wav")
    
    logger.info(f"Writing temporary uploaded file to disk at: {file_path_temp}")
    try:
        with open(file_path_temp, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.critical(f"Disk write failure at path {file_path_temp}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save temporary audio file to local storage."
        )

    # Record upload duration (including write to temp file)
    upload_duration = time.time() - start_upload
    timing_tracker.record(session_id, "upload_duration", upload_duration)

    # Extract and log original audio properties for Task 1
    orig_props = get_audio_properties(file_path_temp)
    logger.info(
        f"[AUDIO_UPLOAD_METADATA] "
        f"Original Upload Format: {orig_props.get('format')} | "
        f"Sample Rate: {orig_props.get('sample_rate')} Hz | "
        f"Channels: {orig_props.get('channels')} | "
        f"Bitrate: {orig_props.get('bitrate')} bps | "
        f"Duration: {orig_props.get('duration'):.3f}s"
    )
 
    # Check if we can bypass transcoding
    bypassed_transcoding = False
    start_transcode = time.time()
    
    if ext == "wav":
        try:
            with wave.open(file_path_temp, "rb") as wav_ref:
                n_channels = wav_ref.getnchannels()
                sample_width = wav_ref.getsampwidth()
                framerate = wav_ref.getframerate()
                
                # Check if it matches: mono (1 channel), 16-bit (2 bytes sample width), 16000 Hz frame rate
                if n_channels == 1 and sample_width == 2 and framerate == 16000:
                    logger.info("Uploaded file is already standard 16kHz mono 16-bit WAV. Bypassing transcoding.")
                    if os.path.exists(file_path_wav):
                        os.remove(file_path_wav)
                    os.rename(file_path_temp, file_path_wav)
                    bypassed_transcoding = True
        except Exception as wav_err:
            logger.warning(f"Could not parse WAV headers directly: {wav_err}. Will proceed with FFmpeg transcoding.")

    if not bypassed_transcoding:
        # Run FFmpeg transcoding
        logger.info(f"Transcoding audio to standard WAV format at: {file_path_wav}")
        try:
            command = [
                "ffmpeg",
                "-y",
                "-i", file_path_temp,
                "-af", "silenceremove=start_periods=1:start_threshold=-50dB,loudnorm",
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                file_path_wav
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8", errors="ignore")
                logger.error(f"FFmpeg transcoding failed: {error_msg}")
                raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"Audio standardization transcoding failed: {e}")
            if os.path.exists(file_path_temp):
                os.remove(file_path_temp)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to transcode audio: {e}"
            )
        finally:
            if os.path.exists(file_path_temp):
                os.remove(file_path_temp)
                
    transcode_duration = time.time() - start_transcode if not bypassed_transcoding else 0.0
    timing_tracker.record(session_id, "audio_conversion_duration", transcode_duration)

    saved_filename = f"{session_id}_q{q_num}.wav"
    file_path = file_path_wav

    # Extract and log transcoded audio properties for Task 2
    final_props = get_audio_properties(file_path)
    logger.info(
        f"[AUDIO_TRANSCODE_METADATA] "
        f"Transcoded Format: {final_props.get('format')} | "
        f"Codec: {final_props.get('codec')} | "
        f"Sample Rate: {final_props.get('sample_rate')} Hz | "
        f"Channels: {final_props.get('channels')} | "
        f"Bitrate: {final_props.get('bitrate')} bps | "
        f"Duration: {final_props.get('duration'):.3f}s"
    )
        
    # 5. Persist metadata in the database
    logger.info("Persisting session and audio metadata in database...")
    try:
        if not db_session:
            # Create sessions table row
            db_session = DbSession(
                session_id=session_id,
                subject_reference="ANON_UPLOAD",
                status="uploaded",
                created_at=datetime.utcnow()
            )
            db.add(db_session)
        else:
            db_session.status = "uploaded"
            
        # Clean any pre-existing audio metadata and files for this question to avoid unique constraint violations
        audio_exist_stmt = select(DbAudioMetadata).where(
            DbAudioMetadata.session_id == session_id,
            DbAudioMetadata.question_number == q_num
        )
        result = await db.execute(audio_exist_stmt)
        existing_audio = result.scalars().first()
        if existing_audio:
            # Delete old file from disk if it exists
            if os.path.exists(existing_audio.file_path):
                try:
                    os.remove(existing_audio.file_path)
                except Exception as ex:
                    logger.warning(f"Failed to delete old file {existing_audio.file_path}: {ex}")
            await db.delete(existing_audio)
            
        # Create audio_metadata table row
        db_audio = DbAudioMetadata(
            session_id=session_id,
            question_number=q_num,
            file_path=file_path,
            duration_seconds=0.0,  # Will be computed during transcription
            file_size_bytes=total_bytes,
            created_at=datetime.utcnow()
        )
        db.add(db_audio)
        
        await db.commit()
        logger.info(f"Upload success: Session {session_id} Q{q_num} registered and file saved.")
    except Exception as e:
        logger.error(f"Failed to commit database metadata for upload: {e}")
        await db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save upload metadata to database."
        )
        
    return UploadResponse(
        session_id=session_id,
        status="uploaded",
        filename=saved_filename,
        size=total_bytes
    )


def get_audio_properties(file_path: str) -> dict:
    """
    Query audio file properties using ffprobe.
    Returns:
        dict: {
            "format": str,      # e.g. "webm", "wav"
            "codec": str,       # e.g. "pcm_s16le", "opus"
            "sample_rate": int,  # e.g. 16000, 44100
            "channels": int,     # e.g. 1, 2
            "bitrate": int,      # e.g. 128000
            "duration": float    # e.g. 20.34
        }
    """
    import json
    import subprocess
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels,bit_rate,duration:format=format_name,duration,size",
        "-of", "json",
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        
        stream = data.get("streams", [{}])[0] if data.get("streams") else {}
        fmt = data.get("format", {})
        
        # Parse duration (can be in stream or format)
        dur = stream.get("duration") or fmt.get("duration")
        duration = float(dur) if dur is not None else 0.0
        
        # Parse bitrate (can be in stream or format)
        br = stream.get("bit_rate") or fmt.get("bit_rate")
        bitrate = int(br) if br is not None else None
        
        return {
            "format": fmt.get("format_name", "unknown"),
            "codec": stream.get("codec_name", "unknown"),
            "sample_rate": int(stream.get("sample_rate")) if stream.get("sample_rate") else None,
            "channels": int(stream.get("channels")) if stream.get("channels") else None,
            "bitrate": bitrate,
            "duration": duration
        }
    except Exception as e:
        logger.warning(f"ffprobe check failed for {file_path}: {e}")
        return {
            "format": "unknown",
            "codec": "unknown",
            "sample_rate": None,
            "channels": None,
            "bitrate": None,
            "duration": 0.0
        }


def cleanup_transcript(text: str) -> str:
    import re
    if not text:
        return ""
    
    # 1. Normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 2. Fix punctuation spacing
    text = re.sub(r'\s+([,.?!])', r'\1', text)
    
    # 3. Capitalize first letter of each sentence
    def capitalize_match(match):
        return match.group(0).upper()
    text = re.compile(r'(^|[.!?]\s+)([a-z])').sub(capitalize_match, text)
    
    # 4. Remove consecutive duplicate phrases/sentences
    parts = re.split(r'([.!?]\s*)', text)
    cleaned_parts = []
    prev_normalized = None
    
    for i in range(0, len(parts), 2):
        sentence = parts[i].strip()
        if not sentence:
            continue
            
        norm_sentence = re.sub(r'\W+', '', sentence).lower()
        if norm_sentence == prev_normalized:
            continue
            
        cleaned_parts.append(parts[i])
        if i + 1 < len(parts):
            cleaned_parts.append(parts[i+1])
        prev_normalized = norm_sentence
        
    return "".join(cleaned_parts).strip()


transcription_locks = {}


@app.post("/transcribe", response_model=TranscribeResponse, tags=["Audio"])
async def transcribe_session_audio(
    payload: TranscribeRequest,
    db: AsyncSession = Depends(get_db)
) -> TranscribeResponse:
    """
    Execute speech transcription on all uploaded audio files of the specified session.
    Loads Faster-Whisper lazily, decodes audio, and persists results.
    """
    logger.info(f"Received transcription request for session: {payload.session_id}")
    
    # Check locks to prevent concurrent runs for the same session
    lock = transcription_locks.setdefault(payload.session_id, asyncio.Lock())
    async with lock:
        # 1. Fetch Session from Database
        session_stmt = select(DbSession).where(DbSession.session_id == payload.session_id)
        result = await db.execute(session_stmt)
        db_session = result.scalars().first()
        if not db_session:
            logger.error(f"Transcription failed: Session {payload.session_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {payload.session_id} not found."
            )
            
        # 2. Fetch Audio Metadata records
        audio_stmt = select(DbAudioMetadata).where(DbAudioMetadata.session_id == payload.session_id)
        result = await db.execute(audio_stmt)
        audio_records = result.scalars().all()
        if not audio_records:
            logger.error(f"Transcription failed: No audio metadata found for session {payload.session_id}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No audio files registered for session {payload.session_id}. Please upload audio first."
            )
            
        # 3. Check if all transcripts already exist in the database
        transcribed_records = []
        for db_audio in audio_records:
            trans_exist_stmt = select(DbTranscript).where(
                DbTranscript.session_id == payload.session_id,
                DbTranscript.question_number == db_audio.question_number
            )
            result = await db.execute(trans_exist_stmt)
            db_transcript = result.scalars().first()
            if db_transcript:
                transcribed_records.append(db_transcript)
                
        if len(transcribed_records) == len(audio_records):
            logger.info(f"All transcripts already computed for session {payload.session_id}. Returning cached results.")
            db_session.status = "transcribed"
            await db.commit()
            
            combined_transcript = cleanup_transcript(" ".join(t.full_text for t in transcribed_records))
            detected_language = transcribed_records[0].language if transcribed_records else "en"
            total_proc_time = sum(t.processing_time_seconds for t in transcribed_records if t.processing_time_seconds)
            
            return TranscribeResponse(
                session_id=payload.session_id,
                language=detected_language,
                processing_time_seconds=total_proc_time,
                transcript=combined_transcript
            )
            
        # 4. Transition status to 'transcribing'
        db_session.status = "transcribing"
        await db.commit()
        logger.info(f"Session {payload.session_id} status updated to 'transcribing'.")
        
        # Clear transcribed_records and do fresh transcription
        transcribed_records = []
        
        # 5. Transcribe each audio record
        for db_audio in audio_records:
            # Check if transcript already exists for this question
            trans_exist_stmt = select(DbTranscript).where(
                DbTranscript.session_id == payload.session_id,
                DbTranscript.question_number == db_audio.question_number
            )
            result = await db.execute(trans_exist_stmt)
            db_transcript = result.scalars().first()
            
            if db_transcript:
                logger.info(f"Transcript already exists for Q{db_audio.question_number}, skipping transcription.")
                transcribed_records.append(db_transcript)
                continue
                
            file_path = db_audio.file_path
            if not os.path.exists(file_path):
                logger.error(f"Audio file not found on disk at {file_path}")
                continue
                
            logger.info(f"Running Faster-Whisper transcription on Q{db_audio.question_number}: {file_path}")
            try:
                loop = asyncio.get_running_loop()
                from functools import partial
                
                # Measure model loading time dynamically
                start_ml = time.time()
                await loop.run_in_executor(
                    None,
                    TranscriptionService.get_model
                )
                ml_duration = time.time() - start_ml
                
                transcribe_res = await loop.run_in_executor(
                    None,
                    partial(TranscriptionService.transcribe, file_path)
                )
                full_text, language, confidence, proc_time, words = transcribe_res
                lang_prob = getattr(transcribe_res, "language_probability", 0.0)
                avg_seg_conf = getattr(transcribe_res, "average_segment_confidence", 0.0)
                
                # Record model loading duration (once per session)
                if timing_tracker.get(payload.session_id, "model_load_duration") == 0.0:
                    timing_tracker.record(payload.session_id, "model_load_duration", ml_duration)
                
                # Record transcription duration
                timing_tracker.record(payload.session_id, "transcription_duration", proc_time)
                
                # If duration is placeholder 0.0, compute it from word timestamps
                if db_audio.duration_seconds == 0.0 and words:
                    db_audio.duration_seconds = max(w.get("end", 0.0) for w in words)
                    
                cleaned_text = cleanup_transcript(full_text)
                db_transcript = DbTranscript(
                    session_id=payload.session_id,
                    question_number=db_audio.question_number,
                    full_text=cleaned_text,
                    words_json=words,
                    confidence=confidence,
                    language=language,
                    language_probability=lang_prob,
                    average_segment_confidence=avg_seg_conf,
                    processing_time_seconds=proc_time,
                    created_at=datetime.utcnow()
                )
                db.add(db_transcript)
                transcribed_records.append(db_transcript)
            except Exception as e:
                logger.error(f"Transcription engine failed for Q{db_audio.question_number}: {e}")
                db_session.status = "failed"
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Transcription failed on question {db_audio.question_number}."
                )
                
        # 6. Transition status: 'transcribing' -> 'transcribed'
        db_session.status = "transcribed"
        await db.commit()
        logger.info(f"Transcription success: All transcripts saved for session {payload.session_id}. Status set to 'transcribed'.")
        
        combined_transcript = cleanup_transcript(" ".join(t.full_text for t in transcribed_records))
        detected_language = transcribed_records[0].language if transcribed_records else "en"
        total_proc_time = sum(t.processing_time_seconds for t in transcribed_records if t.processing_time_seconds)
        
        return TranscribeResponse(
            session_id=payload.session_id,
            language=detected_language,
            processing_time_seconds=total_proc_time,
            transcript=combined_transcript
        )

@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analytics"])
async def analyze_session_transcription(
    payload: AnalyzeRequest,
    db: AsyncSession = Depends(get_db)
) -> AnalyzeResponse:
    """
    Compute speech analytics (temporal and linguistic metrics) for all transcripts of the specified session.
    Persists metrics to database and returns calculations.
    """
    start_analytics = time.time()
    logger.info(f"Received analytics generation request for session: {payload.session_id}")
    
    # 1. Fetch Session from Database
    session_stmt = select(DbSession).where(DbSession.session_id == payload.session_id)
    result = await db.execute(session_stmt)
    db_session = result.scalars().first()
    if not db_session:
        logger.error(f"Analytics failed: Session {payload.session_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {payload.session_id} not found."
        )
        
    # 2. Fetch all transcripts
    transcript_stmt = select(DbTranscript).where(DbTranscript.session_id == payload.session_id)
    result = await db.execute(transcript_stmt)
    db_transcripts = result.scalars().all()
    if not db_transcripts:
        logger.error(f"Analytics failed: No transcripts found for session {payload.session_id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No transcript found for session {payload.session_id}. Please transcribe the audio first."
        )
        
    # 3. Fetch all audio records
    audio_stmt = select(DbAudioMetadata).where(DbAudioMetadata.session_id == payload.session_id)
    result = await db.execute(audio_stmt)
    audio_records = result.scalars().all()
    
    audio_map = {a.question_number: a for a in audio_records}
    
    aggregated_temporal = {
        "total_speech_duration": 0.0,
        "average_response_duration": 0.0,
        "words_per_minute": 0.0,
        "pause_count": 0,
        "longest_pause": 0.0
    }
    aggregated_linguistic = {
        "word_count": 0,
        "unique_word_count": 0,
        "repeated_words": [],
        "filler_words": {}
    }
    
    temp_wpm_list = []
    temp_durations = []
    
    # Clean pre-existing metrics for all audio records of the session to prevent constraints violations
    from sqlalchemy import delete
    audio_ids = [a.audio_id for a in audio_records]
    if audio_ids:
        await db.execute(delete(DbTemporalMetrics).where(DbTemporalMetrics.audio_id.in_(audio_ids)))
        await db.execute(delete(DbLinguisticMetrics).where(DbLinguisticMetrics.audio_id.in_(audio_ids)))
        
    # 4. Compute metrics for each transcript/audio pair
    for t in db_transcripts:
        db_audio = audio_map.get(t.question_number)
        if not db_audio:
            continue
            
        logger.info(f"Computing metrics for session: {payload.session_id} Q{t.question_number}...")
        try:
            loop = asyncio.get_running_loop()
            from functools import partial
            metrics = await loop.run_in_executor(
                None,
                partial(
                    AnalyticsService.calculate_metrics,
                    t.full_text,
                    t.words_json,
                    db_audio.duration_seconds,
                    db_audio.file_path
                )
            )
            
            # Persist temporal metrics
            db_temporal = DbTemporalMetrics(
                audio_id=db_audio.audio_id,
                speech_duration_seconds=metrics["temporal"]["speech_duration_seconds"],
                words_per_minute=metrics["temporal"]["words_per_minute"],
                pause_count=metrics["temporal"]["pause_count"],
                longest_pause_seconds=metrics["temporal"]["longest_pause_seconds"],
                speech_rate_ratio=metrics["temporal"]["speech_rate_ratio"]
            )
            db.add(db_temporal)
            
            # Persist linguistic metrics
            db_linguistic = DbLinguisticMetrics(
                audio_id=db_audio.audio_id,
                word_count=metrics["linguistic"]["word_count"],
                unique_word_count=metrics["linguistic"]["unique_word_count"],
                repeated_words_json=metrics["linguistic"]["repeated_words_json"],
                filler_words_json=metrics["linguistic"]["filler_words_breakdown"],
                lexical_density=metrics["linguistic"]["lexical_density"]
            )
            db.add(db_linguistic)
            
            # Accumulate for the response
            aggregated_temporal["total_speech_duration"] += db_audio.duration_seconds
            temp_durations.append(db_audio.duration_seconds)
            temp_wpm_list.append(metrics["temporal"]["words_per_minute"])
            aggregated_temporal["pause_count"] += metrics["temporal"]["pause_count"]
            aggregated_temporal["longest_pause"] = max(aggregated_temporal["longest_pause"], metrics["temporal"]["longest_pause_seconds"])
            
            aggregated_linguistic["word_count"] += metrics["linguistic"]["word_count"]
            aggregated_linguistic["unique_word_count"] += metrics["linguistic"]["unique_word_count"]
            
            for item in metrics["linguistic"]["repeated_words"]:
                word = item["word"]
                count = item["count"]
                found = False
                for r in aggregated_linguistic["repeated_words"]:
                    if r["word"] == word:
                        r["count"] += count
                        found = True
                        break
                if not found:
                    aggregated_linguistic["repeated_words"].append({"word": word, "count": count})
                    
            for f, c in metrics["linguistic"]["filler_words_breakdown"].items():
                aggregated_linguistic["filler_words"][f] = aggregated_linguistic["filler_words"].get(f, 0) + c
                
        except Exception as e:
            logger.error(f"Failed to compute analytics for Q{t.question_number}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to run analytics calculations for question {t.question_number}."
            )
            
    # Transition session status to 'analyzed'
    db_session.status = "analyzed"
    await db.commit()
    logger.info(f"Analytics success: All metrics persisted and session status set to 'analyzed'.")
    
    if temp_durations:
        aggregated_temporal["average_response_duration"] = sum(temp_durations) / len(temp_durations)
    if temp_wpm_list:
        aggregated_temporal["words_per_minute"] = sum(temp_wpm_list) / len(temp_wpm_list)
        
    from app.schemas.analytics import RepeatedWord
    
    analytics_duration = time.time() - start_analytics
    timing_tracker.record(payload.session_id, "analytics_duration", analytics_duration)
    
    return AnalyzeResponse(
        session_id=payload.session_id,
        temporal_metrics=TemporalAnalyticsSchema(
            total_speech_duration=aggregated_temporal["total_speech_duration"],
            average_response_duration=aggregated_temporal["average_response_duration"],
            words_per_minute=aggregated_temporal["words_per_minute"],
            pause_count=aggregated_temporal["pause_count"],
            longest_pause=aggregated_temporal["longest_pause"]
        ),
        linguistic_metrics=LinguisticAnalyticsSchema(
            word_count=aggregated_linguistic["word_count"],
            unique_word_count=aggregated_linguistic["unique_word_count"],
            repeated_words=[RepeatedWord(word=r["word"], count=r["count"]) for r in aggregated_linguistic["repeated_words"]],
            filler_words=aggregated_linguistic["filler_words"]
        )
    )


@app.post("/score", response_model=ScoreResponse, tags=["Risk Scoring"])
async def score_session_risk(
    payload: ScoreRequest,
    db: AsyncSession = Depends(get_db)
) -> ScoreResponse:
    """
    Evaluate cognitive risk scoring for the specified session based on temporal and linguistic metrics.
    Persists risk assessment to database and transitions session status to 'scored'.
    """
    start_scoring = time.time()
    logger.info(f"Received risk scoring request for session: {payload.session_id}")
    
    # 1. Fetch Session from Database
    session_stmt = select(DbSession).where(DbSession.session_id == payload.session_id)
    result = await db.execute(session_stmt)
    db_session = result.scalars().first()
    if not db_session:
        logger.error(f"Scoring failed: Session {payload.session_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {payload.session_id} not found."
        )
        
    # 2. Fetch Audio Records and associated Temporal/Linguistic Metrics
    metrics_stmt = (
        select(DbAudioMetadata, DbTemporalMetrics, DbLinguisticMetrics)
        .join(DbTemporalMetrics, DbAudioMetadata.audio_id == DbTemporalMetrics.audio_id)
        .join(DbLinguisticMetrics, DbAudioMetadata.audio_id == DbLinguisticMetrics.audio_id)
        .where(DbAudioMetadata.session_id == payload.session_id)
    )
    result = await db.execute(metrics_stmt)
    rows = result.all()
    
    if not rows:
        logger.error(f"Scoring failed: No computed analytics metrics found for session {payload.session_id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No analytics metrics found for session {payload.session_id}. Please run analytics (/analyze) first."
        )
        
    # Extract audio, temporal, and linguistic records
    audio_records = [row[0] for row in rows]
    temporal_records = [row[1] for row in rows]
    linguistic_records = [row[2] for row in rows]
    
    # Calculate average audio duration across responses
    avg_audio_duration = sum(audio.duration_seconds for audio in audio_records) / len(audio_records)
    
    # Fetch transcript confidences to compute average ASR confidence
    trans_stmt = select(DbTranscript).where(DbTranscript.session_id == payload.session_id)
    trans_result = await db.execute(trans_stmt)
    trans_records = trans_result.scalars().all()
    confidences = []
    for t in trans_records:
        if hasattr(t, "confidence"):
            confidences.append(t.confidence)
        elif isinstance(t, (float, int)):
            confidences.append(t)
        elif isinstance(t, tuple) and t:
            confidences.append(t[0])
    avg_asr_confidence = sum(confidences) / len(confidences) if confidences else 1.0

    # 3. Evaluate Risk Score using service layer in thread pool
    logger.info(f"Evaluating cognitive risk profile for session: {payload.session_id}...")
    try:
        loop = asyncio.get_running_loop()
        from functools import partial
        final_score, risk_level, explanation = await loop.run_in_executor(
            None,
            partial(
                RiskScoringService.evaluate_session_risk,
                temporal_records,
                linguistic_records,
                avg_audio_duration,
                avg_asr_confidence
            )
        )
    except Exception as e:
        logger.error(f"Failed to calculate risk score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run cognitive risk scoring algorithms."
        )
        
    # 4. Persist Risk Assessment in Database
    logger.info("Persisting cognitive risk assessment in database...")
    try:
        from sqlalchemy import delete
        
        # Avoid unique constraint violation by cleaning any pre-existing score
        await db.execute(delete(DbRiskScore).where(DbRiskScore.session_id == payload.session_id))
        
        db_risk = DbRiskScore(
            session_id=payload.session_id,
            score=final_score,
            classification=risk_level,
            rationale=explanation
        )
        db.add(db_risk)
        
        # Transition session status to 'scored'
        db_session.status = "scored"
        
        await db.commit()
        logger.info(f"Scoring success: Cognitive risk assessment persisted and session status set to 'scored'.")
    except Exception as e:
        logger.error(f"Failed to commit database risk score: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save cognitive risk score in database."
        )
        
    # Deserialize visual breakdown fields from JSON explanation
    import json
    summary_text = explanation
    confidence_val = 1.0
    factors_list = []
    breakdown_dict = {}
    
    try:
        parsed_data = json.loads(explanation)
        if isinstance(parsed_data, dict) and "summary" in parsed_data:
            summary_text = parsed_data["summary"]
            confidence_val = parsed_data.get("confidence", 1.0)
            factors_list = parsed_data.get("contributing_factors", [])
            breakdown_dict = parsed_data.get("breakdown", {})
    except Exception:
        pass

    scoring_duration = time.time() - start_scoring
    timing_tracker.record(payload.session_id, "scoring_duration", scoring_duration)
    timing_tracker.print_breakdown(payload.session_id)

    return ScoreResponse(
        session_id=payload.session_id,
        risk_level=risk_level,
        score=final_score,
        explanation=summary_text,
        confidence=confidence_val,
        contributing_factors=factors_list,
        breakdown=breakdown_dict
    )

# --- Assessment Workflows Skeleton (Future Implementation) ---

@app.get("/", tags=["Health"])
async def root() -> Dict[str, str]:
    """Basic health route."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}

@app.post(
    "/api/v1/sessions", 
    response_model=SessionResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["Sessions"]
)
async def create_session(session_data: SessionCreate) -> SessionResponse:
    logger.info(f"Received request for session creation: subject={session_data.subject_reference}")
    session_id = uuid.uuid4()
    questions = [
        QuestionSchema(number=1, prompt="Tell us about your morning routine.", status="pending"),
        QuestionSchema(number=2, prompt="Describe a memorable event from the last week.", status="pending"),
        QuestionSchema(number=3, prompt="Talk about your favourite festival or celebration.", status="pending")
    ]
    
    new_session = {
        "session_id": session_id,
        "status": "initialized",
        "subject_reference": session_data.subject_reference,
        "clinician_id": session_data.clinician_id,
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "questions": questions
    }
    
    MOCK_SESSIONS[session_id] = new_session
    return SessionResponse(**new_session)

@app.post(
    "/api/v1/sessions/{session_id}/audio/{question_number}", 
    response_model=AudioUploadResponse,
    tags=["Audio"]
)
async def upload_audio(
    session_id: uuid.UUID,
    question_number: int,
    audio_file: UploadFile = File(...),
) -> AudioUploadResponse:
    logger.info(f"Received audio upload request: session={session_id}, question={question_number}")
    if question_number not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Question number must be 1, 2, or 3."
        )
        
    if session_id not in MOCK_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Session {session_id} not found."
        )
        
    session = MOCK_SESSIONS[session_id]
    for q in session["questions"]:
        if q.number == question_number:
            q.status = "uploaded"
            
    file_name = f"{session_id}_q{question_number}.wav"
    file_path = f"{settings.UPLOAD_DIR}/{file_name}"
    
    return AudioUploadResponse(
        session_id=session_id,
        question_number=question_number,
        status="uploaded",
        file_path=file_path,
        audio_size_bytes=1048576,
        recorded_duration=42.5
    )

@app.post(
    "/api/v1/sessions/{session_id}/process", 
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Processing"]
)
async def process_session(session_id: uuid.UUID) -> Dict[str, str]:
    logger.info(f"Received process trigger request: session={session_id}")
    if session_id not in MOCK_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Session {session_id} not found."
        )
        
    session = MOCK_SESSIONS[session_id]
    for q in session["questions"]:
        if q.status != "uploaded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio for Question {q.number} is missing. Upload all responses first."
            )
            
    session["status"] = "processing"
    
    return {
        "session_id": str(session_id),
        "status": "processing",
        "message": "Speech analytics calculation and risk scoring has been initiated.",
        "check_status_url": f"/api/v1/sessions/{session_id}"
    }

@app.get(
    "/api/v1/sessions/{session_id}", 
    response_model=SessionResultResponse,
    tags=["Sessions"]
)
async def get_session_results(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> SessionResultResponse:
    logger.info(f"Received query results request for database session: {session_id}")
    
    # Imports needed inside the endpoint
    from app.schemas.analytics import (
        TranscriptResponse,
        AnalyticsContainer,
        RiskAssessmentSchema,
        TemporalMetricsSchema,
        LinguisticMetricsSchema,
        WordTimestamp
    )
    
    # 1. Fetch Session from Database
    session_stmt = select(DbSession).where(DbSession.session_id == session_id)
    result = await db.execute(session_stmt)
    db_session = result.scalars().first()
    
    if not db_session:
        # Fall back to in-memory MOCK_SESSIONS if it exists (for backward compatibility of mocks)
        if session_id in MOCK_SESSIONS:
            session = MOCK_SESSIONS[session_id]
            logger.info("Falling back to MOCK_SESSIONS details for backward compatibility")
            
            mock_transcript = TranscriptResponse(
                question_number=1,
                transcript_text="I woke up at six am, had coffee, and went for a run.",
                duration=12.5,
                words=[
                    WordTimestamp(word="I", start=0.2, end=0.4, probability=0.99),
                    WordTimestamp(word="woke", start=0.5, end=0.8, probability=0.98)
                ],
                confidence=0.98
            )
            mock_analytics = AnalyticsContainer(
                temporal_metrics=TemporalMetricsSchema(
                    total_speech_duration=42.5,
                    average_response_duration=14.16,
                    words_per_minute=110.2,
                    pause_count=8,
                    longest_pause_seconds=3.2
                ),
                linguistic_metrics=LinguisticMetricsSchema(
                    word_count=142,
                    unique_word_count=78,
                    repeated_words=[{"and": 12}, {"coffee": 3}],
                    filler_words_count=9,
                    filler_words_breakdown={"um": 5, "ah": 3, "like": 1}
                )
            )
            mock_risk = RiskAssessmentSchema(
                score=0.32,
                classification="LOW_RISK",
                rationale="Speech tempo and linguistic structures are within standard normal limits. Pause counts represent typical speech breaks.",
                created_at=datetime.utcnow()
            )
            
            if session["status"] in ["processing", "completed"]:
                session["status"] = "completed"
                return SessionResultResponse(
                    session_id=session["session_id"],
                    status="completed",
                    subject_reference=session["subject_reference"],
                    clinician_id=session["clinician_id"],
                    created_at=session["created_at"],
                    completed_at=datetime.utcnow(),
                    transcriptions=[mock_transcript],
                    analytics=mock_analytics,
                    risk_assessment=mock_risk
                )
                
            return SessionResultResponse(
                session_id=session["session_id"],
                status=session["status"],
                subject_reference=session["subject_reference"],
                clinician_id=session["clinician_id"],
                created_at=session["created_at"],
                transcriptions=[]
            )
            
        logger.error(f"Session retrieval failed: Session {session_id} not found in DB or mocks.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Session {session_id} not found."
        )
        
    # 2. Fetch Transcripts from DB
    trans_stmt = select(DbTranscript).where(DbTranscript.session_id == session_id).order_by(DbTranscript.question_number)
    result = await db.execute(trans_stmt)
    db_transcripts = result.scalars().all()
    
    # 3. Fetch Audio, Temporal Metrics, and Linguistic Metrics
    metrics_stmt = (
        select(DbAudioMetadata, DbTemporalMetrics, DbLinguisticMetrics)
        .outerjoin(DbTemporalMetrics, DbAudioMetadata.audio_id == DbTemporalMetrics.audio_id)
        .outerjoin(DbLinguisticMetrics, DbAudioMetadata.audio_id == DbLinguisticMetrics.audio_id)
        .where(DbAudioMetadata.session_id == session_id)
    )
    result = await db.execute(metrics_stmt)
    rows = result.all()
    
    # 4. Fetch Risk Score
    risk_stmt = select(DbRiskScore).where(DbRiskScore.session_id == session_id)
    result = await db.execute(risk_stmt)
    db_risk = result.scalars().first()
    
    # Compile Transcript Responses
    transcriptions = []
    for t in db_transcripts:
        audio_dur = 0.0
        for row in rows:
            if row[0].question_number == t.question_number:
                audio_dur = row[0].duration_seconds
                break
                
        # Parse words json into WordTimestamp models
        words = []
        if isinstance(t.words_json, list):
            for w in t.words_json:
                if isinstance(w, dict):
                    words.append(WordTimestamp(
                        word=w.get("word", ""),
                        start=w.get("start", 0.0),
                        end=w.get("end", 0.0),
                        probability=w.get("probability", 1.0)
                    ))
                    
        transcriptions.append(TranscriptResponse(
            question_number=t.question_number,
            transcript_text=t.full_text,
            duration=audio_dur,
            words=words,
            confidence=t.confidence,
            language=t.language,
            language_probability=t.language_probability,
            average_segment_confidence=t.average_segment_confidence
        ))
        
    # Compile Analytics
    analytics = None
    valid_rows = [row for row in rows if row[1] is not None and row[2] is not None]
    if valid_rows:
        temporal_rows = [row[1] for row in valid_rows]
        linguistic_rows = [row[2] for row in valid_rows]
        audio_records = [row[0] for row in valid_rows]
        
        total_duration = sum(a.duration_seconds for a in audio_records)
        avg_duration = total_duration / len(audio_records)
        avg_wpm = sum(t.words_per_minute for t in temporal_rows) / len(temporal_rows)
        total_pauses = sum(t.pause_count for t in temporal_rows)
        max_pause = max(t.longest_pause_seconds for t in temporal_rows)
        
        total_words = sum(l.word_count for l in linguistic_rows)
        total_unique = sum(l.unique_word_count for l in linguistic_rows)
        
        repeated_words = []
        filler_breakdown = {}
        for l in linguistic_rows:
            rep_json = l.repeated_words_json
            if isinstance(rep_json, dict):
                for w, c in rep_json.items():
                    # Merge counts
                    found = False
                    for item in repeated_words:
                        if w in item:
                            item[w] += c
                            found = True
                            break
                    if not found:
                        repeated_words.append({w: c})
            
            fil_json = l.filler_words_json
            if isinstance(fil_json, dict):
                for w, c in fil_json.items():
                    filler_breakdown[w] = filler_breakdown.get(w, 0) + c
                    
        total_fillers = sum(filler_breakdown.values())
        
        analytics = AnalyticsContainer(
            temporal_metrics=TemporalMetricsSchema(
                total_speech_duration=total_duration,
                average_response_duration=avg_duration,
                words_per_minute=avg_wpm,
                pause_count=total_pauses,
                longest_pause_seconds=max_pause
            ),
            linguistic_metrics=LinguisticMetricsSchema(
                word_count=total_words,
                unique_word_count=total_unique,
                repeated_words=repeated_words,
                filler_words_count=total_fillers,
                filler_words_breakdown=filler_breakdown
            )
        )
        
    # Compile Risk Assessment
    risk_assessment = None
    if db_risk:
        import json
        rationale_text = db_risk.rationale
        confidence_val = 1.0
        factors_list = []
        breakdown_dict = {}
        
        try:
            parsed_data = json.loads(db_risk.rationale)
            if isinstance(parsed_data, dict) and "summary" in parsed_data:
                rationale_text = parsed_data["summary"]
                confidence_val = parsed_data.get("confidence", 1.0)
                factors_list = parsed_data.get("contributing_factors", [])
                breakdown_dict = parsed_data.get("breakdown", {})
        except Exception:
            pass
            
        risk_assessment = RiskAssessmentSchema(
            score=db_risk.score / 100.0,  # Map 0-100 to 0.0-1.0 range
            classification=db_risk.classification,
            rationale=rationale_text,
            created_at=db_risk.created_at,
            confidence=confidence_val,
            contributing_factors=factors_list,
            breakdown=breakdown_dict
        )
        
    return SessionResultResponse(
        session_id=db_session.session_id,
        status=db_session.status,
        subject_reference=db_session.subject_reference,
        clinician_id=db_session.clinician_id,
        created_at=db_session.created_at,
        completed_at=db_session.completed_at,
        transcriptions=transcriptions,
        analytics=analytics,
        risk_assessment=risk_assessment
    )

@app.get(
    "/api/v1/sessions", 
    response_model=Dict[str, Any],
    tags=["Sessions"]
)
async def list_sessions(
    limit: int = 20, 
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    logger.info("Received query sessions list request")
    
    # Query sessions and join with risk score if exists
    stmt = (
        select(DbSession, DbRiskScore.classification)
        .outerjoin(DbRiskScore, DbSession.session_id == DbRiskScore.session_id)
        .order_by(DbSession.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    items = []
    for row in rows:
        db_s, risk_class = row
        items.append({
            "session_id": str(db_s.session_id),
            "subject_reference": db_s.subject_reference,
            "created_at": db_s.created_at.isoformat() if db_s.created_at else None,
            "status": db_s.status,
            "risk_classification": risk_class if risk_class else "Pending"
        })
        
    # Merge in-memory mock sessions for backward compatibility if DB is empty
    if not items:
        for s_id, s in MOCK_SESSIONS.items():
            items.append({
                "session_id": str(s_id),
                "subject_reference": s["subject_reference"],
                "created_at": s["created_at"].isoformat() if isinstance(s["created_at"], datetime) else s["created_at"],
                "status": s["status"],
                "risk_classification": "Low Risk" if s["status"] == "completed" else "Pending"
            })
            
    return {
        "total_count": len(items),
        "items": items[offset : offset + limit]
    }
