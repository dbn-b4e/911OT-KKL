#!/usr/bin/env python3
"""911OT-KKL Scanner - Porsche 964/993/965 K-Line Diagnostic Tool.

Flet 0.80+ GUI with real KWP1281 protocol and demo mode.
"""

import flet as ft
import serial.tools.list_ports
import time
import threading

from kwp1281.constants import ECUS, CCU_ACTUATORS
from kwp1281.demo import DemoProtocol
from kwp1281.protocol import KWP1281Protocol

VERSION = "2.0"

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


def main(page: ft.Page):
    page.title = "911OT-KKL Scanner"
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
    state = {"connected": False, "demo": False, "live_running": False}
    proto = [None]  # mutable ref to current protocol instance
    gauges = {}     # name -> (bar, label)

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

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    # ══════════════════════════════════════
    #  ABOUT DIALOG
    # ══════════════════════════════════════

    about_dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("911OT-KKL Scanner", weight=ft.FontWeight.BOLD, color=ACCENT),
        content=ft.Column([
            ft.Text(f"Version {VERSION}", size=14, color=TEXT),
            ft.Divider(height=1, color=BORDER),
            ft.Text("Porsche 964 / 993 / 965 K-Line Diagnostic Tool", size=13, color=DIM),
            ft.Text("Protocol: KWP1281 over ISO 9141 K-Line", size=12, color=DIM),
            ft.Divider(height=1, color=BORDER),
            ft.Text("Based on ScanTool v3/v4 reverse engineering", size=12, color=DIM),
            ft.Text("Original ScanTool by Doug Boyce", size=12, color=DIM),
            ft.Text("OBDPlot analysis by Julian Bunn", size=12, color=DIM),
            ft.Divider(height=1, color=BORDER),
            ft.Text("License: MIT", size=12, color=DIM),
        ], tight=True, spacing=6, width=380),
        actions=[
            ft.TextButton("Close", on_click=lambda e: page.pop_dialog()),
        ],
    )

    def show_about(e):
        page.show_dialog(about_dlg)

    # ══════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════

    demo_badge = ft.Container(
        ft.Text("DEMO", size=11, weight=ft.FontWeight.BOLD, color=BG),
        bgcolor=YELLOW, border_radius=4,
        padding=ft.Padding.symmetric(vertical=3, horizontal=10),
        visible=False,
    )

    info_btn = ft.IconButton(
        icon=ft.Icons.INFO_OUTLINE, icon_color=DIM, icon_size=20,
        on_click=show_about, tooltip="About",
    )

    header = ft.Container(
        ft.Row([
            ft.Text("911OT-KKL", size=22, weight=ft.FontWeight.BOLD, color=ACCENT),
            ft.Text("Porsche 964 / 993 / 965 K-Line Scanner", size=12, color=DIM),
            ft.Container(expand=True),
            demo_badge,
            info_btn,
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

    fault_list = ft.ListView(spacing=0, expand=True, auto_scroll=False)
    fault_status = ft.Text("", size=13, color=DIM, italic=True)
    fault_data = []  # store current faults for selection
    fault_selected = [0]  # currently highlighted index

    def _build_fault_row(code, desc, count, index, selected=False):
        """Build a single fault row container."""
        bg = ACCENT if selected else (BG if index % 2 == 0 else PANEL2)
        text_col = BG if selected else TEXT
        code_col = BG if selected else RED
        cnt_col = BG if selected else YELLOW

        def on_row_click(e):
            fault_selected[0] = index
            _refresh_fault_list()

        return ft.Container(
            ft.Row([
                ft.Text(f"#{code}", size=14, weight=ft.FontWeight.BOLD,
                        color=code_col, font_family="Menlo", width=60),
                ft.Text(desc, size=13, color=text_col, expand=True),
                ft.Text(f"x{count}", size=13, color=cnt_col,
                        font_family="Menlo", width=40, text_align=ft.TextAlign.RIGHT),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=bg, border_radius=4,
            padding=ft.Padding.symmetric(vertical=10, horizontal=14),
            on_click=on_row_click,
            ink=True,
        )

    def _refresh_fault_list():
        """Rebuild fault list with current selection."""
        fault_list.controls.clear()
        if not fault_data:
            fault_list.controls.append(
                ft.Container(
                    ft.Text("No faults read yet", size=13, color=DIM, italic=True,
                            text_align=ft.TextAlign.CENTER),
                    padding=30,
                ))
        else:
            for i, (c, d, n) in enumerate(fault_data):
                fault_list.controls.append(
                    _build_fault_row(c, d, n, i, selected=(i == fault_selected[0])))
        safe_update()

    def _fault_key_nav(e: ft.KeyboardEvent):
        """Handle up/down arrow keys in fault list."""
        if not fault_data:
            return
        if e.key == "Arrow Down":
            fault_selected[0] = min(fault_selected[0] + 1, len(fault_data) - 1)
            _refresh_fault_list()
        elif e.key == "Arrow Up":
            fault_selected[0] = max(fault_selected[0] - 1, 0)
            _refresh_fault_list()

    def read_faults(e):
        if not state["connected"] or proto[0] is None:
            return

        def _do():
            log("Reading fault codes...")
            try:
                faults = proto[0].read_faults()
            except Exception as ex:
                log(f"Error reading faults: {ex}")
                return

            fault_data.clear()
            fault_data.extend(faults)
            fault_selected[0] = 0

            if faults:
                fault_status.value = f"{len(faults)} fault(s) found"
                fault_status.color = RED
            else:
                fault_status.value = "No faults stored"
                fault_status.color = GREEN
            log(f"Found {len(faults)} fault code(s)")
            _refresh_fault_list()

        threading.Thread(target=_do, daemon=True).start()

    def clear_faults(e):
        if not state["connected"] or proto[0] is None:
            return

        def _do():
            log("Clearing fault memory...")
            try:
                ok = proto[0].clear_faults()
            except Exception as ex:
                log(f"Error clearing faults: {ex}")
                return
            if ok:
                fault_data.clear()
                fault_selected[0] = 0
                fault_status.value = "Fault memory cleared"
                fault_status.color = GREEN
                log("Fault memory cleared")
            else:
                fault_status.value = "Clear faults failed"
                fault_status.color = RED
                log("Clear faults: ECU returned NAK")
            _refresh_fault_list()

        threading.Thread(target=_do, daemon=True).start()

    btn_read = ft.Button(content="Read Faults", bgcolor=ACCENT, color=BG,
                         width=140, height=36, disabled=True, on_click=read_faults,
                         style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
    btn_clear = ft.Button(content="Clear Faults", bgcolor=RED, color=TEXT,
                          width=140, height=36, disabled=True, on_click=clear_faults,
                          style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))

    # Column header for fault list
    fault_header = ft.Container(
        ft.Row([
            ft.Text("Code", size=12, weight=ft.FontWeight.BOLD, color=DIM, width=60),
            ft.Text("Description", size=12, weight=ft.FontWeight.BOLD, color=DIM, expand=True),
            ft.Text("Count", size=12, weight=ft.FontWeight.BOLD, color=DIM,
                     width=40, text_align=ft.TextAlign.RIGHT),
        ], spacing=12),
        padding=ft.Padding.symmetric(vertical=6, horizontal=14),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
    )

    _refresh_fault_list()  # show initial "No faults" message

    fault_panel = ft.Column([
        fault_header,
        fault_list,
        ft.Divider(height=1, color=BORDER),
        ft.Row([btn_read, btn_clear, ft.Container(expand=True), fault_status],
               vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
    ], spacing=0, expand=True)

    # ══════════════════════════════════════
    #  TAB: LIVE DATA
    # ══════════════════════════════════════

    gauge_rows = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    live_status = ft.Text("", size=12, color=DIM, italic=True)

    btn_live_start = ft.Button(
        content="Start", bgcolor=GREEN, color=BG,
        width=100, height=32, disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
    btn_live_stop = ft.Button(
        content="Stop", bgcolor=RED, color=TEXT,
        width=100, height=32, disabled=True,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))

    def _build_gauges(params):
        """Rebuild gauge rows for the given live params."""
        gauges.clear()
        gauge_rows.controls.clear()

        for name, reg, formula, mn, mx, unit, fmt in params:
            bar = ft.ProgressBar(value=0, bgcolor=PANEL2, color=ACCENT,
                                 bar_height=14, border_radius=4, expand=True)
            val = ft.Text(f"--- {unit}", size=14, weight=ft.FontWeight.BOLD,
                          font_family="Menlo", color=TEXT, width=120,
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

    def start_live(e):
        if not state["connected"] or proto[0] is None:
            return
        state["live_running"] = True
        btn_live_start.disabled = True
        btn_live_stop.disabled = False
        live_status.value = "Polling..."
        safe_update()
        threading.Thread(target=_live_loop, daemon=True).start()

    def stop_live(e):
        state["live_running"] = False
        proto[0].stop_live()
        btn_live_start.disabled = False
        btn_live_stop.disabled = True
        live_status.value = "Stopped"
        safe_update()

    btn_live_start.on_click = start_live
    btn_live_stop.on_click = stop_live

    def _live_loop():
        while state["connected"] and state["live_running"]:
            try:
                results = proto[0].read_live_values()
            except Exception as ex:
                log(f"Live data error: {ex}")
                break

            for name, val, unit, formatted, ratio in results:
                if name in gauges:
                    bar, lbl = gauges[name]
                    bar.value = ratio
                    bar.color = RED if ratio > 0.85 else (YELLOW if ratio > 0.7 else ACCENT)
                    lbl.value = f"{formatted} {unit}"

            safe_update()
            time.sleep(0.3)

        state["live_running"] = False
        btn_live_start.disabled = not state["connected"]
        btn_live_stop.disabled = True
        live_status.value = "Stopped"
        safe_update()

    live_panel = ft.Column([
        gauge_rows,
        ft.Divider(height=1, color=BORDER),
        ft.Row([btn_live_start, btn_live_stop, ft.Container(expand=True), live_status],
               vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
    ], spacing=8, expand=True)

    # ══════════════════════════════════════
    #  TAB: ACTUATORS
    # ══════════════════════════════════════

    act_btns = []
    act_col = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    for i in range(1, 17):
        name = CCU_ACTUATORS.get(i, f"Actuator {i}")
        confirmed = "?" not in name

        def make_act_handler(num):
            def handler(e):
                if not state["connected"] or proto[0] is None:
                    return
                def _do():
                    log(f"Actuator test #{num:02d}...")
                    try:
                        ok = proto[0].actuator_test(num)
                        if ok:
                            log(f"Actuator #{num:02d} OK")
                        else:
                            log(f"Actuator #{num:02d} no response")
                    except Exception as ex:
                        log(f"Actuator #{num:02d} error: {ex}")
                threading.Thread(target=_do, daemon=True).start()
            return handler

        btn = ft.Button(content="Test", bgcolor=ACCENT, color=BG,
                        height=30, disabled=True, on_click=make_act_handler(i),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
        act_btns.append(btn)

        label_color = TEXT if confirmed else DIM
        suffix = "" if confirmed else " (?)"
        act_col.controls.append(ft.Container(
            ft.Row([
                ft.Text(f"{i:02d}   {name}{suffix}", size=13, font_family="Menlo",
                        color=label_color, expand=True),
                btn,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=BG if i % 2 == 1 else PANEL2,
            border_radius=4,
            padding=ft.Padding.symmetric(vertical=8, horizontal=12),
        ))

    actuator_panel = ft.Column([act_col], expand=True)

    # ══════════════════════════════════════
    #  TAB: ADVANCED
    # ══════════════════════════════════════

    def _section_header(title):
        return ft.Container(
            ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=ACCENT),
            bgcolor=PANEL2, border_radius=4,
            padding=ft.Padding.symmetric(vertical=8, horizontal=12),
            margin=ft.Margin.only(top=8),
        )

    # -- ReadGroup --
    grp_input = ft.TextField(value="1", width=80, dense=True, text_size=13,
                             bgcolor=PANEL2, border_color=BORDER, border_radius=6, color=TEXT)
    grp_result = ft.Text("", size=12, color=TEXT, font_family="Menlo")

    def read_group_click(e):
        if not state["connected"] or proto[0] is None:
            return
        def _do():
            try:
                grp = int(grp_input.value)
            except ValueError:
                grp_result.value = "Invalid group number"
                safe_update()
                return
            log(f"ReadGroup {grp}...")
            try:
                vals = proto[0].read_group(grp)
            except Exception as ex:
                grp_result.value = f"Error: {ex}"
                safe_update()
                return
            lines = []
            for i, (f_id, va, vb) in enumerate(vals):
                val16 = (va << 8) | vb
                lines.append(f"  [{i+1}] formula={f_id:3d}  a=0x{va:02X}  b=0x{vb:02X}  (val={val16})")
            grp_result.value = "\n".join(lines) if lines else "No data"
            safe_update()
        threading.Thread(target=_do, daemon=True).start()

    btn_grp = ft.Button(content="Read", bgcolor=ACCENT, color=BG, height=30, disabled=True,
                        on_click=read_group_click,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))

    # -- ADC --
    adc_input = ft.TextField(value="0", width=80, dense=True, text_size=13,
                             bgcolor=PANEL2, border_color=BORDER, border_radius=6, color=TEXT)
    adc_result = ft.Text("", size=12, color=TEXT, font_family="Menlo")

    def read_adc_click(e):
        if not state["connected"] or proto[0] is None:
            return
        def _do():
            try:
                ch = int(adc_input.value)
            except ValueError:
                adc_result.value = "Invalid channel"
                safe_update()
                return
            log(f"ADC read ch={ch}...")
            try:
                val = proto[0].read_adc(ch)
            except Exception as ex:
                adc_result.value = f"Error: {ex}"
                safe_update()
                return
            adc_result.value = f"  Channel {ch}: {val}" if val is not None else "  No response"
            safe_update()
        threading.Thread(target=_do, daemon=True).start()

    btn_adc = ft.Button(content="Read", bgcolor=ACCENT, color=BG, height=30, disabled=True,
                        on_click=read_adc_click,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))

    # -- Login --
    login_pin_hi = ft.TextField(value="00", width=60, dense=True, text_size=13,
                                bgcolor=PANEL2, border_color=BORDER, border_radius=6, color=TEXT)
    login_pin_lo = ft.TextField(value="00", width=60, dense=True, text_size=13,
                                bgcolor=PANEL2, border_color=BORDER, border_radius=6, color=TEXT)
    login_result = ft.Text("", size=12, color=TEXT)

    def login_click(e):
        if not state["connected"] or proto[0] is None:
            return
        def _do():
            try:
                phi = int(login_pin_hi.value, 16)
                plo = int(login_pin_lo.value, 16)
            except ValueError:
                login_result.value = "Invalid hex PIN"
                safe_update()
                return
            log(f"Login {phi:02X}{plo:02X}...")
            try:
                ok = proto[0].login(phi, plo)
            except Exception as ex:
                login_result.value = f"Error: {ex}"
                safe_update()
                return
            login_result.value = "Login OK" if ok else "Login FAILED"
            login_result.color = GREEN if ok else RED
            safe_update()
        threading.Thread(target=_do, daemon=True).start()

    btn_login = ft.Button(content="Login", bgcolor=ACCENT, color=BG, height=30, disabled=True,
                          on_click=login_click,
                          style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))

    # -- Adaptation --
    adapt_ch = ft.TextField(value="0", width=80, dense=True, text_size=13,
                            bgcolor=PANEL2, border_color=BORDER, border_radius=6, color=TEXT)
    adapt_val = ft.TextField(value="0", width=100, dense=True, text_size=13,
                             bgcolor=PANEL2, border_color=BORDER, border_radius=6, color=TEXT)
    adapt_result = ft.Text("", size=12, color=TEXT, font_family="Menlo")

    def adapt_read_click(e):
        if not state["connected"] or proto[0] is None:
            return
        def _do():
            try:
                ch = int(adapt_ch.value)
            except ValueError:
                adapt_result.value = "Invalid channel"
                safe_update()
                return
            log(f"ReadAdapt ch={ch}...")
            try:
                result = proto[0].read_adaptation(ch)
            except Exception as ex:
                adapt_result.value = f"Error: {ex}"
                safe_update()
                return
            if result:
                ch_r, val = result
                adapt_result.value = f"  Channel {ch_r}: {val} (0x{val:04X})"
                adapt_val.value = str(val)
            else:
                adapt_result.value = "  No response"
            safe_update()
        threading.Thread(target=_do, daemon=True).start()

    def adapt_write_click(e):
        if not state["connected"] or proto[0] is None:
            return
        def _do():
            try:
                ch = int(adapt_ch.value)
                val = int(adapt_val.value)
            except ValueError:
                adapt_result.value = "Invalid channel or value"
                safe_update()
                return
            log(f"WriteAdapt ch={ch} val={val}...")
            try:
                ok = proto[0].write_adaptation(ch, val)
            except Exception as ex:
                adapt_result.value = f"Error: {ex}"
                safe_update()
                return
            adapt_result.value = f"  Write {'OK' if ok else 'FAILED'}"
            adapt_result.color = GREEN if ok else RED
            safe_update()
        threading.Thread(target=_do, daemon=True).start()

    btn_adapt_read = ft.Button(content="Read", bgcolor=ACCENT, color=BG, height=30, disabled=True,
                               on_click=adapt_read_click,
                               style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))
    btn_adapt_write = ft.Button(content="Write", bgcolor=RED, color=TEXT, height=30, disabled=True,
                                on_click=adapt_write_click,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)))

    adv_btns = [btn_grp, btn_adc, btn_login, btn_adapt_read, btn_adapt_write]

    advanced_panel = ft.Column([
        ft.Column([
            # ReadGroup
            _section_header("Measurement Groups (ReadGroup 0x29)"),
            ft.Row([ft.Text("Group", size=12, color=DIM), grp_input, btn_grp],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            grp_result,
            # ADC
            _section_header("ADC Channels (0x08)"),
            ft.Row([ft.Text("Channel", size=12, color=DIM), adc_input, btn_adc],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            adc_result,
            # Login
            _section_header("Login (993 Drive Block)"),
            ft.Row([ft.Text("PIN", size=12, color=DIM),
                    login_pin_hi, ft.Text(":", size=12, color=DIM), login_pin_lo,
                    btn_login, login_result],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            # Adaptation
            _section_header("System Adaptation (0x2B/0x2C)"),
            ft.Row([ft.Text("Channel", size=12, color=DIM), adapt_ch, btn_adapt_read,
                    ft.Text("Value", size=12, color=DIM), adapt_val, btn_adapt_write],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            adapt_result,
        ], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True),
    ], expand=True)

    # ══════════════════════════════════════
    #  TAB: LOG
    # ══════════════════════════════════════

    log_panel = ft.Column([log_field], expand=True)

    # ══════════════════════════════════════
    #  TAB SYSTEM
    # ══════════════════════════════════════

    panels = [fault_panel, live_panel, actuator_panel, advanced_panel, log_panel]
    tab_names = ["Fault Codes", "Live Data", "Actuators", "Advanced", "Log"]

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

    status_dot = ft.Text("\u25cf", size=14, color=RED)
    status_label = ft.Text("Disconnected", size=12, color=DIM)

    statusbar = ft.Container(
        ft.Row([
            status_dot, status_label,
            ft.Container(expand=True),
            ft.Text(f"v{VERSION}", size=11, color=DIM),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
        bgcolor=PANEL,
        padding=ft.Padding.symmetric(vertical=6, horizontal=14),
        border=ft.Border.only(top=ft.BorderSide(1, BORDER)),
    )

    # ══════════════════════════════════════
    #  CONNECT / DISCONNECT
    # ══════════════════════════════════════

    def _get_selected_ecu():
        """Parse selected model and ECU from dropdowns."""
        model = model_seg.selected[0] if model_seg.selected else "965"
        ecu_str = ecu_dd.value or ""
        ecus = ECUS.get(model, [])

        for name, addr, baud in ecus:
            if f"{name} (0x{addr:02X})" == ecu_str:
                return model, name, addr, baud

        # Fallback to first ECU
        if ecus:
            return model, ecus[0][0], ecus[0][1], ecus[0][2]
        return model, "Unknown", 0x00, 9600

    def toggle_connect(e):
        if not state["connected"]:
            do_connect()
        else:
            do_disconnect()

    btn_connect.on_click = toggle_connect

    def do_connect():
        port = port_dd.value
        model, ecu_name, ecu_addr, baudrate = _get_selected_ecu()
        is_demo = port in ("Demo", "(no ports)")

        # Create protocol instance
        def on_state_change(new_state):
            if new_state == "connected":
                status_dot.color = GREEN
                status_label.value = f"Connected | {model} | {ecu_name}"
            elif new_state == "disconnected":
                status_dot.color = RED
                status_label.value = "Disconnected"
            elif new_state == "connecting":
                status_dot.color = YELLOW
                status_label.value = "Connecting..."
            safe_update()

        if is_demo:
            proto[0] = DemoProtocol(on_log=log, on_state_change=on_state_change)
        else:
            proto[0] = KWP1281Protocol(on_log=log, on_state_change=on_state_change)

        # UI: disable connect button during connection
        btn_connect.disabled = True
        btn_connect.content = "Connecting..."
        safe_update()

        def _do_connect():
            try:
                part_number = proto[0].connect(port, model, ecu_name, ecu_addr, baudrate)

                state["connected"] = True
                state["demo"] = is_demo

                # Update UI on success
                btn_connect.content = "Disconnect"
                btn_connect.bgcolor = RED
                btn_connect.color = TEXT
                btn_connect.disabled = False
                btn_read.disabled = False
                btn_clear.disabled = False
                btn_live_start.disabled = False
                for b in act_btns:
                    b.disabled = False
                for b in adv_btns:
                    b.disabled = False

                if is_demo:
                    demo_badge.visible = True

                info_label.value = f"ECU: {part_number}  ({ecu_name})"
                info_label.color = TEXT

                # Build gauges for this ECU's live params
                from kwp1281.formulas import get_live_params
                params = get_live_params(model, ecu_addr)
                _build_gauges(params)

                log(f"Connected to {model} {ecu_name}")

            except Exception as ex:
                log(f"Connection failed: {ex}")
                btn_connect.content = "Connect"
                btn_connect.bgcolor = GREEN
                btn_connect.color = BG
                btn_connect.disabled = False

            safe_update()

        threading.Thread(target=_do_connect, daemon=True).start()

    def do_disconnect():
        state["live_running"] = False
        state["connected"] = False
        state["demo"] = False

        def _do():
            try:
                if proto[0]:
                    proto[0].disconnect()
            except Exception as ex:
                log(f"Disconnect error: {ex}")

            btn_connect.content = "Connect"
            btn_connect.bgcolor = GREEN
            btn_connect.color = BG
            btn_read.disabled = True
            btn_clear.disabled = True
            btn_live_start.disabled = True
            btn_live_stop.disabled = True
            for b in act_btns:
                b.disabled = True
            for b in adv_btns:
                b.disabled = True

            info_label.value = "Not connected"
            info_label.color = DIM
            demo_badge.visible = False

            log("Disconnected")
            safe_update()

        threading.Thread(target=_do, daemon=True).start()

    # ══════════════════════════════════════
    #  KEYBOARD NAVIGATION
    # ══════════════════════════════════════

    page.on_keyboard_event = _fault_key_nav

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
    log("Use 'Demo' port for simulated data without hardware")


if __name__ == "__main__":
    ft.run(main)
