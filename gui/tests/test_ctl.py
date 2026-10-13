from dataclasses import replace

from conftest import SHOW
from PyQt6.QtTest import QSignalSpy

from ctl import (Ctl, Dpi, Lighting, Settings, button_commands, dpi_commands,
                 lighting_commands, macro_commands, parse_buttons, parse_dpi, parse_lighting,
                 parse_macros, parse_settings, settings_commands)

DPI = Dpi(5, (400, 800, 1200, 1600, 2400, 3200),
          ("#ff0000", "#0000ff", "#ffff00", "#00ff00", "#00ffff", "#ff00ff"))


def test_parse_dpi_reads_active_stages_and_colours():
    assert parse_dpi(SHOW) == DPI


def test_parse_dpi_trims_colours_to_the_stage_count():
    two = SHOW.replace("[400,800,1200,1600,2400,3200]", "[400,800]").replace('"active":5', '"active":1')
    assert parse_dpi(two) == Dpi(1, (400, 800), ("#ff0000", "#0000ff"))


def test_parse_dpi_rejects_garbage():
    assert parse_dpi("mouse is asleep - move it") is None
    assert parse_dpi('{"dpi": {}}') is None


def test_no_changes_means_no_commands():
    assert dpi_commands(DPI, DPI) == []


def test_commands_write_values_then_colours_then_select():
    new = replace(DPI, active=2, stages=(400, 900, 1200, 1600, 2400, 3200),
                  colours=("#ff0000", "#0000ff", "#123456", "#00ff00", "#00ffff", "#ff00ff"))
    assert dpi_commands(DPI, new) == [
        ["dpi", "2", "900"], ["dpi-colour", "3", "#123456"], ["dpi", "select", "2"]]


def run(ctl, commands):
    spy = QSignalSpy(ctl.done)
    ctl.run(commands, "page")
    assert spy.wait(5000)
    return list(spy[0])


def test_ctl_runs_commands_in_order_and_returns_last_output(app, fake_ctl):
    assert run(Ctl(), [["dpi", "2", "900"], ["show", "--json"]]) == ["page", True, SHOW]
    assert fake_ctl.calls() == ["dpi 2 900", "show --json"]


def test_ctl_stops_at_the_first_failure(app, fake_ctl, monkeypatch):
    monkeypatch.setenv("FAKE_FAIL", "dpi 2 900")
    assert run(Ctl(), [["dpi", "2", "900"], ["show", "--json"]]) == [
        "page", False, "mouse is asleep - move it"]
    assert fake_ctl.calls() == ["dpi 2 900"]


def test_ctl_reports_a_missing_ajazzctl(app, tmp_path, monkeypatch):
    monkeypatch.setenv("AJAZZCTL", str(tmp_path / "missing"))
    assert run(Ctl(), [["show", "--json"]]) == [
        "page", False, "ajazzctl not found - install aj179-linux"]


def test_ctl_runs_jobs_one_at_a_time_and_names_who_asked(app, fake_ctl):
    ctl = Ctl()
    spy = QSignalSpy(ctl.done)
    ctl.run([["dpi", "2", "900"]], "dpi page")
    ctl.run([["show", "--json"]], "settings page")  # queued, not started alongside
    while len(spy) < 2:
        assert spy.wait(5000)
    assert [spy[i][0] for i in range(2)] == ["dpi page", "settings page"]
    assert fake_ctl.calls() == ["dpi 2 900", "show --json"]


SETTINGS = Settings(rate=1000, lod=2, motion_sync=False, angle_snap=False,
                    debounce=8, sleep=30, wake_on_move=False, lights_off_on_move=False)


def test_parse_settings_reads_rate_sensor_and_power():
    assert parse_settings(SHOW) == SETTINGS


def test_parse_settings_rejects_garbage():
    assert parse_settings("mouse is asleep - move it") is None
    assert parse_settings('{"rate": 1000}') is None


