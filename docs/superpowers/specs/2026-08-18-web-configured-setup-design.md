# Web-Configured Setup for VoiceChess — Design

## Problem

VoiceChess currently requires terminal interaction for game setup: the backend thread calls `input()` to prompt for:
- Input mode selection (push-to-talk vs fully voice)
- Game mode (human vs computer, human vs human)
- Difficulty (ELO 800–3000)
- Color choice (white, black, random)
- Play-again confirmation

This couples the backend to the terminal and prevents the browser from being the primary interface. The goal is to move all setup to a Next.js wizard, eliminating every `input()` call from voicerecognition.py and making the browser the exclusive control surface for game initialization.

## Solution Overview

**Approach: Poll-Based with Shared Config Dict**

1. Frontend: New setup wizard in browser (4 steps)
2. Backend: Polls a shared config dict until frontend populates it
3. Audio: Browser captures via MediaRecorder, detects silence via Web Audio API, sends to backend for Whisper
4. Handoff: POST `/api/setup` unblocks the backend thread; game starts; WebSocket broadcasts state
5. End of game: POST `/api/play-again` resets state; loop returns to setup wait

This approach is minimal—no major thread restructuring, no queues, just a read-once config dict after the thread wakes up.

---

## Architecture

### Shared State Model (server.py)

```python
# Global config dict — frontend populates, backend reads once
game_setup = {
    "input_mode": None,      # "ptt" | "voice"
    "game_mode": None,       # "single" | "double"
    "elo": None,             # int (800–3000) if game_mode === "single"
    "human_color": None,     # "white" | "black" | "random"
    "ready": False,          # Flag to unblock voicerecognition.py thread
    "play_again": None,      # "yes" | "no" (set by play-again endpoint)
}
```

**Thread Safety:** Reads/writes are atomic primitives (bool, str, int); no locks needed for this small dict.

### Backend Thread Lifecycle

1. **Startup:** `_run_game_loop()` imports voicerecognition.py in a background daemon thread
2. **Setup Wait:** New function `web_wait_for_setup()` loops `time.sleep(0.5)` until `game_setup["ready"] == True`
3. **Read Config:** Extract all 4 values from dict in one step; set `ready = False` for next cycle
4. **Game Run:** Pass values to existing game loop; run board/move logic as-is
5. **Game End:** Broadcast final state via WebSocket; set a flag (e.g., `game_over = True`)
6. **Loop:** Return to step 2

**No `input()` calls anywhere** in this flow.

### Frontend Wizard Flow

1. **Permission Request** (Step 0): "Please grant microphone access"
   - Once granted, proceed to wizard

2. **Input Mode Selection** (Step 1): Radio buttons or toggle
   - "Push-to-Talk (hold spacebar)" → `input_mode = "ptt"`
   - "Fully Voice (hands-free)" → `input_mode = "voice"`

3. **Game Mode Selection** (Step 2): Radio buttons
   - "Human vs Computer" → `game_mode = "single"`, show step 3
   - "Human vs Human" → `game_mode = "double"`, skip step 3

4. **Match Customization** (Step 3, only if vs Computer):
   - **Difficulty Slider:** ELO 800–3000
     - Visual presets: "Beginner" (800–1200), "Intermediate" (1200–1800), "Advanced" (1800–2400), "Master" (2400–3000)
   - **Color Selector:** Three buttons "White" / "Random" / "Black"

5. **Confirmation** (Step 4): "Ready to play?"
   - Display summary of chosen settings
   - "Start Game" button → POST `/api/setup`

**On Success:** Close wizard, show game board, connect to `/ws/game`

---

## API Endpoints

### POST /api/setup

**Request:**
```json
{
  "input_mode": "ptt" | "voice",
  "game_mode": "single" | "double",
  "elo": 800,
  "human_color": "white" | "black" | "random"
}
```

**Response:**
```json
{
  "status": "ok",
  "game_started": true
}
```

