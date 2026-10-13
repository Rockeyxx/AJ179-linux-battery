import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PyQt6.QtWidgets import QApplication

# A real `ajazzctl show --json` line from the AJ179.
SHOW = ('{"rate":1000,"dpi":{"active":5,"stages":[400,800,1200,1600,2400,3200],'
        '"colours":["#ff0000","#0000ff","#ffff00","#00ff00","#00ffff","#ff00ff"]},'
        '"lighting":{"mode":"constant","colour":"#ff00ff","brightness":4,"speed":0},"lod":2,'
        '"motion_sync":false,"angle_snap":false,"power":{"sleep":30,"wake_on_move":0,'
        '"lights_off_on_move":0,"debounce":8},'
        '"buttons":["left","right","middle","back","forward","dpi-loop"],"macros":{},'
        '"receiver_fw":"41.01"}\n')

# Stands in for ajazzctl: logs its arguments, prints $FAKE_SHOW for "show --json",
# and fails like a sleeping mouse when its arguments equal $FAKE_FAIL.
FAKE = """#!/bin/sh
echo "$*" >> "$FAKE_LOG"
if [ "$*" = "$FAKE_FAIL" ]; then echo "mouse is asleep - move it" >&2; exit 1; fi
if [ "$*" = "show --json" ]; then cat "$FAKE_SHOW"; fi
"""


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fake_ctl(tmp_path, monkeypatch):
    script, log, show = tmp_path / "ajazzctl", tmp_path / "log", tmp_path / "show.json"
    script.write_text(FAKE)
    script.chmod(0o755)
    show.write_text(SHOW)
    monkeypatch.setenv("AJAZZCTL", str(script))
    monkeypatch.setenv("FAKE_LOG", str(log))
    monkeypatch.setenv("FAKE_SHOW", str(show))
    monkeypatch.setenv("FAKE_FAIL", "")
    return SimpleNamespace(
        show=show,
        calls=lambda: log.read_text().splitlines() if log.exists() else [])
