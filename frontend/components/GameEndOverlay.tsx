// components/GameEndOverlay.tsx
// Semi-transparent overlay shown when the game is over.

"use client";

import type { GameStatus } from "@/hooks/useGameSocket";

const ICONS: Record<string, string> = {
  checkmate: "♚",
  stalemate: "½",
  draw: "½",
  resigned: "⚑",
};

interface GameEndOverlayProps {
  status: GameStatus;
  message: string;
}

export function GameEndOverlay({ status, message }: GameEndOverlayProps) {
  const isOver = ["checkmate", "stalemate", "draw", "resigned"].includes(status);
  if (!isOver) return null;

  const icon = ICONS[status] ?? "✓";

  return (
    <div className="absolute inset-0 flex items-center justify-center z-20 rounded-lg bg-zinc-900/75 backdrop-blur-sm">
      <div className="text-center px-6 py-5 rounded-2xl bg-zinc-800/90 border border-zinc-600 shadow-2xl max-w-xs mx-4">
        <div className="text-5xl mb-3 select-none">{icon}</div>
        <p className="text-amber-300 font-semibold text-lg leading-snug">{message}</p>
        <p className="text-zinc-500 text-xs mt-2">
          The voice game loop has ended. Start a new game to continue.
        </p>
      </div>
    </div>
  );
}
