from huggingface_hub import snapshot_download
import time

print("🚀 Starting download of 'Systran/faster-whisper-small'...")
start = time.time()
try:
    path = snapshot_download(
        repo_id="Systran/faster-whisper-small",
        allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
    )
    print(f"🎉 Download completed successfully in {time.time() - start:.2f} seconds!")
    print("Model path:", path)
except Exception as e:
    print("❌ Download failed:", e)
