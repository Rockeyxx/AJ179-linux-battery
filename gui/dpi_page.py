"""DPI page: one row per stage."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractSpinBox, QButtonGroup, QColorDialog, QFrame,
                             QGridLayout, QLabel, QPushButton, QRadioButton, QSlider, QSpinBox)

from ctl import Dpi, dpi_commands, parse_dpi
from page import DevicePage

MIN_DPI, MAX_DPI, STEP = 50, 26000, 50  # PAW3395


class StageRow:
    """The controls for one DPI stage: active, LED colour, slider and value."""

    def __init__(self, n, on_change):
        self.n, self.on_change, self.colour = n, on_change, "#000000"
        self.radio = QRadioButton(str(n))
        self.radio.setAccessibleName(f"Stage {n} active")
        self.swatch = QPushButton()
        self.swatch.setObjectName("swatch")
        self.swatch.setAccessibleName(f"Stage {n} colour")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(MIN_DPI // STEP, MAX_DPI // STEP)
        self.slider.setAccessibleName(f"Stage {n} DPI")
        self.spin = QSpinBox()
        self.spin.setRange(MIN_DPI, MAX_DPI)
        self.spin.setSingleStep(STEP)
        self.spin.setKeyboardTracking(False)  # only commit typed values on Enter
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)  # arrows/wheel still step
        self.spin.setAccessibleName(f"Stage {n} DPI")

        self.slider.valueChanged.connect(lambda v: self.spin.setValue(v * STEP))
        self.spin.valueChanged.connect(lambda v: self.slider.setValue(v // STEP))
        self.spin.valueChanged.connect(on_change)
        self.radio.toggled.connect(on_change)
        self.swatch.clicked.connect(self.pick_colour)

    def set_colour(self, colour):
        self.colour = colour
        self.swatch.setStyleSheet(f"background: {colour};")
        self.swatch.setToolTip(colour)

    def pick_colour(self):
        c = QColorDialog.getColor(QColor(self.colour), self.swatch, f"Stage {self.n} colour")
        if c.isValid():
            self.set_colour(c.name())
            self.on_change()


class DpiPage(DevicePage):
    def __init__(self, ctl):
        super().__init__(ctl, "DPI",
                         "Choose the active stage and set each stage's DPI and LED colour.")
        self.rows = []
        card = QFrame()
        card.setObjectName("card")
        self.grid = QGridLayout(card)
        self.grid.setContentsMargins(24, 18, 24, 18)
        self.grid.setHorizontalSpacing(18)
        self.grid.setColumnStretch(2, 1)
        for col, text in enumerate(("ACTIVE", "COLOUR", "", "DPI")):
            caption = QLabel(text)
            caption.setObjectName("caption")
            self.grid.addWidget(caption, 0, col)
        self.group = QButtonGroup(self)
        self.body.addWidget(card)

    def parse(self, text):
        return parse_dpi(text)

    def commands(self, old, new):
        return dpi_commands(old, new)

    def current(self):
        return Dpi(self.group.checkedId(), tuple(r.spin.value() for r in self.rows),
                   tuple(r.colour for r in self.rows))

    def show_value(self, dpi):
        if not self.rows:
            for n in range(1, len(dpi.stages) + 1):
                row = StageRow(n, self._changed)
                self.group.addButton(row.radio, n)
                for col, w in enumerate((row.radio, row.swatch, row.slider, row.spin)):
                    self.grid.addWidget(w, n, col)
                self.rows.append(row)
        for row, value, colour in zip(self.rows, dpi.stages, dpi.colours):
            row.spin.setValue(value)
            row.set_colour(colour)
        self.rows[dpi.active - 1].radio.setChecked(True)
