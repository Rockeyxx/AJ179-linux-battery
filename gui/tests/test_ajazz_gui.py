import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication

from ajazz_gui import MainWindow, Status, parse_status, read_status

# Exactly what write_status() in src/ajazz_daemon.c prints.
ON_BATTERY = '{"text": "🖱️ 89%", "tooltip": "Ajazz Mouse", "class": "mouse"}\n'
CHARGING = '{"text": "🖱️ ⚡100%", "tooltip": "Ajazz Mouse (charging)", "class": "charging"}\n'
DISCONNECTED = '{"text": "🖱️ ...", "tooltip": "Sleeping", "class": "disconnected"}\n'


def test_parses_level_on_battery():
    assert parse_status(ON_BATTERY) == Status("mouse", 89)


def test_parses_level_while_charging():
    assert parse_status(CHARGING) == Status("charging", 100)


def test_disconnected_has_no_level():
    assert parse_status(DISCONNECTED) == Status("disconnected", None)


def test_empty_text_is_unreadable():
    assert parse_status("") is None


def test_garbage_is_unreadable():
    assert parse_status('{"text": "🖱') is None


def test_missing_file_means_service_not_running(tmp_path):
    assert read_status(tmp_path / "nope") == Status("no-service", None)


def test_reads_status_file(tmp_path):
    f = tmp_path / "ajazz_battery"
    f.write_text(CHARGING)
    assert read_status(f) == Status("charging", 100)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_window_shows_battery_and_keeps_last_good_state(app, tmp_path):
    f = tmp_path / "ajazz_battery"
    f.write_text(ON_BATTERY)
    win = MainWindow(f)

    assert win.battery.accessibleName() == "Mouse battery"
    assert win.battery.value() == 89
    assert win.status.text() == "On battery"

    f.write_text("")  # caught mid-write by the daemon
    win.refresh()
    assert win.battery.value() == 89


def test_sidebar_lists_every_feature_with_the_built_ones_ready(app, tmp_path):
    win = MainWindow(tmp_path / "none")
    assert [b.text() for b in win.tabs] == [
        "Home", "DPI", "Buttons", "Lighting", "Macro", "Settings"]
    assert [b.isEnabled() for b in win.tabs] == [True, True, False, False, False, True]
    assert win.tabs[0].isChecked()


def test_choosing_dpi_shows_and_loads_the_dpi_page(app, tmp_path, fake_ctl):
    win = MainWindow(tmp_path / "none")
    spy = QSignalSpy(win.dpi.ctl.done)
    win.tabs[1].click()
    assert win.pages.currentWidget() is win.dpi
    assert spy.wait(5000)
    assert len(win.dpi.rows) == 6


def test_choosing_settings_shows_and_loads_the_settings_page(app, tmp_path, fake_ctl):
    win = MainWindow(tmp_path / "none")
    spy = QSignalSpy(win.ctl.done)
    win.tabs[5].click()
    assert win.pages.currentWidget() is win.settings
    assert spy.wait(5000)
    assert win.settings.rates.checkedId() == 1000
