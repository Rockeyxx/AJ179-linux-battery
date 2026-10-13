from PyQt6.QtTest import QSignalSpy

from ctl import Ctl
from lighting_page import LightingPage


def wait(page, action):
    spy = QSignalSpy(page.ctl.done)
    action()
    assert spy.wait(5000)


def loaded_page():
    page = LightingPage(Ctl())
    wait(page, page.load)
    return page


def test_load_shows_the_light(app, fake_ctl):
    page = loaded_page()
    assert page.modes.checkedId() == 2  # constant
    assert page.swatch.colour == "#ff00ff"
    assert (page.brightness.value(), page.speed.value()) == (4, 0)
    assert page.swatch.isEnabled() and not page.speed.isEnabled()
    assert not page.apply_button.isEnabled()


def test_breathing_has_a_speed_but_no_colour_and_applies(app, fake_ctl):
    page = loaded_page()
    page.modes.button(1).click()  # breathing
    page.speed.setValue(2)
    assert page.speed.isEnabled() and not page.swatch.isEnabled()
    wait(page, page.apply)
    assert fake_ctl.calls()[-2:] == ["lighting breathing 4 2", "show --json"]


def test_neon_cycles_its_own_colours_at_a_speed(app, fake_ctl):
    page = loaded_page()
    page.modes.button(3).click()  # neon
    page.speed.setValue(3)
    assert page.speed.isEnabled() and not page.swatch.isEnabled()
    wait(page, page.apply)
    assert fake_ctl.calls()[-2:] == ["lighting neon 4 3", "show --json"]
