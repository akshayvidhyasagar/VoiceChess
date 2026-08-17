"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";

interface AudioRecorderProps {
  mode: "ptt" | "voice";
  onTranscript: (transcript: string) => void;
  onError: (error: string) => void;
}

// Pick the best supported MIME type so the temp file on the server has the right extension.
// Chrome/Edge/Safari all produce WebM or MP4 — never real WAV.
function getSupportedMimeType(): string {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
    "audio/mp4",
  ];
  for (const mime of candidates) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(mime)) {
      return mime;
    }
  }
  return "";
}

export function AudioRecorder({ mode, onTranscript, onError }: AudioRecorderProps) {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState<string>("");

  const sendToTranscribe = useCallback(async (blob: Blob) => {
    try {
      const formData = new FormData();
      // Name the file with a correct extension so the server's content-type detection works
      const ext = blob.type.includes("ogg") ? "ogg" : blob.type.includes("mp4") ? "mp4" : "webm";
      formData.append("audio", blob, `recording.${ext}`);

      const response = await fetch("http://localhost:8000/api/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      if (data.transcript) {
        setTranscript(data.transcript);
        onTranscript(data.transcript);
      }
    } catch (error) {
      console.error("[AudioRecorder] transcribe error:", error);
      onError("Failed to transcribe audio");
    } finally {
      setIsProcessing(false);
    }
  }, [onTranscript, onError]);

  // ──────────────── PTT mode ────────────────
  const handlePTTMouseDown = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const mimeType = getSupportedMimeType();
      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      const chunks: BlobPart[] = [];
      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        setIsProcessing(true);
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
        await sendToTranscribe(blob);
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
    } catch {
      onError("Microphone access denied");
    }
  }, [sendToTranscribe, onError]);

  const handlePTTEnd = useCallback(() => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state === "recording") {
      mr.stop();
    }
  }, []);

  // ──────────────── Voice auto mode ────────────────
  // Uses Web Audio API RMS (root-mean-square) over the time-domain signal —
  // far more reliable than FFT frequency bins which can read near-zero even during speech.
  const startVoiceRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const mimeType = getSupportedMimeType();
      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      const chunks: BlobPart[] = [];
      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      mediaRecorderRef.current = mediaRecorder;

      const context = new (window.AudioContext || (window as any).webkitAudioContext)();
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      const timeDomainData = new Float32Array(analyser.fftSize);

      const getRMS = (): number => {
        analyser.getFloatTimeDomainData(timeDomainData);
        let sum = 0;
        for (let i = 0; i < timeDomainData.length; i++) sum += timeDomainData[i] * timeDomainData[i];
        return Math.sqrt(sum / timeDomainData.length);
      };

      let speechDetected = false;
      let silenceMs = 0;
      let totalMs = 0;
      let speechMs = 0;
      const FRAME_MS = 80;
      const SILENCE_HANG_MS = 1000;     // 1s silence ends recording
      const MAX_INITIAL_WAIT_MS = 8000; // give up if no speech for 8s
      const MAX_TOTAL_MS = 20000;
      const MIN_SPEECH_MS = 400;        // avoid cutting off short words like "white", "black"

      // Calibrate ambient noise for 300ms to set a dynamic threshold
      const calibrationSamples: number[] = [];
      mediaRecorder.start();
      setIsRecording(true);

      await new Promise<void>((resolve) => {
        let elapsed = 0;
        const cal = setInterval(() => {
          calibrationSamples.push(getRMS());
          elapsed += FRAME_MS;
          if (elapsed >= 300) { clearInterval(cal); resolve(); }
        }, FRAME_MS);
      });

      const avg = calibrationSamples.reduce((a, b) => a + b, 0) / calibrationSamples.length;
      const speechThresh = Math.max(avg, 0.002) * 5; // 5x ambient noise = speech

      const detectLoop = setInterval(() => {
        const rms = getRMS();
        totalMs += FRAME_MS;

        if (rms >= speechThresh) {
          speechDetected = true;
          speechMs += FRAME_MS;
          silenceMs = 0;
        } else if (speechDetected) {
          silenceMs += FRAME_MS;
        }

        const shouldStop =
          totalMs >= MAX_TOTAL_MS ||
          (!speechDetected && totalMs >= MAX_INITIAL_WAIT_MS) ||
          (speechDetected && speechMs >= MIN_SPEECH_MS && silenceMs >= SILENCE_HANG_MS);

        if (shouldStop && mediaRecorder.state === "recording") {
          clearInterval(detectLoop);
          context.close();
          mediaRecorder.onstop = async () => {
            setIsRecording(false);
            stream.getTracks().forEach((t) => t.stop());
            if (speechDetected && chunks.length > 0) {
              setIsProcessing(true);
              const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
              await sendToTranscribe(blob);
            } else {
              setIsProcessing(false);
            }
          };
          mediaRecorder.stop();
        }
      }, FRAME_MS);
    } catch {
      onError("Microphone access denied");
    }
  }, [sendToTranscribe, onError]);

  // In voice mode: restart listening automatically after each round
  useEffect(() => {
    if (mode !== "voice" || isRecording || isProcessing) return;
    const t = setTimeout(startVoiceRecording, 300);
    return () => clearTimeout(t);
  }, [mode, isRecording, isProcessing, startVoiceRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => { streamRef.current?.getTracks().forEach((t) => t.stop()); };
  }, []);

  return (
    <div className="flex flex-col items-center gap-4">
      {mode === "ptt" && (
        <button
          onMouseDown={handlePTTMouseDown}
          onMouseUp={handlePTTEnd}
          onMouseLeave={handlePTTEnd}
          onTouchStart={handlePTTMouseDown}
          onTouchEnd={handlePTTEnd}
          disabled={isProcessing}
          className={`px-6 py-3 rounded-lg font-semibold transition-all select-none ${
            isRecording
              ? "bg-red-600 text-white scale-95 shadow-lg shadow-red-900"
              : "bg-blue-600 text-white hover:bg-blue-500 active:scale-95"
          } ${isProcessing ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          {isProcessing ? "Processing..." : isRecording ? "Recording..." : "Hold to Speak"}
        </button>
      )}

      {mode === "voice" && (
        <div className="flex flex-col items-center gap-2 text-center">
          {isProcessing ? (
            <div className="text-zinc-400 text-sm">Transcribing...</div>
          ) : isRecording ? (
            <>
              <div className="w-4 h-4 rounded-full bg-red-500 animate-pulse" />
              <div className="text-zinc-400 text-sm">Listening...</div>
            </>
          ) : (
            <div className="text-zinc-500 text-sm">Waiting to listen...</div>
          )}
        </div>
      )}

      {transcript && (
        <div className="text-center mt-1">
          <div className="text-xs text-zinc-500 uppercase tracking-wider">Heard</div>
          <div className="text-sm font-semibold text-zinc-100 mt-0.5">{transcript}</div>
        </div>
      )}
    </div>
  );
}

