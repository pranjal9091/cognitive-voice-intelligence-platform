import os
import re
import wave
import logging
from typing import Dict, Any, List, Tuple
from collections import Counter
import numpy as np

logger = logging.getLogger("app.analytics_service")

# Supported filler words dictionary definitions
ENGLISH_FILLERS = {"um", "uh", "actually", "like"}
HINDI_FILLERS = {"matlab", "toh", "acha", "haan"}
ALL_FILLERS = ENGLISH_FILLERS.union(HINDI_FILLERS)

class AnalyticsService:
    """
    Service layer providing calculations for voice analysis.
    Computes temporal metrics (WPM, pause rates, speech ratios)
    and linguistic metrics (lexical variety, repeated word counts, filler rates).
    """

    @staticmethod
    def estimate_pauses_from_audio(file_path: str, silence_threshold_ratio: float = 0.03, min_pause_duration_seconds: float = 0.3) -> Tuple[int, float]:
        """
        Acoustic RMS amplitude analysis to detect pauses inside a raw 16-bit PCM mono WAV file.
        Returns:
            - pause_count (int): Number of detected pause segments.
            - longest_pause_seconds (float): Length of the longest silent region in seconds.
        """
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"Audio file not found at {file_path} for acoustic pause analysis. Returning fallback.")
            return 0, 0.0
            
        try:
            with wave.open(file_path, 'rb') as wav:
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                frame_rate = wav.getframerate()
                n_frames = wav.getnframes()
                
                if n_frames == 0:
                    return 0, 0.0
                    
                raw_data = wav.readframes(n_frames)
                data = np.frombuffer(raw_data, dtype=np.int16)
                
                # If multi-channel, merge to mono
                if channels > 1:
                    data = data.reshape(-1, channels).mean(axis=1)
                    
                # Use 50ms window sizing
                window_size = int(frame_rate * 0.05)
                rms_values = []
                for i in range(0, len(data), window_size):
                    frame = data[i:i+window_size]
                    if len(frame) == 0:
                        continue
                    rms = np.sqrt(np.mean(frame.astype(np.float64)**2))
                    rms_values.append(rms)
                    
                if not rms_values:
                    return 0, 0.0
                    
                max_rms = max(rms_values)
                # Silence threshold: 3% of peak amplitude
                silence_threshold = max_rms * silence_threshold_ratio
                
                pauses = []
                current_pause_len = 0.0
                
                for rms in rms_values:
                    if rms < silence_threshold:
                        current_pause_len += 0.05  # Each window maps to 50ms
                    else:
                        if current_pause_len >= min_pause_duration_seconds:
                            pauses.append(current_pause_len)
                        current_pause_len = 0.0
                if current_pause_len >= min_pause_duration_seconds:
                    pauses.append(current_pause_len)
                    
                pause_count = len(pauses)
                longest_pause = max(pauses) if pauses else 0.0
                
                return pause_count, longest_pause
        except Exception as e:
            logger.error(f"Failed to perform acoustic pause estimation: {e}")
            return 0, 0.0

    @staticmethod
    def estimate_pauses_from_timestamps(words: List[Dict[str, Any]], min_pause_duration_seconds: float = 0.25) -> Tuple[int, float]:
        """
        Fallback pause detector using gaps between word-level timestamps.
        Used when the raw audio WAV file is missing or unreadable.
        """
        if not words or len(words) < 2:
            return 0, 0.0
            
        pauses = []
        for i in range(len(words) - 1):
            end_prev = words[i].get("end", 0.0)
            start_next = words[i+1].get("start", 0.0)
            gap = start_next - end_prev
            if gap >= min_pause_duration_seconds:
                pauses.append(gap)
                
        pause_count = len(pauses)
        longest_pause = max(pauses) if pauses else 0.0
        return pause_count, longest_pause

    @classmethod
    def calculate_metrics(cls, transcript_text: str, words_json: List[Dict[str, Any]], duration_seconds: float, audio_path: str) -> Dict[str, Any]:
        """
        Orchestrates calculation of temporal and linguistic metrics.
        """
        logger.info("Computing temporal and linguistic metrics from transcript...")
        
        # --- Linguistic Metrics ---
        # Normalize text to lowercase and remove punctuation
        cleaned_text = re.sub(r'[^\w\s]', '', transcript_text.lower())
        words = cleaned_text.split()
        
        word_count = len(words)
        unique_word_count = len(set(words))
        
        # Word frequency counter
        counts = Counter(words)
        
        # List of repeated words: [{"word": "sample", "count": 2}]
        repeated_words_list = [{"word": word, "count": count} for word, count in counts.items() if count > 1]
        
        # Filler word breakdown
        filler_breakdown = {word: count for word, count in counts.items() if word in ALL_FILLERS}
        filler_count = sum(filler_breakdown.values())
        
        # Lexical Density: unique words divided by total words
        lexical_density = (unique_word_count / word_count) if word_count > 0 else 0.0

        # --- Temporal Metrics ---
        # Estimate pause details
        pause_count, longest_pause = cls.estimate_pauses_from_audio(audio_path)
        if pause_count == 0 and longest_pause == 0.0:
            # Fallback to word-timestamps gaps
            pause_count, longest_pause = cls.estimate_pauses_from_timestamps(words_json)
            
        # Words Per Minute (WPM)
        effective_duration = duration_seconds if duration_seconds > 0 else 1.0
        wpm = (word_count / effective_duration) * 60.0
        
        # Speech Rate Ratio: active speech time over total duration
        total_pause_duration = pause_count * 0.4  # Assume average pause is 400ms for ratio calculations
        speech_duration = max(0.1, duration_seconds - total_pause_duration)
        speech_rate_ratio = min(1.0, speech_duration / effective_duration)
        
        metrics = {
            "temporal": {
                "speech_duration_seconds": speech_duration,
                "words_per_minute": wpm,
                "pause_count": pause_count,
                "longest_pause_seconds": longest_pause,
                "speech_rate_ratio": speech_rate_ratio,
                "total_speech_duration": duration_seconds,
                "average_response_duration": duration_seconds
            },
            "linguistic": {
                "word_count": word_count,
                "unique_word_count": unique_word_count,
                "repeated_words": repeated_words_list,
                "repeated_words_json": {item["word"]: item["count"] for item in repeated_words_list},
                "filler_words_count": filler_count,
                "filler_words_breakdown": filler_breakdown,
                "lexical_density": lexical_density
            }
        }
        
        logger.info(f"Metrics calculations finished: WPM={wpm:.1f}, pauses={pause_count}, fillers={filler_count}")
        return metrics
