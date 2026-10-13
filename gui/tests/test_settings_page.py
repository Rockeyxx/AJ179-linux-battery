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
    assert (page.debounce.value(), page.sleep.value()) == (8, 30)
    assert page.sleep.accessibleName() == "Sleep after"
    assert not page.apply_button.isEnabled()


def test_apply_writes_only_the_changes(app, fake_ctl):
    page = loaded_page()
    page.rates.button(500).click()
    page.motion_sync.setChecked(True)
    assert page.apply_button.isEnabled()
    wait(page, page.apply)
    assert fake_ctl.calls()[-3:] == ["rate 500", "sensor motion-sync on", "show --json"]
