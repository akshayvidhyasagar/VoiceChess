import pytest
from silence_detector import compute_thresholds, SilenceDetector


def test_compute_thresholds_from_calibration_samples():
    speech, silence = compute_thresholds([0.01, 0.01, 0.01])
    assert speech == pytest.approx(0.04)
    assert silence == pytest.approx(0.02)


def test_compute_thresholds_falls_back_when_no_samples():
    speech, silence = compute_thresholds([])
    assert speech == pytest.approx(0.02)
    assert silence == pytest.approx(0.01)


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
