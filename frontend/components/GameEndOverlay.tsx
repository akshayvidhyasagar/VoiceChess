// components/GameEndOverlay.tsx
// Semi-transparent overlay shown when the game is over.

"use client";

import type { GameStatus } from "@/hooks/useGameSocket";

interface GameEndOverlayProps {
  status: GameStatus;
  message: string;
  onPlayAgain?: () => void;
}

export function GameEndOverlay({ status, message, onPlayAgain }: GameEndOverlayProps) {
  const isOver = ["checkmate", "stalemate", "draw", "resigned"].includes(status);
  if (!isOver) return null;

  return (
    <div className="absolute inset-0 flex items-center justify-center z-20 rounded-lg bg-zinc-900/80 backdrop-blur-sm">
      <div className="text-center px-6 py-6 rounded-2xl bg-zinc-800 border border-zinc-650 shadow-2xl max-w-sm mx-4">
        <div className="text-xs uppercase tracking-wider font-semibold text-zinc-400 mb-2">
          Game Over
        </div>
        <p className="text-amber-400 font-bold text-lg leading-snug">{message}</p>

        {onPlayAgain && (
          <div className="flex gap-3 mt-6">
            <button
              onClick={onPlayAgain}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition font-semibold"
            >
              Play Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="flex-1 px-4 py-2 bg-zinc-600 text-white rounded hover:bg-zinc-700 transition"
            >
              Exit
            </button>
          </div>
        )}

        {!onPlayAgain && (
          <p className="text-zinc-500 text-xs mt-3 leading-normal">
            The active voice session has concluded. Start a new game to play again.
          </p>
        )}
      </div>
    </div>
  );
}
