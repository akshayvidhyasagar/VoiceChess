# VoiceChess

Play chess against yourself (or a friend, over the board) using nothing but your voice. Hold spacebar, say your move, and it gets transcribed, validated, and played on a text board — with spoken confirmation read back to you.

## How it works

1. **Two input modes**, chosen by voice at startup:
   - **Push-to-talk**: hold the spacebar to record, release to stop (via `pynput`, no fixed time limit), then press Enter to confirm.
   - **Fully voice**: no keyboard at all. Recording starts and stops automatically via silence detection, and you confirm or redo a heard move by saying "confirm" or "repeat".
2. **Speech-to-text**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) transcribes what you said, primed with a vocabulary hint that's rebuilt every turn from the actual legal moves on the board (better accuracy as the game narrows down).
3. **Parsing**: the transcript ("knight to f3", "e4", "castle kingside") is converted into standard algebraic notation and validated with [python-chess](https://python-chess.readthedocs.io/).
4. **Confirmation**: before a move is committed, you're asked to confirm what was heard — say the wrong thing and it just re-records instead of silently pushing a bad move.
5. **Spoken feedback**: [edge-tts](https://github.com/rany2/edge-tts) + `afplay` announce each move and the final result out loud.

## Requirements

- macOS (uses `afplay` for audio playback, and the push-to-talk listener needs macOS's Input Monitoring permission)
- Python 3.9+
- A microphone

## Setup

```bash
pip install -r requirements.txt
```

On first run, macOS will need **Input Monitoring** access granted to your terminal app so the spacebar can be detected globally (System Settings → Privacy & Security → Input Monitoring).

## Running

```bash
python3 voicerecognition.py
```

You'll be offered a one-time mic/speaker self-test, then the game begins. Controls during play:

- At startup, say **"push to talk"** or **"fully voice"** to pick your mode.
- **Push-to-talk mode**: hold SPACE to speak your move, release when done, then press Enter to confirm. Say or type **"undo"**/**"resign"**/**"draw"**. After 3 failed recognition attempts in a row, it falls back to typing the move directly.
- **Fully voice mode**: no keyboard needed. Speak your move when prompted, then say **"confirm"** or **"repeat"**. Say **"undo"**, **"resign"**, **"draw"**, or **"pause"** (then **"resume"** to continue) at any time.
- **Ctrl+C** to quit — the game is saved as a `.pgn` file either way

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
