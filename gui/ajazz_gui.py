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
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel,
                             QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from ctl import Ctl
from dpi_page import DpiPage
from lighting_page import LightingPage
from page import DevicePage
from settings_page import SettingsPage
from theme import BLACK, BLUE, STYLE

STATUS_FILE = Path("/tmp/ajazz_battery")

STATE_TEXT = {
    "mouse": "On battery",
    "charging": "Charging",
    "disconnected": "Mouse not found",
    "no-service": "Battery service not running",
}

FEATURES = ("Home", "DPI", "Buttons", "Lighting", "Macro", "Settings")


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
    """The driver's layout: a sidebar with every feature, one page per feature."""

    def __init__(self, path=STATUS_FILE):
        super().__init__()
        self.path = path
        self.setWindowTitle("AJ179")
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setStyleSheet(STYLE)
        self.setFixedSize(860, 540)  # a fixed size makes tiling compositors float it

        self.ctl = Ctl()  # shared: one ajazzctl job at a time
        self.dpi = DpiPage(self.ctl)
        self.lighting = LightingPage(self.ctl)
        self.settings = SettingsPage(self.ctl)
        self.page_for = {"Home": self._home_page(), "DPI": self.dpi,
                         "Lighting": self.lighting, "Settings": self.settings}
        self.pages = QStackedWidget()
        for page in self.page_for.values():
            self.pages.addWidget(page)

        title = QLabel("AJ179")
        title.setObjectName("title")
        accent = QFrame()
        accent.setObjectName("accent")
        accent.setFixedSize(40, 3)
        brand = QVBoxLayout()
        brand.setContentsMargins(24, 0, 24, 24)
        brand.setSpacing(6)
        brand.addWidget(title)
        brand.addWidget(accent)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 20, 0, 20)
        side.setSpacing(0)
        side.addLayout(brand)
        self.tabs = []
        group = QButtonGroup(self)
        for i, name in enumerate(FEATURES):
            tab = QPushButton(name)
            tab.setObjectName("tab")
            tab.setCheckable(True)
            if name not in self.page_for:
                tab.setEnabled(False)
                tab.setToolTip("Coming soon")
                tab.setAccessibleDescription("Coming soon")
            group.addButton(tab, i)
            side.addWidget(tab)
            self.tabs.append(tab)
        side.addStretch()
        group.idClicked.connect(self._show_page)
        self.tabs[0].setChecked(True)

        content = QVBoxLayout()
        content.setContentsMargins(32, 28, 32, 28)
        content.addWidget(self.pages)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(sidebar)
        root.addLayout(content, 1)

        QShortcut(QKeySequence.StandardKey.Quit, self, activated=self.close)
        self.timer = QTimer(self, interval=2000, timeout=self.refresh)
        self.timer.start()
        self.refresh()

    def _home_page(self):
        heading = QLabel("Battery")
        heading.setObjectName("heading")
        self.battery = BatteryBar()
        caption = QLabel("BATTERY")
        caption.setObjectName("caption")
        self.percent = QLabel()
        self.percent.setObjectName("percent")
        self.status = QLabel()
        self.status.ensurePolished()  # reserve the longest text so the card never jumps
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
        row.addStretch()

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(heading)
        layout.addSpacing(10)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _show_page(self, i):
        page = self.page_for[FEATURES[i]]
        self.pages.setCurrentWidget(page)
        # Read the mouse when a page opens, unless that would throw away unsaved edits.
        if isinstance(page, DevicePage) and not page.busy and not page.apply_button.isEnabled():
            page.load()

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
