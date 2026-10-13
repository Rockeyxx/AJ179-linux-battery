#!/usr/bin/env python3
"""Low-battery notification, run in the background by aj179-battery-alert.service.

Once a minute it reads the daemon's battery file and, while the alert is on (the
app's Home page writes ~/.config/ajazzctl/battery-alert), sends one desktop
notification when the mouse runs down to the threshold.
"""
import os
import subprocess
import time
from pathlib import Path

from battery import read_status

DEFAULT = (True, 20)  # on, at 20 %
REARM = 5  # % above the threshold that re-arms it, so a 20/21 % flicker stays quiet


def alert_file():
    config = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config) / "ajazzctl" / "battery-alert"


def load_config(path):
    """-> (enabled, threshold); the defaults when the file is missing or garbled."""
    try:
        values = dict(line.split("=", 1) for line in Path(path).read_text().split())
        return values["enabled"] == "1", int(values["threshold"])
    except (OSError, ValueError, KeyError):
        return DEFAULT


def save_config(path, enabled, threshold):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"enabled={int(enabled)}\nthreshold={threshold}\n")


def check(status, threshold, armed):
    """-> (notify now, armed). One notification per discharge: it re-arms when the
    mouse charges or its level is clearly back above the threshold."""
    if status is None or status.level is None:
        return False, armed
    if status.state == "charging" or status.level >= threshold + REARM:
        return False, True
    if armed and status.level <= threshold:
        return True, False
    return False, armed


def main():
    armed = True
    while True:
        enabled, threshold = load_config(alert_file())
        status = read_status()
        notify, now_armed = check(status, threshold, armed)
        if enabled:
            armed = now_armed
            if notify:
                try:
                    subprocess.run(["notify-send", "-u", "critical", "-i", "aj179",
                                    "AJ179 battery low",
                                    f"{status.level}% left - plug in the cable to charge."],
                                   check=False)
                except OSError:  # no notify-send: nothing to show it with
                    pass
        time.sleep(60)


if __name__ == "__main__":
    main()
