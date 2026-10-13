from alert import check, load_config, save_config
from battery import Status


def test_notifies_once_when_the_battery_drops_to_the_threshold():
    assert check(Status("mouse", 21), 20, armed=True) == (False, True)
    assert check(Status("mouse", 20), 20, armed=True) == (True, False)
    assert check(Status("mouse", 15), 20, armed=False) == (False, False)  # already told


def test_charging_or_a_clear_rise_re_arms_it():
    assert check(Status("charging", 15), 20, armed=False) == (False, True)
    assert check(Status("mouse", 22), 20, armed=False) == (False, False)  # no flip-flop at 20/21
    assert check(Status("mouse", 25), 20, armed=False) == (False, True)


def test_unknown_levels_change_nothing():
    assert check(Status("disconnected", None), 20, armed=True) == (False, True)
    assert check(None, 20, armed=False) == (False, False)


def test_config_defaults_to_on_at_20_and_round_trips(tmp_path):
    path = tmp_path / "battery-alert"
    assert load_config(path) == (True, 20)
    save_config(path, False, 15)
    assert load_config(path) == (False, 15)
