import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("app.risk_scoring_service")

class RiskScoringService:
    """
    Service layer providing cognitive risk scoring algorithms.
    Evaluates computed temporal and linguistic metrics against transparent,
    deterministic rules to assign risk levels (LOW_RISK, MEDIUM_RISK, HIGH_RISK).
    """

    @staticmethod
    def evaluate_session_risk(
        temporal_records: List[Any],
        linguistic_records: List[Any],
        avg_audio_duration: float,
        avg_asr_confidence: float = 1.0
    ) -> Tuple[float, str, str]:
        """
        Calculates a cognitive risk score (0.0 to 100.0), a risk category, and a detailed explanation.
        
        Args:
            temporal_records: List of TemporalMetrics database objects or dicts.
            linguistic_records: List of LinguisticMetrics database objects or dicts.
            avg_audio_duration: Average recorded audio duration for session responses.
            avg_asr_confidence: Average word confidence from ASR (0.0 to 1.0).
            
        Returns:
            Tuple of (score, risk_level, explanation_json_string)
        """
        import json
        if not temporal_records or not linguistic_records:
            logger.warning("Empty metrics list passed to risk scoring service. Returning low risk default.")
            explanation_data = {
                "summary": "No metrics available to calculate risk. DISCLAIMER: This is an engineering demonstration only.",
                "confidence": 0.0,
                "contributing_factors": [],
                "breakdown": {
                    "speaking_rate": 0.0,
                    "pause_behavior": 0.0,
                    "vocabulary_diversity": 0.0,
                    "repetition_frequency": 0.0,
                    "filler_usage": 0.0
                }
            }
            return 0.0, "LOW_RISK", json.dumps(explanation_data)

        # 1. Aggregate metrics across session recordings
        num_records = len(temporal_records)
        
        # We can extract values using getattr if they are DB objects, or get() if they are dicts
        def get_val(obj, key, default=0.0):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # Average words per minute
        avg_wpm = sum(get_val(t, "words_per_minute") for t in temporal_records) / num_records
        # Total and longest pause details
        total_pause_count = sum(get_val(t, "pause_count", 0) for t in temporal_records)
        max_longest_pause = max(get_val(t, "longest_pause_seconds") for t in temporal_records)
        
        # Word counts
        total_word_count = sum(get_val(l, "word_count", 0) for l in linguistic_records)
        total_unique_word_count = sum(get_val(l, "unique_word_count", 0) for l in linguistic_records)

        # Repetitions
        total_repeated_count = 0
        for l in linguistic_records:
            repeated_json = get_val(l, "repeated_words_json", {})
            if isinstance(repeated_json, dict):
                total_repeated_count += sum(repeated_json.values())

        # Fillers
        total_filler_count = 0
        for l in linguistic_records:
            filler_json = get_val(l, "filler_words_json", {})
            if isinstance(filler_json, dict):
                total_filler_count += sum(filler_json.values())

        # Calculate ratios
        repeated_word_frequency = (total_repeated_count / total_word_count) if total_word_count > 0 else 0.0
        filler_word_frequency = (total_filler_count / total_word_count) if total_word_count > 0 else 0.0
        lexical_density = (total_unique_word_count / total_word_count) if total_word_count > 0 else 1.0

        # 2. Rule-Based Scoring Calculations (scale of 0-100)
        score_points = 0.0
        contributing_factors = []

        # Rule A: Words Per Minute (normal: 110-150 WPM)
        speed_score = 0.0
        if avg_wpm < 50.0:
            score_points += 25.0
            speed_score = 1.0
            contributing_factors.append("Severe Speech Pacing Delay")
        elif avg_wpm < 80.0:
            score_points += 15.0
            speed_score = 0.7
            contributing_factors.append("Moderately Slowed Speech pacing")
        elif avg_wpm < 100.0:
            score_points += 5.0
            speed_score = 0.3
            contributing_factors.append("Mildly Slowed Speech pacing")

        # Rule B: Excessive/Long Pauses
        max_pause_score = 0.0
        if max_longest_pause > 5.0:
            score_points += 20.0
            max_pause_score = 1.0
            contributing_factors.append("Extended silent Pauses (>5s)")
        elif max_longest_pause >= 3.0:
            score_points += 10.0
            max_pause_score = 0.5
            contributing_factors.append("Elevated silent Pauses (>=3s)")

        pause_freq_score = 0.0
        if total_pause_count > 10:
            score_points += 10.0
            pause_freq_score = 0.8
            contributing_factors.append("Frequent Speech formulation Pauses")
        elif total_pause_count > 5:
            pause_freq_score = 0.4

        pause_score = min(1.0, max_pause_score + pause_freq_score)

        # Rule C: Short Response Duration
        if avg_audio_duration < 4.0:
            score_points += 15.0
            contributing_factors.append("Brief/Unelaborated Responses")

        # Rule D: Filler Words usage
        fillers_score = 0.0
        if filler_word_frequency > 0.15:
            score_points += 20.0
            fillers_score = 1.0
            contributing_factors.append("Excessive Speech Formulation Fillers")
        elif filler_word_frequency >= 0.08:
            score_points += 10.0
            fillers_score = 0.5
            contributing_factors.append("Elevated Speech Formulation Fillers")

        # Rule E: Word Repetitions
        repetitions_score = 0.0
        if repeated_word_frequency > 0.20:
            score_points += 15.0
            repetitions_score = 1.0
            contributing_factors.append("Clinically Significant Phrase/Word Repetitions")
        elif repeated_word_frequency >= 0.10:
            score_points += 8.0
            repetitions_score = 0.5
            contributing_factors.append("Elevated Phrase/Word Repetitions")

        # Rule F: Lexical Density / Diversity
        diversity_score = 0.0
        if lexical_density < 0.40:
            score_points += 10.0
            diversity_score = 1.0
            contributing_factors.append("Severe Lexical Diversity Simplification")
        elif lexical_density < 0.55:
            diversity_score = 0.4
            contributing_factors.append("Reduced Lexical Diversity")

        # Cap score between 0.0 and 100.0
        final_score = min(100.0, max(0.0, score_points))

        # 3. Categorize Risk
        if final_score < 30.0:
            risk_level = "LOW_RISK"
        elif final_score < 70.0:
            risk_level = "MEDIUM_RISK"
        else:
            risk_level = "HIGH_RISK"

        # 4. Compute overall assessment confidence
        completion_deduction = (3 - num_records) * 0.15
        assessment_confidence = max(0.1, min(1.0, avg_asr_confidence - completion_deduction))

        # 5. Build rich, formatted narrative clinical summary
        risk_label_str = risk_level.replace("_", " ").title()
        
        narrative = (
            "CLINICAL COGNITIVE SPEECH ASSESSMENT REPORT\n\n"
            "1. Temporal Flow & Speech Pacing:\n"
            f"The subject demonstrated an average speaking rate of {avg_wpm:.1f} WPM, which is classified as "
            f"{'within normal clinical limits' if avg_wpm >= 100 else 'moderately slowed vocal pacing' if avg_wpm >= 80 else 'severely bradyphasic speech flow'}. "
            f"Acoustic analysis registered a total of {total_pause_count} distinct formulation pauses across the session responses, with the longest formulation latency segment measuring {max_longest_pause:.1f}s. "
            f"This pause behavior is {'indicative of typical formulation phrasing' if max_longest_pause < 3.0 else 'suggestive of moderate word-retrieval latency' if max_longest_pause < 5.0 else 'suggestive of clinically significant cognitive-linguistic formulation delay'}.\n\n"
            "2. Lexical & Linguistic Characterization:\n"
            f"Lexical diversity (ratio of unique vocabulary tokens) was measured at {lexical_density*100:.1f}%, reflecting a "
            f"{'typical and varied vocabulary range' if lexical_density >= 0.55 else 'moderately simplified or restricted lexical diversity' if lexical_density >= 0.40 else 'highly simplified and repetitive vocabulary structure'}. "
            f"Word/phrase repetitions accounted for {repeated_word_frequency*100:.1f}% of the verbal output, indicating "
            f"{'minimal perseverative speech loops' if repeated_word_frequency < 0.1 else 'mildly elevated speech formulation repetitions' if repeated_word_frequency < 0.2 else 'clinically elevated perseverative speech phrasing'}. "
            f"Hesitation fillers (e.g. 'um', 'like', 'matlab', 'toh') comprised {filler_word_frequency*100:.1f}% of spoken words, reflecting "
            f"{'standard conversational filler distribution' if filler_word_frequency < 0.08 else 'moderately elevated formulation fillers' if filler_word_frequency < 0.15 else 'excessive formulation filler density, indicative of marked speech formulation hesitation'}.\n\n"
            "3. Clinical Diagnostic Impression:\n"
            f"The quantitative metric profile indicates a {risk_label_str} cognitive-linguistic risk level (Score: {final_score:.1f}/100.0). "
            f"{'No significant cognitive-acoustic or linguistic markers of concern were identified.' if risk_level == 'LOW_RISK' else 'Mild to moderate acoustic and linguistic formulations deviations are present, suggesting potential mild cognitive formulation delays. Recommend follow-up clinical testing.' if risk_level == 'MEDIUM_RISK' else 'Severe bradyphasia, extended silent pauses, and lexical formulation simplifications are present, indicating significant cognitive-linguistic formulation disruption. Clinical neurological evaluation is recommended.'}"
        )

        # Append medical disclaimer
        narrative += (
            "\n\nDISCLAIMER: This assessment is an engineering demonstration of voice analysis parameters "
            "and does NOT constitute a clinical or medical diagnosis. Please consult a qualified healthcare professional "
            "for formal medical evaluations."
        )

        # 6. Package everything into a JSON string
        explanation_data = {
            "summary": narrative,
            "confidence": assessment_confidence,
            "contributing_factors": contributing_factors,
            "breakdown": {
                "speaking_rate": speed_score,
                "pause_behavior": pause_score,
                "vocabulary_diversity": diversity_score,
                "repetition_frequency": repetitions_score,
                "filler_usage": fillers_score
            }
        }
        explanation_json = json.dumps(explanation_data)

        logger.info(f"Evaluation complete: Score={final_score:.1f}, Risk={risk_level}")
        return final_score, risk_level, explanation_json
