#!/usr/bin/env python3
"""911OT-KKL Scanner - PySide6 (Qt) Prototype"""

import sys
import time
import random
import serial.tools.list_ports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTabWidget, QTextEdit, QProgressBar,
    QFrame, QGridLayout, QButtonGroup, QRadioButton, QScrollArea,
    QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

# --- Colors ---
C_BG       = "#0d1117"
C_PANEL    = "#161b22"
C_PANEL2   = "#1c2333"
C_ACCENT   = "#ff6b00"
C_ACCENT2  = "#ff8c38"
C_GREEN    = "#00c853"
C_RED      = "#ff1744"
C_YELLOW   = "#ffd600"
C_TEXT     = "#e6edf3"
C_TEXT_DIM = "#7d8590"
C_BORDER   = "#30363d"

# --- Stylesheet ---
QSS = f"""
QMainWindow {{
    background-color: {C_BG};
}}
QWidget {{
    color: {C_TEXT};
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}
QFrame#header {{
    background-color: {C_PANEL};
    border-bottom: 1px solid {C_BORDER};
    min-height: 48px;
}}
QFrame#panel {{
    background-color: {C_PANEL};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
}}
QFrame#ecu_info {{
    background-color: {C_PANEL};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
}}
QLabel#logo {{
    color: {C_ACCENT};
    font-size: 20px;
    font-weight: bold;
    font-family: "SF Pro Display", "Helvetica Neue", sans-serif;
}}
QLabel#subtitle {{
    color: {C_TEXT_DIM};
    font-size: 12px;
}}
QLabel#dim {{
    color: {C_TEXT_DIM};
    font-size: 12px;
}}
QLabel#badge {{
    background-color: {C_YELLOW};
    color: #000;
    font-size: 11px;
    font-weight: bold;
    border-radius: 4px;
    padding: 2px 8px;
}}
QLabel#mono {{
    font-family: "Menlo", "SF Mono", monospace;
    font-size: 12px;
}}
QComboBox {{
    background-color: {C_PANEL2};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 200px;
    color: {C_TEXT};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {C_TEXT_DIM};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {C_PANEL2};
    border: 1px solid {C_BORDER};
    selection-background-color: {C_ACCENT};
    selection-color: #000;
    outline: none;
}}
QPushButton {{
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton#connect {{
    background-color: {C_GREEN};
    color: #000;
}}
QPushButton#connect:hover {{
    background-color: #00b848;
}}
QPushButton#disconnect {{
    background-color: {C_RED};
    color: #fff;
}}
QPushButton#disconnect:hover {{
    background-color: #e0143c;
}}
QPushButton#accent {{
    background-color: {C_ACCENT};
    color: #000;
}}
QPushButton#accent:hover {{
    background-color: {C_ACCENT2};
}}
QPushButton#danger {{
    background-color: {C_RED};
    color: #fff;
}}
QPushButton#danger:hover {{
    background-color: #e0143c;
}}
QPushButton:disabled {{
    background-color: {C_PANEL2};
    color: {C_TEXT_DIM};
}}
QRadioButton {{
    spacing: 6px;
    font-size: 13px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid {C_BORDER};
    background-color: {C_PANEL2};
}}
QRadioButton::indicator:checked {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
}}
QTabWidget::pane {{
    background-color: {C_PANEL};
    border: 1px solid {C_BORDER};
    border-radius: 0 0 8px 8px;
    border-top: none;
}}
QTabBar::tab {{
    background-color: {C_PANEL2};
    color: {C_TEXT_DIM};
    border: 1px solid {C_BORDER};
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-radius: 6px 6px 0 0;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    background-color: {C_ACCENT};
    color: #000;
    border-color: {C_ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background-color: {C_BORDER};
    color: {C_TEXT};
}}
QTextEdit {{
    background-color: {C_BG};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 8px;
    font-family: "Menlo", "SF Mono", monospace;
    font-size: 13px;
}}
QTextEdit#log {{
    color: {C_GREEN};
    font-size: 12px;
}}
QProgressBar {{
    background-color: {C_PANEL2};
    border: none;
    border-radius: 4px;
    height: 14px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{
    background-color: {C_ACCENT};
    border-radius: 4px;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QFrame#statusbar {{
    background-color: {C_PANEL};
    border-top: 1px solid {C_BORDER};
    min-height: 28px;
}}
QFrame#gauge_row {{
    background-color: transparent;
    border-bottom: 1px solid {C_BORDER};
    padding: 4px 0;
}}
QFrame#actuator_row {{
    border-bottom: 1px solid {C_BORDER};
    padding: 2px 0;
}}
"""

