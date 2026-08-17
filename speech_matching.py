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
