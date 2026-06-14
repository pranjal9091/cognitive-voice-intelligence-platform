import logging
import time
import threading
from typing import Dict, Any, List, Tuple, Optional
from faster_whisper import WhisperModel
from app.core.config import settings

logger = logging.getLogger("app.transcription_service")

def get_audio_properties(file_path: str) -> dict:
    """
    Query audio file properties using ffprobe.
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
        
        dur = stream.get("duration") or fmt.get("duration")
        duration = float(dur) if dur is not None else 0.0
        
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


class TranscriptionResult(tuple):
    def __new__(cls, full_text: str, language: str, confidence: float, processing_time: float, words_list: List[Dict[str, Any]], language_probability: float = 0.0, average_segment_confidence: float = 0.0):
        return super().__new__(cls, (full_text, language, confidence, processing_time, words_list))

    def __init__(self, full_text: str, language: str, confidence: float, processing_time: float, words_list: List[Dict[str, Any]], language_probability: float = 0.0, average_segment_confidence: float = 0.0):
        self.language_probability = language_probability
        self.average_segment_confidence = average_segment_confidence

    @property
    def full_text(self) -> str:
        return self[0]

    @property
    def language(self) -> str:
        return self[1]

    @property
    def confidence(self) -> float:
        return self[2]

    @property
    def processing_time(self) -> float:
        return self[3]

    @property
    def words_list(self) -> List[Dict[str, Any]]:
        return self[4]



def get_repetition_ratio(text: str) -> float:
    """
    Calculate the ratio of duplicate words to total words.
    """
    if not text:
        return 0.0
    import re
    words = re.findall(r'[\u0900-\u097F\w\']+', text.lower())
    if not words:
        return 0.0
    unique_words = set(words)
    return (len(words) - len(unique_words)) / len(words)


def clean_repetition_loops(text: str) -> str:
    """
    Detect and clean up consecutive repeating words or phrases (e.g. "नहीं नहीं नहीं").
    """
    if not text:
        return ""
    import re
    # Match consecutive repeated words (3 or more times)
    # e.g. "नहीं नहीं नहीं नहीं" -> "नहीं"
    text = re.sub(r'\b(\w+)(?:\s+\1){2,}\b', r'\1', text)
    
    # Match consecutive repeated 2-word phrases (2 or more times)
    # e.g. "नहीं लिए नहीं लिए नहीं लिए" -> "नहीं लिए"
    text = re.sub(r'\b(\w+\s+\w+)(?:\s+\1){1,}\b', r'\1', text)
    
    return text


def align_words_list(cleaned_text: str, words_list: list) -> list:
    """
    Align the words_list with the cleaned_text, removing any dropped word timestamps.
    """
    if not cleaned_text:
        return []
    import re
    cleaned_words = cleaned_text.split()
    if len(cleaned_words) >= len(words_list):
        return words_list
    
    new_words_list = []
    w_idx = 0
    for cw in cleaned_words:
        cw_clean = re.sub(r'[^\u0900-\u097F\w]+', '', cw.lower())
        
        found = False
        while w_idx < len(words_list):
            w_item = words_list[w_idx]
            w_clean = re.sub(r'[^\u0900-\u097F\w]+', '', w_item.get("word", "").lower())
            
            if w_clean == cw_clean or cw_clean in w_clean or w_clean in cw_clean:
                new_words_list.append(w_item)
                w_idx += 1
                found = True
                break
            w_idx += 1
            
        if not found:
            if w_idx - 1 < len(words_list):
                new_words_list.append(words_list[w_idx - 1])
    return new_words_list


class TranscriptionService:
    """
    Singleton-style service class that handles loading the Faster-Whisper model
    lazily and executing speech-to-text transcriptions with word-level timestamps.
    """
    _model_instance: WhisperModel = None
    _model_lock = threading.Lock()
    model_load_duration: float = 0.0

    @classmethod
    def get_model(cls) -> WhisperModel:
        """
        Lazy loader for the WhisperModel instance.
        Ensures the model is loaded into memory only once and is reused.
        """
        if cls._model_instance is None:
            with cls._model_lock:
                if cls._model_instance is None:
                    logger.info(
                        f"Initializing Faster-Whisper model '{settings.WHISPER_MODEL}' "
                        f"on device '{settings.WHISPER_DEVICE}' with compute type '{settings.WHISPER_COMPUTE_TYPE}' "
                        f"and cpu_threads={settings.WHISPER_CPU_THREADS}..."
                    )
                    start_time = time.time()
                    try:
                        # First try loading with local_files_only=True to prevent slow HF Hub connection check
                        cls._model_instance = WhisperModel(
                            settings.WHISPER_MODEL,
                            device=settings.WHISPER_DEVICE,
                            compute_type=settings.WHISPER_COMPUTE_TYPE,
                            cpu_threads=settings.WHISPER_CPU_THREADS,
                            local_files_only=True
                        )
                        elapsed = time.time() - start_time
                        cls.model_load_duration = elapsed
                        logger.info(f"Faster-Whisper model loaded locally (local_files_only=True) in {elapsed:.2f} seconds.")
                    except Exception as local_err:
                        logger.warning(
                            f"Failed to load Faster-Whisper model locally: {local_err}. "
                            "Retrying with local_files_only=False (downloading if needed)..."
                        )
                        try:
                            cls._model_instance = WhisperModel(
                                settings.WHISPER_MODEL,
                                device=settings.WHISPER_DEVICE,
                                compute_type=settings.WHISPER_COMPUTE_TYPE,
                                cpu_threads=settings.WHISPER_CPU_THREADS,
                                local_files_only=False
                            )
                            elapsed = time.time() - start_time
                            cls.model_load_duration = elapsed
                            logger.info(f"Faster-Whisper model downloaded/loaded in {elapsed:.2f} seconds.")
                        except Exception as e:
                            logger.critical(f"Failed to load Faster-Whisper model: {e}")
                            raise
        return cls._model_instance

    @classmethod
    def transcribe(
        cls, 
        file_path: str,
        beam_size: Optional[int] = None,
        vad_filter: bool = False,
        condition_on_previous_text: bool = True
    ) -> TranscriptionResult:
        """
        Transcribes the speech in an audio file using automatic language detection
        and multilingual decoding.
        """
        model = cls.get_model()
        logger.info(f"Beginning speech transcription for: {file_path}")
        start_time = time.time()
        
        # Verify audio properties before transcription
        import os
        props = get_audio_properties(file_path)
        logger.info(
            f"\n[AUDIO_VERIFY_BEFORE_TRANSCRIBE]\n"
            f"File: {os.path.basename(file_path)}\n"
            f"Format: {props.get('format')}\n"
            f"Codec: {props.get('codec')}\n"
            f"Sample Rate: {props.get('sample_rate')} Hz\n"
            f"Channels: {props.get('channels')}\n"
            f"Bitrate: {props.get('bitrate')} bps\n"
            f"Duration: {props.get('duration'):.3f}s\n"
        )
        
        from faster_whisper.audio import decode_audio
        
        # 1. Decode audio once
        sampling_rate = model.feature_extractor.sampling_rate
        audio = decode_audio(file_path, sampling_rate=sampling_rate)
        
        # 2. Detect language
        detected_lang, lang_prob, all_lang_probs_list = model.detect_language(audio=audio)
        
        # Enable multilingual decoding for detected Hindi speech
        multilingual_decoding = True if detected_lang in ["hi", "ur"] else False
        
        # 3. Transcribe audio using automatic language detection and optimized parameters
        segments, info = model.transcribe(
            audio,
            language=None,  # Do NOT force language, use auto detection
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=True,
            word_timestamps=True,
            vad_filter=False,
            compression_ratio_threshold=2.2,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            no_repeat_ngram_size=4,
            multilingual=multilingual_decoding
        )
        segments = list(segments)
        
        full_text = " ".join(s.text for s in segments).strip()
        cleaned_text = clean_repetition_loops(full_text)
        
        # Return and log: info.language, info.language_probability, and transcript (User Request)
        print(f"\n[LANGUAGE]\n{info.language}")
        print(f"\n[LANGUAGE_PROBABILITY]\n{info.language_probability:.4f}")
        print(f"\n[TRANSCRIPT]\n{cleaned_text}")
        
        logger.info(f"\n[LANGUAGE]\n{info.language}")
        logger.info(f"\n[LANGUAGE_PROBABILITY]\n{info.language_probability:.4f}")
        logger.info(f"\n[TRANSCRIPT]\n{cleaned_text}")
        
        # Construct words list
        words_list = []
        total_prob = 0.0
        word_count = 0
        for segment in segments:
            if segment.words:
                for word in segment.words:
                    words_list.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability
                    })
                    total_prob += word.probability
                    word_count += 1
                    
        confidence = total_prob / word_count if word_count > 0 else info.language_probability
        
        # Calculate average segment confidence from avg_logprob
        import math
        segment_probs = [math.exp(s.avg_logprob) for s in segments if hasattr(s, "avg_logprob")]
        avg_segment_conf = sum(segment_probs) / len(segment_probs) if segment_probs else 0.0
        
        cleaned_words_list = align_words_list(cleaned_text, words_list)
        total_time = time.time() - start_time
        
        return TranscriptionResult(
            full_text=cleaned_text,
            language=info.language,
            confidence=confidence,
            processing_time=total_time,
            words_list=cleaned_words_list,
            language_probability=info.language_probability,
            average_segment_confidence=avg_segment_conf
        )
