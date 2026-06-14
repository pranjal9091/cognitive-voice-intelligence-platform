import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from faster_whisper import WhisperModel
from app.core.config import settings

# Find a webm file or any audio file
audio_dir = "/Users/pranjalsingh/.gemini/antigravity-ide/scratch/cognitive-voice-platform/storage/audio/sessions"
webm_file = os.path.join(audio_dir, "271a9822-f7ea-471f-bffe-4f1cdd7344ba_q1.webm")

if not os.path.exists(webm_file):
    print(f"Error: {webm_file} not found!")
    sys.exit(1)

for threads in [4]:
    print(f"\n--- Testing with cpu_threads={threads} ---")
    
    # 1. Model Loading
    print("Loading model...")
    start_load = time.time()
    model = WhisperModel(
        settings.WHISPER_MODEL,
        device="cpu",
        compute_type="int8",
        cpu_threads=threads,
        local_files_only=True
    )
    print(f"Model loaded in: {time.time() - start_load:.2f} seconds")
    
    # 2. Transcription
    print("Transcribing audio...")
    start_transcribe = time.time()
    
    from faster_whisper.audio import decode_audio
    sampling_rate = model.feature_extractor.sampling_rate
    audio = decode_audio(webm_file, sampling_rate=sampling_rate)
    
    segments, info = model.transcribe(
        audio,
        beam_size=3,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 400},
        condition_on_previous_text=False
    )
    segments = list(segments)
    
    print(f"Transcription completed in: {time.time() - start_transcribe:.2f} seconds")
    print(f"Detected language: {info.language}")
    print(f"Text: {' '.join(s.text for s in segments)}")
