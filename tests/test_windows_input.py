from nollie_rgb_idle.windows_input import state_has_activity


def test_controller_buttons_and_large_axis_changes_count_as_activity() -> None:
    assert state_has_activity(None, (0, 0, 0), dead_zone=1000)
    assert state_has_activity((0, 0, 0), (1, 0, 0), dead_zone=1000)
    assert state_has_activity((1, 0, 0), (1, 500, 0), dead_zone=1000) is False
    assert state_has_activity((1, 0, 0), (1, 1500, 0), dead_zone=1000)