**Side Effects:**
- Populate `game_setup` dict with all values
- Set `game_setup["ready"] = True`
- Unblock the backend thread's `web_wait_for_setup()` loop

---

### POST /api/play-again

**Request:**
```json
{
  "play_again": "yes" | "no"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

**Side Effects:**
- If `"yes"`: Reset `game_setup` to all `None` and `ready = False`; backend loops back to `web_wait_for_setup()`
- If `"no"`: Set idle flag or gracefully wind down; frontend shows "thanks for playing" and can reload

---

### POST /api/transcribe

**Request:** Form-data with `audio` file (WAV blob from browser)

**Response:**
```json
{
  "transcript": "e4",
  "confidence": 0.95
}
```

**Behavior:**
- Receives WAV blob from browser's MediaRecorder
- Runs Whisper transcription (same model, same vocabulary bias as current voicerecognition.py)
- Returns transcript string
- Fire-and-forget error handling: if transcription fails, return empty string; backend retries

---

### GET /api/setup-state (optional)

**Response:**
```json
{
  "input_mode": null | "ptt" | "voice",
  "game_mode": null | "single" | "double",
  "elo": null | 800..3000,
  "human_color": null | "white" | "black" | "random",
  "ready": false | true
}
```

**Purpose:** Debugging only—frontend can poll to verify backend received setup.

---

## Frontend Components

### SetupWizard.tsx

**State:**
```typescript
const [step, setStep] = useState(0);
const [inputMode, setInputMode] = useState<"ptt" | "voice" | null>(null);
const [gameMode, setGameMode] = useState<"single" | "double" | null>(null);
const [elo, setElo] = useState(1600);
const [humanColor, setHumanColor] = useState<"white" | "black" | "random">("random");
const [isSubmitting, setIsSubmitting] = useState(false);
```

**Methods:**
- `nextStep()`: Validate current step, advance to next
- `submitSetup()`: POST `/api/setup`, handle response, close wizard on success
- `renderStep()`: Switch on step number, render appropriate UI

**Validation:**
- Step 1: `inputMode` must be set
- Step 2: `gameMode` must be set
- Step 3 (if single): `elo` and `humanColor` must be set
- Step 4: All fields valid before enabling "Start Game"

---

### AudioRecorder.tsx

**Purpose:** Capture microphone audio in both PTT and Voice modes.

**Props:**
```typescript
interface AudioRecorderProps {
  mode: "ptt" | "voice";
  onTranscript: (transcript: string) => void;
  onError: (error: string) => void;
}
```

**Mode 1 (Push-to-Talk):**
- Button: "Hold to record"
- On `mousedown`: Start MediaRecorder, set state to "listening"
- On `mouseup`: Stop MediaRecorder, silence-detect, send WAV to `/api/transcribe`
- Visual feedback: Animated waveform or pulsing "listening" indicator

**Mode 2 (Fully Voice):**
- Auto-start on speech detection via Web Audio RMS threshold
- Continue recording through short pauses (~100ms)
- Auto-stop after ~2.5s of silence (threshold calibrated at startup)
- Optional "cancel" button to abort
- Visual feedback: Animated listening state → processing state

**Audio Details:**
- Capture at 16kHz (Whisper model standard)
- Encode to WAV format
- Send as form-data `multipart/form-data` with field name `audio`

**Error Handling:**
- Microphone unavailable: Display "Microphone not accessible"
- Network error on POST: Retry up to 3 times with exponential backoff
- Whisper timeout (>10s): Show "Audio processing took too long, please try again"
- Empty recording: Re-prompt for audio

---

## Backend (voicerecognition.py) Changes

### Functions to Remove

- `select_mode()` — entire function
- `choose_game_mode()` — entire function
- `choose_elo()` — entire function
- `choose_color()` — entire function
- `ask_play_again()` — entire function

### New Function: web_wait_for_setup()

```python
def web_wait_for_setup():
    """Wait for frontend to populate game_setup dict via /api/setup.
    Returns (input_mode, game_mode, elo, human_color) tuple.
    """
    import time
    global game_setup
    
    print("[Setup] Waiting for frontend to complete wizard...")
    while not game_setup["ready"]:
        time.sleep(0.5)
    
    # Read config once, then reset for next game
    result = (
        game_setup["input_mode"],
        game_setup["game_mode"],
        game_setup["elo"],
        game_setup["human_color"],
    )
    game_setup["ready"] = False
    print(f"[Setup] Received: mode={result[0]}, game={result[1]}, elo={result[2]}, color={result[3]}")
    return result
