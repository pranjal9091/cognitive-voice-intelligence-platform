"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Clock, Activity, MessageSquare, AlertCircle, ShieldAlert, Award, FileText, Calendar, User, CheckCircle, Loader } from "lucide-react";
import { fetchSessionResults } from "../../services/api";
import { SessionResultResponse } from "../../types";

const questionPrompts: Record<number, string> = {
  1: "Tell us about your morning routine.",
  2: "Describe a memorable event from the last week.",
  3: "Talk about your favourite festival or celebration."
};

const highlightFillerWords = (text: string) => {
  if (!text) return "No transcript available.";
  const fillerRegex = /\b(um|uh|like|actually|basically|matlab|toh|ya|ye|you know)\b/gi;
  const parts = text.split(fillerRegex);
  
  return parts.map((part, idx) => {
    if (idx % 2 === 1) {
      return (
        <span
          key={idx}
          className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-bold underline decoration-dotted"
          title="Detected formulation filler word"
        >
          {part}
        </span>
      );
    }
    return part;
  });
};

const domainLabels: Record<string, string> = {
  speaking_rate: "Speaking Speed pacing",
  pause_behavior: "Pauses & Latency",
  vocabulary_diversity: "Vocabulary Diversity",
  repetition_frequency: "Speech Repetitions",
  filler_usage: "Hesitations & Fillers"
};

