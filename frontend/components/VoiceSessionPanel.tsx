// components/VoiceSessionPanel.tsx
// Displays active voice control mode, speech recognition indicators, and transcription outputs.

"use client";

import type { GameState } from "@/hooks/useGameSocket";

interface VoiceSessionPanelProps {
  state: GameState;
}

export function VoiceSessionPanel({ state }: VoiceSessionPanelProps) {
  const { input_mode, mic_status = "idle", last_transcript } = state;

  return (
    <div className="w-full lg:w-80 bg-zinc-800/80 border border-zinc-700 rounded-xl p-4 flex flex-col gap-4 shadow-xl backdrop-blur-md">
      {/* Title */}
      <div>
        <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
          Voice Session
        </h2>
        <div className="h-px bg-zinc-700 my-2" />
      </div>

      {/* Mode Details */}
      <div className="bg-zinc-900/40 p-3 rounded-lg border border-zinc-700/50 flex flex-col gap-2">
        <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Active Input Mode
        </div>
        <div className="text-sm font-medium text-zinc-200">
          {input_mode === "ptt" ? (
            <div className="flex flex-col gap-1">
              <span className="font-semibold text-teal-400">Push-to-Talk</span>
              <span className="text-xs text-zinc-400">
                Hold Spacebar to record move, release to stop, then press Enter to confirm.
              </span>
            </div>
          ) : input_mode === "voice" ? (
            <div className="flex flex-col gap-1">
              <span className="font-semibold text-teal-400">Fully Voice (Hands-Free)</span>
              <span className="text-xs text-zinc-400">
                Speaks moves when prompted, then confirm by saying &ldquo;confirm&rdquo; or &ldquo;repeat&rdquo;.
              </span>
            </div>
          ) : (
            <span className="text-zinc-500 italic">Selecting mode...</span>
          )}
        </div>
      </div>

      {/* Mic Status */}
      <div className="flex items-center justify-between bg-zinc-900/40 p-3 rounded-lg border border-zinc-700/50">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Microphone State
        </span>
        <div className="flex items-center gap-2">
          {mic_status === "listening" ? (
            <>
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
              </span>
              <span className="text-xs font-medium text-red-400 font-mono uppercase">
                Listening
              </span>
            </>
          ) : mic_status === "processing" ? (
            <>
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-pulse absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
              </span>
              <span className="text-xs font-medium text-amber-400 font-mono uppercase">
                Processing
              </span>
            </>
          ) : (
            <>
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-zinc-650" />
              <span className="text-xs font-medium text-zinc-450 font-mono uppercase">
                Idle
              </span>
            </>
          )}
        </div>
      </div>

      {/* Transcription Output */}
      <div className="flex-1 flex flex-col min-h-[140px] gap-2">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Whisper Transcript
        </span>
        <div className="flex-1 bg-zinc-900/60 rounded-lg p-3 border border-zinc-750 flex items-center justify-center text-center">
          {last_transcript ? (
            <p className="text-zinc-200 font-medium text-sm leading-relaxed max-w-[240px]">
              &ldquo;{last_transcript}&rdquo;
            </p>
          ) : (
            <p className="text-zinc-550 text-xs italic">
              Speak a command to view transcription.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
