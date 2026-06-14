import { uploadAudio, transcribeSession, analyzeSession, scoreSession } from "../app/services/api";

export type ProcessingStage =
  | "upload_q1"
  | "upload_q2"
  | "upload_q3"
  | "transcribe"
  | "analyze"
  | "score"
  | "preparing";

export interface ProcessorState {
  stage: ProcessingStage;
  status: "idle" | "running" | "success" | "error";
  error: string | null;
  sessionId: string | null;
  uploadedFiles: Record<number, string>;
}

export async function executeProcessingPipeline(
  recordings: Record<number, Blob | null>,
  currentState: ProcessorState,
  onStateChange: (state: ProcessorState) => void
): Promise<void> {
  let { stage, sessionId, uploadedFiles } = { ...currentState };

  // Helper to update state and call callback
  const updateState = (
    nextStage: ProcessingStage,
    status: "idle" | "running" | "success" | "error",
    error: string | null = null
  ) => {
    stage = nextStage;
    currentState = {
      stage,
      status,
      error,
      sessionId,
      uploadedFiles: { ...uploadedFiles },
    };
    onStateChange(currentState);
  };

  try {
    // 1. Upload Q1
    if (!uploadedFiles[1]) {
      updateState("upload_q1", "running");
      const blob = recordings[1];
      if (!blob) throw new Error("Question 1 recording is missing.");
      const res = await uploadAudio(blob, 1);
      sessionId = res.session_id;
      uploadedFiles[1] = res.filename;
    }

    // 2. Upload Q2
    if (!uploadedFiles[2]) {
      updateState("upload_q2", "running");
      const blob = recordings[2];
      if (!blob) throw new Error("Question 2 recording is missing.");
      if (!sessionId) throw new Error("Session ID is missing during Question 2 upload.");
      const res = await uploadAudio(blob, 2, sessionId);
      uploadedFiles[2] = res.filename;
    }

    // 3. Upload Q3
    if (!uploadedFiles[3]) {
      updateState("upload_q3", "running");
      const blob = recordings[3];
      if (!blob) throw new Error("Question 3 recording is missing.");
      if (!sessionId) throw new Error("Session ID is missing during Question 3 upload.");
      const res = await uploadAudio(blob, 3, sessionId);
      uploadedFiles[3] = res.filename;
    }

    // 4. Transcribe
    if (
      stage === "upload_q3" ||
      stage === "transcribe" ||
      stage === "upload_q1" ||
      stage === "upload_q2" ||
      !stage
    ) {
      updateState("transcribe", "running");
      if (!sessionId) throw new Error("Session ID is missing during transcription.");
      await transcribeSession(sessionId);
      stage = "transcribe";
    }

    // 5. Analyze
    if (stage === "transcribe" || stage === "analyze") {
      updateState("analyze", "running");
      if (!sessionId) throw new Error("Session ID is missing during analysis.");
      await analyzeSession(sessionId);
      stage = "analyze";
    }

    // 6. Score
    if (stage === "analyze" || stage === "score") {
      updateState("score", "running");
      if (!sessionId) throw new Error("Session ID is missing during scoring.");
      await scoreSession(sessionId);
      stage = "score";
    }

    // 7. Preparing dashboard
    updateState("preparing", "success");
  } catch (err: any) {
    console.error("Pipeline execution failed at stage:", stage, err);
    updateState(stage, "error", err.message || "An unexpected error occurred.");
  }
}
