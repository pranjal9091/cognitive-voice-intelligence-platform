import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
print("WHISPER_MODEL:", settings.WHISPER_MODEL)
print("WHISPER_DEVICE:", settings.WHISPER_DEVICE)
print("WHISPER_COMPUTE_TYPE:", settings.WHISPER_COMPUTE_TYPE)

from app.services.transcription_service import TranscriptionService

# Find a webm file or any audio file
audio_dir = "/Users/pranjalsingh/.gemini/antigravity-ide/scratch/cognitive-voice-platform/storage/audio/sessions"
webm_file = os.path.join(audio_dir, "271a9822-f7ea-471f-bffe-4f1cdd7344ba_q1.webm")

if not os.path.exists(webm_file):
    print(f"Error: {webm_file} not found!")
    sys.exit(1)

print("\n--- Phase 1: Model Loading ---")
start = time.time()
model = TranscriptionService.get_model()
print(f"Model loaded in: {time.time() - start:.2f} seconds")

# Call get_model again to verify singleton behavior
start = time.time()
model2 = TranscriptionService.get_model()
print(f"Model second load (singleton verify) in: {time.time() - start:.6f} seconds")
print(f"Same instance: {model is model2}")

print("\n--- Phase 2: Transcription ---")
start = time.time()
full_text, language, confidence, proc_time, words = TranscriptionService.transcribe(webm_file)
print(f"Transcription completed in: {time.time() - start:.2f} seconds")
print("Text:", full_text)
print("Language:", language)
print("Confidence:", confidence)
print("Proc Time from return:", proc_time)
