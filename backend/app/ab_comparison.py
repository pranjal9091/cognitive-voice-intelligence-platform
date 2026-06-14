import os
import sys
import time
import math
import re
from typing import Dict, Any
from faster_whisper import WhisperModel

# Ensure we can import service
sys.path.append("/app")
from app.core.config import settings
from app.services.transcription_service import TranscriptionService, get_repetition_ratio

def get_word_accuracy(reference: str, hypothesis: str) -> float:
    ref_words = re.findall(r'[\u0900-\u097F\w\']+', reference.lower())
    hyp_words = re.findall(r'[\u0900-\u097F\w\']+', hypothesis.lower())
    
    if not ref_words:
        return 0.0 if hyp_words else 100.0
    
    n, m = len(ref_words), len(hyp_words)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
        
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = min(
                    dp[i-1][j] + 1,     # Deletion
                    dp[i][j-1] + 1,     # Insertion
                    dp[i-1][j-1] + 1    # Substitution
                )
    
    errors = dp[n][m]
    accuracy = max(0.0, 1.0 - (errors / n)) * 100.0
    return accuracy

def run_old_pipeline(model: WhisperModel, file_path: str) -> Dict[str, Any]:
    # Old pipeline: VAD=True, Beam=3, temp=None, condition_on_previous_text=False
    start = time.time()
    segments, info = model.transcribe(
        file_path,
        beam_size=3,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 400},
        condition_on_previous_text=False
    )
    segments = list(segments)
    duration = time.time() - start
    
    full_text = " ".join(s.text for s in segments).strip()
    
    total_prob = 0.0
    word_count = 0
    for s in segments:
        if s.words:
            for w in s.words:
                total_prob += w.probability
                word_count += 1
    avg_word_conf = total_prob / word_count if word_count > 0 else info.language_probability
    
    segment_probs = [math.exp(s.avg_logprob) for s in segments if hasattr(s, "avg_logprob")]
    avg_seg_conf = sum(segment_probs) / len(segment_probs) if segment_probs else 0.0
    
    return {
        "text": full_text,
        "language": info.language,
        "language_probability": info.language_probability,
        "confidence": avg_word_conf,
        "average_segment_confidence": avg_seg_conf,
        "duration_seconds": duration,
        "repetition_ratio": get_repetition_ratio(full_text)
    }

def main():
    print("ASR A/B ACCURACY STUDY: OLD VS NEW PIPELINE")
    print("===========================================")
    
    model = WhisperModel(
        settings.WHISPER_MODEL,
        device=settings.WHISPER_DEVICE,
        compute_type="int8",
        cpu_threads=settings.WHISPER_CPU_THREADS,
        local_files_only=True
    )
    
    samples = {
        "Hinglish Sample (Q2 Volleyball)": {
            "path": "/app/uploads/f74c5df7-cbc4-4492-85d9-5cd1e5d2919c_q2.wav",
            "reference": "मैंने बोला था कि रिसेंटली हम वॉलीबॉल टूर्नामेंट जीते"
        },
        "Hindi Sample (Q3 Diwali)": {
            "path": "/app/uploads/f74c5df7-cbc4-4492-85d9-5cd1e5d2919c_q3.wav",
            "reference": "और फेवरेट फेस्टिवल दिवाली है मेरा"
        }
    }
    
    for name, sample in samples.items():
        path = sample["path"]
        ref = sample["reference"]
        
        if not os.path.exists(path):
            print(f"Skipping {name}: file not found at {path}")
            continue
            
        print(f"\n--- Running A/B Study: {name} ---")
        print(f"Expected: \"{ref}\"")
        
        # 1. Run old pipeline
        print("\n[A] Running Old Pipeline...")
        old_res = run_old_pipeline(model, path)
        old_acc = get_word_accuracy(ref, old_res["text"])
        
        # 2. Run new pipeline via TranscriptionService
        print("\n[B] Running New Upgraded Pipeline...")
        new_res = TranscriptionService.transcribe(path)
        new_acc = get_word_accuracy(ref, new_res.full_text)
        
        print("\n=== RESULTS COMPARISON ===")
        print(f"[A] OLD PIPELINE:")
        print(f"  Hypothesis Text:   \"{old_res['text']}\"")
        print(f"  Detected Language: {old_res['language']} (Prob: {old_res['language_probability']:.4f})")
        print(f"  Word Confidence:   {old_res['confidence']:.4f}")
        print(f"  Repetition Ratio:  {old_res['repetition_ratio']:.4f}")
        print(f"  Word Accuracy:     {old_acc:.2f}%")
        print(f"  Time taken:        {old_res['duration_seconds']:.2f}s")
        
        print(f"\n[B] NEW UPGRADED PIPELINE:")
        print(f"  Hypothesis Text:   \"{new_res.full_text}\"")
        print(f"  Detected Language: {new_res.language} (Prob: {new_res.language_probability:.4f})")
        print(f"  Word Confidence:   {new_res.confidence:.4f}")
        print(f"  Repetition Ratio:  {get_repetition_ratio(new_res.full_text):.4f}")
        print(f"  Word Accuracy:     {new_acc:.2f}%")
        print(f"  Time taken:        {new_res.processing_time:.2f}s")
        print("==========================")

if __name__ == "__main__":
    main()
