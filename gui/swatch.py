"""A colour button: shows its colour and opens a colour picker when pressed."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog, QPushButton


class Swatch(QPushButton):
    changed = pyqtSignal()  # the user picked a new colour

    def __init__(self, name):
        super().__init__()
        self.colour = "#000000"
        self.setObjectName("swatch")
        self.setAccessibleName(name)
        self.clicked.connect(self.pick)

    def set_colour(self, colour):
        self.colour = colour
        self.setStyleSheet(f"background: {colour};")
        self.setToolTip(colour)

    def pick(self):
        c = QColorDialog.getColor(QColor(self.colour), self, self.accessibleName())
        if c.isValid():
            self.set_colour(c.name())
            self.changed.emit()
