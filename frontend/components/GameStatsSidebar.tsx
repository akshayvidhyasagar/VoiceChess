// components/GameStatsSidebar.tsx
// Displays game timing, stats, and a list of moves made during the game.

"use client";

import type { GameState } from "@/hooks/useGameSocket";

interface GameStatsSidebarProps {
  state: GameState;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function GameStatsSidebar({ state }: GameStatsSidebarProps) {
  const {
    game_elapsed_seconds = 0,
    white_time_seconds = 0,
    black_time_seconds = 0,
    move_history_list = [],
    turn,
    status,
  } = state;

  // Group moves into pairs (White / Black)
  const pairedMoves: { white: string; black?: string }[] = [];
  for (let i = 0; i < move_history_list.length; i += 2) {
    pairedMoves.push({
      white: move_history_list[i],
      black: move_history_list[i + 1],
    });
  }

  return (
    <aside className="w-full lg:w-80 bg-zinc-800/80 border border-zinc-700 rounded-xl p-4 flex flex-col gap-4 shadow-xl backdrop-blur-md">
      {/* Title */}
      <div>
        <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
          Game Stats & History
        </h2>
        <div className="h-px bg-zinc-700 my-2" />
      </div>

      {/* Clocks */}
      <div className="grid grid-cols-2 gap-3">
        <div className={`p-3 rounded-lg border flex flex-col ${
          turn === "white" && status === "in_progress"
            ? "bg-zinc-100 text-zinc-900 border-teal-500 shadow-md"
            : "bg-zinc-700/50 text-zinc-300 border-zinc-600"
        }`}>
          <span className="text-xs uppercase tracking-wider font-semibold opacity-70">White Time</span>
          <span className="text-2xl font-mono font-bold mt-1">{formatDuration(white_time_seconds)}</span>
        </div>

        <div className={`p-3 rounded-lg border flex flex-col ${
          turn === "black" && status === "in_progress"
            ? "bg-zinc-900 text-zinc-100 border-teal-500 shadow-md"
            : "bg-zinc-700/50 text-zinc-300 border-zinc-600"
        }`}>
          <span className="text-xs uppercase tracking-wider font-semibold opacity-70">Black Time</span>
          <span className="text-2xl font-mono font-bold mt-1">{formatDuration(black_time_seconds)}</span>
        </div>
      </div>

      {/* Total elapsed time */}
      <div className="flex justify-between items-center bg-zinc-900/40 p-2.5 rounded-lg border border-zinc-700/50 text-xs">
        <span className="text-zinc-400">Total Game Time:</span>
        <span className="font-mono text-zinc-200 font-bold">{formatDuration(game_elapsed_seconds)}</span>
      </div>

      {/* Move History list */}
      <div className="flex-1 flex flex-col min-h-[200px] max-h-[320px] lg:max-h-none overflow-hidden">
        <div className="text-xs font-semibold text-zinc-400 mb-2">Move List</div>
        <div className="flex-1 overflow-y-auto bg-zinc-900/60 rounded-lg p-3 border border-zinc-750 font-mono text-sm custom-scrollbar">
          {pairedMoves.length === 0 ? (
            <div className="text-zinc-500 text-center py-8 text-xs italic">
              No moves played yet.
            </div>
          ) : (
            <div className="grid grid-cols-12 gap-y-2 text-zinc-300">
              {pairedMoves.map((pair, idx) => (
                <div key={idx} className="contents">
                  <div className="col-span-2 text-zinc-500 text-right pr-2 select-none">
                    {idx + 1}.
                  </div>
                  <div className="col-span-5 font-semibold text-zinc-100 hover:bg-zinc-800 rounded px-1 cursor-default">
                    {pair.white}
                  </div>
                  <div className="col-span-5 font-semibold text-zinc-300 hover:bg-zinc-800 rounded px-1 cursor-default">
                    {pair.black || ""}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
