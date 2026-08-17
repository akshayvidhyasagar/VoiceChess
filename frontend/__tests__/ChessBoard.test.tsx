// __tests__/ChessBoard.test.tsx
// Frontend smoke tests — verifies the board renders given a FEN + status payload
// and that the game-end overlay appears on terminal states.

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll } from "vitest";
import { ChessGroundBoard } from "@/components/ChessGroundBoard";
import { StatusBar } from "@/components/StatusBar";
import { GameEndOverlay } from "@/components/GameEndOverlay";
import type { GameState } from "@/hooks/useGameSocket";

const STARTING_FEN =
  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

const baseState: GameState = {
  fen: STARTING_FEN,
  turn: "white",
  mode: "double",
  bot_elo: null,
  human_color: null,
  status: "in_progress",
  last_move_san: null,
  last_move_uci: null,
  message: "White to move.",
  move_number: 1,
};

// Mock Chessground call so it doesn't try to manipulate DOM refs in jsdom context directly
vi.mock("chessground", () => {
  return {
    Chessground: vi.fn(() => ({
      destroy: vi.fn(),
      set: vi.fn()
    }))
  };
});

describe("ChessGroundBoard", () => {
  it("renders the container for the board", () => {
    const { container } = render(
      <ChessGroundBoard fen={STARTING_FEN} orientation="white" lastMoveUci={null} />
    );
    expect(container.firstChild).toBeDefined();
  });
});

describe("StatusBar", () => {
  it("shows 'Live' when connected", () => {
    render(<StatusBar state={baseState} connectionStatus="connected" />);
    expect(screen.getByText("Live")).toBeDefined();
  });
});

describe("GameEndOverlay", () => {
  it("renders on checkmate with the correct message", () => {
    render(
      <GameEndOverlay status="checkmate" message="Checkmate — Black wins!" />
    );
    expect(screen.getByText("Checkmate — Black wins!")).toBeDefined();
  });
});
