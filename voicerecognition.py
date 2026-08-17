import os
import warnings

# Suppress Hugging Face symlink and token warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

import logging
logging.getLogger("huggingface_hub").setLevel(logging.ERROR) # Silences the internal logger

warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

import chess
import chess.pgn
from faster_whisper import WhisperModel
import numpy as np
import time
import scipy.io.wavfile as wav
import asyncio
import edge_tts
import sounddevice as sd
from pynput import keyboard as kb
import contextlib
import sys
import subprocess
from silence_detector import record_auto
from speech_matching import match_mode_selection, match_self_test_response

@contextlib.contextmanager
def suppress_native_stderr():
    """Silences macOS's native 'This process is not trusted!' accessibility
    warning, which Quartz prints directly to the fd 2 (not via Python)
    when pynput opens a global key-event tap without permission granted."""
    sys.stderr.flush()
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    saved_fd = os.dup(2)
    try:
        os.dup2(devnull_fd, 2)
        yield
    finally:
        sys.stderr.flush()
        os.dup2(saved_fd, 2)
        os.close(devnull_fd)
        os.close(saved_fd)

print("Loading speech model (this can take a few seconds)...")
model = WhisperModel("small", device="cpu", compute_type="int8")
board = chess.Board()


def LegalMoves():
    global board
    chess_hints = []
    legal_moves = [board.san(move) for move in board.legal_moves]
    for move in legal_moves:
        # Convert algebraic notation of piece to english word 
        clean_move = move.replace("K", "King ").replace("N", "Knight ").replace("B", "Bishop ").replace("R", "Rook ").replace("Q", "Queen ")
        if clean_move == move:
            clean_move = "Pawn "+move
        chess_hints.append(f"{move}, {clean_move}")
    return chess_hints

curr_hints = ["K", "N", "Q", "B", "R", "Castle Queenside", "Castle Kingside", "Check", "Checkmate",
              "King", "Queen", "Knight", "Bishop", "Rook", "Pawn", "takes"]
letters = ["a", "b", "c", "d", "e", "f", "g", "h"]

#Gives all squares as a prompt to whisper
squares = []
for i in range(0, 8):
    for j in range(1, 9):
        newStr = letters[i] + str(j);
        curr_hints.append(newStr)
        squares.append(newStr)
    curr_hints.append(letters[i])
prompt_string = ", ".join(curr_hints)# + ", castling, checkmate"

def build_prompt():
    """Bias Whisper towards whatever moves are actually legal right now
    (accuracy improves as the game narrows down), on top of the base vocabulary."""
    return ", ".join(curr_hints + LegalMoves())

move_history = []

def tryMove(move):
    global board
    try:
        valMove = board.parse_san(move)
    except ValueError:
        # Voice input never specifies a promotion piece (e.g. "e8"); SAN requires
        # one explicitly. If the bare move to the last rank is otherwise legal,
        # assume queen promotion — overwhelmingly the common choice — before rejecting.
        if move and move[-1] in "18" and move[-2:-1] != "=":
            try:
                valMove = board.parse_san(move + "=Q")
            except ValueError:
                valMove = None
        else:
            valMove = None

        if valMove is None:
            print(f"Rejected: \"{move}\" is not a legal move right now.")
            print(f"Current legal moves are: {', '.join([board.san(m) for m in board.legal_moves])}")
            return False

    san = board.san(valMove)
    board.push(valMove)
    move_history.append(san)
    return True

def format_history():
    parts = []
    for i, san in enumerate(move_history):
        parts.append(f"{i // 2 + 1}.{san}" if i % 2 == 0 else san)
    return " ".join(parts)

def undo_last_move():
    global board
    if not move_history:
        print("No moves to undo yet.")
        return
    board.pop()
    undone = move_history.pop()
    print(f"Undone: {undone}")

def spoken_san(san):
    """SAN's trailing +/# reads oddly through TTS as literal symbols; say them as words."""
    if san.endswith("#"):
        return san[:-1] + " checkmate"
    if san.endswith("+"):
        return san[:-1] + " check"
    return san

