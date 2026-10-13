#!/usr/bin/env python3
"""Battery window for the Ajazz AJ179, styled after the AJAZZ Windows driver.

Reads the status file the ajazz-mouse daemon writes; it never talks to the mouse.
"""
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (QColor, QKeySequence, QLinearGradient, QPainter, QPen,
                         QPolygonF, QShortcut)
from PyQt6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLayout,
                             QProgressBar, QVBoxLayout, QWidget)

STATUS_FILE = Path("/tmp/ajazz_battery")

BLACK = "#1e1e1e"
CARD = "#2c2f35"
RED = "#e8383d"   # AJAZZ logo
BLUE = "#49ffe5"  # battery fill in the driver's skin
GREY = "#b0b0b0"

STATE_TEXT = {
    "mouse": "On battery",
    "charging": "Charging",
    "disconnected": "Mouse not found",
    "no-service": "Battery service not running",
}

STYLE = f"""
QWidget#root {{ background: {BLACK}; }}
QLabel {{ color: {GREY}; font-family: "Open Sans"; font-size: 10pt; }}
QLabel#title {{ color: {RED}; font-size: 15pt; font-weight: 600; }}
QFrame#accent {{ background: {RED}; }}
QFrame#card {{ background: {CARD}; border-radius: 8px; }}
QLabel#caption {{ font-size: 8pt; font-weight: 600; }}
QLabel#percent {{ color: #ffffff; font-size: 32pt; font-weight: 600; }}
"""


@dataclass(frozen=True)
class Status:
    state: str          # a STATE_TEXT key
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


class BatteryBar(QProgressBar):
    """A progress bar drawn as the driver's upright battery, so screen readers
    still get a progress bar with its value."""

    def __init__(self):
        super().__init__()
        self.charging = False
        self.setAccessibleName("Mouse battery")
        self.setOrientation(Qt.Orientation.Vertical)
        self.setFixedSize(92, 168)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, stroke = self.width(), self.height(), 5.0
        known = self.value() >= self.minimum()
        edge_hi, edge_lo = ("#ffffff", "#c4c4c4") if known else ("#707070", "#555555")

        cap = QRectF(w * 0.32, 1, w * 0.36, h * 0.075)
        body = QRectF(stroke / 2, cap.bottom() - 1, w - stroke, h - cap.bottom() - stroke / 2)

        # White terminal cap and casing, shaded left-to-right like metal.
        metal = QLinearGradient(0, 0, w, 0)
        metal.setColorAt(0, QColor(edge_lo))
        metal.setColorAt(0.35, QColor(edge_hi))
        metal.setColorAt(1, QColor(edge_lo))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(metal)
        p.drawRoundedRect(cap, 3, 3)
        glass = QLinearGradient(0, body.top(), 0, body.bottom())
        glass.setColorAt(0, QColor("#101010"))
        glass.setColorAt(1, QColor("#1a1a1a"))
        p.setPen(QPen(metal, stroke))
        p.setBrush(glass)
        p.drawRoundedRect(body, 12, 12)

        # Blue charge rising from the bottom, rounded like a cylinder.
        inner = body.adjusted(9, 9, -9, -9)
        if known and self.value() > 0:
            level = inner.height() * self.value() / 100
            fill = QRectF(inner.left(), inner.bottom() - level, inner.width(), level)
            liquid = QLinearGradient(inner.left(), 0, inner.right(), 0)
            liquid.setColorAt(0, QColor("#1aa894"))
            liquid.setColorAt(0.4, QColor(BLUE))
            liquid.setColorAt(0.55, QColor("#a8fff3"))
            liquid.setColorAt(1, QColor("#22c9b2"))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(liquid)
            p.drawRoundedRect(fill, 6, 6)

        # Glass reflection down the left side.
        p.setPen(Qt.PenStyle.NoPen)
        shine = QLinearGradient(body.left(), 0, body.left() + w * 0.3, 0)
        shine.setColorAt(0, QColor(255, 255, 255, 0))
        shine.setColorAt(0.5, QColor(255, 255, 255, 40))
        shine.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(shine)
        p.drawRoundedRect(QRectF(body.left() + w * 0.1, body.top() + 10,
                                 w * 0.2, body.height() - 20), 6, 6)

        if self.charging:
            cx, cy = body.center().x(), body.center().y()
            bw, bh = body.width() * 0.75, body.height() * 0.5
            bolt = QPolygonF([QPointF(cx + x * bw, cy + y * bh) for x, y in (
                (0.12, -0.5), (-0.36, 0.08), (-0.02, 0.08),
                (-0.12, 0.5), (0.36, -0.08), (0.02, -0.08))])
            p.setPen(QPen(QColor(BLACK), 2))
            p.setBrush(QColor("#ffffff"))
            p.drawPolygon(bolt)


class MainWindow(QWidget):
    def __init__(self, path=STATUS_FILE):
        super().__init__()
        self.path = path
        self.setWindowTitle("AJ179 Battery")
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setStyleSheet(STYLE)

        title = QLabel("AJ179")
        title.setObjectName("title")
        accent = QFrame()
        accent.setObjectName("accent")
        accent.setFixedSize(40, 3)

        self.battery = BatteryBar()
        caption = QLabel("BATTERY")
        caption.setObjectName("caption")
        self.percent = QLabel()
        self.percent.setObjectName("percent")
        self.status = QLabel()
        self.status.ensurePolished()  # reserve the longest text so the window never jumps
        self.status.setMinimumWidth(self.status.fontMetrics().horizontalAdvance(
            max(STATE_TEXT.values(), key=len)))

        text = QVBoxLayout()
        text.addStretch()
        text.addWidget(caption)
        text.addWidget(self.percent)
        text.addWidget(self.status)
        text.addStretch()

        card = QFrame()
        card.setObjectName("card")
        row = QHBoxLayout(card)
        row.setContentsMargins(28, 24, 32, 24)
        row.setSpacing(28)
        row.addWidget(self.battery)
        row.addLayout(text)

        root = QVBoxLayout(self)
        root.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)  # tilers float it
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(6)
        root.addWidget(title)
        root.addWidget(accent)
        root.addSpacing(14)
        root.addWidget(card)

        QShortcut(QKeySequence.StandardKey.Quit, self, activated=self.close)
        self.timer = QTimer(self, interval=2000, timeout=self.refresh)
        self.timer.start()
        self.refresh()

    def refresh(self):
        status = read_status(self.path)
        if status is not None:  # a half-written file keeps the last good state
            self.show_status(status)

    def show_status(self, status):
        if status.level is None:
            self.battery.reset()
            self.percent.setText("--")
        else:
            self.battery.setValue(status.level)
            self.percent.setText(f"{status.level}%")
        self.battery.charging = status.state == "charging"
        self.battery.update()
        self.status.setText(STATE_TEXT[status.state])


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
