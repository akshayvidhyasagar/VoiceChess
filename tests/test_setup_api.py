"""tests/test_setup_api.py — Verify /api/setup endpoint functionality.

Follows the same pytest conventions as the rest of the test suite:
  - plain functions, no classes
  - explicit asserts with descriptive names
  - no I/O, no subprocesses
"""

from fastapi.testclient import TestClient
from server import app, game_setup


# ---------------------------------------------------------------------------
# Setup endpoint — valid requests
# ---------------------------------------------------------------------------

def test_setup_endpoint_valid_request():
    """POST /api/setup with valid config returns {status: ok, game_started: true}."""
    client = TestClient(app)
    payload = {
        "input_mode": "voice",
        "game_mode": "single",
        "elo": 1600,
        "human_color": "white",
    }
    response = client.post("/api/setup", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["game_started"] is True


def test_setup_endpoint_populates_config():
    """Posting to /api/setup populates the game_setup dict correctly."""
    client = TestClient(app)
    payload = {
        "input_mode": "voice",
        "game_mode": "single",
        "elo": 1800,
        "human_color": "black",
    }
    client.post("/api/setup", json=payload)

    # Verify the game_setup dict was populated
    assert game_setup["input_mode"] == "voice"
    assert game_setup["game_mode"] == "single"
    assert game_setup["elo"] == 1800
    assert game_setup["human_color"] == "black"
    assert game_setup["ready"] is True


def test_setup_endpoint_double_mode_no_elo():
    """Double mode (human vs human) works without elo parameter."""
    client = TestClient(app)
    payload = {
        "input_mode": "voice",
        "game_mode": "double",
    }
    response = client.post("/api/setup", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["game_started"] is True

    # Verify the dict was populated (elo and human_color may be None)
    assert game_setup["input_mode"] == "voice"
    assert game_setup["game_mode"] == "double"


# ---------------------------------------------------------------------------
# Play again endpoint
# ---------------------------------------------------------------------------

def test_play_again_endpoint_yes():
    """POST /api/play-again with 'yes' resets config and sets ready=False."""
    client = TestClient(app)

    # First, set up a game
    setup_payload = {
        "input_mode": "voice",
        "game_mode": "single",
        "elo": 1600,
        "human_color": "white",
    }
    client.post("/api/setup", json=setup_payload)

    # Verify game is ready
    assert game_setup["ready"] is True
    assert game_setup["input_mode"] == "voice"

    # User chooses to play again
    play_again_payload = {"choice": "yes"}
    response = client.post("/api/play-again", json=play_again_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

    # Verify game_setup was reset: all config to None, ready to False
    assert game_setup["input_mode"] is None
    assert game_setup["game_mode"] is None
    assert game_setup["elo"] is None
    assert game_setup["human_color"] is None
    assert game_setup["ready"] is False


def test_play_again_endpoint_no():
    """POST /api/play-again with 'no' returns ok status without modifying state."""
    client = TestClient(app)

    # First, set up a game
    setup_payload = {
        "input_mode": "voice",
        "game_mode": "single",
        "elo": 1800,
        "human_color": "black",
    }
    client.post("/api/setup", json=setup_payload)

    # Store the state before play-again
    state_before = {
        "input_mode": game_setup["input_mode"],
        "game_mode": game_setup["game_mode"],
        "elo": game_setup["elo"],
        "human_color": game_setup["human_color"],
        "ready": game_setup["ready"],
    }

    # User chooses not to play again
    play_again_payload = {"choice": "no"}
    response = client.post("/api/play-again", json=play_again_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

    # Verify state was not modified (frontend will handle the close)
    assert game_setup["input_mode"] == state_before["input_mode"]
    assert game_setup["game_mode"] == state_before["game_mode"]
    assert game_setup["elo"] == state_before["elo"]
    assert game_setup["human_color"] == state_before["human_color"]
    assert game_setup["ready"] == state_before["ready"]
