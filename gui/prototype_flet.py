#!/usr/bin/env python3
"""911OT-KKL Scanner - Flet 0.80+ Prototype (clean rewrite)"""

import flet as ft
import serial.tools.list_ports
import time
import random
import threading

# ── Palette ──
BG       = "#0d1117"
PANEL    = "#161b22"
PANEL2   = "#1c2333"
ACCENT   = "#ff6b00"
GREEN    = "#00c853"
RED      = "#ff1744"
YELLOW   = "#ffd600"
TEXT     = "#e6edf3"
DIM      = "#7d8590"
BORDER   = "#30363d"

# ── ECU database ──
ECUS = {
    "964": [
        ("Motronic M2.1", 0x10, 8800),
        ("ABS (C4 only)", 0x3D, 4800),
        ("CCU (Climate)", 0x51, 4800),
        ("SRS (Airbag)",  0x57, 9600),
        ("Alarm",         0x40, 9600),
    ],
    "993": [
        ("Motronic M5.2", 0x10, 9600),
        ("ABS",           0x1F, 9600),
        ("CCU (Climate)", 0x51, 4800),
        ("SRS (Airbag)",  0x57, 9600),
        ("Alarm",         0x40, 9600),
        ("Tiptronic",     0x01, 9600),
    ],
    "965": [
        ("CCU (Climate)", 0x51, 4800),
        ("SRS (Airbag)",  0x57, 9600),
        ("Alarm",         0x40, 9600),
        ("ABS",           0x3D, 4800),
    ],
}

DEMO_FAULTS = [
    ("12", "Throttle Position Sensor", 3),
    ("23", "Coolant Temperature Sensor", 1),
    ("24", "O2 Sensor Signal", 5),
]

LIVE_PARAMS = [
    ("RPM",           "0x3A", 850,  7000, "rpm", "{:.0f}"),
    ("Head Temp",     "0x38", 185,  260,  "°F",  "{:.0f}"),
    ("Intake Temp",   "0x37", 95,   200,  "°F",  "{:.0f}"),
    ("AFM Voltage",   "0x45", 1.8,  5.0,  "V",   "{:.2f}"),
    ("Injector Time", "0x42", 3.2,  15.0, "ms",  "{:.1f}"),
    ("Timing",        "0x5D", 12.0, 40.0, "°",   "{:.1f}"),
    ("Battery",       "ADC1", 13.8, 16.0, "V",   "{:.1f}"),
]

ACTUATORS = [
    "Fresh Air Servo", "Defrost Servo", "Footwell Servo",
    "Mixer Servo L", "Mixer Servo R", "Condenser Fan",
    "Oil Cooler Fan", "Rear Blower",
]


