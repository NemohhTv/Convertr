"""Qt stylesheet for the dark, brand-green Convertr theme.

Kept as a Python module rather than a .qss file so PyInstaller bundles it
without extra ``--add-data`` config.

Color palette:
  bg            #15181c   app background
  bg_elev       #1c2026   panels, cards, list rows
  bg_elev_hi    #232830   hover state, alt rows
  border        #2a2f37   subtle dividers
  text          #e8eaed   primary text
  text_muted    #9aa0a6   secondary text
  accent        #5fd068   brand green (matches logo)
  accent_hi     #74e07d   hover green
  accent_lo     #4ab854   pressed green
  danger        #ef5b5b   destructive actions
"""

STYLESHEET = """
* {
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    color: #e8eaed;
    outline: none;
}

QMainWindow, QDialog, QWidget#root {
    background-color: #15181c;
}

QLabel {
    background: transparent;
    color: #e8eaed;
}
QLabel[role="muted"] {
    color: #9aa0a6;
}
QLabel[role="title"] {
    font-size: 22px;
    font-weight: 600;
    color: #ffffff;
}
QLabel[role="subtitle"] {
    font-size: 13px;
    color: #9aa0a6;
}
QLabel[role="section"] {
    font-size: 11px;
    font-weight: 700;
    color: #9aa0a6;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}

/* --- Cards / panels ----------------------------------------------------- */
QFrame#card {
    background-color: #1c2026;
    border: 1px solid #2a2f37;
    border-radius: 10px;
}

/* --- Buttons ------------------------------------------------------------ */
QPushButton {
    background-color: #232830;
    color: #e8eaed;
    border: 1px solid #2a2f37;
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 20px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #2b313b;
    border-color: #353c47;
}
QPushButton:pressed {
    background-color: #1f242c;
}
QPushButton:disabled {
    color: #5a6068;
    background-color: #1c2026;
    border-color: #232830;
}

QPushButton[role="primary"] {
    background-color: #5fd068;
    color: #0c1a0e;
    border: 1px solid #5fd068;
    font-weight: 600;
}
QPushButton[role="primary"]:hover {
    background-color: #74e07d;
    border-color: #74e07d;
}
QPushButton[role="primary"]:pressed {
    background-color: #4ab854;
    border-color: #4ab854;
}
QPushButton[role="primary"]:disabled {
    background-color: #2c3a2e;
    color: #6c8a6f;
    border-color: #2c3a2e;
}

QPushButton[role="danger"] {
    color: #ef5b5b;
    border-color: #3a2528;
}
QPushButton[role="danger"]:hover {
    background-color: #2a1c1f;
    border-color: #4a2d31;
}

QPushButton[role="ghost"] {
    background-color: transparent;
    border-color: transparent;
    color: #9aa0a6;
}
QPushButton[role="ghost"]:hover {
    background-color: #1c2026;
    color: #e8eaed;
}

/* --- Inputs ------------------------------------------------------------- */
QLineEdit, QComboBox, QSpinBox {
    background-color: #15181c;
    color: #e8eaed;
    border: 1px solid #2a2f37;
    border-radius: 8px;
    padding: 7px 10px;
    min-height: 20px;
    selection-background-color: #5fd068;
    selection-color: #0c1a0e;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #5fd068;
}
QLineEdit:disabled, QComboBox:disabled {
    color: #5a6068;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9aa0a6;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1c2026;
    border: 1px solid #2a2f37;
    border-radius: 6px;
    selection-background-color: #2b313b;
    selection-color: #e8eaed;
    padding: 4px;
}

/* --- Checkbox ----------------------------------------------------------- */
QCheckBox {
    spacing: 10px;
    color: #e8eaed;
    background: transparent;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #353c47;
    border-radius: 4px;
    background-color: #15181c;
}
QCheckBox::indicator:hover {
    border-color: #5fd068;
}
QCheckBox::indicator:checked {
    background-color: #5fd068;
    border-color: #5fd068;
    image: none;
}

/* --- Tabs --------------------------------------------------------------- */
QTabWidget::pane {
    border: none;
    background: transparent;
    top: -1px;
}
QTabBar {
    qproperty-drawBase: 0;
    background: transparent;
}
QTabBar::tab {
    background-color: transparent;
    color: #9aa0a6;
    padding: 9px 18px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:hover {
    color: #e8eaed;
}
QTabBar::tab:selected {
    color: #ffffff;
    border-bottom: 2px solid #5fd068;
}

/* --- Progress bar ------------------------------------------------------- */
QProgressBar {
    background-color: #232830;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #5fd068;
    border-radius: 4px;
}

/* --- Lists / tables ----------------------------------------------------- */
QListWidget, QTableWidget, QTreeWidget {
    background-color: #15181c;
    border: 1px solid #2a2f37;
    border-radius: 8px;
    padding: 4px;
    alternate-background-color: #181b20;
}
QListWidget::item, QTableWidget::item {
    padding: 8px 10px;
    border-radius: 5px;
    border: none;
}
QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #2b313b;
    color: #e8eaed;
}
QListWidget::item:hover, QTableWidget::item:hover {
    background-color: #1c2026;
}
QHeaderView::section {
    background-color: #1c2026;
    color: #9aa0a6;
    border: none;
    border-bottom: 1px solid #2a2f37;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* --- Scrollbars --------------------------------------------------------- */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}
QScrollBar::handle:vertical {
    background: #2a2f37;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #353c47;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px 4px;
}
QScrollBar::handle:horizontal {
    background: #2a2f37;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #353c47;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

/* --- Update banner ------------------------------------------------------ */
QFrame#update_banner {
    background-color: #1f2a20;
    border: 1px solid #2c5a32;
    border-radius: 8px;
}

/* --- Drop zone ---------------------------------------------------------- */
QFrame#drop_zone {
    background-color: #181b20;
    border: 2px dashed #353c47;
    border-radius: 12px;
}
QFrame#drop_zone[dragging="true"] {
    border-color: #5fd068;
    background-color: #1f2a20;
}

/* --- Tooltip ------------------------------------------------------------ */
QToolTip {
    background-color: #232830;
    color: #e8eaed;
    border: 1px solid #2a2f37;
    border-radius: 6px;
    padding: 6px 8px;
}

/* --- Menu --------------------------------------------------------------- */
QMenu {
    background-color: #1c2026;
    border: 1px solid #2a2f37;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 7px 18px;
    border-radius: 5px;
}
QMenu::item:selected {
    background-color: #2b313b;
}
QMenu::separator {
    height: 1px;
    background: #2a2f37;
    margin: 6px 8px;
}

/* --- Status bar --------------------------------------------------------- */
QStatusBar {
    background-color: #15181c;
    color: #9aa0a6;
    border-top: 1px solid #2a2f37;
}

/* --- Dialog ------------------------------------------------------------- */
QMessageBox {
    background-color: #1c2026;
}
QMessageBox QLabel {
    color: #e8eaed;
}
"""
