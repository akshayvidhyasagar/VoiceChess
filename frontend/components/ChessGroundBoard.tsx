// components/ChessGroundBoard.tsx
// Displays the board using the Lichess Chessground library to match Lichess design.

"use client";

import { useEffect, useRef } from "react";
import { Chessground } from "chessground";
import type { Key } from "chessground/types";
import "chessground/assets/chessground.base.css";
import "chessground/assets/chessground.brown.css";
import "chessground/assets/chessground.cburnett.css";

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

  // Initialize Chessground once on mount
  useEffect(() => {
    if (!containerRef.current) return;

    cgRef.current = Chessground(containerRef.current, {
      fen,
      orientation,
      viewOnly: true,
      lastMove,
      drawable: { enabled: false },
      animation: { enabled: true, duration: 200 },
    });

    return () => {
      if (cgRef.current) {
        cgRef.current.destroy();
        cgRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // mount only

  // Update board state when fen/orientation/lastMove changes without recreating
  useEffect(() => {
    if (!cgRef.current) return;
    cgRef.current.set({
      fen,
      orientation,
      lastMove,
    });
  }, [fen, orientation, lastMove]);

  return (
    <div className="w-full max-w-[560px] mx-auto aspect-square rounded-lg overflow-hidden shadow-2xl border border-zinc-700">
      <div 
        ref={containerRef} 
        className="w-full h-full"
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
