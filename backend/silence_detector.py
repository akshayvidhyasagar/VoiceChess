"""Silence-detection recording engine for hands-free (Mode 2) voice input.

compute_thresholds() and SilenceDetector are pure and unit-tested without
audio hardware. record_auto() (added in a later task) is the I/O glue that
wires the detector to a live sounddevice stream, mirroring the existing
spacebar-driven record() in voicerecognition.py.
"""

import os
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav


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


def record_auto(sampleRate=16000, filename="recording_auto.wav"):
    """
    Hands-free recording: starts automatically once speech is detected,
    stops after a period of silence following that speech. Returns the
    filename, or None if no speech was detected before timing out.
    """
    # Lazily fetch game context broadcaster if enabled
    try:
        from voicerecognition import _game_context, _broadcast_state
        broadcaster_integration = True
    except ImportError:
        broadcaster_integration = False

    if broadcaster_integration:
        _game_context["mic_status"] = "listening"
        _broadcast_state()

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

    if broadcaster_integration:
        _game_context["mic_status"] = "processing"
        _broadcast_state()

    if state["result"] == "stop_timeout" or not chunks:
        if broadcaster_integration:
            _game_context["mic_status"] = "idle"
            _broadcast_state()
        return None

    audio = np.concatenate(chunks, axis=0).flatten()
    pcm = np.clip(audio, -1.0, 1.0)
    if os.path.exists(filename):
        os.remove(filename)
    wav.write(filename, sampleRate, (pcm * 32767).astype(np.int16))
    return filename
