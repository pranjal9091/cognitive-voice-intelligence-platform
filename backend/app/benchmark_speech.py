import sys
import os
import time
from typing import Dict, Any

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.transcription_service import TranscriptionService
from app.main import cleanup_transcript

def run_baseline_transcribe(model, file_path: str):
    """
    Transcribes the audio using baseline settings (beam_size=5, VAD filter disabled,
    condition_on_previous_text=True, and default Whisper language detection).
    """
    start_time = time.time()
    
    # Run default transcribe
    segments, info = model.transcribe(
        file_path,
        beam_size=5,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=True
    )
    
    segments = list(segments)
    processing_time = time.time() - start_time
    
    full_text = " ".join(s.text for s in segments).strip()
    return full_text, info.language, processing_time

def run_optimized_transcribe(file_path: str):
    """
    Transcribes the audio using optimized settings: VAD filter enabled,
    beam_size=3, condition_on_previous_text=False, language mapping, and post-processing cleanup.
    """
    start_time = time.time()
    
    # Run optimized transcribe (which does language mapping and VAD)
    full_text, language, confidence, proc_time, words = TranscriptionService.transcribe(
        file_path,
        beam_size=3,
        vad_filter=True,
        condition_on_previous_text=False
    )
    
    # Apply cleanup
    cleaned_text = cleanup_transcript(full_text)
    processing_time = time.time() - start_time
    
    return cleaned_text, language, processing_time

def main():
    print("======================================================================")
    print("📊 SPEECH TRANSCRIPTION PIPELINE BENCHMARK (Whisper Medium)")
    print("======================================================================\n")
    
    # Load model
    print("Initializing Whisper model...")
    model = TranscriptionService.get_model()
    print("Model initialized successfully.\n")
    
    # Define test samples
    samples = {
        "English Sample": "/app/uploads/46a40782-c5b3-44c5-888f-4fa542f37644_q1.wav",
        "Hinglish Sample": "/app/uploads/eef65994-864a-4f2e-86c0-0c82085c45a0_q1.wav",
        "Hindi Sample": "/app/uploads/79186850-6975-4ab6-82d7-9a15f93099fb_q1.wav"
    }
    
    results = []
    
    for label, path in samples.items():
        if not os.path.exists(path):
            print(f"⚠️ Warning: Sample file not found at {path}, skipping.")
            continue
            
        print(f"👉 Benchmarking {label} ({os.path.basename(path)})...")
        
        # 1. Run Baseline
        base_text, base_lang, base_time = run_baseline_transcribe(model, path)
        print(f"   [Baseline]  Lang: '{base_lang}' | Time: {base_time:.2f}s")
        print(f"   [Baseline]  Text: {base_text[:120]}...")
        
        # 2. Run Optimized
        opt_text, opt_lang, opt_time = run_optimized_transcribe(path)
        print(f"   [Optimized] Lang: '{opt_lang}' | Time: {opt_time:.2f}s")
        print(f"   [Optimized] Text: {opt_text[:120]}...")
        
        speedup = (base_time - opt_time) / base_time * 100
        print(f"   ⚡ Speedup: {speedup:.1f}%\n")
        
        results.append({
            "label": label,
            "filename": os.path.basename(path),
            "base_lang": base_lang,
            "opt_lang": opt_lang,
            "base_time": base_time,
            "opt_time": opt_time,
            "speedup": speedup,
            "base_text": base_text,
            "opt_text": opt_text
        })
        
    # Print Markdown Summary
    print("\n" + "="*70)
    print("📈 BENCHMARK RESULTS SUMMARY (Markdown Format)")
    print("="*70 + "\n")
    
    print("| Sample | Baseline Lang | Optimized Lang | Baseline Time | Optimized Time | Speedup (%) |")
    print("|---|---|---|---|---|---|")
    for r in results:
        print(f"| {r['label']} | `{r['base_lang']}` | `{r['opt_lang']}` | {r['base_time']:.2f}s | {r['opt_time']:.2f}s | {r['speedup']:.1f}% |")
        
    print("\n### Transcription Text Comparison\n")
    for r in results:
        print(f"#### {r['label']} ({r['filename']})")
        print(f"- **Baseline ({r['base_lang']}):**")
        print(f"  > {r['base_text']}")
        print(f"- **Optimized ({r['opt_lang']}):**")
        print(f"  > {r['opt_text']}")
        print()

if __name__ == "__main__":
    main()
