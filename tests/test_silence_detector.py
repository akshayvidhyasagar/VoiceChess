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
