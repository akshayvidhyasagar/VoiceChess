// components/ChessGroundBoard.tsx
// Displays the board using the Lichess Chessground library to match Lichess design.

"use client";

import { useEffect, useRef } from "react";
import { Chessground } from "chessground";
import type { Key } from "chessground/types";
import "chessground/assets/chessground.base.css";
import "chessground/assets/chessground.brown.css";

interface ChessGroundBoardProps {
  fen: string;
  orientation: "white" | "black";
  lastMoveUci: string | null;
}

export function ChessGroundBoard({ fen, orientation, lastMoveUci }: ChessGroundBoardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cgRef = useRef<any>(null);

  // Convert lastMoveUci (e.g. "e2e4") into Chessground Key pair (e.g. ["e2", "e4"])
  const lastMove = lastMoveUci && lastMoveUci.length >= 4 
    ? [lastMoveUci.slice(0, 2) as Key, lastMoveUci.slice(2, 4) as Key] as [Key, Key]
    : undefined;

  useEffect(() => {
    if (!containerRef.current) return;

    cgRef.current = Chessground(containerRef.current, {
      fen: fen,
      orientation: orientation,
      viewOnly: true, // Read-only view
      lastMove: lastMove,
      drawable: {
        enabled: true,
      },
    });

    return () => {
      if (cgRef.current) {
        cgRef.current.destroy();
      }
    };
  }, [fen, orientation, lastMoveUci]);

  return (
    <div className="w-full max-w-[560px] mx-auto aspect-square rounded-lg overflow-hidden shadow-2xl border border-zinc-700 bg-zinc-850">
      <div 
        ref={containerRef} 
        className="w-full h-full cg-brown"
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
