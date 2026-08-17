// components/StatusBar.tsx
// Displays turn, mode, ELO, last move, and connection status.

"use client";

import type { ConnectionStatus, GameMode, GameState, GameStatus } from "@/hooks/useGameSocket";

interface StatusBarProps {
  state: GameState;
  connectionStatus: ConnectionStatus;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConnectionDot({ status }: { status: ConnectionStatus }) {
  const colorClass =
    status === "connected"
      ? "bg-teal-400"
      : status === "connecting"
      ? "bg-amber-400 animate-pulse"
      : "bg-red-500";

  const label =
    status === "connected"
      ? "Live"
      : status === "connecting"
      ? "Connecting..."
      : "Disconnected";

  return (
    <span className="flex items-center gap-1.5 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
      <span className={`inline-block w-2 h-2 rounded-full ${colorClass}`} />
      {label}
    </span>
  );
}

function ModeBadge({ mode }: { mode: GameMode }) {
  if (!mode) return null;
  const label = mode === "single" ? "vs Computer" : "Human vs Human";
  return (
    <span className="rounded bg-zinc-700 px-2 py-0.5 text-xs font-semibold text-zinc-200 uppercase tracking-wider">
      {label}
    </span>
  );
}

function EloBadge({ elo }: { elo: number | null }) {
  if (elo === null) return null;
  return (
    <span className="rounded bg-teal-950 px-2 py-0.5 text-xs font-semibold text-teal-300 border border-teal-800 uppercase tracking-wider">
      ELO {elo}
    </span>
  );
}

function StatusBanner({ status, message }: { status: GameStatus; message: string }) {
  const isOver = ["checkmate", "stalemate", "draw", "resigned"].includes(status);
  return (
    <p
      className={`text-sm font-semibold tracking-tight text-center ${
        isOver ? "text-amber-400" : "text-zinc-100"
      }`}
    >
      {message}
    </p>
  );
}

function TurnIndicator({ turn, status }: { turn: "white" | "black"; status: GameStatus }) {
  if (!["in_progress"].includes(status)) return null;
  return (
    <div className="flex items-center gap-2 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
      <span
        className={`inline-block w-2.5 h-2.5 rounded-full border border-zinc-500 ${
          turn === "white" ? "bg-zinc-100" : "bg-zinc-900"
        }`}
      />
      <span>{turn} to move</span>
    </div>
  );
}

function LastMove({ san }: { san: string | null }) {
  if (!san) return null;
  return (
    <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
      Last Move: <span className="text-zinc-300 font-mono font-bold lowercase normal-case">{san}</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function StatusBar({ state, connectionStatus }: StatusBarProps) {
  const { status, message, turn, mode, bot_elo, last_move_san, move_number } = state;

  return (
    <div className="w-full max-w-[560px] mx-auto rounded-xl bg-zinc-800/80 border border-zinc-700 backdrop-blur px-4 py-3 flex flex-col gap-3 shadow-xl">
      {/* Top row: connection + badges */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <ConnectionDot status={connectionStatus} />
        <div className="flex items-center gap-2 flex-wrap">
          <ModeBadge mode={mode} />
          <EloBadge elo={bot_elo} />
        </div>
      </div>

      {/* Message row */}
      <StatusBanner status={status} message={message} />

      {/* Bottom row: turn indicator + last move + move number */}
      <div className="flex items-center justify-between flex-wrap gap-2 pt-1 border-t border-zinc-750">
        <TurnIndicator turn={turn} status={status} />
        <div className="flex items-center gap-3">
          <LastMove san={last_move_san} />
          {status === "in_progress" && (
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Move {move_number}</span>
          )}
        </div>
      </div>
    </div>
  );
}