# --- ECU definitions ---
ECUS = {
    "964": [
        ("Motronic M2.1",  0x10, 8800),
        ("ABS (C4 only)",  0x3D, 4800),
        ("CCU (Climate)",  0x51, 4800),
        ("SRS (Airbag)",   0x57, 9600),
        ("Alarm",          0x40, 9600),
    ],
    "993": [
        ("Motronic M5.2",  0x10, 9600),
        ("ABS",            0x1F, 9600),
        ("CCU (Climate)",  0x51, 4800),
        ("SRS (Airbag)",   0x57, 9600),
        ("Alarm",          0x40, 9600),
        ("Tiptronic",      0x01, 9600),
    ],
    "965": [
        ("CCU (Climate)",  0x51, 4800),
        ("SRS (Airbag)",   0x57, 9600),
        ("Alarm",          0x40, 9600),
        ("ABS",            0x3D, 4800),
    ],
}

DEMO_FAULTS = [
    ("12", "Throttle Position Sensor", 3),
    ("23", "Coolant Temperature Sensor", 1),
    ("24", "O2 Sensor Signal", 5),
]

DEMO_LIVE = {
    "RPM":           {"addr": "0x3A", "value": 850,  "max": 7000, "unit": "rpm",  "fmt": "{:.0f}"},
    "Head Temp":     {"addr": "0x38", "value": 185,  "max": 260,  "unit": "°F",   "fmt": "{:.0f}"},
    "Intake Temp":   {"addr": "0x37", "value": 95,   "max": 200,  "unit": "°F",   "fmt": "{:.0f}"},
    "AFM Voltage":   {"addr": "0x45", "value": 1.8,  "max": 5.0,  "unit": "V",    "fmt": "{:.2f}"},
    "Injector Time": {"addr": "0x42", "value": 3.2,  "max": 15.0, "unit": "ms",   "fmt": "{:.1f}"},
    "Timing":        {"addr": "0x5D", "value": 12.0, "max": 40.0, "unit": "°",    "fmt": "{:.1f}"},
    "Battery":       {"addr": "ADC1", "value": 13.8, "max": 16.0, "unit": "V",    "fmt": "{:.1f}"},
}