```

### Main Game Loop Changes

**Before (excerpt):**
```python
MODE = select_mode()
GAME_MODE, ELO, HUMAN_COLOR = choose_game_mode(), choose_elo(), choose_color()
```

**After:**
```python
MODE, GAME_MODE, ELO, HUMAN_COLOR = web_wait_for_setup()
```

**No other structural changes** to the game loop. Move input still goes through:
1. Audio capture (browser) → WAV blob
2. POST `/api/transcribe` → backend Whisper
3. Existing `test_whisper_accuracy()`, `WordsToMove()`, `tryMove()` pipeline

---

## Data Flow: Complete Sequence

```
┌─ Frontend ─────────────────────┐         ┌─ Backend ──────────────┐
│                                │         │                        │
│ 1. Load app                    │         │                        │
│    Show "Grant microphone"     │         │ 1. Thread starts       │
│                                │         │    web_wait_for_setup()│
│ 2. User grants permission      │         │    loops waiting...    │
│    Show SetupWizard            │         │                        │
│                                │         │                        │
│ 3. User completes 4 steps      │         │                        │
│    Click "Start Game"          │         │                        │
│                                │         │                        │
│ 4. POST /api/setup ────────────┼────────►│ game_setup populated   │
│    ↓                           │         │ ready = True           │
│                                │         │ ↓                      │
│ 5. Connect WebSocket /ws/game  │         │ Read config once       │
│    ↓                           │         │ Start game loop        │
│                                │         │ ↓                      │
│ 6. Game board appears          │         │ 2. Game running        │
│    AudioRecorder ready         │         │    Broadcasting moves  │
│                                │         │                        │
│ 7. Each turn:                  │         │ 3. On each turn:       │
│    User speaks move            │         │    Waiting for audio   │
│    AudioRecorder captures      │         │                        │
│    → POST /api/transcribe ────►│    ┌───►│ Whisper transcription  │
│    ← Response: transcript      │◄───┘    │ Move validation        │
│                                │         │ Board update           │
│                                │         │ Broadcast state        │
│    Move appears on board       │         │                        │
│                                │         │                        │
│ 8. Game ends                   │         │ 4. Game over           │
│    WebSocket receives final    │         │    Set game_over flag  │
│    state                       │         │ (awaiting play_again)  │
│                                │         │                        │
│ 9. Show "Play Again?" dialog   │         │                        │
│    User clicks "Yes"           │         │                        │
│                                │         │                        │
│ 10. POST /api/play-again ─────►│        │ Reset game_setup       │
│     ↓                          │         │ ready = False          │
│     Loop back to step 1        │         │ ↓                      │
│     (SetupWizard reappears)    │         │ Loop back to step 1    │
│                                │         │ (web_wait_for_setup)   │
└────────────────────────────────┘         └────────────────────────┘
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| **Microphone permission denied** | Frontend shows alert; user can reload and retry |
| **Whisper transcription fails** | Backend logs error; game loop re-prompts for next speech (no keyboard fallback) |
| **Audio upload timeout (>10s)** | Frontend retries POST `/api/transcribe` up to 3 times |
| **Empty audio recording** | AudioRecorder re-prompts; no timeout penalty |
| **WebSocket disconnects mid-game** | Frontend shows "Connection lost" overlay; can reconnect to `/ws/game` and resume viewing |
| **Backend thread crashes** | Server logs error; frontend can retry `/api/setup` to restart |
| **Network error on /api/setup** | Frontend shows alert; user can retry or reload |
| **Backend already in game (setup.ready already True)** | Second `/api/setup` call is ignored; no concurrent games |

