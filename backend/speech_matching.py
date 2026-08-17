"""Pure text-matching helpers for voice command interpretation.

These operate on already-transcribed text and contain no I/O, so they're
unit-testable without a microphone or the Whisper model.
"""


def _normalize(text):
    """Normalize text: convert to lowercase and replace non-alphanumeric chars with spaces."""
    return "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())


def match_mode_selection(text):
    """Parse spoken input to detect input mode preference.

    Args:
        text: Transcribed speech as a string.

    Returns:
        "ptt" for push-to-talk mode, "voice" for hands-free mode, or None if unrecognized.
    """
    normalized = _normalize(text)
    if "push to talk" in normalized or "spacebar" in normalized or "space bar" in normalized:
        return "ptt"
    if "voice" in normalized or "hands free" in normalized:
        return "voice"
    return None


def match_self_test_response(text):
    """Returns "test", "skip", or None. "skip" takes priority since a
    sentence mentioning both ("skip the test") means skip."""
    normalized = _normalize(text)
    if "skip" in normalized:
        return "skip"
    if "test" in normalized:
        return "test"
    return None


def match_confirm_response(text):
    """Parse spoken input to confirm or reject a suggestion.

    Args:
        text: Transcribed speech as a string.

    Returns:
        "confirm" if user confirms, "repeat" if user requests re-speak, or None if unrecognized.
    """
    normalized = _normalize(text)
    confirm_words = ("confirm", "yes", "correct", "right")
    repeat_words = ("repeat", "no", "redo", "wrong")
    if any(word in normalized for word in confirm_words):
        return "confirm"
    if any(word in normalized for word in repeat_words):
        return "repeat"
    return None


def detect_command(text):
    """Parse spoken input to detect game control commands.

    Args:
        text: Transcribed speech as a string.

    Returns:
        "undo", "resign", "draw", or "pause" if recognized, or None if unrecognized.
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


def match_game_mode(text):
    """Parse spoken input to select the game mode.

    Args:
        text: Transcribed speech as a string.

    Returns:
        "single" for single player mode, "double" for double player mode, or None if unrecognized.
    """
    normalized = _normalize(text)
    single_words = ("single", "one player", "vs bot", "versus bot", "computer", "bot", "stockfish", "solo")
    double_words = ("double", "two player", "two players", "versus human", "vs human", "multiplayer", "local")

    if any(word in normalized for word in single_words):
        return "single"
    if any(word in normalized for word in double_words):
        return "double"
    return None


def parse_elo(text):
    """Parse spoken input for Stockfish ELO strength rating or preset.

    Args:
        text: Transcribed speech as a string.

    Returns:
        An integer ELO rating, or None if unrecognized.
    """
    import re
    normalized = _normalize(text)

    # Check for presets
    presets = {
        "beginner": 800,
        "intermediate": 1400,
        "advanced": 2000,
        "master": 2600
    }
    for word, rating in presets.items():
        if word in normalized:
            return rating

    # Check for digits
    numbers = re.findall(r"\d+", normalized)
    if numbers:
        return int(numbers[0])

    return None


def match_color_selection(text):
    """Parse spoken input to select the user's color.

    Args:
        text: Transcribed speech as a string.

    Returns:
        "white", "black", "random", or None if unrecognized.
    """
    normalized = _normalize(text)
    if "white" in normalized:
        return "white"
    if "black" in normalized:
        return "black"
    if "random" in normalized or "either" in normalized or "any" in normalized:
        return "random"
    return None

