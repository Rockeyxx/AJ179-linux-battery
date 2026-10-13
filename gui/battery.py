"""The battery level, read from the file the ajazz-mouse daemon writes (no Qt)."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

STATUS_FILE = Path("/tmp/ajazz_battery")


@dataclass(frozen=True)
class Status:
    state: str          # "mouse", "charging", "disconnected" or "no-service"
    level: int | None   # 0-100, None when unknown


def parse_status(text):
    """Daemon JSON -> Status, or None when the text is empty or half-written."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    state = data.get("class")
    if state == "disconnected":
        return Status(state, None)
    m = re.search(r"(\d+)%", str(data.get("text", "")))
    if state not in ("mouse", "charging") or not m:
        return None
    return Status(state, int(m.group(1)))


def read_status(path=STATUS_FILE):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return Status("no-service", None)
    except (OSError, ValueError):
        return None
    return parse_status(text)
