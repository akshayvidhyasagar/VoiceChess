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
      ? "Connecting…"
      : "Disconnected";

  return (
    <span className="flex items-center gap-1.5 text-xs font-medium text-zinc-400">
      <span className={`inline-block w-2 h-2 rounded-full ${colorClass}`} />
      {label}
    </span>
  );
}

function ModeBadge({ mode }: { mode: GameMode }) {
  if (!mode) return null;
  const label = mode === "single" ? "vs Computer" : "Human vs Human";
  return (
    <span className="rounded-full px-2.5 py-0.5 text-xs font-semibold bg-zinc-700 text-zinc-200">
      {label}
    </span>
  );
}

function EloBadge({ elo }: { elo: number | null }) {
  if (elo === null) return null;
  return (
    <span className="rounded-full px-2.5 py-0.5 text-xs font-semibold bg-teal-900 text-teal-300 border border-teal-700">
      ELO {elo}
    </span>
  );
}

function StatusBanner({ status, message }: { status: GameStatus; message: string }) {
  const isOver = ["checkmate", "stalemate", "draw", "resigned"].includes(status);
  return (
    <p
      className={`text-sm font-medium text-center ${
        isOver ? "text-amber-300" : "text-zinc-100"
      }`}
    >
      {message}
    </p>
  );
}

function TurnIndicator({ turn, status }: { turn: "white" | "black"; status: GameStatus }) {
  if (!["in_progress"].includes(status)) return null;
  return (
    <div className="flex items-center gap-2 text-xs text-zinc-400">
      <span
        className={`inline-block w-3 h-3 rounded-full border border-zinc-500 ${
          turn === "white" ? "bg-zinc-100" : "bg-zinc-900"
        }`}
      />
      <span className="capitalize">{turn} to move</span>
    </div>
  );
}

function LastMove({ san }: { san: string | null }) {
  if (!san) return null;
  return (
    <span className="text-xs text-zinc-500 font-mono">
      Last: <span className="text-zinc-300">{san}</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function StatusBar({ state, connectionStatus }: StatusBarProps) {
  const { status, message, turn, mode, bot_elo, last_move_san, move_number } = state;

  return (
    <div className="w-full max-w-[560px] mx-auto mb-3 rounded-xl bg-zinc-800/70 border border-zinc-700 backdrop-blur px-4 py-3 flex flex-col gap-2">
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
      <div className="flex items-center justify-between flex-wrap gap-2">
        <TurnIndicator turn={turn} status={status} />
        <div className="flex items-center gap-3">
          <LastMove san={last_move_san} />
          {status === "in_progress" && (
            <span className="text-xs text-zinc-600">Move {move_number}</span>
          )}
        </div>
      </div>
    </div>
  );
}
