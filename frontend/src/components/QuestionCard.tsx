import React, { useState, useEffect, useRef } from "react";
import { Mic, Square, Play, RotateCcw, AlertCircle, CheckCircle2, Circle } from "lucide-react";

interface QuestionCardProps {
  questionNumber: number;
  prompt: string;
  recordingStatus: "idle" | "recording" | "recorded";
  duration: number;
  recordedBlob: Blob | null;
  onStartRecording: (qNum: number) => void;
  onStopRecording: (qNum: number, duration: number, blob: Blob) => void;
  onResetRecording: (qNum: number) => void;
}

export default function QuestionCard({
  questionNumber,
  prompt,
  recordingStatus,
  duration,
  recordedBlob,
  onStartRecording,
  onStopRecording,
  onResetRecording,
}: QuestionCardProps) {
  const [seconds, setSeconds] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const getSupportedMimeType = () => {
    if (typeof window === "undefined" || !window.MediaRecorder) return "";
    const types = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
      "audio/mp4",
      "audio/wav",
    ];
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    return "";
  };

  // Synchronize local timer with external state and clean up resources
  useEffect(() => {
    setPermissionError(null);
    setSeconds(duration);
    setIsPlaying(false);

    if (recordingStatus === "recording") {
      setSeconds(0);
      timerRef.current = setInterval(() => {
        setSeconds((prev) => prev + 0.1);
      }, 100);
    } else if (recordingStatus === "recorded") {
      setSeconds(duration);
      if (timerRef.current) clearInterval(timerRef.current);
    } else {
      setSeconds(0);
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [recordingStatus, duration, questionNumber]);

  // Clean up media streams and players on unmount
  useEffect(() => {
    return () => {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const handleStart = async () => {
    try {
      setPermissionError(null);
      
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      streamRef.current = stream;
      
      const mimeType = getSupportedMimeType();
      const options = mimeType ? { mimeType } : undefined;
      
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      const startTime = Date.now();
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType || "audio/webm" });
        const finalDuration = (Date.now() - startTime) / 1000;
        onStopRecording(questionNumber, finalDuration, audioBlob);
        
        // Stop all tracks to turn off recording indicator light
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }
      };
      
      mediaRecorder.start();
      onStartRecording(questionNumber);
    } catch (err: any) {
      console.error("Microphone access failed", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setPermissionError("Microphone access was denied. Please enable microphone permissions in your browser settings.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setPermissionError("No microphone found on your device. Please connect a microphone and try again.");
      } else {
        setPermissionError(`Microphone error: ${err.message || "Unknown error"}`);
      }
    }
  };

  const handleStop = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) clearInterval(timerRef.current);
  };

  const handlePlay = () => {
    if (!recordedBlob || isPlaying) return;
    
    // Stop any existing playback
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }
    
    const url = URL.createObjectURL(recordedBlob);
    const player = new Audio(url);
    audioPlayerRef.current = player;
    
    player.onplay = () => {
      setIsPlaying(true);
      setSeconds(0);
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        setSeconds(player.currentTime);
      }, 100);
    };
    
    player.onended = () => {
      setIsPlaying(false);
      setSeconds(duration);
      if (timerRef.current) clearInterval(timerRef.current);
    };
    
    player.onerror = (e) => {
      console.error("Audio playback error:", e);
      setIsPlaying(false);
      setSeconds(duration);
      if (timerRef.current) clearInterval(timerRef.current);
    };
    
    player.play().catch((err) => {
      console.error("Failed to play audio:", err);
      setIsPlaying(false);
      setSeconds(duration);
      if (timerRef.current) clearInterval(timerRef.current);
    });
  };

  const handleReset = () => {
    // Stop playing audio
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current = null;
    }
    // Stop recorder if active
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    // Stop stream if active
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setSeconds(0);
    setIsPlaying(false);
    onResetRecording(questionNumber);
  };

  const formatTime = (time: number) => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    const tenths = Math.floor((time * 10) % 10);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}.${tenths}`;
  };

  return (
    <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-slate-900 flex flex-col gap-6 w-full relative overflow-hidden transition-all duration-300">
      {/* Question Badge Header */}
      <div className="flex justify-between items-center">
        <span className="text-[10px] uppercase tracking-widest font-extrabold text-cyan-400 bg-cyan-950/30 border border-cyan-800/30 px-3 py-1 rounded-full">
          Prompt {questionNumber} of 3
        </span>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          {recordingStatus === "recorded" ? (
            <span className="flex items-center gap-1 text-emerald-400 font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              <span>Answer Captured</span>
            </span>
          ) : recordingStatus === "recording" ? (
            <span className="flex items-center gap-1.5 text-rose-400 font-semibold animate-pulse">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              <span>Recording active</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-slate-500 font-medium">
              <Circle className="w-2.5 h-2.5" />
              <span>Ready</span>
            </span>
          )}
        </div>
      </div>

      {/* Prompts Text */}
      <div className="flex flex-col gap-2">
        <h3 className="text-lg sm:text-xl font-bold text-white leading-snug tracking-tight">
          {prompt}
        </h3>
        <p className="text-xs text-slate-400 leading-relaxed">
          Please respond verbally. Speak clearly into your device's microphone.
        </p>
      </div>

      {/* Recording sandbox */}
      <div className="bg-slate-950/60 border border-slate-900/60 p-8 rounded-2xl flex flex-col items-center justify-center gap-6 relative min-h-[200px]">
        {/* Timer display */}
        <div className="text-3xl font-mono font-bold tracking-wider text-white select-none">
          {formatTime(seconds)}
        </div>

        {/* Visualizer animation during active recording */}
        {recordingStatus === "recording" && (
          <div className="flex items-center justify-center gap-1 h-8">
            {[...Array(6)].map((_, i) => (
              <span
                key={i}
                className="w-1 bg-rose-500 rounded-full animate-bounce"
                style={{
                  height: `${Math.max(15, Math.sin(i + seconds * 5) * 32)}px`,
                  animationDelay: `${i * 0.1}s`,
                  animationDuration: "0.6s"
                }}
              />
            ))}
          </div>
        )}

        {/* Playback animation during play */}
        {isPlaying && (
          <div className="flex items-center justify-center gap-1 h-8">
            {[...Array(6)].map((_, i) => (
              <span
                key={i}
                className="w-1 bg-cyan-400 rounded-full animate-pulse"
                style={{
                  height: `${Math.max(10, Math.cos(i + seconds * 3) * 20)}px`,
                  animationDelay: `${i * 0.15}s`
                }}
              />
            ))}
          </div>
        )}

        {/* Dynamic Controls Layout */}
        <div className="flex items-center justify-center gap-6">
          {recordingStatus === "idle" && (
            <button
              onClick={handleStart}
              className="w-16 h-16 rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-500 hover:opacity-90 transition-all flex items-center justify-center shadow-lg shadow-indigo-500/10 group ring-4 ring-indigo-500/15"
            >
              <Mic className="w-7 h-7 text-white group-hover:scale-105 transition-transform" />
            </button>
          )}

          {recordingStatus === "recording" && (
            <button
              onClick={handleStop}
              className="w-16 h-16 rounded-full bg-rose-600 hover:bg-rose-500 transition-colors flex items-center justify-center shadow-lg shadow-rose-500/20 ring-4 ring-rose-500/15"
            >
              <Square className="w-6 h-6 text-white animate-pulse" />
            </button>
          )}

          {recordingStatus === "recorded" && (
            <div className="flex items-center gap-4">
              {/* Play Button */}
              <button
                onClick={handlePlay}
                disabled={isPlaying}
                className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl border transition-all ${
                  isPlaying
                    ? "bg-cyan-500/10 border-cyan-500/20 text-cyan-400 cursor-not-allowed"
                    : "bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-white"
                }`}
              >
                <Play className="w-3.5 h-3.5" />
                <span>{isPlaying ? "Playing..." : "Play Answer"}</span>
              </button>

              {/* Reset / Re-record Button */}
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-white rounded-xl transition-all"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Re-Record</span>
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Warning Box / Info Box */}
      {recordingStatus === "idle" && !permissionError && (
        <div className="p-3 bg-slate-950/30 rounded-xl border border-slate-900 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-cyan-500 mt-0.5 shrink-0" />
          <p className="text-[10px] text-slate-400 leading-relaxed">
            Note: This session is configured to capture real microphone audio. Ensure your recording device is properly connected.
          </p>
        </div>
      )}

      {/* Permission Error display */}
      {permissionError && (
        <div className="p-3.5 bg-rose-950/20 rounded-xl border border-rose-900/30 flex items-start gap-2.5 animate-in fade-in slide-in-from-top-1 duration-200">
          <AlertCircle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider">Permission Error</span>
            <p className="text-[10px] text-rose-300/90 leading-relaxed">
              {permissionError}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