def test_settings_commands_write_only_what_changed():
    assert settings_commands(SETTINGS, SETTINGS) == []
    new = replace(SETTINGS, rate=500, motion_sync=True, sleep=60, lights_off_on_move=True)
    assert settings_commands(SETTINGS, new) == [
        ["rate", "500"], ["sensor", "motion-sync", "on"], ["power", "sleep", "60"],
        ["power", "lights-off-on-move", "on"]]


LIGHT = Lighting(mode="constant", colour="#ff00ff", brightness=4, speed=0)


def test_parse_lighting_reads_mode_colour_brightness_and_speed():
    assert parse_lighting(SHOW) == LIGHT
    assert parse_lighting("mouse is asleep - move it") is None


def test_lighting_commands_send_one_full_command():
    assert lighting_commands(LIGHT, LIGHT) == []
    assert lighting_commands(LIGHT, replace(LIGHT, colour="#00ff00")) == [
        ["lighting", "constant", "#00ff00", "4", "0"]]
    assert lighting_commands(LIGHT, replace(LIGHT, mode="breathing", speed=2)) == [
        ["lighting", "breathing", "4", "2"]]


def test_ctl_falls_back_to_stdout_when_ajazzctl_says_nothing_on_stderr(app, tmp_path, monkeypatch):
    script = tmp_path / "ajazzctl"  # ajazzctl prints read-back mismatches on stdout
    script.write_text("#!/bin/sh\nprintf 'read-back mismatch\\n  wrote: 02 23\\n'\nexit 1\n")
    script.chmod(0o755)
    monkeypatch.setenv("AJAZZCTL", str(script))
    assert run(Ctl(), [["lighting", "breathing", "2", "3"]]) == [
        "page", False, "read-back mismatch"]


def test_parse_lighting_defaults_the_colour_outside_constant_mode():
    breathing = SHOW.replace('"mode":"constant","colour":"#ff00ff"', '"mode":"breathing","colour":null')
    assert parse_lighting(breathing) == Lighting("breathing", "#ff0000", 4, 0)


FACTORY = ("left", "right", "middle", "back", "forward", "dpi-loop")


def test_parse_buttons_reads_the_six_functions():
    assert parse_buttons(SHOW) == FACTORY
    assert parse_buttons('{"buttons": ["left"]}') is None


def test_button_commands_set_changed_buttons_but_never_the_left_one():
    new = ("right", "right", "middle", "scroll-up", "forward", "key:ctrl+c")
    assert button_commands(FACTORY, new) == [
        ["button", "4", "scroll-up"], ["button", "6", "key:ctrl+c"]]


def test_parse_macros_gives_each_buttons_text():
    assert parse_macros(SHOW) == ("",) * 6
    with_macro = SHOW.replace('"macros":{}', '"macros":{"4":"ctrl+c wait:50 ctrl+v"}')
    assert parse_macros(with_macro)[3] == "ctrl+c wait:50 ctrl+v"
    assert parse_macros('{"rate": 1000}') is None


def test_macro_commands_upload_changed_macros_only():
    old = ("", "", "", "a", "", "")
    new = ("", "", "", "ctrl+c wait:50 ctrl+v", "", "")
    assert macro_commands(old, new) == [["macro", "4", "ctrl+c", "wait:50", "ctrl+v"]]
    assert macro_commands(old, ("",) * 6) == []  # an empty macro is never uploaded


def test_ctl_says_when_the_installed_ajazzctl_is_too_old(app, tmp_path, monkeypatch):
    script = tmp_path / "ajazzctl"  # an ajazzctl without show --json prints its usage
    script.write_text("#!/bin/sh\necho 'usage: ajazzctl info | show' >&2\n"
                      "echo '       ajazzctl read <cmd-hex>' >&2\nexit 2\n")
    script.chmod(0o755)
    monkeypatch.setenv("AJAZZCTL", str(script))
    assert run(Ctl(), [["show", "--json"]]) == [
        "page", False, "ajazzctl is too old for this app - run: sudo make install"]
