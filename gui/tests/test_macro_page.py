from PyQt6.QtGui import QKeySequence
from PyQt6.QtTest import QSignalSpy

from ctl import Ctl
from macro_page import MacroPage, step_label


def test_steps_read_like_the_keys():
    assert step_label("ctrl+c") == "Ctrl+C"
    assert step_label("wait:50") == "Wait 50 ms"


def wait(page, action):
    spy = QSignalSpy(page.ctl.done)
    action()
    assert spy.wait(5000)


def loaded_page():
    page = MacroPage(Ctl())
    wait(page, page.load)
    return page


def add_key(page, keys):
    page.keys.setKeySequence(QKeySequence(keys))
    page.add_key()


def test_a_macro_is_built_from_keys_and_waits_and_uploaded(app, fake_ctl):
    page = loaded_page()
    page.button.setCurrentIndex(page.button.findData(4))
    add_key(page, "Ctrl+C")
    page.wait.setValue(50)
    page.add_wait()
    add_key(page, "Ctrl+V")
    assert [page.steps.item(i).text() for i in range(page.steps.count())] == [
        "Ctrl+C", "Wait 50 ms", "Ctrl+V"]
    assert page.apply_button.isEnabled()
    wait(page, page.apply)
    assert fake_ctl.calls()[-2:] == ["macro 4 ctrl+c wait:50 ctrl+v", "show --json"]


def test_a_macro_cannot_start_with_a_wait(app, fake_ctl):
    page = loaded_page()
    page.add_wait()
    assert page.steps.count() == 0
    assert not page.apply_button.isEnabled()
