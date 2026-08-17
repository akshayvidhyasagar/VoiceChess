"use client";

import React, { useRef, useState, useEffect } from "react";

interface AudioRecorderProps {
  mode: "ptt" | "voice";
  onTranscript: (transcript: string) => void;
  onError: (error: string) => void;
}

export function AudioRecorder({ mode, onTranscript, onError }: AudioRecorderProps) {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState<string>("");

  // PTT: Mouse down to start, up to stop
  const handlePTTMouseDown = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const chunks: BlobPart[] = [];

      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        setIsProcessing(true);

        const blob = new Blob(chunks, { type: "audio/wav" });
        await sendToTranscribe(blob);

        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
    } catch (error) {
      onError("Microphone access denied");
    }
  };

  const handlePTTMouseUp = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
  };

  const sendToTranscribe = async (blob: Blob) => {
    try {
      const formData = new FormData();
      formData.append("audio", blob, "audio.wav");

      const response = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Transcription failed");

      const data = await response.json();
      setTranscript(data.transcript);
      onTranscript(data.transcript);
    } catch (error) {
      onError("Failed to transcribe audio");
    } finally {
      setIsProcessing(false);
    }
  };

  // Voice mode: Auto-detect speech via Web Audio
  useEffect(() => {
    if (mode === "voice" && !isRecording && !isProcessing) {
      startVoiceRecording();
    }
  }, [mode, isRecording, isProcessing]);

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = context;

      const analyser = context.createAnalyser();
      analyser.fftSize = 2048;
      const source = context.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const chunks: BlobPart[] = [];

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);

      let silenceDuration = 0;
      const silenceThreshold = 2500; // ~2.5s
      const frameSize = 100; // ~100ms chunks

      const detectSilence = () => {
        analyser.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;

        if (average < 30) {
          silenceDuration += frameSize;
        } else {
          silenceDuration = 0;
        }

        if (silenceDuration >= silenceThreshold && mediaRecorder.state === "recording") {
          mediaRecorder.stop();
          stream.getTracks().forEach((track) => track.stop());
          setIsRecording(false);
          setIsProcessing(true);

          mediaRecorder.onstop = async () => {
            const blob = new Blob(chunks, { type: "audio/wav" });
            await sendToTranscribe(blob);
          };

          return;
        }

        if (mediaRecorder.state === "recording") {
          setTimeout(detectSilence, frameSize);
        }
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);

      detectSilence();
    } catch (error) {
      onError("Microphone access denied");
    }
  };

  return (
    <div className="flex flex-col items-center gap-4">
      {mode === "ptt" && (
        <button
          onMouseDown={handlePTTMouseDown}
          onMouseUp={handlePTTMouseUp}
          onMouseLeave={handlePTTMouseUp}
          disabled={isProcessing}
          className={`px-6 py-3 rounded font-semibold transition ${
            isRecording
              ? "bg-red-600 text-white"
              : "bg-blue-600 text-white hover:bg-blue-700"
          } ${isProcessing ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          {isProcessing ? "Processing..." : "Hold to record"}
        </button>
      )}

      {mode === "voice" && (
        <div className="text-center">
          <div className="text-sm text-zinc-400 mb-2">
            {isRecording ? "Listening for speech..." : "Waiting to start..."}
          </div>
          {isRecording && (
            <div className="w-16 h-16 mx-auto">
              <div className="animate-pulse w-full h-full bg-blue-500 rounded-full opacity-75" />
            </div>
          )}
        </div>
      )}

      {transcript && (
        <div className="text-center">
          <div className="text-sm text-zinc-400">Heard:</div>
          <div className="text-lg font-semibold text-white">{transcript}</div>
        </div>
      )}
    </div>
  );
}
