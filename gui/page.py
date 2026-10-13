"""What every settings page shares: read the mouse with `ajazzctl show --json`,
let the user edit, and write only the changes on Apply."""
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class DevicePage(QWidget):
    def __init__(self, ctl, title, hint):
        super().__init__()
        self.ctl, self.value, self.busy, self.saving = ctl, None, False, False
        ctl.done.connect(self._done)

        heading = QLabel(title)
        heading.setObjectName("heading")
        self.body = QVBoxLayout()  # the page's own controls go here
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
        layout.addWidget(QLabel(hint))
        layout.addSpacing(10)
        layout.addLayout(self.body)
        layout.addLayout(buttons)
        layout.addStretch()

    # Each page provides these four.
    def parse(self, text):  # `show --json` output -> the page's value, or None
        raise NotImplementedError

    def commands(self, old, new):  # ajazzctl commands that turn old into new
        raise NotImplementedError

    def current(self):  # the value the controls show now
        raise NotImplementedError

    def show_value(self, value):  # set the controls from a value
        raise NotImplementedError

    def load(self):
        self._start("Reading the mouse…", saving=False)
        self.ctl.run([["show", "--json"]], self)

    def apply(self):
        commands = self.commands(self.value, self.current())
        self._start("Saving…", saving=True)
        self.ctl.run(commands + [["show", "--json"]], self)  # re-read what the mouse kept

    def _start(self, text, saving):
        self.busy, self.saving = True, saving
        self.message.setText(text)
        self.apply_button.setEnabled(False)
        self.reload_button.setEnabled(False)

    def _done(self, owner, ok, out):
        if owner is not self:
            return
        self.busy = False
        self.reload_button.setEnabled(True)
        value = self.parse(out) if ok else None
        if value is None:  # keep the user's edits so Apply can be retried
            self.message.setText(out if not ok else "ajazzctl gave an unexpected reply")
            self._changed()
            return
        self.value = value
        self.show_value(value)
        self.message.setText("Saved" if self.saving else "")
        self._changed()

    def _changed(self, *_):  # also a slot for the controls' change signals
        self.apply_button.setEnabled(
            not self.busy and self.value is not None and self.current() != self.value)
