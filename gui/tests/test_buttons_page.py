from PyQt6.QtGui import QKeySequence
from PyQt6.QtTest import QSignalSpy

from buttons_page import ButtonsPage, key_sequence, key_spec
from ctl import Ctl


def test_key_spec_turns_a_shortcut_into_ajazzctl_words():
    assert key_spec(QKeySequence("Ctrl+Shift+Esc")) == "ctrl+shift+esc"
    assert key_spec(QKeySequence("Meta+Tab")) == "super+tab"
    assert key_spec(QKeySequence("F5")) == "f5"
    assert key_spec(QKeySequence("Ctrl+Home")) is None  # ajazzctl has no Home key


def test_key_sequence_is_the_inverse():
    assert key_sequence("ctrl+c") == QKeySequence("Ctrl+C")
    assert key_spec(key_sequence("super+enter")) == "super+enter"


def wait(page, action):
    spy = QSignalSpy(page.ctl.done)
    action()
    assert spy.wait(5000)


def loaded_page():
    page = ButtonsPage(Ctl())
    wait(page, page.load)
    return page


def choose(row, name):
    row.combo.setCurrentIndex(row.combo.findData(name))


def test_load_shows_each_button_and_locks_the_left_one(app, fake_ctl):
    page = loaded_page()
    assert [r.combo.currentData() for r in page.rows] == [
        "left", "right", "middle", "back", "forward", "dpi-loop"]
    assert not page.rows[0].combo.isEnabled()
    assert page.rows[3].combo.accessibleName() == "Button 4 function"
    assert not page.apply_button.isEnabled()


def test_apply_sends_a_function_and_a_shortcut(app, fake_ctl):
    page = loaded_page()
    choose(page.rows[3], "scroll-up")
    choose(page.rows[5], "key")
    page.rows[5].keys.setKeySequence(QKeySequence("Ctrl+C"))
    wait(page, page.apply)
    assert fake_ctl.calls()[-3:] == ["button 4 scroll-up", "button 6 key:ctrl+c", "show --json"]


def test_factory_layout_resets_the_controls(app, fake_ctl):
    page = loaded_page()
    choose(page.rows[3], "mute")
    page.factory_button.click()
    assert page.rows[3].combo.currentData() == "back"
    assert not page.apply_button.isEnabled()