**Timeouts:**
- Silence detection (browser): ~2.5s silence threshold (same as current `silence_detector.py`)
- Whisper processing (backend): assume <3s for typical chess move phrase
- POST `/api/transcribe`: 10s client-side timeout with up to 3 retries
- `web_wait_for_setup()` polling: indefinite (frontend is responsible for completing wizard)

---

## Testing Strategy

### Backend Tests (Python)

1. **Unit: `web_wait_for_setup()`**
   - Mock `game_setup` dict; verify function waits until `ready = True`
   - Verify it reads all 4 values and returns correct tuple
   - Verify it resets `ready = False` for next cycle

2. **Integration: `/api/setup` endpoint**
   - POST valid setup config
   - Verify `game_setup` dict is populated
   - Verify response is `{"status": "ok"}`
   - Verify backend thread reads config (via logging or state inspection)

3. **Integration: `/api/transcribe` endpoint**
   - Upload sample WAV files (no actual Whisper—mock it)
   - Verify response format is `{"transcript": "...", "confidence": ...}`
   - Test error cases: malformed request, timeout simulation

### Frontend Tests (TypeScript/Vitest)

1. **Unit: `SetupWizard` component**
   - Verify each step renders correct UI
   - Verify step validation (e.g., can't advance without selecting input mode)
   - Verify form submission calls `POST /api/setup` with correct payload

2. **Unit: `AudioRecorder` component**
   - Mock `MediaRecorder` API
   - Verify PTT mode: starts on mousedown, stops on mouseup
   - Verify Voice mode: triggers on speech detection, stops on silence
   - Verify WAV encoding and form-data submission

3. **Integration: Setup → Game State**
   - Mock `/api/setup` and `/ws/game` endpoints
   - Verify wizard closes after successful POST
   - Verify WebSocket connects and receives board state

### Manual Testing (End-to-End)

1. **Setup Flow:**
   - Start server and frontend
   - Grant microphone permission
   - Complete all 4 wizard steps
   - Verify "Start Game" transitions to board view

2. **PTT Mode Gameplay:**
   - Hold "Hold to record" button
   - Speak a move (e.g., "e4")
   - Release button
   - Verify move appears on board

3. **Voice Mode Gameplay:**
   - Speak a move
   - Verify auto-detect (no button)
   - Verify move appears on board

4. **Play Again Flow:**
   - Finish a game
   - Verify "Play Again?" dialog appears
   - Click "Yes"
   - Verify wizard reappears
   - Complete new game

5. **Error Cases:**
   - Unplug/disable microphone mid-game
   - Disconnect browser network
   - Speak unintelligible audio
   - Verify error messages are user-friendly

---

## Out of Scope

- Wake-word activation (uses silence detection as established in two-input-modes)
- Browser-based move confirmation (game loop decides; frontend is spectator)
- Pause/resume in the browser (Mode 2's voice-based pause/resume remains in backend)
- Player-to-player chat or messaging
- Persistent game history or statistics dashboard
- Mobile responsiveness (design targets desktop browser)

---

## Success Criteria

1. ✓ Zero `input()` calls in voicerecognition.py
2. ✓ All game setup flows through browser wizard
3. ✓ Browser captures audio via MediaRecorder; backend runs Whisper
4. ✓ Full game loop runs without terminal interaction
5. ✓ Play-again resets and returns to setup wizard
6. ✓ Both PTT and Voice modes available in wizard
7. ✓ WebSocket broadcasts game state throughout; frontend remains spectator
8. ✓ Existing two-input-modes logic (mode selection, confirm/repeat, pause/resume) intact
