# Two Input Modes: Push-to-Talk and Fully Voice — Design

## Problem

VoiceChess currently supports exactly one input flow: hold spacebar to record a move,
release to stop, then press Enter to confirm what was heard (or type anything to redo).
This requires a keyboard for two of the three interaction points (starting/stopping
recording, and confirming a move).

The goal is to offer two selectable modes:

1. **Push-to-talk** — today's existing flow, unchanged, formalized as a named mode.
2. **Fully voice** — no keyboard at any point during play. Recording starts/stops
   automatically via silence detection, and confirming/repeating a heard move is done
   by speaking "confirm" or "repeat" rather than pressing Enter.

## Mode selection

Every session starts with a spoken prompt, regardless of which mode ends up selected —
this lets the same code path pick the mode without assuming a keyboard is available:

```python
speak("Say push to talk, or say fully voice.")
```

The response is captured with the new auto-silence recorder (see below), transcribed,
and matched against keywords:

- "push to talk" / "push-to-talk" / "spacebar" → **Mode 1 (push-to-talk)**
- "voice" / "fully voice" / "hands free" → **Mode 2 (fully voice)**
- Unrecognized → re-prompt and listen again (no keyboard fallback here either, for
  consistency — this is a small, low-stakes loop).

### Self-test

The existing one-time mic/speaker self-test (a TTS→Whisper roundtrip check — it does
not actually exercise the physical microphone) is retained in both modes:

- **Mode 1**: unchanged. Typed prompts ("Press Enter to test...", "Type a move to
  speak back...").
- **Mode 2**: voice-driven. `speak("Say test to check your mic, or say skip.")`,
  listens for the answer via `record_auto()`. If "test," it runs the roundtrip using a
  fixed default phrase ("e4") — no typing a custom phrase — and speaks the result. If
  "skip," proceeds straight to the game. Any other/unrecognized response re-prompts
  once more (same low-stakes re-prompt pattern as mode selection above).

After mode selection (and self-test), the rest of the session proceeds entirely within
the chosen mode.

## New primitive: `record_auto()`

A silence-detection recording function, parallel to the existing spacebar-driven
`record()`. Used throughout Mode 2 (mode selection, self-test, move capture,
confirm/repeat responses, pause/resume).

Behavior:

- Streams mic input via `sounddevice`, computing RMS energy over short (~100ms) chunks.
- **Waiting for speech**: if no speech is detected (RMS below threshold) within ~8s of
  starting, gives up and returns `None` — same signal `record()` gives today when
  nothing was captured (e.g. key tapped instantly).
- **Recording**: once speech starts, keeps recording through pauses. Only stops after
  ~2.5s of continuous silence following detected speech. This generous threshold is
  intentional — it allows mid-move thinking pauses without cutting the recording short.
- **Safety cap**: hard maximum recording duration (~20s) regardless of the above, so a
  stuck-open mic or continuous background noise can't record indefinitely.
- **Threshold calibration**: performs a brief ambient-noise calibration once at program
  startup (not on every call) to set speech/silence RMS thresholds relative to the
  room's actual noise floor, rather than relying on a fixed constant that may not suit
  every mic/room.

Return value and calling convention mirror `record()` (returns a filename or `None`) so
downstream code (`test_whisper_accuracy`, etc.) doesn't need to know which recorder
produced the file.

## Mode 2 turn flow

Replaces the "hold space → confirm with Enter" sequence with:

1. `speak(f"{mover} to move.")` — necessary in Mode 2 since there's no spacebar press
   to signal readiness; this is the player's cue that it's their turn.
2. `record_auto()` → transcribe with Whisper (same `build_prompt()` vocabulary bias as
   today). The transcript is checked for command keywords first (`undo`, `resign`,
   `draw`, `pause` — see below), then parsed as a move via the existing
   `WordsToMove()` / `tryMove()` pipeline.
3. If a move parses successfully:
   - `speak(f"I heard {spoken_san(...)}. Say confirm or repeat.")`
   - `record_auto()` again to capture the response, transcribe it.
   - "confirm" / "yes" / "correct" → commit the move (`board.push`, existing
     `speak(f"{mover} plays ...")` announcement).
   - "repeat" / "no" / "redo" → discard the heard move, go back to step 2 and listen
     for the move again from scratch.
   - Unrecognized response → `speak("Please say confirm or repeat.")` and listen again
     at step 3 (does not count as a failure, does not go back to step 2).
4. If nothing was recorded (`record_auto()` returned `None`) or the transcript didn't
   parse into a legal move → `speak("Sorry, please say your move again.")` and loop
   back to step 2.

There is **no typed fallback** in Mode 2. Per explicit decision, voice retry continues
indefinitely rather than escaping to the keyboard after N failures — this preserves the
"fully voice" guarantee even in noisy conditions, at the cost of a session that could in
theory loop for a while in a bad audio environment.

## Commands in Mode 2

`undo`, `resign`, and `draw` are detected exactly as they are today — keyword-checked
in the transcript before move-parsing is attempted — carried over unchanged into the
`record_auto()` path.

**`pause`** is new, checked at the same point in the transcript:

- `speak("Game paused. Say resume to continue.")`
- Enters a wait loop: repeatedly calls `record_auto()` — silently, without re-prompting
  between attempts — discarding any transcript that doesn't contain "resume."
- Board state and turn are frozen for the duration; nothing else is processed while
  paused.
- Once "resume" is heard: `speak(f"Resuming. {mover} to move.")` and returns to the
  normal turn flow (step 2 above).

`pause`/`resume` is Mode-2-only. Mode 1 keeps its existing typed/spoken `undo` /
`resign` / `draw` support unchanged and does not gain a `pause` command — it already
has a keyboard available for that kind of session control, and it wasn't requested.

## Code structure

Mode 1 and Mode 2 share nearly everything: move parsing (`tryMove`, `WordsToMove`),
TTS (`speak`, `spoken_san`), Whisper transcription (`test_whisper_accuracy`,
`build_prompt`), and PGN export (`save_pgn`). The fork between modes is isolated to:

- **Input capture**: `record()` (spacebar) vs. `record_auto()` (silence detection).
- **Confirmation**: `input()`-based Enter-to-confirm vs. spoken confirm/repeat loop.
- **Failure handling**: typed fallback after N fails (Mode 1) vs. indefinite voice
  retry (Mode 2).
- **Commands**: Mode 2 adds `pause`/`resume`.

A `mode` variable (`"ptt"` or `"voice"`), set once during mode selection, drives
branching at exactly these points inside the existing game loop — the loop is not
duplicated wholesale for each mode.

## Out of scope

- Wake-word activation (rejected in favor of silence detection).
- Fixed-duration recording windows (rejected in favor of silence detection).
- Typed fallback in Mode 2 (explicitly rejected — voice retries indefinitely instead).
- `pause`/`resume` support in Mode 1 (not requested; Mode 1 retains keyboard-based
  control).
