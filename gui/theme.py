"""Colours and style sheet: the AJAZZ driver's red and black, drawn in code."""
from pathlib import Path

ICONS = (Path(__file__).parent / "icons").as_posix()
BLACK = "#1e1e1e"
SIDEBAR = "#25262b"
CARD = "#2c2f35"
RAISED = "#353842"
LINE = "#45484f"
RED = "#e8383d"       # AJAZZ logo; headings, accents, outlines
DARK_RED = "#b3262b"  # filled buttons: white text on it is 6.5:1
BLUE = "#49ffe5"      # battery fill in the driver's skin
GREY = "#b0b0b0"
MUTED = "#6b6b6b"

STYLE = f"""
QWidget#root {{ background: {BLACK}; }}
QLabel {{ color: {GREY}; font-family: "Open Sans"; font-size: 10pt; }}
QLabel#title {{ color: {RED}; font-size: 15pt; font-weight: 600; }}
QLabel#heading {{ color: #ffffff; font-size: 15pt; font-weight: 600; }}
QLabel#caption {{ font-size: 8pt; font-weight: 600; }}
QLabel#name {{ color: #ffffff; }}
QLabel#percent {{ color: #ffffff; font-size: 32pt; font-weight: 600; }}
QFrame#accent {{ background: {RED}; }}
QFrame#card {{ background: {CARD}; border-radius: 8px; }}
QFrame#sidebar {{ background: {SIDEBAR}; }}

QPushButton {{ color: #ffffff; background: transparent; border: 1px solid {RED};
    border-radius: 4px; padding: 6px 18px; font-family: "Open Sans"; font-size: 10pt; }}
QPushButton:hover, QPushButton:focus {{ background: {DARK_RED}; }}
QPushButton:disabled {{ color: {MUTED}; border-color: {LINE}; }}
QPushButton#tab {{ border: none; border-left: 3px solid transparent; border-radius: 0;
    padding: 0 21px; min-height: 52px; text-align: left; font-size: 11pt; }}
QPushButton#tab:hover {{ background: {RAISED}; }}
QPushButton#tab:focus {{ background: transparent; border-left-color: {GREY}; }}
QPushButton#tab:checked {{ background: {RAISED}; border-left-color: {RED}; }}
QPushButton#tab:disabled {{ color: {MUTED}; }}
QPushButton#swatch {{ border: 2px solid #ffffff; border-radius: 4px; padding: 0;
    min-width: 30px; max-width: 30px; min-height: 18px; max-height: 18px; }}
QPushButton#swatch:focus {{ border-color: {RED}; }}
QPushButton#swatch:disabled {{ border-color: {MUTED}; }}

QRadioButton {{ color: #ffffff; font-family: "Open Sans"; font-size: 10pt; spacing: 8px; }}
QRadioButton::indicator {{ width: 12px; height: 12px; border-radius: 8px;
    border: 2px solid {GREY}; }}
QRadioButton::indicator:checked {{ background: {RED}; border-color: #ffffff; }}
QCheckBox {{ color: #ffffff; font-family: "Open Sans"; font-size: 10pt; spacing: 8px; }}
QCheckBox::indicator {{ width: 12px; height: 12px; border-radius: 3px;
    border: 2px solid {GREY}; }}
QCheckBox::indicator:checked {{ background: {RED}; border-color: #ffffff; }}
QSlider::groove:horizontal {{ height: 4px; background: {LINE}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {RED}; border-radius: 2px; }}
QSlider::sub-page:horizontal:disabled {{ background: {MUTED}; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 14px; margin: -5px 0;
    border-radius: 7px; }}
QSlider::handle:horizontal:disabled {{ background: {MUTED}; }}
QRadioButton:disabled, QCheckBox:disabled {{ color: {MUTED}; }}
QSpinBox {{ color: #ffffff; background: {BLACK}; border: 1px solid {LINE};
    border-radius: 4px; padding: 4px 6px; min-width: 76px;
    font-family: "Open Sans"; font-size: 10pt; }}
QSpinBox:focus {{ border-color: {RED}; }}
QComboBox, QLineEdit {{ color: #ffffff; background: {BLACK}; border: 1px solid {LINE};
    border-radius: 4px; padding: 4px 8px; font-family: "Open Sans"; font-size: 10pt; }}
QComboBox {{ min-width: 170px; }}
QComboBox:focus, QLineEdit:focus {{ border-color: {RED}; }}
QComboBox:disabled {{ color: {MUTED}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url({ICONS}/chevron-down.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ color: #ffffff; background: {CARD}; border: 1px solid {LINE};
    selection-background-color: {DARK_RED}; }}
QListWidget {{ color: #ffffff; background: {BLACK}; border: 1px solid {LINE};
    border-radius: 4px; padding: 4px; font-family: "Open Sans"; font-size: 10pt; }}
QListWidget:focus {{ border-color: {RED}; }}
QListWidget::item {{ padding: 3px 6px; }}
QListWidget::item:selected {{ background: {DARK_RED}; color: #ffffff; }}
QScrollArea {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle {{ background: {LINE}; border-radius: 4px; min-height: 30px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QToolTip {{ color: #ffffff; background: {CARD}; border: 1px solid {LINE}; }}
"""
