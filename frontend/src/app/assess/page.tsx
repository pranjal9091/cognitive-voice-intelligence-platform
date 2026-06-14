"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Clipboard, CheckCircle, AlertTriangle, ArrowRight, ArrowLeft, Send, Loader } from "lucide-react";
import AssessmentLayout from "../../components/AssessmentLayout";
import QuestionCard from "../../components/QuestionCard";
import { executeProcessingPipeline, ProcessorState } from "../../lib/assessmentProcessor";

interface RecordingState {
  status: "idle" | "recording" | "recorded";
  duration: number;
  blob: Blob | null;
  completed: boolean;
  fileSize?: number;
  mimeType?: string;
}

const QUESTIONS = [
  { number: 1, prompt: "Tell us about your morning routine." },
  { number: 2, prompt: "Describe a memorable event from the last week." },
  { number: 3, prompt: "Talk about your favourite festival or celebration." },
];

export default function SubjectAssessment() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [recordings, setRecordings] = useState<Record<number, RecordingState>>({
    1: { status: "idle", duration: 0, blob: null, completed: false },
    2: { status: "idle", duration: 0, blob: null, completed: false },
    3: { status: "idle", duration: 0, blob: null, completed: false },
  });

  const [submitting, setSubmitting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Pipeline Processing States
  const [pipelineState, setPipelineState] = useState<ProcessorState>({
    stage: "upload_q1",
    status: "idle",
    error: null,
    sessionId: null,
    uploadedFiles: {},
  });

  const handleStartRecording = (qNum: number) => {
    setRecordings((prev) => ({
      ...prev,
      [qNum]: {
        ...prev[qNum],
        status: "recording",
        duration: 0,
        blob: null,
        completed: false,
      },
    }));
  };

  const handleStopRecording = (qNum: number, duration: number, blob: Blob) => {
    setRecordings((prev) => ({
      ...prev,
      [qNum]: {
        status: "recorded",
        duration,
        blob,
        completed: true,
        fileSize: blob.size,
        mimeType: blob.type,
      },
    }));
  };

  const handleResetRecording = (qNum: number) => {
    setRecordings((prev) => ({
      ...prev,
      [qNum]: {
        status: "idle",
        duration: 0,
        blob: null,
        completed: false,
      },
    }));
  };

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleSubmit = async (resumingState?: ProcessorState) => {
    setSubmitting(true);
    const stateToUse = resumingState || (pipelineState.status === "error" ? pipelineState : {
      stage: "upload_q1" as const,
      status: "idle" as const,
      error: null,
      sessionId: null,
      uploadedFiles: {},
    });

    const recordingsBlobs = {
      1: recordings[1].blob,
      2: recordings[2].blob,
      3: recordings[3].blob,
    };

    try {
      await executeProcessingPipeline(
        recordingsBlobs,
        stateToUse,
        (updatedState) => {
          setPipelineState(updatedState);
          if (updatedState.sessionId) {
            setSessionId(updatedState.sessionId);
          }
          if (updatedState.status === "success" && updatedState.stage === "preparing") {
            router.push(`/session/${updatedState.sessionId}`);
          }
        }
      );
    } catch (err: any) {
      console.error("Pipeline submission failed:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyId = () => {
    if (!sessionId) return;
    navigator.clipboard.writeText(sessionId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Check if active question is answered to enable Next button
  const isCurrentStepAnswered = () => {
    if (currentStep === 4) return true;
    return recordings[currentStep].completed;
  };

  const allRecorded = recordings[1].completed && recordings[2].completed && recordings[3].completed;

  return (
    <AssessmentLayout currentStep={currentStep} totalSteps={4}>
      {currentStep <= 3 ? (
        /* Question workflow step */
        <div className="flex flex-col gap-6">
          <QuestionCard
            questionNumber={currentStep}
            prompt={QUESTIONS[currentStep - 1].prompt}
            recordingStatus={recordings[currentStep].status}
            duration={recordings[currentStep].duration}
            recordedBlob={recordings[currentStep].blob}
            onStartRecording={handleStartRecording}
            onStopRecording={handleStopRecording}
            onResetRecording={handleResetRecording}
          />

          {/* Navigation Controls */}
          <div className="flex justify-between items-center mt-2">
            <button
              onClick={handlePrev}
              disabled={currentStep === 1}
              className={`flex items-center gap-1 text-xs font-semibold px-4 py-2 border rounded-xl transition-all ${
                currentStep === 1
                  ? "bg-transparent border-slate-900 text-slate-700 cursor-not-allowed"
                  : "bg-slate-900 border-slate-800 text-slate-400 hover:text-white hover:bg-slate-850"
              }`}
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>

            <button
              onClick={handleNext}
              disabled={!isCurrentStepAnswered()}
              className={`flex items-center gap-1 text-xs font-bold px-5 py-2.5 rounded-xl transition-all ${
                isCurrentStepAnswered()
                  ? "bg-white text-slate-950 shadow-lg hover:opacity-90 cursor-pointer"
                  : "bg-slate-900 text-slate-600 border border-slate-900 cursor-not-allowed"
              }`}
            >
              <span>{currentStep === 3 ? "Review Answers" : "Next Question"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      ) : (
        /* Step 4: Final Review Screen & Submissions */
        <div className="flex flex-col gap-6">
          {pipelineState.status === "running" ? (
            /* Progress Experience */
            <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-slate-900 flex flex-col gap-6">
              <div className="flex flex-col gap-1.5">
                <h2 className="text-xl font-bold text-white tracking-tight">Processing Assessment...</h2>
                <p className="text-xs text-slate-450 font-medium">
                  {pipelineState.stage === "upload_q1" || pipelineState.stage === "upload_q2" || pipelineState.stage === "upload_q3"
                    ? "Uploading audio response files to server..."
                    : pipelineState.stage === "transcribe"
                    ? "Transcribing voice recording speech to text..."
                    : pipelineState.stage === "analyze"
                    ? "Extracting speech cadence, pauses, and vocabulary metrics..."
                    : pipelineState.stage === "score"
                    ? "Calculating cognitive risk scoring profile..."
                    : "Preparing your clinical assessment dashboard..."}
                </p>
              </div>

              {/* Progress indicators */}
              <div className="flex flex-col gap-3 py-2">
                {[
                  {
                    key: "upload",
                    label: "Uploading audio responses",
                    isActive: ["upload_q1", "upload_q2", "upload_q3"].includes(pipelineState.stage),
                    isCompleted: !!(pipelineState.uploadedFiles[1] && pipelineState.uploadedFiles[2] && pipelineState.uploadedFiles[3]),
                  },
                  {
                    key: "transcribe",
                    label: "Transcribing speech",
                    isActive: pipelineState.stage === "transcribe",
                    isCompleted: ["analyze", "score", "preparing"].includes(pipelineState.stage),
                  },
                  {
                    key: "analyze",
                    label: "Analyzing language metrics",
                    isActive: pipelineState.stage === "analyze",
                    isCompleted: ["score", "preparing"].includes(pipelineState.stage),
                  },
                  {
                    key: "score",
                    label: "Calculating cognitive score",
                    isActive: pipelineState.stage === "score",
                    isCompleted: pipelineState.stage === "preparing",
                  },
                  {
                    key: "preparing",
                    label: "Preparing dashboard",
                    isActive: pipelineState.stage === "preparing",
                    isCompleted: false, // Redirect happens immediately on success
                  },
                ].map((step) => {
                  return (
                    <div
                      key={step.key}
                      className="p-4 bg-slate-950/60 border border-slate-900/60 rounded-2xl flex justify-between items-center gap-4"
                    >
                      <div className="flex flex-col gap-1">
                        <p className="text-xs text-slate-300 font-semibold">{step.label}</p>
                      </div>
                      
                      {step.isCompleted ? (
                        <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950/20 border border-emerald-900/30 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" />
                          <span>Complete</span>
                        </span>
                      ) : step.isActive ? (
                        <span className="text-[10px] font-semibold text-cyan-400 bg-cyan-950/20 border border-cyan-800/30 px-2.5 py-0.5 rounded-full flex items-center gap-1.5">
                          <Loader className="w-3 h-3 text-cyan-400 animate-spin" />
                          <span>Processing...</span>
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-slate-500 bg-slate-950 border border-slate-900 px-2.5 py-0.5 rounded-full">
                          Pending
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : pipelineState.status === "error" ? (
            /* Error Panel */
            <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-rose-950/30 flex flex-col gap-6">
              <div className="flex flex-col items-center text-center gap-3">
                <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-rose-500" />
                </div>
                <h2 className="text-lg font-bold text-white">Pipeline Interrupted</h2>
                <p className="text-xs text-rose-300/80 leading-relaxed max-w-sm">
                  Failed during <strong>{
                    ["upload_q1", "upload_q2", "upload_q3"].includes(pipelineState.stage)
                      ? "Audio Upload"
                      : pipelineState.stage === "transcribe"
                      ? "Speech Transcription"
                      : pipelineState.stage === "analyze"
                      ? "Metrics Analysis"
                      : pipelineState.stage === "score"
                      ? "Cognitive Risk Scoring"
                      : "Dashboard Preparation"
                  }</strong> stage.
                </p>
                <div className="bg-slate-950/80 border border-rose-950/30 p-4 rounded-xl text-left w-full">
                  <p className="font-mono text-[11px] text-rose-400 break-words leading-normal">
                    {pipelineState.error}
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => setPipelineState({
                    stage: "upload_q1",
                    status: "idle",
                    error: null,
                    sessionId: null,
                    uploadedFiles: {},
                  })}
                  className="flex-1 py-3 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-bold rounded-xl transition-all"
                >
                  Back to Review
                </button>
                <button
                  onClick={() => handleSubmit(pipelineState)}
                  className="flex-1 py-3 bg-gradient-to-r from-cyan-500 to-indigo-500 text-white font-bold text-xs rounded-xl transition-all shadow-lg shadow-indigo-500/10 hover:opacity-90"
                >
                  Retry Stage
                </button>
              </div>
            </div>
          ) : (
            /* Review Screen */
            <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-slate-900 flex flex-col gap-5">
              <div className="flex flex-col gap-1.5">
                <h2 className="text-xl font-bold text-white tracking-tight">Review Voice Assessment</h2>
                <p className="text-xs text-slate-450 leading-relaxed">
                  Confirm your response clips are complete before sending the recordings for cognitive analysis.
                </p>
              </div>

              {/* Checklist */}
              <div className="flex flex-col gap-3 py-2">
                {QUESTIONS.map((q) => {
                  const recorded = recordings[q.number].completed;
                  const dur = recordings[q.number].duration;
                  const sizeKB = recordings[q.number].fileSize
                    ? (recordings[q.number].fileSize! / 1024).toFixed(1) + " KB"
                    : "";

                  return (
                    <div
                      key={q.number}
                      className="p-4 bg-slate-950/60 border border-slate-900/60 rounded-2xl flex justify-between items-center gap-4"
                    >
                      <div className="flex flex-col gap-1">
                        <span className="text-[9px] uppercase tracking-wider font-extrabold text-slate-500">
                          Question {q.number}
                        </span>
                        <p className="text-xs text-slate-300 font-medium line-clamp-1">{q.prompt}</p>
                      </div>
                      {recorded ? (
                        <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950/20 border border-emerald-900/30 px-2.5 py-0.5 rounded-full shrink-0 flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" />
                          <span>Recorded ({dur.toFixed(1)}s, {sizeKB})</span>
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-rose-400 bg-rose-950/20 border border-rose-900/30 px-2.5 py-0.5 rounded-full shrink-0 flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5 animate-pulse" />
                          <span>Pending</span>
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Submit Control */}
              <button
                onClick={() => handleSubmit()}
                disabled={!allRecorded || submitting}
                className={`w-full py-3.5 rounded-2xl font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                  allRecorded && !submitting
                    ? "bg-gradient-to-r from-cyan-500 to-indigo-500 text-white shadow-lg hover:opacity-90"
                    : "bg-slate-900 text-slate-600 border border-slate-900 cursor-not-allowed"
                }`}
              >
                <Send className="w-4 h-4" />
                <span>Submit Responses</span>
              </button>
            </div>
          )}

          {/* Navigation Controls (Visible in review page if not uploading/success) */}
          {pipelineState.status === "idle" && (
            <div className="flex justify-start">
              <button
                onClick={handlePrev}
                className="flex items-center gap-1 text-xs font-semibold px-4 py-2 border border-slate-800 bg-slate-900 text-slate-400 hover:text-white rounded-xl transition-all"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Go Back</span>
              </button>
            </div>
          )}

        </div>
      )}
    </AssessmentLayout>
  );
}
