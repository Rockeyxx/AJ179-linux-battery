"""DPI page: one row per stage, written with ajazzctl when Apply is pressed."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QButtonGroup, QColorDialog, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QPushButton, QRadioButton, QSlider, QSpinBox,
                             QVBoxLayout, QWidget)

from ctl import Dpi, dpi_commands, parse_dpi

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


class DpiPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl, self.dpi, self.busy, self.saving = ctl, None, False, False
        self.rows = []
        ctl.done.connect(self._done)

        heading = QLabel("DPI")
        heading.setObjectName("heading")
        hint = QLabel("Choose the active stage and set each stage's DPI and LED colour.")
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

        self.message = QLabel()
        self.message.setWordWrap(True)
        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.load)
        self.apply_button = QPushButton("Apply")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply)
        buttons = QHBoxLayout()
        buttons.addWidget(self.message, 1)
        buttons.addWidget(self.reload_button)
        buttons.addWidget(self.apply_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(heading)
        layout.addWidget(hint)
        layout.addSpacing(10)
        layout.addWidget(card)
        layout.addLayout(buttons)
        layout.addStretch()

    def load(self):
        self._start("Reading the mouse…", saving=False)
        self.ctl.run([["show", "--json"]])

    def apply(self):
        commands = dpi_commands(self.dpi, self.current())
        self._start("Saving…", saving=True)
        self.ctl.run(commands + [["show", "--json"]])  # re-read what the mouse kept

    def current(self):
        return Dpi(self.group.checkedId(), tuple(r.spin.value() for r in self.rows),
                   tuple(r.colour for r in self.rows))

    def show_dpi(self, dpi):
        if not self.rows:
            for n in range(1, len(dpi.stages) + 1):
                row = StageRow(n, self._changed)
                self.group.addButton(row.radio, n)
                for col, w in enumerate((row.radio, row.swatch, row.slider, row.spin)):
                    self.grid.addWidget(w, n, col)
                self.rows.append(row)
        self.dpi = dpi
        for row, value, colour in zip(self.rows, dpi.stages, dpi.colours):
            row.spin.setValue(value)
            row.set_colour(colour)
        self.rows[dpi.active - 1].radio.setChecked(True)
        self._changed()

    def _start(self, text, saving):
        self.busy, self.saving = True, saving
        self.message.setText(text)
        self.apply_button.setEnabled(False)
        self.reload_button.setEnabled(False)

    def _done(self, ok, out):
        self.busy = False
        self.reload_button.setEnabled(True)
        dpi = parse_dpi(out) if ok else None
        if dpi is None:  # keep the user's edits so Apply can be retried
            self.message.setText(out if not ok else "ajazzctl gave an unexpected reply")
            self._changed()
            return
        self.show_dpi(dpi)
        self.message.setText("Saved" if self.saving else "")

    def _changed(self):
        self.apply_button.setEnabled(
            not self.busy and self.dpi is not None and self.current() != self.dpi)
