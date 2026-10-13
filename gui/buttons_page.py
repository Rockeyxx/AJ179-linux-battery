"""Buttons page: what each mouse button does."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QKeySequenceEdit,
                             QLabel, QPushButton)

from ctl import button_commands, parse_buttons
from page import DevicePage

BUTTONS = ("Left button", "Right button", "Wheel click", "Back (rear side)",
           "Forward (front side)", "DPI button")
FACTORY = ("left", "right", "middle", "back", "forward", "dpi-loop")
FUNCTIONS = (("left", "Left click"), ("right", "Right click"), ("middle", "Middle click"),
             ("back", "Back"), ("forward", "Forward"), ("scroll-up", "Scroll up"),
             ("scroll-down", "Scroll down"), ("dpi-loop", "DPI cycle"),
             ("play-pause", "Play / pause"), ("stop", "Stop"), ("previous", "Previous track"),
             ("next", "Next track"), ("volume-up", "Volume up"), ("volume-down", "Volume down"),
             ("mute", "Mute"), ("key", "Keyboard shortcut"))
KEY_HINT = ("Press a shortcut: a-z, 0-9, F1-F12, Enter, Esc, Tab, Space or Backspace, "
            "with Ctrl, Shift, Alt or Super.")

MODIFIERS = ((Qt.KeyboardModifier.ControlModifier, "ctrl"),
             (Qt.KeyboardModifier.ShiftModifier, "shift"),
             (Qt.KeyboardModifier.AltModifier, "alt"),
             (Qt.KeyboardModifier.MetaModifier, "super"))
NAMED_KEYS = {Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter", Qt.Key.Key_Escape: "esc",
              Qt.Key.Key_Tab: "tab", Qt.Key.Key_Space: "space", Qt.Key.Key_Backspace: "backspace"}
QT_WORDS = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "super": "Meta", "enter": "Return",
            "esc": "Esc", "tab": "Tab", "space": "Space", "backspace": "Backspace"}


def key_spec(sequence):
    """A Qt shortcut -> ajazzctl's words ("ctrl+c"), or None if ajazzctl has no such key."""
    if sequence.isEmpty():
        return None
    combo = sequence[0]
    key, k = combo.key(), combo.key().value
    if Qt.Key.Key_A.value <= k <= Qt.Key.Key_Z.value:
        name = chr(ord("a") + k - Qt.Key.Key_A.value)
    elif Qt.Key.Key_0.value <= k <= Qt.Key.Key_9.value:
        name = chr(ord("0") + k - Qt.Key.Key_0.value)
    elif Qt.Key.Key_F1.value <= k <= Qt.Key.Key_F12.value:
        name = f"f{k - Qt.Key.Key_F1.value + 1}"
    else:
        name = NAMED_KEYS.get(key)
    if name is None:
        return None
    mods = combo.keyboardModifiers()
    return "+".join([word for flag, word in MODIFIERS if mods & flag] + [name])


def key_sequence(spec):
    """ajazzctl's words ("ctrl+c") -> a Qt shortcut."""
    return QKeySequence("+".join(QT_WORDS.get(w, w.upper()) for w in spec.split("+")))


class ButtonRow:
    """One mouse button: its function, and a shortcut box for "Keyboard shortcut"."""

    def __init__(self, n, on_change):
        self.label = QLabel(f"{n}   {BUTTONS[n - 1]}")
        self.label.setObjectName("name")
        self.combo = QComboBox()
        self.combo.setAccessibleName(f"Button {n} function")
        for value, text in FUNCTIONS:
            self.combo.addItem(text, value)
        self.keys = QKeySequenceEdit()
        if hasattr(self.keys, "setMaximumSequenceLength"):  # Qt 6.5+
            self.keys.setMaximumSequenceLength(1)
        self.keys.setAccessibleName(f"Button {n} shortcut")
        self.keys.setToolTip(KEY_HINT)
        self.keys.setVisible(False)
        self.combo.currentIndexChanged.connect(
            lambda: self.keys.setVisible(self.combo.currentData() == "key"))
        self.combo.currentIndexChanged.connect(on_change)
        self.keys.keySequenceChanged.connect(on_change)
        self.combo.setEnabled(n > 1)  # the left button is locked

    def value(self):
        if self.combo.currentData() != "key":
            return self.combo.currentData()
        spec = key_spec(self.keys.keySequence())
        return f"key:{spec}" if spec else "key:?"

    def set_value(self, name):
        if name.startswith("key:"):
            self.keys.setKeySequence(key_sequence(name[4:]))
            name = "key"
        i = self.combo.findData(name)
        if i < 0:  # "macro" or "unknown": shown, but only set elsewhere
            self.combo.addItem(name.capitalize(), name)
            i = self.combo.count() - 1
        self.combo.setCurrentIndex(i)


class ButtonsPage(DevicePage):
    def __init__(self, ctl):
        super().__init__(ctl, "Buttons",
                         "What each mouse button does. The left button stays a left click.")
        self.rows = []
        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(24, 18, 24, 18)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        for col, text in enumerate(("BUTTON", "FUNCTION")):
            caption = QLabel(text)
            caption.setObjectName("caption")
            grid.addWidget(caption, 0, col)
        for n in range(1, 7):
            row = ButtonRow(n, self._changed)
            line = QHBoxLayout()
            line.setSpacing(12)
            line.addWidget(row.combo)
            line.addWidget(row.keys)
            line.addStretch()
            grid.addWidget(row.label, n, 0)
            grid.addLayout(line, n, 1)
            self.rows.append(row)

        note = QLabel("The mouse can't report its buttons, so this shows what was last set "
                      "from Linux.")
        note.setWordWrap(True)
        self.factory_button = QPushButton("Factory layout")
        self.factory_button.clicked.connect(lambda: self.show_value(FACTORY))
        extra = QHBoxLayout()
        extra.addWidget(note, 1)
        extra.addWidget(self.factory_button)
        self.body.addWidget(card)
        self.body.addLayout(extra)

    def parse(self, text):
        return parse_buttons(text)

    def commands(self, old, new):
        return button_commands(old, new)

    def current(self):
        return tuple(row.value() for row in self.rows)

    def show_value(self, names):
        for row, name in zip(self.rows, names):
            row.set_value(name)
        self._changed()

    def _changed(self, *_):
        super()._changed()
        if not self.rows:
            return
        if "key:?" in self.current():  # a shortcut ajazzctl cannot send yet
            self.apply_button.setEnabled(False)
            self.message.setText(KEY_HINT)
        elif self.message.text() == KEY_HINT:
            self.message.setText("")
