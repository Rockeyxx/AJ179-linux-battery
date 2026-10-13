"""Runs ajazzctl for the GUI and reads its `show --json` output.

All mouse I/O goes through ajazzctl; set $AJAZZCTL to use another binary.
"""
import json
import os
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


@dataclass(frozen=True)
class Dpi:
    active: int                # 1-based stage, as on the command line
    stages: tuple[int, ...]
    colours: tuple[str, ...]   # "#rrggbb", one per stage


def parse_dpi(text):
    """`ajazzctl show --json` output -> Dpi, or None if it is not that."""
    try:
        d = json.loads(text)["dpi"]
        stages = tuple(int(v) for v in d["stages"])
        colours = tuple(str(c) for c in d["colours"])[:len(stages)]
        active = int(d["active"])
    except (ValueError, KeyError, TypeError):
        return None
    if not stages or len(colours) != len(stages) or not 1 <= active <= len(stages):
        return None
    return Dpi(active, stages, colours)


def dpi_commands(old, new):
    """ajazzctl commands that turn old into new: values, colours, then the active stage."""
    cmds = [["dpi", str(i), str(b)]
            for i, (a, b) in enumerate(zip(old.stages, new.stages), 1) if a != b]
    cmds += [["dpi-colour", str(i), b]
             for i, (a, b) in enumerate(zip(old.colours, new.colours), 1) if a.lower() != b.lower()]
    if old.active != new.active:
        cmds.append(["dpi", "select", str(new.active)])
    return cmds


class Ctl(QObject):
    """Runs ajazzctl jobs without blocking the window (ajazzctl waits for a sleeping
    mouse). Pages share one Ctl, so jobs run one at a time and never talk to the
    mouse at once; each result names the page that asked."""

    done = pyqtSignal(object, bool, str)  # owner, ok, last stdout or the error line

    def __init__(self):
        super().__init__()
        self.jobs, self.queue, self.owner, self.active = [], [], None, False
        self.proc = QProcess(self)
        self.proc.finished.connect(self._finished)
        self.proc.errorOccurred.connect(self._error)

    def run(self, commands, owner=None):
        self.jobs.append((owner, list(commands)))
        if not self.active:
            self._start()

    def _start(self):
        self.active = True
        self.owner, self.queue = self.jobs.pop(0)
        self._next("")

    def _next(self, out):
        if not self.queue:
            self._finish(True, out)
            return
        self.proc.start(os.environ.get("AJAZZCTL", "ajazzctl"), self.queue.pop(0))

    def _finish(self, ok, text):
        self.active = False
        self.done.emit(self.owner, ok, text)
        if self.jobs and not self.active:  # a handler may already have started one
            self._start()

    def _finished(self, code, status):
        out = bytes(self.proc.readAllStandardOutput()).decode()
        if status == QProcess.ExitStatus.NormalExit and code == 0:
            self._next(out)
            return
        err = bytes(self.proc.readAllStandardError()).decode().strip().splitlines()
        self._finish(False, err[-1] if err else f"ajazzctl failed ({code})")

    def _error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._finish(False, "ajazzctl not found - install aj179-linux")