class GaugeRow(QFrame):
    """A single live data gauge row."""

    def __init__(self, name, unit, max_val, parent=None):
        super().__init__(parent)
        self.setObjectName("gauge_row")
        self.max_val = max_val
        self.unit = unit

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_name = QLabel(name)
        self.lbl_name.setObjectName("dim")
        self.lbl_name.setFixedWidth(120)
        layout.addWidget(self.lbl_name)

        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        layout.addWidget(self.bar, 1)

        self.lbl_val = QLabel(f"--- {unit}")
        self.lbl_val.setObjectName("mono")
        self.lbl_val.setFixedWidth(100)
        self.lbl_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        font = QFont("Menlo", 14)
        font.setBold(True)
        self.lbl_val.setFont(font)
        layout.addWidget(self.lbl_val)

    def set_value(self, val, fmt="{:.0f}"):
        ratio = min(val / self.max_val, 1.0) if self.max_val > 0 else 0
        self.bar.setValue(int(ratio * 1000))

        if ratio > 0.85:
            color = C_RED
        elif ratio > 0.7:
            color = C_YELLOW
        else:
            color = C_ACCENT

        self.bar.setStyleSheet(f"""
            QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}
        """)
        self.lbl_val.setText(f"{fmt.format(val)} {self.unit}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("911OT-KKL Scanner [PySide6 / Qt]")
        self.resize(800, 720)
        self.setMinimumSize(720, 600)

        self.connected = False
        self.gauges = {}

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._build_header(main_layout)

        content = QVBoxLayout()
        content.setContentsMargins(12, 10, 12, 6)
        content.setSpacing(6)

        self._build_connection(content)
        self._build_ecu_info(content)
        self._build_tabs(content)

        main_layout.addLayout(content, 1)
        self._build_statusbar(main_layout)

        # Demo timer
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self._demo_tick)

    def _build_header(self, parent):
        header = QFrame()
        header.setObjectName("header")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(16, 8, 16, 8)

        logo = QLabel("911OT-KKL")
        logo.setObjectName("logo")
        hlay.addWidget(logo)

        sub = QLabel("Porsche 964 / 993 / 965 K-Line Scanner")
        sub.setObjectName("subtitle")
        hlay.addWidget(sub)

        hlay.addStretch()

        self.badge = QLabel(" DEMO ")
        self.badge.setObjectName("badge")
        self.badge.hide()
        hlay.addWidget(self.badge)

        parent.addWidget(header)

    def _build_connection(self, parent):
        panel = QFrame()
        panel.setObjectName("panel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        # Port
        lbl_port = QLabel("Port")
        lbl_port.setObjectName("dim")
        grid.addWidget(lbl_port, 0, 0)

        self.port_combo = QComboBox()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        ports = ports if ports else ["(no ports)"]
        ports.append("Demo")
        self.port_combo.addItems(ports)
        grid.addWidget(self.port_combo, 0, 1)

        # Model radio
        lbl_model = QLabel("Model")
        lbl_model.setObjectName("dim")
        grid.addWidget(lbl_model, 0, 2)

        model_box = QHBoxLayout()
        self.model_group = QButtonGroup(self)
        for m in ["964", "993", "965"]:
            rb = QRadioButton(m)
            rb.setChecked(m == "965")
            self.model_group.addButton(rb)
            model_box.addWidget(rb)
            rb.toggled.connect(self._on_model_change)
        grid.addLayout(model_box, 0, 3)

        # ECU
        lbl_ecu = QLabel("ECU")
        lbl_ecu.setObjectName("dim")
        grid.addWidget(lbl_ecu, 1, 0)

        self.ecu_combo = QComboBox()
        grid.addWidget(self.ecu_combo, 1, 1)

        self._on_model_change()

        # Connect button
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("connect")
        self.btn_connect.setFixedSize(130, 36)
        self.btn_connect.clicked.connect(self._toggle_connect)
        grid.addWidget(self.btn_connect, 1, 3, Qt.AlignRight)

        grid.setColumnStretch(1, 1)
        parent.addWidget(panel)

    def _build_ecu_info(self, parent):
        self.info_frame = QFrame()
        self.info_frame.setObjectName("ecu_info")
        hlay = QHBoxLayout(self.info_frame)
        hlay.setContentsMargins(12, 6, 12, 6)

        self.info_label = QLabel("Not connected")
        self.info_label.setObjectName("mono")
        self.info_label.setStyleSheet(f"color: {C_TEXT_DIM};")
        hlay.addWidget(self.info_label)

        parent.addWidget(self.info_frame)

    def _build_tabs(self, parent):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)

        # --- Faults ---
        faults_w = QWidget()
        flay = QVBoxLayout(faults_w)
        flay.setContentsMargins(8, 8, 8, 8)

        self.fault_text = QTextEdit()
        self.fault_text.setReadOnly(True)
        flay.addWidget(self.fault_text)

        btn_row = QHBoxLayout()
        self.btn_read = QPushButton("Read Faults")
        self.btn_read.setObjectName("accent")
        self.btn_read.setEnabled(False)
        self.btn_read.clicked.connect(self._read_faults)
        btn_row.addWidget(self.btn_read)

        self.btn_clear = QPushButton("Clear Faults")
        self.btn_clear.setObjectName("danger")
        self.btn_clear.setEnabled(False)
        self.btn_clear.clicked.connect(self._clear_faults)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        flay.addLayout(btn_row)

        self.tabs.addTab(faults_w, "Fault Codes")

        # --- Live Data ---
        live_w = QWidget()
        llay = QVBoxLayout(live_w)
        llay.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        for name, info in DEMO_LIVE.items():
            g = GaugeRow(name, info["unit"], info["max"])
            scroll_layout.addWidget(g)
            self.gauges[name] = g

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        llay.addWidget(scroll)

        self.tabs.addTab(live_w, "Live Data")

        # --- Actuators ---
        act_w = QWidget()
        alay = QVBoxLayout(act_w)
        alay.setContentsMargins(8, 8, 8, 8)

        actuators = ["Fresh Air Servo", "Defrost Servo", "Footwell Servo",
                     "Mixer Servo L", "Mixer Servo R", "Condenser Fan",
                     "Oil Cooler Fan", "Rear Blower"]

        for i, name in enumerate(actuators):
            row = QFrame()
            row.setObjectName("actuator_row")
            bg = C_BG if i % 2 == 0 else C_PANEL2
            row.setStyleSheet(f"QFrame#actuator_row {{ background-color: {bg}; border-radius: 4px; }}")
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(12, 6, 12, 6)

            lbl = QLabel(f"{i+1:02d}   {name}")
            font = QFont("Menlo", 13)
            lbl.setFont(font)
            rlay.addWidget(lbl, 1)

            btn = QPushButton("Test")
            btn.setObjectName("accent")
            btn.setFixedSize(70, 28)
            btn.setEnabled(False)
            rlay.addWidget(btn)

            alay.addWidget(row)

        alay.addStretch()
        self.tabs.addTab(act_w, "Actuators")

        # --- Log ---
        log_w = QWidget()
        loglay = QVBoxLayout(log_w)
        loglay.setContentsMargins(8, 8, 8, 8)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("log")
        self.log_text.setReadOnly(True)
        loglay.addWidget(self.log_text)

        self.tabs.addTab(log_w, "Log")

        parent.addWidget(self.tabs, 1)

        self._log("911OT-KKL Scanner ready")
        self._log("Select port and model, then click Connect")

    def _build_statusbar(self, parent):
        bar = QFrame()
        bar.setObjectName("statusbar")
        hlay = QHBoxLayout(bar)
        hlay.setContentsMargins(12, 4, 12, 4)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {C_RED}; font-size: 14px;")
        self.status_dot.setFixedWidth(20)
        hlay.addWidget(self.status_dot)

        self.status_text = QLabel("Disconnected")
        self.status_text.setObjectName("dim")
        hlay.addWidget(self.status_text)

        hlay.addStretch()

        ver = QLabel("v1.0")
        ver.setObjectName("dim")
        hlay.addWidget(ver)

        parent.addWidget(bar)

    # ── Actions ──
    def _on_model_change(self):
        checked = self.model_group.checkedButton()
        if not checked:
            return
        model = checked.text()
        ecus = ECUS.get(model, [])
        self.ecu_combo.clear()
        for name, addr, baud in ecus:
            self.ecu_combo.addItem(f"{name} (0x{addr:02X})")

    def _toggle_connect(self):
        if not self.connected:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        port = self.port_combo.currentText()
        model = self.model_group.checkedButton().text()
        ecu = self.ecu_combo.currentText()
        is_demo = port in ("Demo", "(no ports)")

        self._log(f"Connecting to {ecu} on {port}...")

        if is_demo:
            self.badge.show()
            self._log("DEMO MODE - simulated data")

        self.connected = True
        self.btn_connect.setText("Disconnect")
        self.btn_connect.setObjectName("disconnect")
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.btn_read.setEnabled(True)
        self.btn_clear.setEnabled(True)

        ecu_parts = {
            "964": "964.618.124.02  Motronic M2.1",
            "993": "993.618.124.00  Motronic M5.2",
            "965": "965.618.xxx.xx  CCU Climate Control",
        }
        self.info_label.setText(f"ECU: {ecu_parts.get(model, 'Unknown')}")
        self.info_label.setStyleSheet(f"color: {C_TEXT};")
        self.status_dot.setStyleSheet(f"color: {C_GREEN}; font-size: 14px;")
        self.status_text.setText(f"Connected | {model} | {ecu}")
        self._log(f"Connected to {model} {ecu}")

        if is_demo:
            self.demo_timer.start(300)

    def _disconnect(self):
        self.connected = False
        self.demo_timer.stop()
        self.btn_connect.setText("Connect")
        self.btn_connect.setObjectName("connect")
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.btn_read.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.info_label.setText("Not connected")
        self.info_label.setStyleSheet(f"color: {C_TEXT_DIM};")
        self.status_dot.setStyleSheet(f"color: {C_RED}; font-size: 14px;")
        self.status_text.setText("Disconnected")
        self.badge.hide()
        self._log("Disconnected")

    def _read_faults(self):
        self._log("Reading fault codes...")
        lines = []
        lines.append(f"  {'Code':<8}{'Description':<35}{'Count':>5}")
        lines.append("  " + "─" * 50)
        for code, desc, count in DEMO_FAULTS:
            lines.append(f"  {code:<8}{desc:<35}{'x'+str(count):>5}")
        lines.append(f"\n  {len(DEMO_FAULTS)} fault(s) found")
        self.fault_text.setPlainText("\n".join(lines))
        self._log(f"Found {len(DEMO_FAULTS)} fault code(s)")

    def _clear_faults(self):
        self.fault_text.setPlainText("\n  Fault memory cleared.")
        self._log("Fault memory cleared")

    def _demo_tick(self):
        for name, info in DEMO_LIVE.items():
            base = info["value"]
            jitter = base * 0.05
            val = base + random.uniform(-jitter, jitter)
            val = max(0, min(val, info["max"]))
            if name in self.gauges:
                self.gauges[name].set_value(val, info["fmt"])

    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
