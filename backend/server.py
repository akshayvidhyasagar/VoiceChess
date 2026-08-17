"""server.py — FastAPI WebSocket bridge for VoiceChess.

Architecture
------------
* FastAPI runs the asyncio event loop on the MAIN thread (uvicorn).
* The voice/game loop (voicerecognition.py) runs in a BACKGROUND thread
  started here via ``threading.Thread``.
* ``broadcast.py`` bridges them without either side importing the other.

Run locally:
    python server.py

Or via uvicorn directly (for Render deployment):
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading

import tempfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from broadcast import get_broadcaster

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="VoiceChess API", version="1.0.0")

# CORS — allow the Next.js dev server and the deployed Vercel frontend.
# Set ALLOWED_ORIGINS env var to a comma-separated list for production.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Shared state — game setup configuration
# ---------------------------------------------------------------------------

game_setup = {
    "input_mode": None,
    "game_mode": None,
    "elo": None,
    "human_color": None,
    "ready": False,
}


# ---------------------------------------------------------------------------
# Lifecycle — register the running event loop with the broadcaster
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    loop = asyncio.get_running_loop()
    get_broadcaster().set_loop(loop)
    # Start the game loop in a daemon background thread so it doesn't
    # block the server from shutting down cleanly.
    # Skip during tests (PYTEST_CURRENT_TEST env var is set by pytest)
    if not os.getenv("PYTEST_CURRENT_TEST"):
        t = threading.Thread(target=_run_game_loop, daemon=True, name="game-loop")
        t.start()


def _run_game_loop() -> None:
    """Import and run voicerecognition.py inside the background thread.

    Importing the module runs the top-level game loop (it's a script).
    We catch SystemExit so a 'quit' command doesn't kill the server.
    """
    try:
        # Add the repo root to sys.path so the import resolves correctly
        # regardless of cwd.
        repo_root = os.path.dirname(os.path.abspath(__file__))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        import voicerecognition  # noqa: F401 — side-effectful import
    except SystemExit:
        pass
    except Exception as exc:
        print(f"[server] Game loop exited with error: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/setup")
async def setup(config: dict) -> dict:
    """Receive game setup configuration from the browser.

    Populates the shared game_setup dict and signals the backend thread to proceed.
    Immediately broadcasts an in_progress state so the frontend transitions to the board.
    """
    global game_setup
    game_setup["input_mode"] = config.get("input_mode")
    game_setup["game_mode"] = config.get("game_mode")
    game_setup["elo"] = config.get("elo")
    game_setup["human_color"] = config.get("human_color")
    game_setup["ready"] = True

    print(f"[setup] Received config: input_mode={config.get('input_mode')}, "
          f"game_mode={config.get('game_mode')}, elo={config.get('elo')}, "
          f"human_color={config.get('human_color')}")

    # Immediately push an in_progress state so the frontend transitions to the board
    # before the game loop thread even picks up the config.
    broadcaster = get_broadcaster()
    import chess as _chess
    _board = _chess.Board()
    broadcaster.push_state(
        board=_board,
        move_history=[],
        game_mode=config.get("game_mode"),
        elo=config.get("elo"),
        human_color=config.get("human_color"),
        game_end_override=None,
        start_time=None,
        white_time=0.0,
        black_time=0.0,
        input_mode=config.get("input_mode"),
        mic_status="idle",
        last_transcript=None,
    )
    # Patch the status to in_progress so the gate flips
    broadcaster._last_payload["status"] = "in_progress"

    return {"status": "ok", "game_started": True}


@app.post("/api/play-again")
async def play_again(request: dict) -> dict:
    """Handle the end-of-game 'play again' choice.

    If play_again is 'yes': reset game_setup dict to allow new game configuration.
    If play_again is 'no': log the exit; frontend handles close.
    """
    global game_setup
    user_choice = request.get("play_again")

    if user_choice == "yes":
        # Reset all config to None and ready to False so we loop back to setup
        game_setup["input_mode"] = None
        game_setup["game_mode"] = None
        game_setup["elo"] = None
        game_setup["human_color"] = None
        game_setup["ready"] = False
        # Reset broadcaster to waiting so frontend shows wizard again
        get_broadcaster()._last_payload["status"] = "waiting"
        get_broadcaster()._last_payload["mode"] = None
        print("[play-again] User chose to play again; game_setup reset")
    elif user_choice == "no":
        print("[play-again] User chose to exit")

    return {"status": "ok"}


# Global Whisper model (lazy-loaded on first transcribe call or when voicerecognition thread loads it)
_whisper_model = None
_prompt_string = (
    "K, N, Q, B, R, Castle Queenside, Castle Kingside, Check, Checkmate, "
    "King, Queen, Knight, Bishop, Rook, Pawn, takes, a, b, c, d, e, f, g, h, "
    "a1, a2, a3, a4, a5, a6, a7, a8, b1, b2, b3, b4, b5, b6, b7, b8, "
    "c1, c2, c3, c4, c5, c6, c7, c8, d1, d2, d3, d4, d5, d6, d7, d8, "
    "e1, e2, e3, e4, e5, e6, e7, e8, f1, f2, f3, f4, f5, f6, f7, f8, "
    "g1, g2, g3, g4, g5, g6, g7, g8, h1, h2, h3, h4, h5, h6, h7, h8"
)


def _get_whisper_model():
    """Get the Whisper model, loading it if necessary.

    Safe retrieval of the model from loaded voicerecognition or direct lazy-load.
    """
    global _whisper_model

    if _whisper_model is not None:
        return _whisper_model, _prompt_string

    # Check if voicerecognition is already imported in sys.modules to avoid circular/side-effect importing hangs
    import sys
    if "voicerecognition" in sys.modules:
        vr = sys.modules["voicerecognition"]
        if hasattr(vr, "model") and vr.model is not None:
            return vr.model, getattr(vr, "prompt_string", _prompt_string)

    # Otherwise, initialize a dedicated instance for server transcribe endpoint
    from faster_whisper import WhisperModel
    _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model, _prompt_string


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict:
    """Receive audio WAV blob, run Whisper transcription, return transcript.

    Accepts WAV files via form-data (form field: "audio").
    Returns JSON: {"transcript": "...", "confidence": 0.95}
    On error: {"transcript": "", "confidence": 0.0}
    """
    try:
        # Get the Whisper model (from voicerecognition if available, or load directly)
        model, prompt_string = _get_whisper_model()

        # Browsers (Chrome/Safari) produce WebM/Opus via MediaRecorder, not real WAV.
        # Detect the actual format from Content-Type and give the temp file the right
        # extension so faster-whisper's ffmpeg demuxer picks the right container.
        content_type = audio.content_type or "audio/webm"
        if "wav" in content_type:
            suffix = ".wav"
        elif "mp4" in content_type or "m4a" in content_type:
            suffix = ".mp4"
        elif "ogg" in content_type:
            suffix = ".ogg"
        else:
            suffix = ".webm"  # Default: Chrome/Edge/Safari all produce WebM

        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
        try:
            # Read the uploaded file and write to temp file
            contents = await audio.read()
            os.write(temp_fd, contents)
            os.close(temp_fd)

            # Run Whisper transcription — vad_filter=True skips silence regions,
            # beam_size=1 is 4x faster than beam_size=5 with minimal accuracy loss
            # for short chess move commands.
            segments, info = model.transcribe(
                temp_path,
                language="en",
                vad_filter=True,
                beam_size=1,
                initial_prompt=prompt_string,
            )

            # Extract transcript from segments
            transcribed_text = " ".join([segment.text for segment in segments]).strip()

            # Return 0.0 confidence for empty transcripts
            confidence = 0.95 if transcribed_text else 0.0
            return {"transcript": transcribed_text, "confidence": confidence}
        finally:
            # Always clean up the temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        # Log error but never raise — return empty transcript instead
        print(f"[transcribe] Error: {e}", file=sys.stderr)
        return {"transcript": "", "confidence": 0.0}


@app.get("/state")
async def current_state() -> dict:
    """Return the current game snapshot (useful for debugging / initial HTTP poll)."""
    return get_broadcaster()._last_payload


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/game")
async def websocket_game(websocket: WebSocket) -> None:
    await websocket.accept()

    broadcaster = get_broadcaster()
    queue: asyncio.Queue = asyncio.Queue(maxsize=32)

    # Send the current snapshot immediately on connect.
    snapshot = await broadcaster.connect(queue)
    await websocket.send_text(json.dumps(snapshot))

    try:
        while True:
            # Wait for a new state update pushed by the game loop.
            payload = await queue.get()
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await broadcaster.disconnect(queue)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
