export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  probability: number;
}

export interface TranscriptResponse {
  question_number: number;
  transcript_text: string;
  duration: number;
  words: WordTimestamp[];
  confidence: number;
  language?: string;
}

export interface TemporalMetrics {
  total_speech_duration: number;
  average_response_duration: number;
  words_per_minute: number;
  pause_count: number;
  longest_pause_seconds: number;
}

export interface RepeatedWord {
  [word: string]: number;
}

export interface LinguisticMetrics {
  word_count: number;
  unique_word_count: number;
  repeated_words: RepeatedWord[];
  filler_words_count: number;
  filler_words_breakdown: Record<string, number>;
}

export interface RiskAssessment {
  score: number; // 0.0 to 1.0
  classification: string; // "LOW_RISK" | "MEDIUM_RISK" | "HIGH_RISK"
  rationale: string;
  created_at?: string;
  confidence: number;
  contributing_factors: string[];
  breakdown: Record<string, number>;
}

export interface AnalyticsContainer {
  temporal_metrics: TemporalMetrics;
  linguistic_metrics: LinguisticMetrics;
}

export interface SessionResultResponse {
  session_id: string;
  status: string; // "initialized" | "uploaded" | "transcribed" | "analyzed" | "scored"
  subject_reference: string;
  clinician_id: string | null;
  created_at: string;
  completed_at: string | null;
  transcriptions: TranscriptResponse[];
  analytics: AnalyticsContainer | null;
  risk_assessment: RiskAssessment | null;
}

export interface SessionListItem {
  session_id: string;
  subject_reference: string;
  created_at: string | null;
  status: string;
  risk_classification: string;
}

export interface SessionListResponse {
  total_count: number;
  items: SessionListItem[];
}
