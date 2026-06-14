const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchSessions(limit: number = 20, offset: number = 0) {
  const res = await fetch(`${API_URL}/api/v1/sessions?limit=${limit}&offset=${offset}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch sessions: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSessionResults(sessionId: string) {
  const res = await fetch(`${API_URL}/api/v1/sessions/${sessionId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 404) {
      return null;
    }
    throw new Error(`Failed to fetch session results: ${res.statusText}`);
  }
  return res.json();
}

export interface UploadResponse {
  session_id: string;
  status: string;
  filename: string;
  size: number;
}

export async function uploadAudio(
  file: Blob,
  questionNumber: number,
  sessionId?: string
): Promise<UploadResponse> {
  const formData = new FormData();
  
  // Determine file extension from MIME type
  const mimeType = file.type || "audio/webm";
  let extension = "webm";
  if (mimeType.includes("mp4") || mimeType.includes("m4a") || mimeType.includes("x-m4a")) {
    extension = "m4a";
  } else if (mimeType.includes("wav") || mimeType.includes("x-wav")) {
    extension = "wav";
  } else if (mimeType.includes("mpeg") || mimeType.includes("mp3")) {
    extension = "mp3";
  }
  
  const filename = `question_${questionNumber}.${extension}`;
  formData.append("audio_file", file, filename);
  
  if (sessionId) {
    formData.append("session_id", sessionId);
  }
  formData.append("question_number", questionNumber.toString());

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Upload failed for Q${questionNumber}: ${res.statusText}. Details: ${errorText}`);
  }
  return res.json();
}

export async function transcribeSession(sessionId: string): Promise<any> {
  const res = await fetch(`${API_URL}/transcribe`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Transcription failed: ${res.statusText}. Details: ${errorText}`);
  }
  return res.json();
}

export async function analyzeSession(sessionId: string): Promise<any> {
  const res = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Analysis failed: ${res.statusText}. Details: ${errorText}`);
  }
  return res.json();
}

export async function scoreSession(sessionId: string): Promise<any> {
  const res = await fetch(`${API_URL}/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Scoring failed: ${res.statusText}. Details: ${errorText}`);
  }
  return res.json();
}

