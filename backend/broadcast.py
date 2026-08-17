"""broadcast.py — Thread-safe game-state broadcaster.

The voice/game loop runs in a background thread; the FastAPI server runs
the asyncio event loop on the main thread.  This module bridges them:

  - The game thread calls ``push_state(...)`` (synchronous).
  - ``push_state`` schedules a coroutine on the FastAPI event loop via
    ``loop.call_soon_threadsafe``, which fans the payload out to every
    connected WebSocket.

No imports from voicerecognition.py here — the dependency is one-way.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Optional

import chess


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def _game_status(board: chess.Board, game_end_override) -> str:
    """Derive a status string from the current board and override."""
    if game_end_override:
        result, _ = game_end_override
        if result in ("1-0", "0-1"):
            return "resigned"
        return "draw"
    if board.is_checkmate():
        return "checkmate"
    if board.is_stalemate():
        return "stalemate"
    if board.is_game_over():
        return "draw"
    return "in_progress"


def build_payload(
    board: chess.Board,
    move_history: list[str],
    game_mode: str,
    elo: Optional[int],
    human_color: Optional[str],
    game_end_override=None,
) -> dict:
    """Return a JSON-serialisable dict representing the current game state."""
    last_san = move_history[-1] if move_history else None
    last_uci: Optional[str] = None
    if board.move_stack:
        last_uci = board.peek().uci()

    turn = "white" if board.turn == chess.WHITE else "black"
    mover = "White" if board.turn == chess.WHITE else "Black"
    status = _game_status(board, game_end_override)

    if game_end_override:
        _, message = game_end_override
    elif status == "checkmate":
        winner = "Black" if board.turn == chess.WHITE else "White"
        message = f"Checkmate — {winner} wins!"
    elif status in ("stalemate", "draw"):
        message = "Game drawn."
    elif last_san:
        mover_who_just_moved = "Black" if board.turn == chess.WHITE else "White"
        message = f"{mover_who_just_moved} plays {last_san}"
    else:
        message = f"Waiting for {mover} to move."

    move_number = (len(move_history) + 2) // 2 if move_history else 1

    return {
        "fen": board.fen(),
        "turn": turn,
        "mode": game_mode,          # "single" | "double" | None (waiting)
        "bot_elo": elo,             # int or null
        "human_color": human_color, # "white" | "black" | null
        "status": status,
        "last_move_san": last_san,
        "last_move_uci": last_uci,
        "message": message,
        "move_number": move_number,
    }


# ---------------------------------------------------------------------------
# Broadcaster singleton
# ---------------------------------------------------------------------------

class GameBroadcaster:
    """Singleton that fans game-state payloads out to all WebSocket clients."""

    def __init__(self) -> None:
        self._clients: set[asyncio.Queue] = set()
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Most-recent state — sent to newly connecting clients immediately.
        self._last_payload: dict = {
            "fen": chess.Board().fen(),
            "turn": "white",
            "mode": None,
            "bot_elo": None,
            "human_color": None,
            "status": "waiting",
            "last_move_san": None,
            "last_move_uci": None,
            "message": "Waiting for game to start…",
            "move_number": 1,
        }

    # --- called from the FastAPI / asyncio thread ---

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the running event loop so push_state can schedule on it."""
        self._loop = loop

    async def connect(self, queue: asyncio.Queue) -> dict:
        """Register a new WebSocket client queue; return the current snapshot."""
        with self._lock:
            self._clients.add(queue)
        return self._last_payload

    async def disconnect(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._clients.discard(queue)

    async def _broadcast_async(self, payload: dict) -> None:
        """Fan payload out to all client queues (runs on the event loop)."""
        with self._lock:
            queues = list(self._clients)
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # slow client — drop frame, they'll catch up on reconnect

    # --- called from the game-loop thread ---

    def push_state(
        self,
        board: chess.Board,
        move_history: list[str],
        game_mode: str,
        elo: Optional[int],
        human_color: Optional[str],
        game_end_override=None,
    ) -> None:
        """Build and broadcast the current state. Safe to call from any thread."""
        payload = build_payload(board, move_history, game_mode, elo,
                                human_color, game_end_override)
        self._last_payload = payload

        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                self._loop.create_task,
                self._broadcast_async(payload),
            )
        # If no loop yet (no clients connected), the snapshot is still saved
        # and will be delivered to the next connecting client.


_broadcaster: Optional[GameBroadcaster] = None
_broadcaster_lock = threading.Lock()


def get_broadcaster() -> GameBroadcaster:
    """Return the process-wide broadcaster singleton."""
    global _broadcaster
    if _broadcaster is None:
        with _broadcaster_lock:
            if _broadcaster is None:
                _broadcaster = GameBroadcaster()
    return _broadcaster
