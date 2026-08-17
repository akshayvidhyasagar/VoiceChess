"use client";

import { ChessGroundBoard } from "@/components/ChessGroundBoard";
import { StatusBar } from "@/components/StatusBar";
import { GameEndOverlay } from "@/components/GameEndOverlay";
import { GameStatsSidebar } from "@/components/GameStatsSidebar";
import { VoiceSessionPanel } from "@/components/VoiceSessionPanel";
import { useGameSocket } from "@/hooks/useGameSocket";

export default function Home() {
  const { state, connectionStatus } = useGameSocket();

  // Orientation: in single-player, face the human's colour; else always white.
  const orientation =
    state.mode === "single" && state.human_color === "black" ? "black" : "white";

  return (
    <main className="min-h-screen bg-zinc-900 flex flex-col items-center justify-center p-4 lg:p-8 select-none">
      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100 uppercase tracking-widest">
          VoiceChess
        </h1>
        <p className="text-zinc-550 text-xs mt-1.5 uppercase tracking-wider">
          Spectator Dashboard
        </p>
      </div>

      <div className="w-full max-w-7xl">
        {/* Layout Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start justify-center">
          
          {/* Left Column: Voice Session */}
          <div className="lg:col-span-3 flex flex-col h-full">
            <VoiceSessionPanel state={state} />
          </div>

          {/* Middle Column: Board & Status */}
          <div className="lg:col-span-6 flex flex-col gap-4 items-center justify-center">
            <StatusBar state={state} connectionStatus={connectionStatus} />
            
            <div
              className="relative w-full"
              style={{ maxWidth: "560px" }}
              data-testid="board-container"
            >
              <ChessGroundBoard
                fen={state.fen}
                orientation={orientation}
                lastMoveUci={state.last_move_uci}
              />
              <GameEndOverlay status={state.status} message={state.message} />
            </div>
          </div>

          {/* Right Column: Game Stats Sidebar */}
          <div className="lg:col-span-3 flex flex-col h-full">
            <GameStatsSidebar state={state} />
          </div>

        </div>
      </div>

      {/* Footer hint */}
      <p className="mt-12 text-zinc-650 text-xxs uppercase tracking-wider text-center max-w-sm leading-normal">
        Moves are made by voice only. This display updates automatically as each
        move is spoken.
      </p>
    </main>
  );
}
