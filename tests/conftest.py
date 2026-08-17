"""Pytest configuration and fixtures for VoiceChess tests.

Configures pytest to run without the voicerecognition game loop.
The game loop is automatically skipped during tests via the PYTEST_CURRENT_TEST
environment variable (set by pytest itself).
"""

# No special setup needed — server.py checks PYTEST_CURRENT_TEST
# to skip the game loop during tests.
