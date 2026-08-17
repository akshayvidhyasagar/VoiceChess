// components/ChessBoard.tsx
// Pure display board — no drag-and-drop. Voice is the only move input.

"use client";

import { useMemo } from "react";
import { Chessboard } from "react-chessboard";

interface ChessBoardProps {
  fen: string;
  orientation: "white" | "black";
  lastMoveUci: string | null;
}

/**
 * Parse a UCI move string like "e2e4" into chessground-style square highlights.
 */
function parseHighlights(
  uci: string | null
): Record<string, { background: string }> {
  if (!uci || uci.length < 4) return {};
  const from = uci.slice(0, 2);
  const to = uci.slice(2, 4);
  const highlight = "rgba(20, 184, 166, 0.55)"; // teal-500 at 55% opacity
  return {
    [from]: { background: highlight },
    [to]: { background: highlight },
  };
}

export function ChessBoard({ fen, orientation, lastMoveUci }: ChessBoardProps) {
  const highlights = useMemo(
    () => parseHighlights(lastMoveUci),
    [lastMoveUci]
  );

  return (
    <div className="w-full max-w-[560px] mx-auto" data-testid="chess-board-wrapper">
      <Chessboard
        id="voice-chess-board"
        position={fen}
        boardOrientation={orientation}
        arePiecesDraggable={false}
        customSquareStyles={highlights}
        customBoardStyle={{
          borderRadius: "8px",
          boxShadow: "0 0 40px rgba(20, 184, 166, 0.15), 0 8px 32px rgba(0,0,0,0.6)",
        }}
        customDarkSquareStyle={{ backgroundColor: "#1e4d3a" }}
        customLightSquareStyle={{ backgroundColor: "#d4e8d1" }}
      />
    </div>
  );
}
