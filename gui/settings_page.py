"""Settings page: report rate, sensor and power options."""
from PyQt6.QtWidgets import (QAbstractSpinBox, QButtonGroup, QCheckBox, QComboBox, QFrame,
                             QGridLayout, QHBoxLayout, QLabel, QRadioButton, QSpinBox)

from ctl import Settings, parse_settings, settings_commands
from page import DevicePage

# The official app's sleep choices: the mouse counts in steps of 10 seconds.
SLEEP_CHOICES = ((1, "10 s"), (3, "30 s"), (6, "1 min"), (12, "2 min"), (30, "5 min"),
                 (60, "10 min"), (120, "20 min"), (180, "30 min"))


class SettingsPage(DevicePage):
    def __init__(self, ctl):
        super().__init__(ctl, "Settings", "Report rate, sensor and power options.")
        self.rates = self._choices("Report rate", [(hz, str(hz)) for hz in (125, 250, 500, 1000)],
                                   " Hz")
        self.lods = self._choices("Lift-off distance", [(1, "Low (1 mm)"), (2, "High (2 mm)")])
        self.motion_sync = self._check("Motion sync")
        self.angle_snap = self._check("Angle snap")
        self.debounce = self._spin("Debounce time", " ms", 0, 20)  # the official app's range
        self.sleep = QComboBox()
        self.sleep.setAccessibleName("Sleep after")
        for value, text in SLEEP_CHOICES:
            self.sleep.addItem(text, value)
        self.sleep.currentIndexChanged.connect(self._changed)
        self.wake_on_move = self._check("Wake up when moved")
        self.lights_off_on_move = self._check("Turn lights off when moving")

        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(24, 18, 24, 18)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)
        rows = (("SENSOR", None),
                ("Report rate (Hz)", self.rates.buttons()),
                ("Lift-off distance", self.lods.buttons()),
                ("", [self.motion_sync, self.angle_snap]),
                ("POWER", None),
                ("Debounce time", [self.debounce]),
                ("Sleep after", [self.sleep]),
                ("", [self.wake_on_move, self.lights_off_on_move]))
        for r, (name, widgets) in enumerate(rows):
            label = QLabel(name)
            if widgets is None:
                label.setObjectName("caption")
                grid.addWidget(label, r, 0, 1, 2)
                continue
            label.setObjectName("name")
            line = QHBoxLayout()
            line.setSpacing(14)
            for w in widgets:
                line.addWidget(w)
            line.addStretch()
            grid.addWidget(label, r, 0)
            grid.addLayout(line, r, 1)
        self.body.addWidget(card)

    def _choices(self, name, options, unit=""):
        group = QButtonGroup(self)
        for value, text in options:
            button = QRadioButton(text, self)  # parented, so Qt keeps it alive
            button.setAccessibleName(f"{name} {text}{unit}")
            group.addButton(button, value)
        group.idToggled.connect(self._changed)
        return group

    def _check(self, text):
        box = QCheckBox(text)
        box.toggled.connect(self._changed)
        return box

    def _spin(self, name, suffix, low, high):
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setSuffix(suffix)
        spin.setKeyboardTracking(False)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setAccessibleName(name)
        spin.valueChanged.connect(self._changed)
        return spin

    def parse(self, text):
        return parse_settings(text)

    def commands(self, old, new):
        return settings_commands(old, new)

    def current(self):
        return Settings(self.rates.checkedId(), self.lods.checkedId(),
                        self.motion_sync.isChecked(), self.angle_snap.isChecked(),
                        self.debounce.value(), self.sleep.currentData(),
                        self.wake_on_move.isChecked(), self.lights_off_on_move.isChecked())

    def show_value(self, s):
        for group, value in ((self.rates, s.rate), (self.lods, s.lod)):
            if group.button(value):
                group.button(value).setChecked(True)
        self.motion_sync.setChecked(s.motion_sync)
        self.angle_snap.setChecked(s.angle_snap)
        self.debounce.setValue(s.debounce)
        if self.sleep.findData(s.sleep) < 0:  # set some other way: still show it
            self.sleep.addItem(f"{s.sleep * 10} s", s.sleep)
        self.sleep.setCurrentIndex(self.sleep.findData(s.sleep))
        self.wake_on_move.setChecked(s.wake_on_move)
        self.lights_off_on_move.setChecked(s.lights_off_on_move)
