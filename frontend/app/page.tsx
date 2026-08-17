"use client";

import { ChessGroundBoard } from "@/components/ChessGroundBoard";
import { StatusBar } from "@/components/StatusBar";
import { GameEndOverlay } from "@/components/GameEndOverlay";
import { GameStatsSidebar } from "@/components/GameStatsSidebar";
import { VoiceSessionPanel } from "@/components/VoiceSessionPanel";
import { SetupWizard } from "@/components/SetupWizard";
import { useGameSocket } from "@/hooks/useGameSocket";
import { useSetupWizard } from "@/hooks/useSetupWizard";

export default function Home() {
  const { state, connectionStatus } = useGameSocket();
  const { submitSetup, resetSetup, isSubmitting, error } = useSetupWizard();

  // Game is running if the backend says so — this survives page refresh
  const gameIsRunning =
    state.status === "in_progress" ||
    state.status === "checkmate" ||
    state.status === "stalemate" ||
    state.status === "draw" ||
    state.status === "resigned";

  // Show setup wizard when backend is still waiting (or on first load before WS connects)
  if (!gameIsRunning) {
    return (
      <main className="min-h-screen bg-zinc-900 flex flex-col items-center justify-center p-4">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100 uppercase tracking-widest">
            VoiceChess
          </h1>
          <p className="text-zinc-400 text-xs mt-1.5 uppercase tracking-wider">
            Setup Wizard
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-900 text-red-100 rounded max-w-md">
            {error}
          </div>
        )}

        <SetupWizard onComplete={submitSetup} />

        {isSubmitting && (
          <div className="mt-4 text-zinc-400">
            Starting game...
          </div>
        )}
      </main>
    );
  }

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
        <p className="text-zinc-400 text-xs mt-1.5 uppercase tracking-wider">
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
              <GameEndOverlay
                status={state.status}
                message={state.message}
                onPlayAgain={resetSetup}
              />
            </div>
          </div>

          {/* Right Column: Game Stats Sidebar */}
          <div className="lg:col-span-3 flex flex-col h-full">
            <GameStatsSidebar state={state} />
          </div>

        </div>
      </div>

      {/* Footer hint */}
      <p className="mt-12 text-zinc-500 text-xs uppercase tracking-wider text-center max-w-sm leading-normal">
        Moves are made by voice only. This display updates automatically as each
        move is spoken.
      </p>
    </main>
  );
}
