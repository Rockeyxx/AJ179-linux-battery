"""Lighting page: mode, colour, brightness and speed of the mouse's light."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QRadioButton, QSlider)

from ctl import Lighting, lighting_commands, parse_lighting
from page import DevicePage
from swatch import Swatch

MODES = ("off", "breathing", "constant")  # the modes the AJ179 offers


class LightingPage(DevicePage):
    def __init__(self, ctl):
        super().__init__(ctl, "Lighting", "Mode, colour, brightness and speed of the mouse's light.")
        self.modes = QButtonGroup(self)
        for i, mode in enumerate(MODES):
            button = QRadioButton(mode.capitalize(), self)  # parented, so Qt keeps it alive
            button.setAccessibleName(f"Lighting {mode}")
            self.modes.addButton(button, i)
        self.modes.idToggled.connect(self._changed)
        self.swatch = Swatch("Lighting colour")
        self.swatch.changed.connect(self._changed)
        self.brightness = self._level("Brightness")
        self.speed = self._level("Speed")

        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(24, 18, 24, 18)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(1, 1)
        rows = (("Mode", self.modes.buttons()),
                ("Colour", [self.swatch, QLabel("Constant mode")]),
                ("Brightness", [self.brightness]),
                ("Speed", [self.speed, QLabel("Breathing mode")]))
        for r, (name, widgets) in enumerate(rows):
            label = QLabel(name)
            label.setObjectName("name")
            line = QHBoxLayout()
            line.setSpacing(20)
            for w in widgets:
                line.addWidget(w)
            line.addStretch()
            grid.addWidget(label, r, 0)
            grid.addLayout(line, r, 1)
        self.body.addWidget(card)

    def _level(self, name):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 4)
        slider.setPageStep(1)
        slider.setMinimumWidth(120)
        slider.setMaximumWidth(260)
        slider.setAccessibleName(name)
        slider.valueChanged.connect(self._changed)
        return slider

    def _mode(self):
        i = self.modes.checkedId()
        return MODES[i] if i >= 0 else (self.value.mode if self.value else "off")

    def _changed(self, *_):
        mode = self._mode()
        self.swatch.setEnabled(mode == "constant")
        self.brightness.setEnabled(mode != "off")
        self.speed.setEnabled(mode == "breathing")
        super()._changed()

    def parse(self, text):
        return parse_lighting(text)

    def commands(self, old, new):
        return lighting_commands(old, new)

    def current(self):
        return Lighting(self._mode(), self.swatch.colour, self.brightness.value(),
                        self.speed.value())

    def show_value(self, light):
        if light.mode in MODES:
            self.modes.button(MODES.index(light.mode)).setChecked(True)
        self.swatch.set_colour(light.colour)
        self.brightness.setValue(light.brightness)
        self.speed.setValue(light.speed)
