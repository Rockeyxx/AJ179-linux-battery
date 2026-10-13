from conftest import SHOW
from PyQt6.QtTest import QSignalSpy

from ctl import Ctl
from dpi_page import DpiPage


def wait(page, action):
    spy = QSignalSpy(page.ctl.done)
    action()
    assert spy.wait(5000)


def loaded_page():
    page = DpiPage(Ctl())
    wait(page, page.load)
    return page


def test_load_shows_every_stage_and_the_active_one(app, fake_ctl):
    page = loaded_page()
    assert [r.spin.value() for r in page.rows] == [400, 800, 1200, 1600, 2400, 3200]
    assert [r.colour for r in page.rows][:2] == ["#ff0000", "#0000ff"]
    assert page.rows[4].radio.isChecked()
    assert page.rows[1].spin.accessibleName() == "Stage 2 DPI"
    assert not page.apply_button.isEnabled()


def test_editing_a_stage_moves_its_slider_and_enables_apply(app, fake_ctl):
    page = loaded_page()
    page.rows[1].spin.setValue(900)
    assert page.rows[1].slider.value() == 900 // 50
    assert page.apply_button.isEnabled()


def test_apply_writes_only_the_change_then_rereads(app, fake_ctl):
    page = loaded_page()
    page.rows[1].spin.setValue(900)
    fake_ctl.show.write_text(SHOW.replace("[400,800,", "[400,900,"))  # what the mouse reads back
    wait(page, page.apply)
    assert fake_ctl.calls()[-2:] == ["dpi 2 900", "show --json"]
    assert page.rows[1].spin.value() == 900
    assert not page.apply_button.isEnabled()
    assert page.message.text() == "Saved"


def test_a_failed_apply_shows_the_error_and_keeps_the_edit(app, fake_ctl, monkeypatch):
    page = loaded_page()
    page.rows[1].spin.setValue(900)
    monkeypatch.setenv("FAKE_FAIL", "dpi 2 900")
    wait(page, page.apply)
    assert page.message.text() == "mouse is asleep - move it"
    assert page.rows[1].spin.value() == 900
    assert page.apply_button.isEnabled()
