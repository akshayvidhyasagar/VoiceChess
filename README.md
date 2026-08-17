# VoiceChess

Play chess against yourself, a friend, or a **Stockfish AI opponent** using nothing but your voice. Hold spacebar, say your move, and it gets transcribed, validated, and played on a text board — with spoken confirmation read back to you.

## How it works

1. **Game mode**, chosen by voice at startup:
   - **Human vs Human**: two players take turns speaking moves on the same machine.
   - **Human vs Computer**: you play against a local [Stockfish](https://stockfishchess.org/) engine at an adjustable ELO rating.
2. **Two input modes**, chosen by voice:
   - **Push-to-talk**: hold the spacebar to record, release to stop (via `pynput`, no fixed time limit), then press Enter to confirm.
   - **Fully voice**: no keyboard at all. Recording starts and stops automatically via silence detection, and you confirm or redo a heard move by saying "confirm" or "repeat".
3. **Speech-to-text**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) transcribes what you said, primed with a vocabulary hint that's rebuilt every turn from the actual legal moves on the board (better accuracy as the game narrows down).
4. **Parsing**: the transcript ("knight to f3", "e4", "castle kingside") is converted into standard algebraic notation and validated with [python-chess](https://python-chess.readthedocs.io/).
5. **Confirmation**: before a move is committed, you're asked to confirm what was heard — say the wrong thing and it just re-records instead of silently pushing a bad move.
6. **Spoken feedback**: [edge-tts](https://github.com/rany2/edge-tts) + `afplay` announce each move and the final result out loud.

## Requirements

- macOS (uses `afplay` for audio playback, and the push-to-talk listener needs macOS's Input Monitoring permission)
- Python 3.9+
- A microphone
- [Stockfish](https://stockfishchess.org/) (for Human vs Computer mode)

## Setup

```bash
pip install -r requirements.txt
```

**Install Stockfish** (required for vs-computer mode):

```bash
brew install stockfish        # macOS via Homebrew (recommended)
# or download from https://stockfishchess.org/download/
```

By default, VoiceChess auto-detects Stockfish from your `PATH`. If you installed it to a custom location, set the `STOCKFISH_PATH` environment variable:

```bash
export STOCKFISH_PATH=/path/to/stockfish
python3 voicerecognition.py
```

On first run, macOS will need **Input Monitoring** access granted to your terminal app so the spacebar can be detected globally (System Settings → Privacy & Security → Input Monitoring).

## Running

```bash
python3 voicerecognition.py
```

At startup you will be guided by voice through:
1. **Game mode** — say "human" / "human vs human" or "computer" / "play computer"
2. *(vs Computer only)* **Difficulty** — say a level name or an ELO number (see table below)
3. *(vs Computer only)* **Your colour** — say "white" or "black"
4. **Input mode** — say "push to talk" or "fully voice"

## ELO / Difficulty presets (vs Computer)

| You say | ELO | Strength |
|---|---|---|
| "beginner" | 800 | Very easy — makes many blunders |
| "easy" | 1000 | Casual club level |
| "medium" / "intermediate" | 1500 | Solid amateur |
| "hard" | 2000 | Strong club player |
| "expert" | 2500 | Near master level |
| "maximum" / "max" | 3000 | Full Stockfish strength |
| *(number)* e.g. "1200" | 1200 | Any value 800–3000 |

## Controls during play

- **Push-to-talk mode**: hold SPACE to speak your move, release when done, then press Enter to confirm. Say or type **"undo"**/**"resign"**/**"draw"**. After 3 failed recognition attempts in a row, it falls back to typing the move directly.
- **Fully voice mode**: no keyboard needed. Speak your move when prompted, then say **"confirm"** or **"repeat"**. Say **"undo"**, **"resign"**, **"draw"**, or **"pause"** (then **"resume"** to continue) at any time.
- **Ctrl+C** to quit — the game is saved as a `.pgn` file either way.

## Requirements (dev)

To run the unit test suite: `pip install -r requirements-dev.txt`, then `python3 -m pytest tests/ -v`.

## Voice command examples

| You say | Interpreted as |
|---|---|
| "e4" | `e4` |
| "knight to f3" | `Nf3` |
| "bishop b5" | `Bb5` |
| "rook takes e5" | `Rxe5` |
| "castle kingside" | `O-O` |
| "castle queenside" | `O-O-O` |

## Output

Each game is saved as a timestamped `game_YYYYMMDD_HHMMSS.pgn` file in the project directory when it ends or is quit.

---

## Web UI (live board display)

A **Next.js frontend** connects to a **FastAPI WebSocket server** and shows the live board as moves are made by voice. The board is read-only — voice remains the only way to move pieces.

### Architecture

```
voicerecognition.py  ──push_state()──►  broadcast.py  ──WebSocket──►  Next.js frontend
  (voice/game loop)                      (broadcaster)                 (display only)
```

### Running the FastAPI server

```bash
# Install server dependencies (one-time)
pip install -r requirements-server.txt

# Start the server (also starts the voice game loop in a background thread)
python server.py
```

The server listens on `http://localhost:8000`. Useful endpoints:
- `GET /health` — liveness check
- `GET /state` — current game snapshot (JSON)
- `WebSocket /ws/game` — live updates; connects immediately and pushes on every move

### Running the Next.js frontend

```bash
cd frontend
npm install         # one-time
npm run dev         # starts at http://localhost:3000
```

Open `http://localhost:3000` in a browser. The board will show "Waiting for game to start…" until the first voice game begins, then update in real-time.

### How they connect

The frontend reads the backend URL from the `NEXT_PUBLIC_WS_URL` environment variable:

| Environment | Value |
|---|---|
| Local dev (default) | `ws://localhost:8000/ws/game` |
| Production (Vercel → Render) | `wss://your-api.onrender.com/ws/game` |

For local dev this is pre-configured in `frontend/.env.local`. No changes needed.

### Deployment (Vercel + Render)

**Backend (Render):**
1. Create a new **Web Service** pointing to this repo.
2. Build command: `pip install -r requirements.txt -r requirements-server.txt`
3. Start command: `python server.py`
4. Set environment variables:
   - `ALLOWED_ORIGINS=https://your-app.vercel.app` (comma-separated if multiple)
   - `PORT=8000` (Render sets this automatically)

**Frontend (Vercel):**
1. Import this repo into Vercel, set **Root Directory** to `frontend`.
2. Set environment variable:
   - `NEXT_PUBLIC_WS_URL=wss://your-api.onrender.com/ws/game`

> **CORS note**: The FastAPI server reads `ALLOWED_ORIGINS` to set Access-Control headers. Add your Vercel domain (e.g. `https://voicechess.vercel.app`) to this variable on Render so the browser allows the WebSocket connection from a different origin.

### Running frontend tests

```bash
cd frontend
npm test
```
