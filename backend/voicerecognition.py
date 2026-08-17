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
from speech_matching import (
    match_mode_selection,
    match_self_test_response,
    match_confirm_response,
    detect_command,
    match_game_mode,
    parse_elo,
    match_color_selection,
)
from stockfish_engine import StockfishBot, find_stockfish

# Broadcast hook — imported lazily so voicerecognition.py still works
# standalone (without the server deps installed).
try:
    from broadcast import get_broadcaster as _get_broadcaster
    _BROADCAST_ENABLED = True
except ImportError:
    _BROADCAST_ENABLED = False

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

# Game-session context — includes timing and voice panel properties
_game_context = {
    "mode": None,
    "elo": None,
    "human_color": None,
    "end_override": None,
    "start_time": None,      # float: time.time() when game started
    "move_start_time": None, # float: time.time() when current turn began
    "white_time": 0.0,       # cumulative seconds white has spent on moves
    "black_time": 0.0,       # cumulative seconds black has spent on moves
    "mic_status": "idle",    # "idle" | "listening" | "processing"
    "last_transcript": None, # last heard speech segment
}


def _broadcast_state() -> None:
    """Push current board state to all connected WebSocket clients.
    Fire-and-forget: never raises, never blocks the game loop."""
    if not _BROADCAST_ENABLED:
        return
    try:
        # Determine global MODE (ptt vs voice) to broadcast as input_mode
        # If MODE is not yet set at top-level execution, use None.
        input_mode = None
        try:
            input_mode = MODE
        except NameError:
            pass

        _get_broadcaster().push_state(
            board,
            move_history,
            _game_context["mode"],
            _game_context["elo"],
            _game_context["human_color"],
            _game_context["end_override"],
            start_time=_game_context["start_time"],
            white_time=_game_context["white_time"],
            black_time=_game_context["black_time"],
            input_mode=input_mode,
            mic_status=_game_context["mic_status"],
            last_transcript=_game_context["last_transcript"],
        )
    except Exception:
        pass  # UI is optional; never let it affect the game

