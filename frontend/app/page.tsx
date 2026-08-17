"use client";

import { useCallback, useEffect, useState } from "react";
import { ChessGroundBoard } from "@/components/ChessGroundBoard";
import { StatusBar } from "@/components/StatusBar";
import { GameEndOverlay } from "@/components/GameEndOverlay";
import { GameStatsSidebar } from "@/components/GameStatsSidebar";
import { useGameSocket } from "@/hooks/useGameSocket";

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
    <main className="min-h-screen bg-zinc-900 flex flex-col items-center justify-center p-4 lg:p-8 select-none">
      {/* Header */}
      <div className="mb-6 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100">
          ♟ VoiceChess
        </h1>
        <p className="text-zinc-500 text-sm mt-1">
          Voice-controlled chess — spectator view
        </p>
      </div>

      <div className="w-full max-w-5xl flex flex-col gap-6">
        {/* Status bar */}
        <StatusBar state={state} connectionStatus={connectionStatus} />

        {/* Sidebar + Board container */}
        <div className="flex flex-col lg:flex-row gap-6 items-stretch justify-center">
          {/* Board + overlay */}
          <div
            className="relative flex-1 flex items-center justify-center"
            style={{ maxWidth: "560px", margin: "0 auto" }}
            data-testid="board-container"
          >
            <ChessGroundBoard
              fen={state.fen}
              orientation={orientation}
              lastMoveUci={state.last_move_uci}
            />
            <GameEndOverlay status={state.status} message={state.message} />
          </div>

          {/* Stats Sidebar */}
          <GameStatsSidebar state={state} />
        </div>
      </div>

      {/* Footer hint */}
      <p className="mt-8 text-zinc-650 text-xs text-center max-w-sm">
        Moves are made by voice only. This display updates automatically as each
        move is spoken.
      </p>
    </main>
  );
}
