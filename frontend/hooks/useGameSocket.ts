// hooks/useGameSocket.ts
// Manages the WebSocket connection to the VoiceChess FastAPI backend.
// Handles reconnection with exponential backoff and exposes typed state.

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type GameStatus =
  | "waiting"
  | "in_progress"
  | "checkmate"
  | "stalemate"
  | "draw"
  | "resigned";

export type GameMode = "single" | "double" | null;

export interface GameState {
  fen: string;
  turn: "white" | "black";
  mode: GameMode;
  bot_elo: number | null;
  human_color: "white" | "black" | null;
  status: GameStatus;
  last_move_san: string | null;
  last_move_uci: string | null;
  message: string;
  move_number: number;
  game_elapsed_seconds?: number;
  white_time_seconds?: number;
  black_time_seconds?: number;
  move_history_list?: string[];
  input_mode?: "ptt" | "voice" | null;
  mic_status?: "idle" | "listening" | "processing";
  last_transcript?: string | null;
}

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

const STARTING_FEN =
  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

const DEFAULT_STATE: GameState = {
  fen: STARTING_FEN,
  turn: "white",
  mode: null,
  bot_elo: null,
  human_color: null,
  status: "waiting",
  last_move_san: null,
  last_move_uci: null,
  message: "Waiting for game to start…",
  move_number: 1,
  game_elapsed_seconds: 0,
  white_time_seconds: 0,
  black_time_seconds: 0,
  move_history_list: [],
  input_mode: null,
  mic_status: "idle",
  last_transcript: null,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/game";

const MIN_BACKOFF_MS = 500;
const MAX_BACKOFF_MS = 16_000;

export function useGameSocket() {
  const [state, setState] = useState<GameState>(DEFAULT_STATE);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("connecting");

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(MIN_BACKOFF_MS);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    setConnectionStatus("connecting");

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      backoffRef.current = MIN_BACKOFF_MS;
      setConnectionStatus("connected");
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data as string) as GameState;
        setState(payload);
      } catch {
        // Malformed payload — ignore
      }
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      setConnectionStatus("disconnected");
      // Exponential backoff reconnect
      const delay = backoffRef.current;
      backoffRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      wsRef.current?.close();
    };
  }, [connect]);

  return { state, connectionStatus };
}
