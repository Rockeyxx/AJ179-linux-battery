from dataclasses import replace

from conftest import SHOW
from PyQt6.QtTest import QSignalSpy

from ctl import Ctl, Dpi, dpi_commands, parse_dpi

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
