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
