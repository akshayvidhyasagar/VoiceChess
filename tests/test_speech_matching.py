from speech_matching import match_mode_selection, match_self_test_response


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
