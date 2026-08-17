// components/GameEndOverlay.tsx
// Semi-transparent overlay shown when the game is over.

"use client";

import type { GameStatus } from "@/hooks/useGameSocket";

interface GameEndOverlayProps {
  status: GameStatus;
  message: string;
}

export function GameEndOverlay({ status, message }: GameEndOverlayProps) {
  const isOver = ["checkmate", "stalemate", "draw", "resigned"].includes(status);
  if (!isOver) return null;

  return (
    <div className="absolute inset-0 flex items-center justify-center z-20 rounded-lg bg-zinc-900/80 backdrop-blur-sm">
      <div className="text-center px-6 py-6 rounded-2xl bg-zinc-800 border border-zinc-650 shadow-2xl max-w-xs mx-4">
        <div className="text-xs uppercase tracking-wider font-semibold text-zinc-400 mb-2">
          Game Over
        </div>
        <p className="text-amber-400 font-bold text-lg leading-snug">{message}</p>
        <p className="text-zinc-500 text-xs mt-3 leading-normal">
          The active voice session has concluded. Start a new game to play again.
        </p>
      </div>
    </div>
  );
}
