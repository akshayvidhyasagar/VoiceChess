// __tests__/ChessBoard.test.tsx
// Frontend smoke tests — verifies the board renders given a FEN + status payload
// and that the game-end overlay appears on terminal states.

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll } from "vitest";
import { ChessBoard } from "@/components/ChessBoard";
import { StatusBar } from "@/components/StatusBar";
import { GameEndOverlay } from "@/components/GameEndOverlay";
import type { GameState, ConnectionStatus } from "@/hooks/useGameSocket";

// react-chessboard uses ResizeObserver internally; polyfill in jsdom.
beforeAll(() => {
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

const STARTING_FEN =
  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

const AFTER_E4_FEN =
  "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1";

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

// ---------------------------------------------------------------------------
// ChessBoard component
// ---------------------------------------------------------------------------

describe("ChessBoard", () => {
  it("renders the board wrapper for the starting position", () => {
    render(
      <ChessBoard fen={STARTING_FEN} orientation="white" lastMoveUci={null} />
    );
    expect(screen.getByTestId("chess-board-wrapper")).toBeDefined();
  });

  it("renders the board wrapper for an arbitrary FEN after e4", () => {
    render(
      <ChessBoard
        fen={AFTER_E4_FEN}
        orientation="white"
        lastMoveUci="e2e4"
      />
    );
    expect(screen.getByTestId("chess-board-wrapper")).toBeDefined();
  });

  it("renders with black orientation for single-player human playing black", () => {
    render(
      <ChessBoard fen={STARTING_FEN} orientation="black" lastMoveUci={null} />
    );
    expect(screen.getByTestId("chess-board-wrapper")).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// StatusBar component
// ---------------------------------------------------------------------------

describe("StatusBar", () => {
  it("shows 'Live' when connected", () => {
    render(<StatusBar state={baseState} connectionStatus="connected" />);
    expect(screen.getByText("Live")).toBeDefined();
  });

  it("shows 'Connecting…' when connecting", () => {
    render(<StatusBar state={baseState} connectionStatus="connecting" />);
    expect(screen.getByText("Connecting…")).toBeDefined();
  });

  it("shows 'Disconnected' when disconnected", () => {
    render(<StatusBar state={baseState} connectionStatus="disconnected" />);
    expect(screen.getByText("Disconnected")).toBeDefined();
  });

  it("shows the ELO badge in single-player mode", () => {
    const state: GameState = {
      ...baseState,
      mode: "single",
      bot_elo: 1500,
      human_color: "white",
    };
    render(<StatusBar state={state} connectionStatus="connected" />);
    expect(screen.getByText("ELO 1500")).toBeDefined();
  });

  it("shows 'vs Computer' badge in single mode", () => {
    const state: GameState = {
      ...baseState,
      mode: "single",
      bot_elo: 1200,
      human_color: "black",
    };
    render(<StatusBar state={state} connectionStatus="connected" />);
    expect(screen.getByText("vs Computer")).toBeDefined();
  });

  it("shows 'Human vs Human' badge in double mode", () => {
    render(<StatusBar state={baseState} connectionStatus="connected" />);
    expect(screen.getByText("Human vs Human")).toBeDefined();
  });

  it("shows the last move when provided", () => {
    const state: GameState = {
      ...baseState,
      last_move_san: "e4",
      last_move_uci: "e2e4",
    };
    render(<StatusBar state={state} connectionStatus="connected" />);
    expect(screen.getByText("e4")).toBeDefined();
  });

  it("shows waiting message when status is waiting", () => {
    const state: GameState = {
      ...baseState,
      status: "waiting",
      message: "Waiting for game to start…",
    };
    render(<StatusBar state={state} connectionStatus="connecting" />);
    expect(screen.getByText("Waiting for game to start…")).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// GameEndOverlay component
// ---------------------------------------------------------------------------

describe("GameEndOverlay", () => {
  it("is not rendered during an in-progress game", () => {
    const { container } = render(
      <GameEndOverlay status="in_progress" message="White to move." />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders on checkmate with the correct message", () => {
    render(
      <GameEndOverlay status="checkmate" message="Checkmate — Black wins!" />
    );
    expect(screen.getByText("Checkmate — Black wins!")).toBeDefined();
  });

  it("renders on resignation", () => {
    render(
      <GameEndOverlay status="resigned" message="White resigns. Black wins!" />
    );
    expect(screen.getByText("White resigns. Black wins!")).toBeDefined();
  });

  it("renders on draw", () => {
    render(
      <GameEndOverlay status="draw" message="Game drawn by agreement." />
    );
    expect(screen.getByText("Game drawn by agreement.")).toBeDefined();
  });

  it("renders on stalemate", () => {
    render(<GameEndOverlay status="stalemate" message="Game drawn." />);
    expect(screen.getByText("Game drawn.")).toBeDefined();
  });
});