def speak(text, filename="_tts_out.mp3"):
    """Speaks text aloud via edge-tts + afplay (macOS). Best-effort: never blocks the game on failure."""
    try:
        asyncio.run(generate_chess_move_audio(text, filename))
        subprocess.run(["afplay", filename], check=False)
    except Exception as e:
        print(f"[TTS] Could not speak: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def save_pgn(result_override=None):
    if not move_history:
        return
    game = chess.pgn.Game.from_board(board)
    game.headers["Event"] = "VoiceChess Game"
    game.headers["Date"] = time.strftime("%Y.%m.%d")
    if result_override:
        game.headers["Result"] = result_override
    filename = time.strftime("game_%Y%m%d_%H%M%S.pgn")
    with open(filename, "w") as f:
        print(game, file=f)
    print(f"[PGN] Game saved to {filename}")

async def generate_chess_move_audio(text_command, filename="test_move.wav"):
    if os.path.exists(filename):
        os.remove(filename)
        print(f"[TTS] Deleted existing file: {filename}")
    print(f"[TTS] Generating speech for command: '{text_command}'...")
    
    communicate = edge_tts.Communicate(text_command, "en-US-AvaNeural")
    await communicate.save(filename)
    print(f"Audio saved to {filename}")
    return filename

def record(sampleRate=16000, filename="recording.wav", max_duration=20):
    """
    Push-to-talk: hold SPACE to record, release to stop.
    Returns the filename, or None if nothing was recorded
    (e.g. the key was tapped instantly, or listener permission is missing).
    """
    chunks = []
    state = {"active": False, "started": False}

    def audio_callback(indata, frames, time_info, status):
        if state["active"]:
            chunks.append(indata.copy())

    def on_press(key):
        if key == kb.Key.space and not state["active"]:
            state["active"] = True
            state["started"] = True
            print("\a[Mic] Recording... (release SPACE to stop)")

    def on_release(key):
        if key == kb.Key.space and state["active"]:
            state["active"] = False
            print("\a[Mic] Stopped.")
            return False  # stop the listener

    print("Hold SPACE to speak your move, release when done...")
    stream = sd.InputStream(samplerate=sampleRate, channels=1, dtype="float32", callback=audio_callback)
    with stream:
        listener = kb.Listener(on_press=on_press, on_release=on_release)
        with suppress_native_stderr():
            listener.start()
            listener.wait()  # blocks until the OS-level tap is actually created
        listener.join(timeout=max_duration)
        if listener.is_alive():
            state["active"] = False
            listener.stop()

    if not state["started"]:
        print("[Mic] No SPACE press detected. If this keeps happening, grant your terminal app")
        print("      'Input Monitoring' access in System Settings > Privacy & Security, then restart it.")
        return None

    if not chunks:
        print("[Mic] Recording was empty (released too fast).")
        return None

    audio = np.concatenate(chunks, axis=0).flatten()
    pcm = np.clip(audio, -1.0, 1.0)
    if os.path.exists(filename):
        os.remove(filename)
    wav.write(filename, sampleRate, (pcm * 32767).astype(np.int16))
    return filename

def test_whisper_accuracy(audio_file, prompt=None):
    global prompt_string
    global model

    segments, info = model.transcribe(audio_file, language="en", vad_filter=False, beam_size=5, initial_prompt=prompt or prompt_string)
    transcribed_text = " ".join([segment.text for segment in segments]).strip()

    print(f"[Whisper] Result: \"{transcribed_text}\"")
    return transcribed_text

def WordsToMove(Move):
    # Whisper punctuates ("E4." / "Knight to F3!"), which breaks the word lookups below
    Move = "".join(c if c.isalnum() or c.isspace() else " " for c in Move.lower())

    if "castle" in Move or "castling" in Move:
        return "O-O-O" if "queen" in Move else "O-O"

    ActualMove = ""
    if "knight" in Move:
        ActualMove += "N"
    elif "king" in Move:
        ActualMove += "K"
    elif "queen" in Move:
        ActualMove += "Q"
    elif "rook" in Move:
        ActualMove += "R"
    elif "bishop" in Move:
        ActualMove += "B"
    
    words = Move.split()
    for word in words:
        if word in letters:
            ActualMove += word
        else:
            try:
                num = int(word)
                if num < 9 and num > 0:
                    ActualMove += word
            except ValueError:
                continue

    for word in words:
        if word in squares:
            ActualMove += word

    return ActualMove

try:
    active_input = sd.query_devices(sd.default.device[0])["name"]
    print(f"[Mic] Using input device: {active_input} (change with sd.default.device if this is wrong)")
except Exception:
    pass

print(f"\nVoiceChess ready. {board.legal_moves.count()} legal opening moves.")


def select_mode():
    """Spoken prompt to choose between push-to-talk and fully-voice mode.
    Runs before any keyboard-vs-voice branching, since the mode itself
    hasn't been picked yet."""
    speak("Say push to talk, or say fully voice.")
    while True:
        audio_file = record_auto()
        text = test_whisper_accuracy(audio_file, "push to talk, fully voice, hands free, spacebar") if audio_file else ""
        choice = match_mode_selection(text)
        if choice:
            return choice
        speak("Sorry, I didn't catch that. Say push to talk, or say fully voice.")


MODE = select_mode()
print(f"Mode selected: {'Push-to-talk' if MODE == 'ptt' else 'Fully voice'}")

if MODE == "ptt":
    run_test = input("Press Enter to test your mic & speaker setup first, or type 's' to skip: ").strip().lower()
    if run_test != "s":
        test_move = input("Type a move to speak back (default e4): ").strip() or "e4"
        asyncio.run(generate_chess_move_audio(test_move, "_selftest.wav"))
        heard = test_whisper_accuracy("_selftest.wav", prompt_string)
        print(f"Spoke: \"{test_move}\"  ->  Whisper heard: \"{heard}\"")
        if os.path.exists("_selftest.wav"):
            os.remove("_selftest.wav")
else:
    speak("Say test to check your mic, or say skip.")
    while True:
        audio_file = record_auto()
        response_text = test_whisper_accuracy(audio_file, "test, skip") if audio_file else ""
        choice = match_self_test_response(response_text)
        if choice == "skip":
            break
        if choice == "test":
            test_move = "e4"
            asyncio.run(generate_chess_move_audio(test_move, "_selftest.wav"))
            heard = test_whisper_accuracy("_selftest.wav", prompt_string)
            print(f"Spoke: \"{test_move}\"  ->  Whisper heard: \"{heard}\"")
            speak(f"I said {test_move} and heard back {heard}")
            if os.path.exists("_selftest.wav"):
                os.remove("_selftest.wav")
            break
        speak("Sorry, say test to check your mic, or say skip.")

print("\nGame started. Hold SPACE to speak your move on your turn.")
print("Say 'undo' to take back a move, 'resign' to forfeit, or 'draw' to end in a draw. Ctrl+C to quit.")

MAX_FAILS_BEFORE_TYPED_FALLBACK = 3
game_end_override = None  # (pgn_result, spoken/printed message), set by resign/draw

def declare_resignation(resigning_side):
    global game_end_override
    winner = "Black" if resigning_side == "White" else "White"
    game_end_override = (
        "0-1" if winner == "Black" else "1-0",
        f"{resigning_side} resigns. {winner} wins!",
    )

def declare_draw_by_agreement():
    global game_end_override
    game_end_override = ("1/2-1/2", "Game drawn by agreement.")

try:
    while not board.is_game_over() and game_end_override is None:
        print()
        print(board)
        if move_history:
            print(f"Moves so far: {format_history()}")
        mover = "White" if board.turn else "Black"
        print(f"\n{mover} to move.")
        Moved = False
        fail_count = 0
        while not Moved and game_end_override is None:
            if fail_count >= MAX_FAILS_BEFORE_TYPED_FALLBACK:
                typed = input("\nHaving trouble hearing you — type your move directly (or 'undo'/'resign'/'draw'): ").strip()
                if not typed:
                    fail_count = 0
                    continue
                typed_lower = typed.lower()
                if typed_lower in ("undo", "takeback", "take back"):
                    undo_last_move()
                    break
                if typed_lower in ("resign", "i resign"):
                    declare_resignation(mover)
                    break
                if typed_lower in ("draw", "offer draw", "agree draw"):
                    declare_draw_by_agreement()
                    break
                Moved = tryMove(typed)
                if not Moved:
                    print("Please try again.")
                    speak("Illegal move, please try again.")
                else:
                    speak(f"{mover} plays {spoken_san(move_history[-1])}")
                fail_count = 0
                continue

            audio_file = record()
            if audio_file is None:
                fail_count += 1
                continue

            DetectedText = test_whisper_accuracy(audio_file, build_prompt())
            normalized = DetectedText.lower()
            if "undo" in normalized or "take back" in normalized or "takeback" in normalized:
                undo_last_move()
                break
            if "resign" in normalized:
                declare_resignation(mover)
                break
            if "draw" in normalized:
                declare_draw_by_agreement()
                break

            if not DetectedText:
                print("Didn't catch anything — please repeat your move.")
                fail_count += 1
                continue

            realMove = WordsToMove(DetectedText)
            if not realMove:
                print(f"Could not parse a move from: \"{DetectedText}\" — please repeat your move.")
                fail_count += 1
                continue

            confirm = input(f"Heard: {realMove} — press Enter to confirm, or type anything to redo: ").strip()
            if confirm:
                continue

            Moved = tryMove(realMove)
            if not Moved:
                print("Please repeat your move.")
                speak("Illegal move, please repeat.")
                fail_count += 1
            else:
                speak(f"{mover} plays {spoken_san(move_history[-1])}")
except KeyboardInterrupt:
    print("\nGame abandoned.")
    save_pgn()
    raise SystemExit

if game_end_override:
    result, message = game_end_override
    save_pgn(result_override=result)
    print()
    print(board)
    print(f"\n{message}")
    speak(message)
else:
    save_pgn()
    print()
    print(board)
    outcome = board.outcome()
    if outcome.winner is None:
        reason = outcome.termination.name.lower().replace('_', ' ')
        print(f"\nDraw by {reason}")
        speak(f"Game over. Draw by {reason}.")
    else:
        winner = "White" if outcome.winner else "Black"
        print("\nWinner: ", winner)
        speak(f"Game over. {winner} wins.")

