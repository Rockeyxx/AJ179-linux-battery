#!/usr/bin/env python3
"""Battery window for the Ajazz AJ179, styled after the AJAZZ Windows driver.

Reads the status file the ajazz-mouse daemon writes; it never talks to the mouse.
"""
import sys
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (QColor, QIcon, QKeySequence, QLinearGradient, QPainter, QPen,
                         QPolygonF, QShortcut)
from PyQt6.QtWidgets import (QAbstractSpinBox, QApplication, QButtonGroup, QCheckBox, QFrame,
                             QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea,
                             QSpinBox, QStackedWidget, QVBoxLayout, QWidget)

from alert import alert_file, load_config, save_config
from battery import STATUS_FILE, Status, parse_status, read_status  # noqa: F401 (tests)
from buttons_page import ButtonsPage
from ctl import Ctl
from dpi_page import DpiPage
from lighting_page import LightingPage
from macro_page import MacroPage
from page import DevicePage
from settings_page import SettingsPage
from theme import BLACK, BLUE, STYLE

ICON = Path(__file__).parent / "icons" / "aj179.svg"

STATE_TEXT = {
    "mouse": "On battery",
    "charging": "Charging",
    "disconnected": "Mouse not found",
    "no-service": "Battery service not running",
}

FEATURES = ("Home", "DPI", "Buttons", "Lighting", "Macro", "Settings")


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
        self.setMinimumSize(480, 360)  # resizable, so tiling compositors tile it
        self.resize(860, 540)

        self.ctl = Ctl()  # shared: one ajazzctl job at a time
        self.dpi = DpiPage(self.ctl)
        self.buttons = ButtonsPage(self.ctl)
        self.lighting = LightingPage(self.ctl)
        self.macro = MacroPage(self.ctl)
        self.settings = SettingsPage(self.ctl)
        self.page_for = {"Home": self._home_page(), "DPI": self.dpi, "Buttons": self.buttons,
                         "Lighting": self.lighting, "Macro": self.macro,
                         "Settings": self.settings}
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

        self.sidebar = sidebar = QFrame()
        sidebar.setObjectName("sidebar")
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

        # Pages scroll when the tile is smaller than they are, and stay a readable width,
        # centred, when it is much wider.
        inner = QWidget()
        self.content = QHBoxLayout(inner)
        self.pages.setMaximumWidth(860)
        self.content.addStretch(1)
        self.content.addWidget(self.pages, 30)
        self.content.addStretch(1)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.setWidget(inner)
        inner.setAutoFillBackground(False)  # setWidget turns it on: keep the theme's black
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(sidebar)
        root.addWidget(self.scroll, 1)
        self._fit(self.width())

        QShortcut(QKeySequence.StandardKey.Quit, self, activated=self.close)
        self.timer = QTimer(self, interval=2000, timeout=self.refresh)
        self.timer.start()
        self.refresh()

    def resizeEvent(self, event):
        self._fit(event.size().width())
        super().resizeEvent(event)

    def _fit(self, width):
        narrow = width < 760  # e.g. a third of the screen: give the page the room
        self.sidebar.setFixedWidth(132 if narrow else 190)
        margin = 16 if narrow else 32
        self.content.setContentsMargins(margin, 24, margin, 24)

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

        # Low-battery notification: a background service reads these settings.
        enabled, threshold = load_config(alert_file())
        self.alert = QCheckBox("Notify me when the battery is low")
        self.alert.setChecked(enabled)
        self.alert_level = QSpinBox()
        self.alert_level.setRange(5, 50)
        self.alert_level.setSuffix(" %")
        self.alert_level.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.alert_level.setAccessibleName("Low battery level")
        self.alert_level.setValue(threshold)
        self.alert_level.setEnabled(enabled)
        self.alert.toggled.connect(self._save_alert)
        self.alert_level.valueChanged.connect(self._save_alert)
        alert = QHBoxLayout()
        alert.setSpacing(12)
        alert.addWidget(self.alert)
        alert.addWidget(QLabel("at"))
        alert.addWidget(self.alert_level)
        alert.addStretch()

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(heading)
        layout.addSpacing(10)
        layout.addWidget(card)
        layout.addSpacing(14)
        layout.addLayout(alert)
        layout.addWidget(QLabel("Works in the background, even with this window closed."))
        layout.addStretch()
        return page

    def _save_alert(self, *_):
        self.alert_level.setEnabled(self.alert.isChecked())
        save_config(alert_file(), self.alert.isChecked(), self.alert_level.value())

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
    app.setDesktopFileName("aj179")  # Wayland app id, matching aj179.desktop
    app.setWindowIcon(QIcon(str(ICON)))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
