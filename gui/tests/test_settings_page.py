from PyQt6.QtTest import QSignalSpy

from ctl import Ctl
from settings_page import SettingsPage


def wait(page, action):
    spy = QSignalSpy(page.ctl.done)
    action()
    assert spy.wait(5000)


def loaded_page():
    page = SettingsPage(Ctl())
    wait(page, page.load)
    return page


def test_load_shows_the_mouse_settings(app, fake_ctl):
    page = loaded_page()
    assert page.rates.checkedId() == 1000
    assert page.lods.checkedId() == 2
    assert not page.motion_sync.isChecked()
    assert page.debounce.value() == 8
    assert (page.sleep.currentData(), page.sleep.currentText()) == (30, "5 min")  # 10 s steps
    assert page.sleep.accessibleName() == "Sleep after"
    assert not page.apply_button.isEnabled()


def test_apply_writes_only_the_changes(app, fake_ctl):
    page = loaded_page()
    page.rates.button(500).click()
    page.motion_sync.setChecked(True)
    assert page.apply_button.isEnabled()
    wait(page, page.apply)
    assert fake_ctl.calls()[-3:] == ["rate 500", "sensor motion-sync on", "show --json"]


def test_sleep_offers_the_official_choices_and_debounce_stops_at_20(app, fake_ctl):
    page = loaded_page()
    assert [page.sleep.itemText(i) for i in range(page.sleep.count())] == [
        "10 s", "30 s", "1 min", "2 min", "5 min", "10 min", "20 min", "30 min"]
    assert (page.debounce.minimum(), page.debounce.maximum()) == (0, 20)
    page.sleep.setCurrentIndex(page.sleep.findData(6))  # 1 min
    wait(page, page.apply)
    assert fake_ctl.calls()[-2:] == ["power sleep 6", "show --json"]
