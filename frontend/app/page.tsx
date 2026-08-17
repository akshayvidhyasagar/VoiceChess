"use client";

import { useCallback, useEffect, useState } from "react";
import { ChessBoard } from "@/components/ChessBoard";
import { StatusBar } from "@/components/StatusBar";
import { GameEndOverlay } from "@/components/GameEndOverlay";
import { useGameSocket } from "@/hooks/useGameSocket";

/**
 * Compute board pixel width — capped at 560px, 16px padding on each side.
 */
function useBoardWidth() {
  const [width, setWidth] = useState(560);
  const update = useCallback(() => {
    setWidth(Math.min(window.innerWidth - 32, 560));
  }, []);

  useEffect(() => {
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [update]);

  return width;
}

export default function Home() {
  const { state, connectionStatus } = useGameSocket();
  const boardWidth = useBoardWidth();

  // Orientation: in single-player, face the human's colour; else always white.
  const orientation =
    state.mode === "single" && state.human_color === "black" ? "black" : "white";

  return (
    <main className="min-h-screen bg-zinc-900 flex flex-col items-center justify-center px-4 py-8 select-none">
      {/* Header */}
      <div className="mb-6 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100">
          ♟ VoiceChess
        </h1>
        <p className="text-zinc-500 text-sm mt-1">
          Voice-controlled chess — spectator view
        </p>
      </div>

      {/* Status bar */}
      <StatusBar state={state} connectionStatus={connectionStatus} />

      {/* Board + overlay */}
      <div
        className="relative"
        style={{ width: boardWidth, maxWidth: "560px" }}
        data-testid="board-container"
      >
        <ChessBoard
          fen={state.fen}
          orientation={orientation}
          lastMoveUci={state.last_move_uci}
        />
        <GameEndOverlay status={state.status} message={state.message} />
      </div>

      {/* Footer hint */}
      <p className="mt-6 text-zinc-600 text-xs text-center max-w-sm">
        Moves are made by voice only. This display updates automatically as each
        move is spoken.
      </p>
    </main>
  );
}
