# Two Input Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a selectable "fully voice" input mode (no keyboard at any point) alongside the existing push-to-talk mode, per `docs/superpowers/specs/2026-08-17-two-input-modes-design.md`.

**Architecture:** Extract the new text-matching logic (mode selection, confirm/repeat, command detection) and the new silence-detection recording engine into two small, independently testable modules (`speech_matching.py`, `silence_detector.py`). `voicerecognition.py` imports both and branches its startup and main game loop on a `MODE` variable set once at program start via a spoken prompt.

**Tech Stack:** Python 3.9+, `pytest` (new, dev-only dependency) for unit tests, existing `sounddevice`/`numpy`/`faster-whisper`/`edge-tts` stack, unchanged.

---

## File Structure

- Create: `speech_matching.py` — pure text-matching functions, no I/O. Unit tested.
- Create: `silence_detector.py` — `compute_thresholds()` and `SilenceDetector` (pure, unit tested) plus `record_auto()` (I/O glue wiring the detector to `sounddevice`, mirrors the existing untested `record()` — not unit tested for the same reason `record()` isn't).
- Create: `tests/test_speech_matching.py`, `tests/test_silence_detector.py`
- Create: `pytest.ini`, `requirements-dev.txt`
- Modify: `voicerecognition.py` — import the new modules; replace the self-test block with mode selection + mode-aware self-test; replace the main game loop's inner attempt logic with a `MODE`-branched version; add `wait_for_resume()`.
- Modify: `README.md` — document both modes.

---

### Task 1: Test tooling setup

**Files:**
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `tests/` (directory, via first test file)

- [ ] **Step 1: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0.0
```

- [ ] **Step 2: Create `pytest.ini` at repo root**

```ini
[pytest]
pythonpath = .
```

This lets `tests/*.py` do `import speech_matching` / `import silence_detector` without needing `__init__.py` files, since those modules live at the repo root.

- [ ] **Step 3: Install dev dependencies**

Run: `pip install -r requirements-dev.txt`
Expected: `pytest` installs successfully alongside the existing runtime deps.

- [ ] **Step 4: Commit**

```bash
git add requirements-dev.txt pytest.ini
git commit -m "Add pytest dev dependency and config for unit testing"
```

---

### Task 2: `speech_matching.py` — `match_mode_selection()`

**Files:**
- Create: `speech_matching.py`
- Test: `tests/test_speech_matching.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_speech_matching.py`:

```python
from speech_matching import match_mode_selection


def test_match_mode_selection_push_to_talk():
    assert match_mode_selection("push to talk") == "ptt"
    assert match_mode_selection("I want push-to-talk please") == "ptt"
    assert match_mode_selection("use the spacebar") == "ptt"


def test_match_mode_selection_fully_voice():
    assert match_mode_selection("fully voice") == "voice"
    assert match_mode_selection("I want to go hands free") == "voice"
    assert match_mode_selection("voice") == "voice"


def test_match_mode_selection_unrecognized():
    assert match_mode_selection("banana") is None
    assert match_mode_selection("") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_speech_matching.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'speech_matching'`

- [ ] **Step 3: Write minimal implementation**

Create `speech_matching.py`:

```python
"""Pure text-matching helpers for voice command interpretation.

These operate on already-transcribed text and contain no I/O, so they're
unit-testable without a microphone or the Whisper model.
"""


def _normalize(text):
    return "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())


def match_mode_selection(text):
    """Returns "ptt", "voice", or None."""
    normalized = _normalize(text)
    if "push to talk" in normalized or "spacebar" in normalized or "space bar" in normalized:
        return "ptt"
    if "voice" in normalized or "hands free" in normalized:
        return "voice"
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_speech_matching.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add speech_matching.py tests/test_speech_matching.py
git commit -m "Add match_mode_selection() for spoken mode selection"
```

---

### Task 3: `speech_matching.py` — `match_self_test_response()`

**Files:**
- Modify: `speech_matching.py`
- Modify: `tests/test_speech_matching.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_speech_matching.py`:

```python
from speech_matching import match_self_test_response


def test_match_self_test_response():
    assert match_self_test_response("let's test it") == "test"
    assert match_self_test_response("skip") == "skip"
    assert match_self_test_response("please skip the test") == "skip"
    assert match_self_test_response("banana") is None
```

(Combine the `from speech_matching import ...` lines at the top of the file into one import statement rather than repeating them.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_speech_matching.py::test_match_self_test_response -v`
Expected: FAIL with `ImportError: cannot import name 'match_self_test_response'`

- [ ] **Step 3: Write minimal implementation**

Append to `speech_matching.py`:

```python
def match_self_test_response(text):
    """Returns "test", "skip", or None. "skip" takes priority since a
    sentence mentioning both ("skip the test") means skip."""
    normalized = _normalize(text)
    if "skip" in normalized:
        return "skip"
    if "test" in normalized:
        return "test"
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_speech_matching.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add speech_matching.py tests/test_speech_matching.py
git commit -m "Add match_self_test_response() for voice-driven self-test"
```

---

### Task 4: `speech_matching.py` — `match_confirm_response()`

**Files:**
- Modify: `speech_matching.py`
- Modify: `tests/test_speech_matching.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_speech_matching.py`:

```python
from speech_matching import match_confirm_response


def test_match_confirm_response():
    assert match_confirm_response("confirm") == "confirm"
    assert match_confirm_response("yes that's right") == "confirm"
    assert match_confirm_response("correct") == "confirm"
    assert match_confirm_response("repeat") == "repeat"
    assert match_confirm_response("no, that's wrong") == "repeat"
    assert match_confirm_response("redo it") == "repeat"
    assert match_confirm_response("banana") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_speech_matching.py::test_match_confirm_response -v`
Expected: FAIL with `ImportError: cannot import name 'match_confirm_response'`

- [ ] **Step 3: Write minimal implementation**

Append to `speech_matching.py`:

```python
def match_confirm_response(text):
    """Returns "confirm", "repeat", or None."""
    normalized = _normalize(text)
    confirm_words = ("confirm", "yes", "correct", "right")
    repeat_words = ("repeat", "no", "redo", "wrong")
    if any(word in normalized for word in confirm_words):
        return "confirm"
    if any(word in normalized for word in repeat_words):
        return "repeat"
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_speech_matching.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add speech_matching.py tests/test_speech_matching.py
git commit -m "Add match_confirm_response() for voice confirm/repeat"
```

---

### Task 5: `speech_matching.py` — `detect_command()`

**Files:**
- Modify: `speech_matching.py`
- Modify: `tests/test_speech_matching.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_speech_matching.py`:

```python
from speech_matching import detect_command


def test_detect_command():
    assert detect_command("undo that") == "undo"
    assert detect_command("take back") == "undo"
    assert detect_command("takeback") == "undo"
    assert detect_command("I resign") == "resign"
    assert detect_command("let's draw") == "draw"
    assert detect_command("pause game") == "pause"
    assert detect_command("knight to f3") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_speech_matching.py::test_detect_command -v`
Expected: FAIL with `ImportError: cannot import name 'detect_command'`

- [ ] **Step 3: Write minimal implementation**

Append to `speech_matching.py`:

```python
def detect_command(text):
    """Returns "undo", "resign", "draw", "pause", or None.

    Mirrors the keyword checks previously duplicated between the typed and
    voice input paths in the game loop.
    """
    normalized = _normalize(text)
    if "undo" in normalized or "take back" in normalized or "takeback" in normalized:
        return "undo"
    if "resign" in normalized:
        return "resign"
    if "draw" in normalized:
        return "draw"
    if "pause" in normalized:
        return "pause"
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_speech_matching.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Tidy up imports and commit**

Consolidate the four separate `from speech_matching import ...` lines at the top of `tests/test_speech_matching.py` into:

```python
from speech_matching import (
    match_mode_selection,
    match_self_test_response,
    match_confirm_response,
    detect_command,
)
```

Run: `python3 -m pytest tests/test_speech_matching.py -v` — Expected: PASS (6 tests), confirming the import cleanup didn't break anything.

```bash
git add speech_matching.py tests/test_speech_matching.py
git commit -m "Add detect_command() for undo/resign/draw/pause detection"
```

---

### Task 6: `silence_detector.py` — `compute_thresholds()`

**Files:**
- Create: `silence_detector.py`
- Create: `tests/test_silence_detector.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_silence_detector.py`:

```python
import pytest
from silence_detector import compute_thresholds


def test_compute_thresholds_from_calibration_samples():
    speech, silence = compute_thresholds([0.01, 0.01, 0.01])
    assert speech == pytest.approx(0.04)
    assert silence == pytest.approx(0.02)


def test_compute_thresholds_falls_back_when_no_samples():
    speech, silence = compute_thresholds([])
    assert speech == pytest.approx(0.02)
    assert silence == pytest.approx(0.01)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_silence_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'silence_detector'`

- [ ] **Step 3: Write minimal implementation**

Create `silence_detector.py`:

```python
"""Silence-detection recording engine for hands-free (Mode 2) voice input.

compute_thresholds() and SilenceDetector are pure and unit-tested without
audio hardware. record_auto() (added in a later task) is the I/O glue that
wires the detector to a live sounddevice stream, mirroring the existing
spacebar-driven record() in voicerecognition.py.
"""


def compute_thresholds(calibration_rms_samples):
    """Derives speech/silence RMS thresholds from a short ambient-noise sample.

    Returns (speech_threshold, silence_threshold). Falls back to fixed
    defaults if calibration produced no samples (e.g. a silent input device).
    """
    if not calibration_rms_samples:
        return 0.02, 0.01
    baseline = sum(calibration_rms_samples) / len(calibration_rms_samples)
    baseline = max(baseline, 0.001)  # avoid a near-zero baseline making thresholds too sensitive
    return baseline * 4, baseline * 2
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_silence_detector.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add silence_detector.py tests/test_silence_detector.py
git commit -m "Add compute_thresholds() for ambient-noise calibration"
```

---

### Task 7: `silence_detector.py` — `SilenceDetector`

**Files:**
- Modify: `silence_detector.py`
- Modify: `tests/test_silence_detector.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_silence_detector.py`:

```python
from silence_detector import SilenceDetector


def test_no_speech_times_out():
    detector = SilenceDetector(speech_threshold=0.1, silence_threshold=0.05,
                                max_initial_wait=0.3, chunk_duration=0.1)
    results = [detector.feed(0.0) for _ in range(3)]
    assert results[-1] == "stop_timeout"


def test_speech_then_silence_stops():
    detector = SilenceDetector(speech_threshold=0.1, silence_threshold=0.05,
                                silence_hang_duration=0.3, chunk_duration=0.1)
    assert detector.feed(0.2) == "continue"        # speech starts
    assert detector.feed(0.0) == "continue"        # silence, 0.1s elapsed
    assert detector.feed(0.0) == "continue"        # silence, 0.2s elapsed
    assert detector.feed(0.0) == "stop_silence"     # silence, 0.3s elapsed


def test_pause_mid_speech_does_not_stop_early():
    detector = SilenceDetector(speech_threshold=0.1, silence_threshold=0.05,
                                silence_hang_duration=0.3, chunk_duration=0.1)
    assert detector.feed(0.2) == "continue"    # speaking
    assert detector.feed(0.0) == "continue"    # brief pause, 0.1s
    assert detector.feed(0.2) == "continue"    # speaking resumes, resets silence counter
    assert detector.feed(0.0) == "continue"    # silence again, 0.1s elapsed
    assert detector.feed(0.0) == "continue"    # silence, 0.2s elapsed
    assert detector.feed(0.0) == "stop_silence" # silence, 0.3s elapsed, now stops


def test_max_duration_cap_stops_even_during_speech():
    detector = SilenceDetector(speech_threshold=0.1, silence_threshold=0.05,
                                max_total_duration=0.3, chunk_duration=0.1)
    assert detector.feed(0.2) == "continue"
    assert detector.feed(0.2) == "continue"
    assert detector.feed(0.2) == "stop_max_duration"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_silence_detector.py -v`
Expected: FAIL with `ImportError: cannot import name 'SilenceDetector'`

- [ ] **Step 3: Write minimal implementation**

Append to `silence_detector.py`:

```python
DEFAULT_SILENCE_HANG_DURATION = 2.5  # seconds of continuous silence that ends a recording
DEFAULT_MAX_INITIAL_WAIT = 8.0       # seconds to wait for speech to start before giving up
DEFAULT_MAX_TOTAL_DURATION = 20.0    # hard cap regardless of speech/silence
DEFAULT_CHUNK_DURATION = 0.1         # seconds per RMS sample fed to the detector


class SilenceDetector:
    """Feed RMS values one chunk at a time; reports when to stop recording.

    The generous default silence_hang_duration (2.5s) is intentional: it
    lets a speaker pause mid-move to think without being cut off, while
    still ending the recording once they're actually done talking.
    """

    def __init__(self, speech_threshold, silence_threshold,
                 silence_hang_duration=DEFAULT_SILENCE_HANG_DURATION,
                 max_initial_wait=DEFAULT_MAX_INITIAL_WAIT,
                 max_total_duration=DEFAULT_MAX_TOTAL_DURATION,
                 chunk_duration=DEFAULT_CHUNK_DURATION):
        self.speech_threshold = speech_threshold
        self.silence_threshold = silence_threshold
        self.silence_hang_duration = silence_hang_duration
        self.max_initial_wait = max_initial_wait
        self.max_total_duration = max_total_duration
        self.chunk_duration = chunk_duration
        self.started = False
        self.silence_elapsed = 0.0
        self.total_elapsed = 0.0

    def feed(self, rms):
        """Returns "continue", "stop_timeout", "stop_silence", or "stop_max_duration"."""
        self.total_elapsed += self.chunk_duration

        if rms >= self.speech_threshold:
            self.started = True
            self.silence_elapsed = 0.0
        elif self.started:
            self.silence_elapsed += self.chunk_duration

        if self.total_elapsed >= self.max_total_duration:
            return "stop_max_duration"
        if not self.started and self.total_elapsed >= self.max_initial_wait:
            return "stop_timeout"
        if self.started and self.silence_elapsed >= self.silence_hang_duration:
            return "stop_silence"
        return "continue"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_silence_detector.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add silence_detector.py tests/test_silence_detector.py
git commit -m "Add SilenceDetector state machine for hands-free recording"
```

---

### Task 8: `silence_detector.py` — `record_auto()`

**Files:**
- Modify: `silence_detector.py`

This is I/O glue wired to real audio hardware (mirrors the existing, also-untested `record()` in `voicerecognition.py`). It's verified by import/syntax check here and by manual end-to-end testing in Task 11.

- [ ] **Step 1: Add the imports and function**

Add to the top of `silence_detector.py` (above the docstring's following code):

```python
import os
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
```

Append to `silence_detector.py`:

```python
def record_auto(sampleRate=16000, filename="recording_auto.wav"):
    """
    Hands-free recording: starts automatically once speech is detected,
    stops after a period of silence following that speech. Returns the
    filename, or None if no speech was detected before timing out.
    """
    chunks = []
    calibration_rms = []
    calibration_chunks_needed = 3  # ~0.3s of ambient noise sampled at stream start

    state = {"detector": None, "result": None}

    def audio_callback(indata, frames, time_info, status):
        rms = float(np.sqrt(np.mean(np.square(indata))))
        if state["detector"] is None:
            calibration_rms.append(rms)
            if len(calibration_rms) >= calibration_chunks_needed:
                speech_threshold, silence_threshold = compute_thresholds(calibration_rms)
                state["detector"] = SilenceDetector(speech_threshold, silence_threshold)
            return
        chunks.append(indata.copy())
        action = state["detector"].feed(rms)
        if action != "continue" and state["result"] is None:
            state["result"] = action

    blocksize = int(sampleRate * DEFAULT_CHUNK_DURATION)
    stream = sd.InputStream(samplerate=sampleRate, channels=1, dtype="float32",
                             blocksize=blocksize, callback=audio_callback)
    print("[Mic] Listening...")
    with stream:
        while state["result"] is None:
            sd.sleep(int(DEFAULT_CHUNK_DURATION * 1000))
    print(f"[Mic] Stopped ({state['result']}).")

    if state["result"] == "stop_timeout" or not chunks:
        return None

    audio = np.concatenate(chunks, axis=0).flatten()
    pcm = np.clip(audio, -1.0, 1.0)
    if os.path.exists(filename):
        os.remove(filename)
    wav.write(filename, sampleRate, (pcm * 32767).astype(np.int16))
    return filename
```

- [ ] **Step 2: Syntax/import check**

Run: `python3 -c "import silence_detector"`
Expected: no output, exit code 0 (confirms no syntax errors and all imports resolve)

- [ ] **Step 3: Run the full unit test suite to confirm nothing broke**

Run: `python3 -m pytest tests/ -v`
Expected: PASS (8 tests total — the `record_auto` addition doesn't add new unit tests since it's hardware I/O)

- [ ] **Step 4: Commit**

```bash
git add silence_detector.py
git commit -m "Add record_auto() hands-free recording function"
```

---

### Task 9: Wire mode selection and voice-driven self-test into `voicerecognition.py`

**Files:**
- Modify: `voicerecognition.py:1-26` (imports)
- Modify: `voicerecognition.py:266-283` (self-test block)

- [ ] **Step 1: Add imports**

In `voicerecognition.py`, after the existing `import subprocess` line (line 25), add:

```python
from silence_detector import record_auto
from speech_matching import match_mode_selection, match_self_test_response
```

- [ ] **Step 2: Replace the self-test block with mode selection + mode-aware self-test**

Find this block (`voicerecognition.py:266-283`):

```python
try:
    active_input = sd.query_devices(sd.default.device[0])["name"]
    print(f"[Mic] Using input device: {active_input} (change with sd.default.device if this is wrong)")
except Exception:
    pass

print(f"\nVoiceChess ready. {board.legal_moves.count()} legal opening moves.")
run_test = input("Press Enter to test your mic & speaker setup first, or type 's' to skip: ").strip().lower()
if run_test != "s":
    test_move = input("Type a move to speak back (default e4): ").strip() or "e4"
    asyncio.run(generate_chess_move_audio(test_move, "_selftest.wav"))
    heard = test_whisper_accuracy("_selftest.wav", prompt_string)
    print(f"Spoke: \"{test_move}\"  ->  Whisper heard: \"{heard}\"")
    if os.path.exists("_selftest.wav"):
        os.remove("_selftest.wav")
```

Replace it with:

```python
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
```

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile voicerecognition.py`
Expected: no output, exit code 0

- [ ] **Step 4: Run the unit test suite to confirm nothing broke**

Run: `python3 -m pytest tests/ -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add voicerecognition.py
git commit -m "Add spoken mode selection and voice-driven self-test"
```

---

### Task 10: Branch the main game loop on `MODE`

**Files:**
- Modify: `voicerecognition.py:1-26` (imports, continued from Task 9)
- Modify: `voicerecognition.py` (startup print messages, previously lines 282-283)
- Modify: `voicerecognition.py` (main game loop, previously lines 285-377)

- [ ] **Step 1: Add remaining imports**

In `voicerecognition.py`, extend the import line added in Task 9 to include the rest of `speech_matching`:

```python
from speech_matching import match_mode_selection, match_self_test_response, match_confirm_response, detect_command
```

(This replaces the `from speech_matching import match_mode_selection, match_self_test_response` line added in Task 9.)

- [ ] **Step 2: Replace the mode-specific startup print messages**

Find this block (previously `voicerecognition.py:282-283`, now shifted down by the Task 9 changes — locate by content):

```python
print("\nGame started. Hold SPACE to speak your move on your turn.")
print("Say 'undo' to take back a move, 'resign' to forfeit, or 'draw' to end in a draw. Ctrl+C to quit.")
```

Replace it with:

```python
if MODE == "ptt":
    print("\nGame started. Hold SPACE to speak your move on your turn.")
    print("Say 'undo' to take back a move, 'resign' to forfeit, or 'draw' to end in a draw. Ctrl+C to quit.")
else:
    print("\nGame started in fully-voice mode. Listen for the prompt, then speak your move.")
    print("Say 'undo', 'resign', 'draw', or 'pause' at any time. Ctrl+C to quit.")
```

- [ ] **Step 3: Replace the main game loop**

Find the `MAX_FAILS_BEFORE_TYPED_FALLBACK` block through the end of the `try/except KeyboardInterrupt` block (previously `voicerecognition.py:285-377`):

```python
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
```

Replace it with:

```python
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

try:
    while not board.is_game_over() and game_end_override is None:
        print()
        print(board)
        if move_history:
            print(f"Moves so far: {format_history()}")
        mover = "White" if board.turn else "Black"
        print(f"\n{mover} to move.")
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
    raise SystemExit
```

- [ ] **Step 4: Syntax check**

Run: `python3 -m py_compile voicerecognition.py`
Expected: no output, exit code 0

- [ ] **Step 5: Run the unit test suite to confirm nothing broke**

Run: `python3 -m pytest tests/ -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Commit**

```bash
git add voicerecognition.py
git commit -m "Branch main game loop on MODE for push-to-talk vs fully-voice play"
```

---

### Task 11: Manual end-to-end verification

**Files:** none (manual testing only — `record_auto()` and the live game loop depend on real audio hardware, which can't be exercised by an automated test)

- [ ] **Step 1: Run the app and select Mode 1 (push-to-talk)**

Run: `python3 voicerecognition.py`, say "push to talk" (or "spacebar") at the mode prompt.
Verify: self-test still uses typed prompts; hold-space-to-record and press-Enter-to-confirm behave exactly as before; `undo`/`resign`/`draw` still work, typed and spoken.

- [ ] **Step 2: Run the app and select Mode 2 (fully voice)**

Run: `python3 voicerecognition.py`, say "fully voice" (or "voice") at the mode prompt.
Verify:
- Self-test responds to spoken "test"/"skip".
- On your turn, it announces "White to move" (or Black), then starts listening without any key press.
- Recording stops shortly after you finish speaking, without cutting off a short mid-sentence pause.
- It reads back "I heard ...", and responds correctly to spoken "confirm" and spoken "repeat".
- Say "pause" mid-turn — verify it announces "Game paused" and waits; say "resume" — verify it announces resuming and returns to the same turn.
- Say "undo", "resign", and "draw" — verify each works the same as in Mode 1.

- [ ] **Step 2a: Tune silence-detection constants if needed**

If recordings cut off too early or too late during Step 2, adjust `DEFAULT_SILENCE_HANG_DURATION`, `DEFAULT_MAX_INITIAL_WAIT`, or the `compute_thresholds()` multipliers (`baseline * 4` / `baseline * 2`) in `silence_detector.py` based on what you observed, then re-run Step 2.

- [ ] **Step 3: Commit any tuning adjustments**

```bash
git add silence_detector.py
git commit -m "Tune silence-detection thresholds based on manual testing"
```

(Skip this step if no tuning was needed.)

---

### Task 12: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document both modes**

In `README.md`, replace the "How it works" section's first bullet and the "Controls during play" list to describe both modes. Replace:

```markdown
1. **Push-to-talk**: hold the spacebar to record, release to stop (via `pynput`, no fixed time limit).
```

with:

```markdown
1. **Two input modes**, chosen by voice at startup:
   - **Push-to-talk**: hold the spacebar to record, release to stop (via `pynput`, no fixed time limit), then press Enter to confirm.
   - **Fully voice**: no keyboard at all. Recording starts and stops automatically via silence detection, and you confirm or redo a heard move by saying "confirm" or "repeat".
```

Replace the "Controls during play" list:

```markdown
- **Hold SPACE** to speak your move, release when done
- Say or type **"undo"** to take back the last move
- After 3 failed recognition attempts in a row, it falls back to typing that move directly
- **Ctrl+C** to quit — the game is saved as a `.pgn` file either way
```

with:

```markdown
- At startup, say **"push to talk"** or **"fully voice"** to pick your mode.
- **Push-to-talk mode**: hold SPACE to speak your move, release when done, then press Enter to confirm. Say or type **"undo"**/**"resign"**/**"draw"**. After 3 failed recognition attempts in a row, it falls back to typing the move directly.
- **Fully voice mode**: no keyboard needed. Speak your move when prompted, then say **"confirm"** or **"repeat"**. Say **"undo"**, **"resign"**, **"draw"**, or **"pause"** (then **"resume"** to continue) at any time.
- **Ctrl+C** to quit — the game is saved as a `.pgn` file either way

## Requirements (dev)

To run the unit test suite: `pip install -r requirements-dev.txt`, then `python3 -m pytest tests/ -v`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Document push-to-talk and fully-voice modes in README"
```

---

## Self-Review Notes

- **Spec coverage:** mode selection (Task 9), voice-driven self-test (Task 9), silence-detection recording with forgiving mid-speech pauses (Tasks 6-8), confirm/repeat voice loop (Task 10), pause/resume (Task 10), indefinite voice retry with no typed fallback in Mode 2 (Task 10), Mode 1 left functionally unchanged (Task 10, `if MODE == "ptt"` branch preserves the original code paths verbatim) — all covered.
- **Type/name consistency:** `record_auto()`, `SilenceDetector`, `compute_thresholds()`, `match_mode_selection()`, `match_self_test_response()`, `match_confirm_response()`, `detect_command()` are named identically wherever referenced across tasks.
- **Known behavior change (intentional):** replacing the Mode 1 typed-command exact-match checks (`typed_lower in ("undo", "takeback", "take back")`) with `detect_command()`'s substring match makes typed commands slightly more forgiving (e.g. "please undo that" now works) — consistent with the existing voice-side substring matching it's replacing duplication of.