export default function SessionDashboard() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<number | "combined">(1);

  useEffect(() => {
    async function loadSession() {
      if (!sessionId) return;
      try {
        setLoading(true);
        const data = await fetchSessionResults(sessionId);
        if (!data) {
          setError(`Session ${sessionId} was not found.`);
        } else {
          setSession(data);
          setError(null);
        }
      } catch (err: any) {
        console.error(err);
        setError("Failed to fetch session assessment details. Verify your backend service state.");
      } finally {
        setLoading(false);
      }
    }
    loadSession();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-4">
        <Loader className="w-10 h-10 text-cyan-400 animate-spin" />
        <p className="text-slate-400 text-sm font-medium">Retrieving cognitive voice dashboard...</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 text-center">
        <div className="glass-panel p-8 rounded-2xl max-w-md w-full border border-rose-950/30 flex flex-col items-center gap-4">
          <ShieldAlert className="w-12 h-12 text-rose-500" />
          <h2 className="text-xl font-bold text-white">Assessment Load Failed</h2>
          <p className="text-slate-400 text-sm">{error || "The requested session does not exist."}</p>
          <button
            onClick={() => router.push("/")}
            className="mt-2 w-full py-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Portal</span>
          </button>
        </div>
      </div>
    );
  }

  const hasAnalytics = session.analytics !== null;
  const hasRisk = session.risk_assessment !== null;

  // Extract metrics variables
  const temporal = session.analytics?.temporal_metrics;
  const linguistic = session.analytics?.linguistic_metrics;
  const risk = session.risk_assessment;

  // Calculations for frequencies
  const repeatedCount = linguistic?.repeated_words.reduce((sum, item) => {
    return sum + Object.values(item).reduce((a, b) => a + b, 0);
  }, 0) || 0;
  const repeatedFreq = linguistic && linguistic.word_count > 0 
    ? (repeatedCount / linguistic.word_count) * 100 
    : 0;
    
  const fillerFreq = linguistic && linguistic.word_count > 0 
    ? (linguistic.filler_words_count / linguistic.word_count) * 100 
    : 0;

  // Visual calculations for radial risk score
  const score = risk ? risk.score : 0; // 0.0 to 1.0
  const percentageScore = Math.round(score * 100);
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score * circumference);

  const getRiskBadgeColor = (level: string) => {
    switch (level.toUpperCase()) {
      case "HIGH_RISK":
        return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      case "MEDIUM_RISK":
        return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      case "LOW_RISK":
        return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border border-slate-500/20";
    }
  };

  const getRiskMeterColor = (level: string) => {
    switch (level.toUpperCase()) {
      case "HIGH_RISK":
        return "stroke-rose-500";
      case "MEDIUM_RISK":
        return "stroke-amber-500";
      default:
        return "stroke-emerald-400";
    }
  };

  const getBreakdownColor = (val: number) => {
    if (val >= 0.7) return "bg-rose-500";
    if (val >= 0.3) return "bg-amber-500";
    return "bg-emerald-500";
  };

  // Extract triggers for the AI Summary card
  const getAISummary = () => {
    if (!risk) return "Session assessment calculations are pending.";
    const explanation = risk.rationale;
    const triggerIndex = explanation.indexOf("DISCLAIMER:");
    if (triggerIndex > 0) {
      return explanation.substring(0, triggerIndex).trim();
    }
    return explanation;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative overflow-hidden pb-12">
      {/* Background radial glow */}
      <div className="absolute top-[-300px] right-[-100px] w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Header bar */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Sessions</span>
          </button>
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900/50 px-3 py-1 rounded-full border border-slate-800">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>ID: {session.subject_reference}</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl w-full mx-auto px-6 py-8 flex flex-col gap-6 z-10">
        {/* Top Session Details Row */}
        <section className="flex flex-col md:flex-row justify-between items-start md:items-center p-6 bg-slate-900/20 border border-slate-900 rounded-2xl gap-4">
          <div className="flex flex-col gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-cyan-400" />
              <span>Assessment Dashboard</span>
            </h2>
            <p className="text-xs text-slate-500 font-mono select-all break-all">{session.session_id}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 px-3 py-1 bg-slate-950/60 rounded-xl border border-slate-900">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              <span>
                {new Date(session.created_at).toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </span>
            </div>
            <span className={`text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full ${getRiskBadgeColor(session.status)}`}>
              {session.status}
            </span>
          </div>
        </section>

        {/* Dashboard Grid */}
        {session.status !== "scored" && session.status !== "analyzed" ? (
          <section className="glass-panel p-10 rounded-3xl border border-slate-900 text-center flex flex-col items-center gap-4 py-20">
            <AlertCircle className="w-12 h-12 text-amber-500" />
            <h3 className="text-lg font-bold text-white">Assessment Incomplete</h3>
            <p className="text-slate-400 text-sm max-w-md">
              This session is currently in state <span className="font-mono text-cyan-400">"{session.status}"</span>.
              Please execute transcription and run the analytics / scoring pipeline on the backend to populate the dashboard metrics.
            </p>
          </section>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* LEFT COLUMN: Risk Score & Summary */}
            <div className="lg:col-span-1 flex flex-col gap-6">
              {/* Cognitive Risk assessment Card */}
              <div className="glass-panel p-6 rounded-3xl border border-slate-900 flex flex-col items-center text-center gap-6 relative overflow-hidden">
                <div className="absolute top-3 left-4 text-xs font-semibold text-slate-400 flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Cognitive Assessment</span>
                </div>

                {/* Circular progress meter */}
                <div className="relative w-40 h-40 mt-6 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="80"
                      cy="80"
                      r={radius}
                      className="stroke-slate-900 fill-none"
                      strokeWidth="10"
                    />
                    <circle
                      cx="80"
                      cy="80"
                      r={radius}
                      className={`fill-none transition-all duration-1000 ease-out ${getRiskMeterColor(risk?.classification || "LOW_RISK")}`}
                      strokeWidth="10"
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center">
                    <span className="text-3xl font-extrabold text-white tracking-tight">{percentageScore}%</span>
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Risk Index</span>
                  </div>
                </div>

                <div className="w-full flex flex-col gap-4">
                  {/* Risk Profile Row */}
                  <div className="flex justify-between items-center px-4 py-2 bg-slate-950/40 rounded-2xl border border-slate-900/60">
                    <span className="text-xs text-slate-500">Risk Profile</span>
                    <span className={`text-xs uppercase tracking-wider px-2 py-0.5 rounded-full font-bold ${getRiskBadgeColor(risk?.classification || "LOW_RISK")}`}>
                      {(risk?.classification || "LOW_RISK").replace("_", " ")}
                    </span>
                  </div>

                  {/* Confidence progress bar */}
                  <div className="w-full bg-slate-950/40 p-4 rounded-2xl border border-slate-900 flex flex-col gap-2 text-left">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-slate-500 font-semibold uppercase tracking-wider">Assessment Confidence</span>
                      <span className="text-white font-bold">{Math.round((risk?.confidence || 1.0) * 100)}%</span>
                    </div>
                    <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-900">
                      <div className="h-full bg-indigo-500" style={{ width: `${(risk?.confidence || 1.0) * 100}%` }} />
                    </div>
                    <p className="text-[9px] text-slate-500 leading-normal">
                      Reliability score adjusted for formulation completions.
                    </p>
                  </div>

                  {/* Contributing Factors Badges */}
                  <div className="w-full flex flex-col gap-2 text-left bg-slate-950/40 p-4 rounded-2xl border border-slate-900">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Primary Contributing Factors</span>
                    {!risk?.contributing_factors || risk.contributing_factors.length === 0 ? (
                      <span className="text-xs text-slate-400 italic">No abnormal vocal deviations identified.</span>
                    ) : (
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {risk.contributing_factors.map((factor, idx) => (
                          <span key={idx} className="text-[9px] bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-0.5 rounded-full font-medium">
                            {factor}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Visual Risk Breakdown progress bars */}
                  <div className="w-full flex flex-col gap-3 text-left bg-slate-950/40 p-4 rounded-2xl border border-slate-900">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Visual Risk Breakdown</span>
                    {risk?.breakdown && Object.entries(risk.breakdown).map(([key, val]) => (
                      <div key={key} className="flex flex-col gap-1">
                        <div className="flex justify-between items-center text-[10px]">
                          <span className="text-slate-400">{domainLabels[key] || key}</span>
                          <span className="text-slate-500 font-bold">{Math.round(val * 100)}%</span>
                        </div>
                        <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-900">
                          <div className={`h-full ${getBreakdownColor(val)}`} style={{ width: `${val * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Disclaimer box */}
                <div className="p-3.5 bg-rose-950/10 rounded-2xl border border-rose-950/20 text-left flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                  <p className="text-[10px] text-rose-300/80 leading-relaxed">
                    Disclaimer: This is an engineering demonstration of voice analysis parameters and does not constitute a clinical or medical diagnosis.
                  </p>
                </div>
              </div>

              {/* AI Clinical Summary Card */}
              <div className="glass-panel p-6 rounded-3xl border border-slate-900 flex flex-col gap-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-1.5 border-b border-slate-900 pb-2">
                  <Award className="w-4.5 h-4.5 text-cyan-400" />
                  <span>AI Clinical Narrative Report</span>
                </h3>
                <div className="bg-slate-950/50 border border-slate-900 p-5 rounded-2xl text-[11px] text-slate-300 leading-relaxed whitespace-pre-line font-mono select-text border-l-2 border-l-cyan-400">
                  {getAISummary()}
                </div>
              </div>
            </div>

            {/* RIGHT COLUMN: Voice Metrics & Transcripts */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              {/* Voice Metrics Grid */}
              <div className="glass-panel p-6 rounded-3xl border border-slate-900 flex flex-col gap-4">
                <h3 className="text-sm font-bold text-white tracking-tight">Speech & Linguistic Metrics</h3>
                
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {/* Speech Duration */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Speech Duration</span>
                    <span className="text-lg font-bold text-white tracking-tight">{temporal?.total_speech_duration.toFixed(1)}s</span>
                  </div>
                  
                  {/* Avg Response Duration */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Avg Response</span>
                    <span className="text-lg font-bold text-white tracking-tight">{temporal?.average_response_duration.toFixed(1)}s</span>
                  </div>

                  {/* Words Per Minute */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">WPM (Speed)</span>
                    <span className="text-lg font-bold text-gradient-cyan tracking-tight">{temporal?.words_per_minute.toFixed(1)}</span>
                  </div>

                  {/* Pause Count */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Pause Count</span>
                    <span className="text-lg font-bold text-white tracking-tight">{temporal?.pause_count}</span>
                  </div>

                  {/* Longest Pause */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Longest Pause</span>
                    <span className="text-lg font-bold text-white tracking-tight">{temporal?.longest_pause_seconds.toFixed(1)}s</span>
                  </div>

                  {/* Word Count */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Total Spoken Words</span>
                    <span className="text-lg font-bold text-white tracking-tight">{linguistic?.word_count}</span>
                  </div>

                  {/* Unique Words */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Unique Words</span>
                    <span className="text-lg font-bold text-white tracking-tight">{linguistic?.unique_word_count}</span>
                  </div>

                  {/* Repeated Word Freq */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Repetition Freq</span>
                    <span className="text-lg font-bold text-white tracking-tight">{repeatedFreq.toFixed(1)}%</span>
                  </div>

                  {/* Filler Word Freq */}
                  <div className="p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Filler Freq</span>
                    <span className="text-lg font-bold text-gradient-indigo tracking-tight">{fillerFreq.toFixed(1)}%</span>
                  </div>
                </div>
              </div>

              {/* Transcripts Section */}
              <div className="glass-panel p-6 rounded-3xl border border-slate-900 flex flex-col gap-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-1.5">
                    <MessageSquare className="w-4 h-4 text-cyan-400" />
                    <span>Transcripts Detail View</span>
                  </h3>
                  
                  {/* Tab list */}
                  <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-900 text-xs">
                    {[1, 2, 3].map((num) => (
                      <button
                        key={num}
                        onClick={() => setActiveTab(num)}
                        className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                          activeTab === num ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-300"
                        }`}
                      >
                        Q{num}
                      </button>
                    ))}
                    <button
                      onClick={() => setActiveTab("combined")}
                      className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                        activeTab === "combined" ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-300"
                      }`}
                    >
                      Combined
                    </button>
                  </div>
                </div>

                {/* Tab content view */}
                <div className="bg-slate-950/40 border border-slate-900/60 p-5 rounded-2xl min-h-[160px] flex flex-col justify-between">
                  <div>
                    {activeTab !== "combined" && (
                      <h4 className="text-xs font-bold text-slate-400 mb-3 border-b border-slate-900/40 pb-2">
                        Prompt: <span className="text-slate-300 font-medium italic">"{questionPrompts[activeTab as number]}"</span>
                      </h4>
                    )}
                    <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap select-text">
                      {activeTab === "combined"
                        ? highlightFillerWords(session.transcriptions.map((t) => t.transcript_text).join(" "))
                        : highlightFillerWords(session.transcriptions.find((t) => t.question_number === activeTab)?.transcript_text || `Question ${activeTab} has no transcription registered.`)}
                    </p>
                  </div>
                  
                  {activeTab !== "combined" && session.transcriptions.find((t) => t.question_number === activeTab) && (
                    <div className="mt-6 pt-3 border-t border-slate-900/60 flex flex-wrap gap-4 justify-between text-[11px] text-slate-500 font-medium">
                      <span>Duration: {session.transcriptions.find((t) => t.question_number === activeTab)?.duration.toFixed(1)}s</span>
                      <span className="capitalize">Language: {session.transcriptions.find((t) => t.question_number === activeTab)?.language === 'hi' ? 'Hindi / Hinglish' : session.transcriptions.find((t) => t.question_number === activeTab)?.language === 'en' ? 'English' : session.transcriptions.find((t) => t.question_number === activeTab)?.language || 'N/A'}</span>
                      <span>ASR Confidence: {((session.transcriptions.find((t) => t.question_number === activeTab)?.confidence || 1) * 100).toFixed(0)}%</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
