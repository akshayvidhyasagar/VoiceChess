"""tests/test_broadcast.py — Verify broadcast payload shape and correctness.

Follows the same pytest conventions as the rest of the test suite:
  - plain functions, no classes
  - explicit asserts with descriptive names
  - no I/O, no subprocesses
"""

import chess
import pytest
from broadcast import build_payload, get_broadcaster, GameBroadcaster


# ---------------------------------------------------------------------------
# build_payload — payload shape
# ---------------------------------------------------------------------------

def test_broadcast_payload_has_all_required_keys():
    """Every broadcast payload must have the full set of documented fields."""
    board = chess.Board()
    payload = build_payload(board, [], "double", None, None)

    required_keys = {
        "fen", "turn", "mode", "bot_elo", "human_color",
        "status", "last_move_san", "last_move_uci", "message", "move_number",
        "game_elapsed_seconds", "white_time_seconds", "black_time_seconds", "move_history_list",
        "input_mode", "mic_status", "last_transcript"
    }
    assert required_keys == set(payload.keys()), (
        f"Missing keys: {required_keys - set(payload.keys())}, Extra keys: {set(payload.keys()) - required_keys}"
    )


def test_broadcast_payload_starting_position():
    """Starting-position payload should report white to move, in_progress."""
    board = chess.Board()
    payload = build_payload(board, [], "double", None, None)

    assert payload["fen"] == chess.STARTING_FEN
    assert payload["turn"] == "white"
    assert payload["status"] == "in_progress"
    assert payload["last_move_san"] is None
    assert payload["last_move_uci"] is None
    assert payload["mode"] == "double"
    assert payload["bot_elo"] is None


# ---------------------------------------------------------------------------
# build_payload — after a move
# ---------------------------------------------------------------------------

def test_broadcast_payload_after_human_move():
    """After e4, the payload should reflect the updated FEN, last-move info,
    black to move, and the correct message."""
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    board.push(move)
    move_history = ["e4"]

    payload = build_payload(board, move_history, "single", 1500, "white")

    assert payload["fen"] == board.fen()
    assert payload["turn"] == "black"          # black to move after e4
    assert payload["status"] == "in_progress"
    assert payload["last_move_san"] == "e4"
    assert payload["last_move_uci"] == "e2e4"
    assert payload["bot_elo"] == 1500
    assert payload["human_color"] == "white"
    assert "White" in payload["message"] and "e4" in payload["message"]
    assert payload["move_number"] == 1


def test_broadcast_payload_move_number_increments():
    """move_number should increment every two half-moves (full moves)."""
    board = chess.Board()
    history = []
    for uci, san in [("e2e4", "e4"), ("e7e5", "e5"), ("g1f3", "Nf3")]:
        board.push(chess.Move.from_uci(uci))
        history.append(san)

    payload = build_payload(board, history, "double", None, None)
    # 3 half-moves = move 2 (1.e4 e5  2.Nf3 ...)
    assert payload["move_number"] == 2


# ---------------------------------------------------------------------------
# build_payload — game-end states
# ---------------------------------------------------------------------------

def test_broadcast_payload_checkmate_status():
    """Scholar's mate board should report 'checkmate' status."""
    board = chess.Board()
    for uci in ["e2e4", "e7e5", "f1c4", "b8c6", "d1h5", "a7a6", "h5f7"]:
        board.push(chess.Move.from_uci(uci))
    assert board.is_checkmate()

    history = ["e4", "e5", "Bc4", "Nc6", "Qh5", "a6", "Qxf7#"]
    payload = build_payload(board, history, "single", 800, "white")

    assert payload["status"] == "checkmate"
    assert "Checkmate" in payload["message"]


def test_broadcast_payload_resignation():
    """When game_end_override signals a resignation, status should be 'resigned'."""
    board = chess.Board()
    override = ("0-1", "White resigns. Black wins!")
    payload = build_payload(board, [], "single", 1600, "white",
                            game_end_override=override)

    assert payload["status"] == "resigned"
    assert payload["message"] == "White resigns. Black wins!"


def test_broadcast_payload_draw_by_agreement():
    """Draw-by-agreement override should produce 'draw' status."""
    board = chess.Board()
    override = ("1/2-1/2", "Game drawn by agreement.")
    payload = build_payload(board, [], "double", None, None,
                            game_end_override=override)

    assert payload["status"] == "draw"
    assert payload["message"] == "Game drawn by agreement."


# ---------------------------------------------------------------------------
# GameBroadcaster singleton
# ---------------------------------------------------------------------------

def test_get_broadcaster_returns_singleton():
    """get_broadcaster() must always return the same instance."""
    b1 = get_broadcaster()
    b2 = get_broadcaster()
    assert b1 is b2


def test_broadcaster_initial_waiting_state():
    """A fresh broadcaster should expose a 'waiting' payload."""
    broadcaster = GameBroadcaster()
    assert broadcaster._last_payload["status"] == "waiting"
    assert broadcaster._last_payload["mode"] is None
