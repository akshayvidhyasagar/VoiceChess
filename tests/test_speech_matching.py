from speech_matching import (
    match_mode_selection,
    match_self_test_response,
    match_confirm_response,
    detect_command,
    match_game_mode,
    parse_elo,
    match_color_selection,
)


def test_match_mode_selection_push_to_talk():
    assert match_mode_selection("push to talk") == "ptt"
    assert match_mode_selection("I want push-to-talk please") == "ptt"
    assert match_mode_selection("use the spacebar") == "ptt"


def test_match_mode_selection_fully_voice():
    assert match_mode_selection("fully voice") == "voice"
    assert match_mode_selection("I want to go hands free") == "voice"
    assert match_mode_selection("voice") == "voice"


def test_match_mode_selection_unrecognized():
    assert match_mode_selection("banana") is None
    assert match_mode_selection("") is None


def test_match_mode_selection_case_insensitive():
    assert match_mode_selection("PUSH TO TALK") == "ptt"
    assert match_mode_selection("Voice") == "voice"


def test_match_self_test_response():
    assert match_self_test_response("let's test it") == "test"
    assert match_self_test_response("skip") == "skip"
    assert match_self_test_response("please skip the test") == "skip"
    assert match_self_test_response("banana") is None


def test_match_confirm_response():
    assert match_confirm_response("confirm") == "confirm"
    assert match_confirm_response("yes that's right") == "confirm"
    assert match_confirm_response("correct") == "confirm"
    assert match_confirm_response("repeat") == "repeat"
    assert match_confirm_response("no, that's wrong") == "repeat"
    assert match_confirm_response("redo it") == "repeat"
    assert match_confirm_response("banana") is None
    assert match_confirm_response("") is None
    assert match_confirm_response("CONFIRM") == "confirm"
    assert match_confirm_response("YES") == "confirm"
    assert match_confirm_response("NO") == "repeat"


def test_detect_command():
    assert detect_command("undo that") == "undo"
    assert detect_command("take back") == "undo"
    assert detect_command("takeback") == "undo"
    assert detect_command("I resign") == "resign"
    assert detect_command("let's draw") == "draw"
    assert detect_command("pause game") == "pause"
    assert detect_command("knight to f3") is None


def test_match_game_mode():
    assert match_game_mode("single player") == "single"
    assert match_game_mode("versus bot") == "single"
    assert match_game_mode("play the computer") == "single"
    assert match_game_mode("double player") == "double"
    assert match_game_mode("two players") == "double"
    assert match_game_mode("versus human") == "double"
    assert match_game_mode("banana") is None
    assert match_game_mode("") is None


def test_parse_elo():
    # Test presets
    assert parse_elo("beginner") == 800
    assert parse_elo("intermediate") == 1400
    assert parse_elo("set to advanced") == 2000
    assert parse_elo("master") == 2600
    
    # Test digits
    assert parse_elo("1200") == 1200
    assert parse_elo("play at 1800 elo") == 1800
    assert parse_elo("rating 2500") == 2500
    
    # Unrecognized
    assert parse_elo("play chess") is None
    assert parse_elo("") is None


def test_match_color_selection():
    assert match_color_selection("white") == "white"
    assert match_color_selection("I want black please") == "black"
    assert match_color_selection("random color") == "random"
    assert match_color_selection("any") == "random"
    assert match_color_selection("banana") is None
    assert match_color_selection("") is None

