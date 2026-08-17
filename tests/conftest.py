"""Pytest configuration and fixtures for VoiceChess tests.

Configures pytest to run without the voicerecognition game loop.
The game loop is automatically skipped during tests via the PYTEST_CURRENT_TEST
environment variable (set by pytest itself).
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Mark this as a test run so voicerecognition.py skips the game loop
if "PYTEST_CURRENT_TEST" not in os.environ:
    os.environ["PYTEST_CURRENT_TEST"] = "conftest"

# Mock Whisper model before it gets loaded by voicerecognition
_mock_model = MagicMock()
_mock_model.transcribe = MagicMock(return_value=([], {"language": "en"}))

# Patch the WhisperModel import before voicerecognition imports it
sys.modules["faster_whisper"] = MagicMock(
    WhisperModel=MagicMock(return_value=_mock_model)
)

# Also mock external dependencies that voicerecognition might use
sys.modules["edge_tts"] = MagicMock()
sys.modules["sounddevice"] = MagicMock()
sys.modules["pynput"] = MagicMock()
sys.modules["pynput.keyboard"] = MagicMock()
sys.modules["scipy"] = MagicMock()
sys.modules["scipy.io"] = MagicMock()
sys.modules["scipy.io.wavfile"] = MagicMock()
