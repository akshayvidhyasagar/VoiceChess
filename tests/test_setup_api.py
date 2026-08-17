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