def main(page: ft.Page):
    page.title = "911OT-KKL Scanner [Flet / Flutter]"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ACCENT)
    page.window.width = 820
    page.window.height = 740
    page.window.min_width = 700
    page.window.min_height = 600
    page.padding = 0
    page.spacing = 0

    # ── State ──
    state = {"connected": False, "demo": False}
    gauges = {}  # name -> (bar, label)

    # ══════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════

    log_field = ft.TextField(
        value="", multiline=True, read_only=True,
        min_lines=20, text_size=12, color=GREEN,
        bgcolor=BG, border_color=BORDER, border_radius=6,
        text_style=ft.TextStyle(font_family="Menlo"),
        expand=True,
    )

    def log(msg):
        ts = time.strftime("%H:%M:%S")
        log_field.value = (log_field.value + "\n" if log_field.value else "") + f"[{ts}] {msg}"
        try:
            page.update()
        except Exception:
            pass

    # ══════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════

    demo_badge = ft.Container(
        ft.Text("DEMO", size=11, weight=ft.FontWeight.BOLD, color=BG),
        bgcolor=YELLOW, border_radius=4,
        padding=ft.Padding.symmetric(vertical=3, horizontal=10),
        visible=False,
    )

    header = ft.Container(
        ft.Row([
            ft.Text("911OT-KKL", size=22, weight=ft.FontWeight.BOLD, color=ACCENT),
            ft.Text("Porsche 964 / 993 / 965 K-Line Scanner", size=12, color=DIM),
            ft.Container(expand=True),
            demo_badge,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=PANEL,
        padding=ft.Padding.symmetric(vertical=10, horizontal=18),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
    )

    # ══════════════════════════════════════
    #  CONNECTION PANEL
    # ══════════════════════════════════════

    ports = [p.device for p in serial.tools.list_ports.comports()]
    if not ports:
        ports = ["(no ports)"]
    ports.append("Demo")

    port_dd = ft.Dropdown(
        options=[ft.dropdown.Option(p) for p in ports],
        value=ports[0], width=260, dense=True,
        bgcolor=PANEL2, border_color=BORDER, border_radius=6,
        text_size=13, color=TEXT,
    )

    ecu_dd = ft.Dropdown(
        options=[], width=260, dense=True,
        bgcolor=PANEL2, border_color=BORDER, border_radius=6,
        text_size=13, color=TEXT,
    )

    def on_model_change(e):
        model = model_seg.selected[0] if model_seg.selected else "965"
        ecus = ECUS.get(model, [])
        ecu_dd.options = [ft.dropdown.Option(f"{n} (0x{a:02X})") for n, a, b in ecus]
        if ecu_dd.options:
            ecu_dd.value = ecu_dd.options[0].key
        page.update()

    model_seg = ft.SegmentedButton(
        selected=["965"],
        segments=[
            ft.Segment(value="964", label=ft.Text("964")),
            ft.Segment(value="993", label=ft.Text("993")),
            ft.Segment(value="965", label=ft.Text("965")),
        ],
        on_change=on_model_change,
    )
    on_model_change(None)

    # Connect button
    btn_connect = ft.Button(
        content="Connect", bgcolor=GREEN, color=BG,
        width=130, height=38,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
    )

    conn_panel = ft.Container(
        ft.Column([
            ft.Row([
                ft.Text("Port", size=12, color=DIM, width=50),
                port_dd,
                ft.Container(width=16),
                ft.Text("Model", size=12, color=DIM),
                model_seg,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            ft.Row([
                ft.Text("ECU", size=12, color=DIM, width=50),
                ecu_dd,
                ft.Container(expand=True),
                btn_connect,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        ], spacing=8),
        bgcolor=PANEL, border_radius=8, padding=16,
        border=ft.Border.all(1, BORDER),
        margin=ft.Margin.only(left=12, right=12, top=10, bottom=4),
    )

    # ══════════════════════════════════════
    #  ECU INFO BAR
    # ══════════════════════════════════════

    info_label = ft.Text("Not connected", size=12, color=DIM,
                         font_family="Menlo")

    ecu_info = ft.Container(
        info_label,
        bgcolor=PANEL, border_radius=6,
        padding=ft.Padding.symmetric(vertical=8, horizontal=16),
        border=ft.Border.all(1, BORDER),
        margin=ft.Margin.symmetric(horizontal=12, vertical=4),
    )

    # ══════════════════════════════════════
    #  TAB: FAULT CODES
    # ══════════════════════════════════════

    fault_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Code", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Description", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Count", weight=ft.FontWeight.BOLD, size=13), numeric=True),
        ],
        rows=[],
        border=ft.Border.all(1, BORDER),
        border_radius=6,
        heading_row_color=PANEL2,
        data_row_color=BG,
        column_spacing=20, horizontal_margin=16,
    )
    fault_status = ft.Text("", size=13, color=DIM, italic=True)

    def read_faults(e):
        log("Reading fault codes...")
        fault_table.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(c, size=14, weight=ft.FontWeight.BOLD,
                                    color=RED, font_family="Menlo")),
                ft.DataCell(ft.Text(d, size=13)),
                ft.DataCell(ft.Text(f"x{n}", size=13, color=YELLOW)),
            ]) for c, d, n in DEMO_FAULTS
        ]
        fault_status.value = f"{len(DEMO_FAULTS)} fault(s) found"
        fault_status.color = RED
        log(f"Found {len(DEMO_FAULTS)} fault code(s)")
        page.update()

    def clear_faults(e):
        fault_table.rows = []
        fault_status.value = "Fault memory cleared"
        fault_status.color = GREEN
        log("Fault memory cleared")
        page.update()

    btn_read = ft.Button(content="Read Faults", bgcolor=ACCENT, color=BG,
                         width=140, height=36, disabled=True, on_click=read_faults,
                         style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
    btn_clear = ft.Button(content="Clear Faults", bgcolor=RED, color=TEXT,
                          width=140, height=36, disabled=True, on_click=clear_faults,
                          style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))

    fault_panel = ft.Column([
        ft.Container(
            ft.Column([fault_table], scroll=ft.ScrollMode.AUTO),
            expand=True,
        ),
        ft.Divider(height=1, color=BORDER),
        ft.Row([btn_read, btn_clear, ft.Container(expand=True), fault_status],
               vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
    ], spacing=8, expand=True)

    # ══════════════════════════════════════
    #  TAB: LIVE DATA
    # ══════════════════════════════════════

    gauge_rows = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    for name, addr, base, mx, unit, fmt in LIVE_PARAMS:
        bar = ft.ProgressBar(value=0, bgcolor=PANEL2, color=ACCENT,
                             bar_height=14, border_radius=4, expand=True)
        val = ft.Text(f"--- {unit}", size=14, weight=ft.FontWeight.BOLD,
                      font_family="Menlo", color=TEXT, width=100,
                      text_align=ft.TextAlign.RIGHT)
        gauges[name] = (bar, val)

        gauge_rows.controls.append(ft.Container(
            ft.Row([
                ft.Text(name, size=13, color=DIM, width=120),
                bar,
                val,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(vertical=8, horizontal=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
        ))

    live_panel = ft.Column([gauge_rows], expand=True)

    # ══════════════════════════════════════
    #  TAB: ACTUATORS
    # ══════════════════════════════════════

    act_btns = []
    act_col = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    for i, name in enumerate(ACTUATORS):
        btn = ft.Button(content="Test", bgcolor=ACCENT, color=BG,
                        height=30, disabled=True,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
        act_btns.append(btn)
        act_col.controls.append(ft.Container(
            ft.Row([
                ft.Text(f"{i+1:02d}   {name}", size=13, font_family="Menlo",
                        color=TEXT, expand=True),
                btn,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=BG if i % 2 == 0 else PANEL2,
            border_radius=4,
            padding=ft.Padding.symmetric(vertical=8, horizontal=12),
        ))

    actuator_panel = ft.Column([act_col], expand=True)

    # ══════════════════════════════════════
    #  TAB: LOG
    # ══════════════════════════════════════

    log_panel = ft.Column([log_field], expand=True)

    # ══════════════════════════════════════
    #  TAB SYSTEM (swap content)
    # ══════════════════════════════════════

    panels = [fault_panel, live_panel, actuator_panel, log_panel]
    tab_names = ["Fault Codes", "Live Data", "Actuators", "Log"]

    # Content area: holds the active panel
    content_area = ft.Container(
        content=panels[0],
        bgcolor=PANEL,
        border_radius=ft.BorderRadius.only(
            top_right=8, bottom_left=8, bottom_right=8),
        border=ft.Border.all(1, BORDER),
        padding=12,
        expand=True,
    )

    tab_btns = []
    tab_labels = []

    def switch_tab(e):
        idx = int(e.control.data)
        content_area.content = panels[idx]
        for i, (b, lbl) in enumerate(zip(tab_btns, tab_labels)):
            if i == idx:
                b.bgcolor = ACCENT
                lbl.color = TEXT
            else:
                b.bgcolor = PANEL2
                lbl.color = DIM
        page.update()

    for i, name in enumerate(tab_names):
        active = (i == 0)
        lbl = ft.Text(name, size=13, weight=ft.FontWeight.BOLD,
                      color=TEXT if active else DIM)
        tab_labels.append(lbl)
        c = ft.Container(
            lbl,
            bgcolor=ACCENT if active else PANEL2,
            border_radius=ft.BorderRadius.only(top_left=6, top_right=6),
            padding=ft.Padding.symmetric(vertical=10, horizontal=20),
            on_click=switch_tab,
            data=str(i),
            ink=True,
        )
        tab_btns.append(c)

    tab_bar = ft.Row(tab_btns, spacing=2)

    tabs_section = ft.Container(
        ft.Column([tab_bar, content_area], spacing=0, expand=True),
        margin=ft.Margin.symmetric(horizontal=12, vertical=4),
        expand=True,
    )

    # ══════════════════════════════════════
    #  STATUS BAR
    # ══════════════════════════════════════

    status_dot = ft.Text("●", size=14, color=RED)
    status_label = ft.Text("Disconnected", size=12, color=DIM)

    statusbar = ft.Container(
        ft.Row([
            status_dot, status_label,
            ft.Container(expand=True),
            ft.Text("v1.0", size=11, color=DIM),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
        bgcolor=PANEL,
        padding=ft.Padding.symmetric(vertical=6, horizontal=14),
        border=ft.Border.only(top=ft.BorderSide(1, BORDER)),
    )

    # ══════════════════════════════════════
    #  CONNECT / DISCONNECT
    # ══════════════════════════════════════

    def toggle_connect(e):
        if not state["connected"]:
            do_connect()
        else:
            do_disconnect()

    btn_connect.on_click = toggle_connect

    def do_connect():
        port = port_dd.value
        model = model_seg.selected[0] if model_seg.selected else "965"
        ecu = ecu_dd.value or "?"
        is_demo = port in ("Demo", "(no ports)")

        log(f"Connecting to {ecu} on {port}...")
        if is_demo:
            demo_badge.visible = True
            log("DEMO MODE - simulated data")

        state["connected"] = True
        state["demo"] = is_demo

        btn_connect.content = "Disconnect"
        btn_connect.bgcolor = RED
        btn_connect.color = TEXT
        btn_read.disabled = False
        btn_clear.disabled = False
        for b in act_btns:
            b.disabled = False

        ecu_info_map = {
            "964": "964.618.124.02  Motronic M2.1",
            "993": "993.618.124.00  Motronic M5.2",
            "965": "965.618.xxx.xx  CCU Climate Control",
        }
        info_label.value = f"ECU: {ecu_info_map.get(model, 'Unknown')}"
        info_label.color = TEXT
        status_dot.color = GREEN
        status_label.value = f"Connected | {model} | {ecu}"

        log(f"Connected to {model} {ecu}")
        page.update()

        if is_demo:
            threading.Thread(target=demo_loop, daemon=True).start()

    def do_disconnect():
        state["connected"] = False
        state["demo"] = False

        btn_connect.content = "Connect"
        btn_connect.bgcolor = GREEN
        btn_connect.color = BG
        btn_read.disabled = True
        btn_clear.disabled = True
        for b in act_btns:
            b.disabled = True

        info_label.value = "Not connected"
        info_label.color = DIM
        status_dot.color = RED
        status_label.value = "Disconnected"
        demo_badge.visible = False

        log("Disconnected")
        page.update()

    # ══════════════════════════════════════
    #  DEMO LOOP
    # ══════════════════════════════════════

    def demo_loop():
        while state["connected"] and state["demo"]:
            for name, addr, base, mx, unit, fmt in LIVE_PARAMS:
                if not state["connected"]:
                    return
                jitter = base * 0.05
                val = max(0, min(base + random.uniform(-jitter, jitter), mx))
                ratio = min(val / mx, 1.0) if mx > 0 else 0

                bar, lbl = gauges[name]
                bar.value = ratio
                bar.color = RED if ratio > 0.85 else (YELLOW if ratio > 0.7 else ACCENT)
                lbl.value = f"{fmt.format(val)} {unit}"

            try:
                page.update()
            except Exception:
                return
            time.sleep(0.3)

    # ══════════════════════════════════════
    #  ASSEMBLE
    # ══════════════════════════════════════

    page.add(ft.Column([
        header,
        conn_panel,
        ecu_info,
        tabs_section,
        statusbar,
    ], spacing=0, expand=True))

    log("911OT-KKL Scanner ready")
    log("Select port and model, then click Connect")


if __name__ == "__main__":
    ft.run(main)
