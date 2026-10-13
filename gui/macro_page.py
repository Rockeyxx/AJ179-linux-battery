"""Macro page: key presses and waits that a mouse button plays."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractSpinBox, QComboBox, QFrame, QGridLayout, QHBoxLayout,
                             QKeySequenceEdit, QLabel, QListWidget, QPushButton, QSpinBox,
                             QVBoxLayout)

from buttons_page import BUTTONS, KEY_HINT, key_sequence, key_spec
from ctl import macro_commands, parse_buttons, parse_macros
from page import DevicePage

KEEP_ONE = ("To stop a button playing its macro, give it another function on the "
            "Buttons page.")


def step_label(token):
    """One of ajazzctl's macro tokens ("ctrl+c", "wait:50") as the user reads it."""
    if token.startswith("wait:"):
        return f"Wait {token[5:]} ms"
    return key_sequence(token).toString()


class MacroPage(DevicePage):
    def __init__(self, ctl):
        super().__init__(ctl, "Macro", "Key presses and waits that a mouse button plays.")
        self.drafts, self.functions = [""] * 6, None
        self.button = QComboBox()
        self.button.setAccessibleName("Macro button")
        for n in range(2, 7):  # the left button is locked
            self.button.addItem(f"{n}   {BUTTONS[n - 1]}", n)
        self.button.currentIndexChanged.connect(self._show_steps)
        self.state = QLabel()
        self.state.setWordWrap(True)
        self.steps = QListWidget()
        self.steps.setAccessibleName("Macro steps")
        self.steps.setFixedHeight(150)
        self.keys = QKeySequenceEdit()
        self.keys.setMaximumSequenceLength(1)
        self.keys.setAccessibleName("Key to add")
        self.keys.setToolTip(KEY_HINT)
        self.keys.setMinimumWidth(150)
        self.wait = QSpinBox()
        self.wait.setRange(1, 65535)
        self.wait.setValue(50)
        self.wait.setSuffix(" ms")
        self.wait.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.wait.setAccessibleName("Wait to add")
        self.wait.setMinimumWidth(90)

        add_key = QHBoxLayout()
        add_key.setSpacing(10)
        add_key.addWidget(self.keys)
        add_key.addWidget(self._button("Add key", self.add_key))
        add_key.addStretch()
        add_wait = QHBoxLayout()
        add_wait.setSpacing(10)
        add_wait.addWidget(self.wait)
        add_wait.addWidget(self._button("Add wait", self.add_wait))
        add_wait.addStretch()
        edit = QVBoxLayout()
        edit.addWidget(self._button("Remove", self.remove))
        edit.addWidget(self._button("Clear", self.clear))
        edit.addStretch()
        steps = QHBoxLayout()
        steps.setSpacing(12)
        steps.addWidget(self.steps, 1)
        steps.addLayout(edit)
        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(self.button)
        top.addWidget(self.state, 1)

        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(24, 18, 24, 18)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)
        rows = (("Button", top), ("Steps", steps), ("Add", add_key), ("", add_wait))
        for r, (name, line) in enumerate(rows):
            label = QLabel(name)
            label.setObjectName("name")
            grid.addWidget(label, r, 0, Qt.AlignmentFlag.AlignTop if name == "Steps"
                           else Qt.AlignmentFlag.AlignVCenter)
            grid.addLayout(line, r, 1)
        self.body.addWidget(card)

    def _button(self, text, slot):
        button = QPushButton(text)
        button.clicked.connect(slot)
        return button

    def _tokens(self):
        return self.drafts[self.button.currentData() - 1].split()

    def _set_tokens(self, tokens):
        while tokens and tokens[0].startswith("wait:"):  # a macro starts with a key
            tokens.pop(0)
        self.drafts[self.button.currentData() - 1] = " ".join(tokens)
        self._show_steps()
        self._changed()

    def add_key(self):
        spec = key_spec(self.keys.keySequence())
        if spec is None:
            self.message.setText(KEY_HINT)
            return
        self.keys.clear()
        self._set_tokens(self._tokens() + [spec])

    def add_wait(self):
        if not self._tokens():
            self.message.setText("A macro starts with a key; add one before a wait.")
            return
        self._set_tokens(self._tokens() + [f"wait:{self.wait.value()}"])

    def remove(self):
        tokens, row = self._tokens(), self.steps.currentRow()
        if 0 <= row < len(tokens):
            del tokens[row]
            self._set_tokens(tokens)

    def clear(self):
        self._set_tokens([])

    def _show_steps(self, *_):
        self.steps.clear()
        self.steps.addItems([step_label(t) for t in self._tokens()])
        n = self.button.currentData()
        plays = self.functions is not None and self.functions[n - 1] == "macro"
        self.state.setText(f"Button {n} plays this macro." if plays
                           else f"Saving makes button {n} play this macro.")

    def parse(self, text):
        self.functions = parse_buttons(text)  # to say whether the button plays its macro
        return parse_macros(text)

    def commands(self, old, new):
        return macro_commands(old, new)

    def current(self):
        return tuple(self.drafts)

    def show_value(self, macros):
        self.drafts = list(macros)
        self._show_steps()

    def _changed(self, *_):
        super()._changed()
        if self.value and any(old and not new for old, new in zip(self.value, self.drafts)):
            self.apply_button.setEnabled(False)  # an empty macro cannot be uploaded
            self.message.setText(KEEP_ONE)
        elif self.message.text() == KEEP_ONE:
            self.message.setText("")
