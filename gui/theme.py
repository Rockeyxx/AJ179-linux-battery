"""Colours and style sheet: the AJAZZ driver's red and black, drawn in code."""
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
QSlider::handle:horizontal {{ background: #ffffff; width: 14px; margin: -5px 0;
    border-radius: 7px; }}
QSpinBox {{ color: #ffffff; background: {BLACK}; border: 1px solid {LINE};
    border-radius: 4px; padding: 4px 6px; min-width: 76px;
    font-family: "Open Sans"; font-size: 10pt; }}
QSpinBox:focus {{ border-color: {RED}; }}
QToolTip {{ color: #ffffff; background: {CARD}; border: 1px solid {LINE}; }}
"""