def _tick_move_clock() -> None:
    """Accumulate elapsed time for whoever just moved, then reset the clock."""
    now = time.time()
    if _game_context["move_start_time"] is not None:
        elapsed = now - _game_context["move_start_time"]
        # board.turn has already flipped after board.push(), so the mover was the OTHER side
        if board.turn == chess.WHITE:       # black just moved
            _game_context["black_time"] += elapsed
        else:                               # white just moved
            _game_context["white_time"] += elapsed
    _game_context["move_start_time"] = now


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
    _tick_move_clock()    # update per-player timing
    _broadcast_state()    # push immediately — don't wait for next loop iteration
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
    _game_context["move_start_time"] = time.time()  # reset clock for re-do
    _broadcast_state()   # push immediately

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
    """
    _game_context["mic_status"] = "listening"
    _broadcast_state()

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

    _game_context["mic_status"] = "processing"
    _broadcast_state()

    if not state["started"]:
        print("[Mic] No SPACE press detected. If this keeps happening, grant your terminal app")
        print("      'Input Monitoring' access in System Settings > Privacy & Security, then restart it.")
        _game_context["mic_status"] = "idle"
        _broadcast_state()
        return None

    if not chunks:
        print("[Mic] Recording was empty (released too fast).")
        _game_context["mic_status"] = "idle"
        _broadcast_state()
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
    
    # Save transcript and reset mic state
    _game_context["last_transcript"] = transcribed_text
    _game_context["mic_status"] = "idle"
    _broadcast_state()
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


def choose_game_mode():
    speak("Say single player or double player.")
    print("Prompt: Say single player or double player.")
    while True:
        if MODE == "ptt":
            typed = input("Type 'single' or 'double' (or press Enter to record via SPACE): ").strip()
            if typed:
                choice = match_game_mode(typed)
                if choice:
                    return choice
            else:
                audio_file = record()
                if audio_file:
                    text = test_whisper_accuracy(audio_file, "single player, double player, versus bot, computer, two players")
                    choice = match_game_mode(text)
                    if choice:
                        return choice
        else:
            audio_file = record_auto()
            if audio_file:
                text = test_whisper_accuracy(audio_file, "single player, double player, versus bot, computer, two players")
                choice = match_game_mode(text)
                if choice:
                    return choice
        speak("Sorry, I didn't catch that. Say single player or double player.")


def choose_elo():
    speak("Say the bot's rating, or say beginner, intermediate, advanced, or master.")
    print("Prompt: Say rating (e.g. 1500) or beginner/intermediate/advanced/master.")
    while True:
        if MODE == "ptt":
            typed = input("Type rating (or press Enter to record via SPACE): ").strip()
            if typed:
                val = parse_elo(typed)
                if val is not None:
                    if 100 <= val <= 3200:
                        return val
                    print(f"Rating {val} is out of range. Please choose between 100 and 3200.")
                    speak("Rating out of range. Choose between 100 and 3200.")
                    continue
            else:
                audio_file = record()
                if audio_file:
                    text = test_whisper_accuracy(audio_file, "beginner, intermediate, advanced, master, rating, elo, 800, 1200, 1400, 1600, 1800, 2000, 2600")
                    val = parse_elo(text)
                    if val is not None:
                        if 100 <= val <= 3200:
                            return val
                        speak(f"Rating {val} is out of range. Choose between 100 and 3200.")
                        continue
        else:
            audio_file = record_auto()
            if audio_file:
                text = test_whisper_accuracy(audio_file, "beginner, intermediate, advanced, master, rating, elo, 800, 1200, 1400, 1600, 1800, 2000, 2600")
                val = parse_elo(text)
                if val is not None:
                    if 100 <= val <= 3200:
                        return val
                    speak("Rating out of range. Choose between 100 and 3200.")
                    continue
        speak("Sorry, please select a rating between 100 and 3200.")


def choose_color():
    speak("Say white, black, or random to choose your color.")
    print("Prompt: Say white, black, or random.")
    while True:
        if MODE == "ptt":
            typed = input("Type 'white', 'black', or 'random' (or press Enter to record via SPACE): ").strip()
            if typed:
                choice = match_color_selection(typed)
                if choice:
                    if choice == "random":
                        import random
                        return random.choice(["white", "black"])
                    return choice
            else:
                audio_file = record()
                if audio_file:
                    text = test_whisper_accuracy(audio_file, "white, black, random, either, any")
                    choice = match_color_selection(text)
                    if choice:
                        if choice == "random":
                            import random
                            return random.choice(["white", "black"])
                        return choice
        else:
            audio_file = record_auto()
            if audio_file:
                text = test_whisper_accuracy(audio_file, "white, black, random, either, any")
                choice = match_color_selection(text)
                if choice:
                    if choice == "random":
                        import random
                        return random.choice(["white", "black"])
                    return choice
        speak("Sorry, please select white, black, or random.")


def ask_play_again():
    speak("Would you like to play another game?")
    print("Would you like to play another game? Say yes or no.")
    while True:
        if MODE == "ptt":
            typed = input("Type 'yes' or 'no' (or press Enter to record via SPACE): ").strip().lower()
            if typed:
                if typed in ("yes", "y"):
                    return True
                if typed in ("no", "n"):
                    return False
            else:
                audio_file = record()
                if audio_file:
                    text = test_whisper_accuracy(audio_file, "yes, no")
                    if "yes" in text.lower():
                        return True
                    if "no" in text.lower():
                        return False
        else:
            audio_file = record_auto()
            if audio_file:
                text = test_whisper_accuracy(audio_file, "yes, no")
                if "yes" in text.lower():
                    return True
                if "no" in text.lower():
                    return False
        speak("Sorry, please say yes or no.")


BOT_TIME_LIMIT = 0.5
BOT_MAX_DEPTH = 15

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

def wait_for_resume():
    """Mode 2 only: freezes the game and listens (silently, no re-prompt
    spam between attempts) until the player says "resume"."""
    speak("Game paused. Say resume to continue.")
    while True:
        audio_file = record_auto()
        if audio_file is None:
            continue
        text = test_whisper_accuracy(audio_file, "resume")
        if "resume" in text.lower():
            return

def play_game(game_mode, elo=1600, human_color="white"):
    global board, move_history, game_end_override
    
    board = chess.Board()
    move_history = []
    game_end_override = None

    # Update broadcast context for the new game
    _game_context["mode"] = game_mode
    _game_context["elo"] = elo if game_mode == "single" else None
    _game_context["human_color"] = human_color if game_mode == "single" else None
    _game_context["end_override"] = None
    _game_context["start_time"] = time.time()
    _game_context["move_start_time"] = time.time()
    _game_context["white_time"] = 0.0
    _game_context["black_time"] = 0.0
    _broadcast_state()  # Announce game start
    
    bot = None
    if game_mode == "single":
        try:
            bot = StockfishBot(elo=elo)
        except Exception as e:
            err_msg = str(e)
            print(err_msg)
            speak("Error starting Stockfish. Falling back to double player mode.")
            game_mode = "double"

    if MODE == "ptt":
        print("\nGame started. Hold SPACE to speak your move on your turn.")
        print("Say 'undo' to take back a move, 'resign' to forfeit, or 'draw' to end in a draw. Ctrl+C to quit.")
    else:
        print("\nGame started in fully-voice mode. Listen for the prompt, then speak your move.")
        print("Say 'undo', 'resign', 'draw', or 'pause' at any time. Ctrl+C to quit.")

    try:
        while not board.is_game_over() and game_end_override is None:
            print()
            print(board)
            if move_history:
                print(f"Moves so far: {format_history()}")
            
            mover = "White" if board.turn else "Black"
            print(f"\n{mover} to move.")
            # Note: state is already broadcast immediately after each move/undo.
            # This broadcast covers the very first turn (no prior move yet).
            if not move_history:
                _broadcast_state()
            
            # Check if it is the bot's turn
            is_bot_turn = (
                game_mode == "single" and
                ((board.turn == chess.WHITE and human_color == "black") or
                 (board.turn == chess.BLACK and human_color == "white"))
            )
            
            if is_bot_turn:
                print("Stockfish is thinking...")
                speak("Stockfish is thinking.")
                bot_move = bot.get_move(board, time_limit=BOT_TIME_LIMIT, depth_limit=BOT_MAX_DEPTH)
                san = board.san(bot_move)
                board.push(bot_move)
                move_history.append(san)
                _tick_move_clock()   # update timing
                _broadcast_state()   # push immediately — before TTS
                print(f"\nStockfish plays {san}")
                speak(f"{mover} plays {spoken_san(san)}")
                continue

            if MODE == "voice":
                speak(f"{mover} to move.")
            
            Moved = False
            fail_count = 0
            while not Moved and game_end_override is None:
                if MODE == "ptt":
                    if fail_count >= MAX_FAILS_BEFORE_TYPED_FALLBACK:
                        typed = input("\nHaving trouble hearing you — type your move directly (or 'undo'/'resign'/'draw'): ").strip()
                        if not typed:
                            fail_count = 0
                            continue
                        command = detect_command(typed)
                        if command == "undo":
                            if game_mode == "single":
                                undo_last_move()
                                undo_last_move()
                            else:
                                undo_last_move()
                            break
                        if command == "resign":
                            declare_resignation(mover)
                            break
                        if command == "draw":
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
                    command = detect_command(DetectedText)
                    if command == "undo":
                        if game_mode == "single":
                            undo_last_move()
                            undo_last_move()
                        else:
                            undo_last_move()
                        break
                    if command == "resign":
                        declare_resignation(mover)
                        break
                    if command == "draw":
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

                else:  # MODE == "voice"
                    audio_file = record_auto()
                    if audio_file is None:
                        speak("Sorry, please say your move again.")
                        continue

                    DetectedText = test_whisper_accuracy(audio_file, build_prompt())
                    command = detect_command(DetectedText)
                    if command == "undo":
                        if game_mode == "single":
                            undo_last_move()
                            undo_last_move()
                        else:
                            undo_last_move()
                        speak("Move undone.")
                        break
                    if command == "resign":
                        declare_resignation(mover)
                        break
                    if command == "draw":
                        declare_draw_by_agreement()
                        break
                    if command == "pause":
                        wait_for_resume()
                        speak(f"Resuming. {mover} to move.")
                        continue

                    if not DetectedText:
                        speak("Sorry, please say your move again.")
                        continue

                    realMove = WordsToMove(DetectedText)
                    if not realMove:
                        speak("Sorry, please say your move again.")
                        continue

                    speak(f"I heard {realMove}. Say confirm or repeat.")
                    confirmed = None
                    while confirmed is None:
                        response_audio = record_auto()
                        response_text = test_whisper_accuracy(response_audio, "confirm, repeat") if response_audio else ""
                        confirmed = match_confirm_response(response_text)
                        if confirmed is None:
                            speak("Please say confirm or repeat.")

                    if confirmed == "repeat":
                        continue

                    Moved = tryMove(realMove)
                    if not Moved:
                        speak("That's not a legal move. Please say your move again.")
                    else:
                        speak(f"{mover} plays {spoken_san(move_history[-1])}")
    except KeyboardInterrupt:
        print("\nGame abandoned.")
        save_pgn()
        if bot:
            bot.close()
        raise SystemExit
    finally:
        if bot:
            bot.close()

    if game_end_override:
        result, message = game_end_override
        _game_context["end_override"] = game_end_override
        _broadcast_state()  # Broadcast final resigned/drawn state
        save_pgn(result_override=result)
        print()
        print(board)
        print(f"\n{message}")
        speak(message)
    else:
        _broadcast_state()  # Broadcast checkmate/stalemate/draw
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


def web_wait_for_setup():
    """Wait for frontend to populate game_setup dict via /api/setup.

    Polls the shared game_setup dict until ready=True, then reads all values
    in one atomic operation and resets ready for the next game cycle.

    Returns: (input_mode, game_mode, elo, human_color) tuple
    """
    # Import here to avoid circular dependency
    try:
        from server import game_setup
    except ImportError:
        print("[ERROR] Cannot import game_setup from server.py")
        raise

    print("[Setup] Waiting for frontend wizard to complete...")
    while not game_setup["ready"]:
        time.sleep(0.5)

    # Read all values once, atomically
    result = (
        game_setup["input_mode"],
        game_setup["game_mode"],
        game_setup["elo"],
        game_setup["human_color"],
    )

    # Reset for next game
    game_setup["ready"] = False

    print(f"[Setup] Received: input_mode={result[0]}, game_mode={result[1]}, "
          f"elo={result[2]}, human_color={result[3]}")

    return result


try:
    while True:
        # Get setup configuration from browser wizard via /api/setup
        input_mode, game_mode, elo, human_color = web_wait_for_setup()

        # Set global MODE for the game loop to use
        MODE = input_mode

        if game_mode == "single":
            speak(f"Starting a game against Stockfish rated {elo}.")
            print(f"Starting a game against Stockfish rated {elo}.")
            play_game(game_mode, elo=elo, human_color=human_color)
        else:
            play_game(game_mode, human_color=human_color)

        # Loop back to waiting for next game setup
except SystemExit:
    pass
except KeyboardInterrupt:
    print("\nGame abandoned.")


