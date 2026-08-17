from speech_matching import match_mode_selection, match_self_test_response, match_confirm_response


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
