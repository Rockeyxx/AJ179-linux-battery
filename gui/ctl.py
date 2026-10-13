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


@dataclass(frozen=True)
class Settings:
    rate: int                  # report rate, Hz
    lod: int                   # lift-off distance: 1 = 1 mm, 2 = 2 mm
    motion_sync: bool
    angle_snap: bool
    debounce: int              # ms going by the default of 8 (units unconfirmed)
    sleep: int                 # s going by the default of 30 (units unconfirmed)
    wake_on_move: bool
    lights_off_on_move: bool


def parse_settings(text):
    """`ajazzctl show --json` output -> Settings, or None if it is not that."""
    try:
        d = json.loads(text)
        p = d["power"]
        return Settings(int(d["rate"]), int(d["lod"]), bool(d["motion_sync"]),
                        bool(d["angle_snap"]), int(p["debounce"]), int(p["sleep"]),
                        bool(p["wake_on_move"]), bool(p["lights_off_on_move"]))
    except (ValueError, KeyError, TypeError):
        return None


ON = {True: "on", False: "off"}
SETTING_COMMANDS = (  # Settings field -> ajazzctl command that sets it
    ("rate", lambda v: ["rate", str(v)]),
    ("lod", lambda v: ["sensor", "lod", str(v)]),
    ("motion_sync", lambda v: ["sensor", "motion-sync", ON[v]]),
    ("angle_snap", lambda v: ["sensor", "angle-snap", ON[v]]),
    ("debounce", lambda v: ["power", "debounce", str(v)]),
    ("sleep", lambda v: ["power", "sleep", str(v)]),
    ("wake_on_move", lambda v: ["power", "wake-on-move", ON[v]]),
    ("lights_off_on_move", lambda v: ["power", "lights-off-on-move", ON[v]]),
)


def settings_commands(old, new):
    return [command(getattr(new, field)) for field, command in SETTING_COMMANDS
            if getattr(old, field) != getattr(new, field)]


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
