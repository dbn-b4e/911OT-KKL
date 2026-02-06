#!/usr/bin/env python3
"""911OT-KKL Scanner - CustomTkinter Prototype"""

import customtkinter as ctk
import serial.tools.list_ports
import threading
import time
import random

# --- Theme ---
ctk.set_appearance_mode("dark")

# Porsche-inspired palette
C_BG        = "#0f0f17"
C_PANEL     = "#1a1a2e"
C_PANEL2    = "#222240"
C_ACCENT    = "#ff6b00"   # Porsche orange
C_ACCENT2   = "#ff8c38"
C_GREEN     = "#00c853"
C_RED       = "#ff1744"
C_YELLOW    = "#ffd600"
C_TEXT      = "#e8e8ec"
C_TEXT_DIM  = "#8888a0"
C_BORDER    = "#2a2a45"

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


class GaugeBar(ctk.CTkFrame):
    """Horizontal gauge bar with label and value."""

    def __init__(self, master, name, unit, max_val, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.max_val = max_val
        self.name = name

        self.grid_columnconfigure(1, weight=1)

        self.lbl_name = ctk.CTkLabel(self, text=name, width=120, anchor="w",
                                      font=ctk.CTkFont(size=13), text_color=C_TEXT_DIM)
        self.lbl_name.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.bar = ctk.CTkProgressBar(self, height=14, corner_radius=4,
                                       fg_color=C_PANEL2, progress_color=C_ACCENT)
        self.bar.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self.bar.set(0)

        self.lbl_val = ctk.CTkLabel(self, text=f"--- {unit}", width=90, anchor="e",
                                     font=ctk.CTkFont(family="Menlo", size=14, weight="bold"),
                                     text_color=C_TEXT)
        self.lbl_val.grid(row=0, column=2, sticky="e")
        self.unit = unit

    def set_value(self, val, fmt="{:.0f}"):
        ratio = min(val / self.max_val, 1.0) if self.max_val > 0 else 0
        self.bar.set(ratio)
        # Color coding
        if ratio > 0.85:
            self.bar.configure(progress_color=C_RED)
        elif ratio > 0.7:
            self.bar.configure(progress_color=C_YELLOW)
        else:
            self.bar.configure(progress_color=C_ACCENT)
        self.lbl_val.configure(text=f"{fmt.format(val)} {self.unit}")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("911OT-KKL Scanner [CustomTkinter]")
        self.geometry("780x700")
        self.minsize(700, 600)
        self.configure(fg_color=C_BG)

        self.connected = False
        self.demo_running = False
        self.gauges = {}

        self._build_header()
        self._build_connection()
        self._build_ecu_info()
        self._build_tabs()
        self._build_statusbar()

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

    # ── Header ──
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=0, height=50)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)

        logo = ctk.CTkLabel(hdr, text="  911OT-KKL",
                            font=ctk.CTkFont(size=20, weight="bold"),
                            text_color=C_ACCENT)
        logo.grid(row=0, column=0, padx=16, pady=10, sticky="w")

        sub = ctk.CTkLabel(hdr, text="Porsche 964 / 993 / 965 K-Line Scanner",
                           font=ctk.CTkFont(size=12), text_color=C_TEXT_DIM)
        sub.grid(row=0, column=1, padx=8, pady=10, sticky="w")

        self.demo_badge = ctk.CTkLabel(hdr, text=" DEMO ", corner_radius=4,
                                        fg_color=C_YELLOW, text_color="#000",
                                        font=ctk.CTkFont(size=11, weight="bold"))
        self.demo_badge.grid(row=0, column=2, padx=16, pady=10, sticky="e")
        self.demo_badge.grid_remove()

    # ── Connection ──
    def _build_connection(self):
        frm = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=8)
        frm.grid(row=1, column=0, sticky="ew", padx=12, pady=(10, 4))
        frm.grid_columnconfigure(1, weight=1)

        # Row 1: Port + Model
        ctk.CTkLabel(frm, text="Port", text_color=C_TEXT_DIM,
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(16, 6), pady=(12, 4), sticky="w")

        ports = [p.device for p in serial.tools.list_ports.comports()]
        ports = ports if ports else ["(no ports)"]
        ports.append("Demo")

        self.port_var = ctk.StringVar(value=ports[0])
        self.port_menu = ctk.CTkOptionMenu(frm, variable=self.port_var, values=ports,
                                            width=250, fg_color=C_PANEL2,
                                            button_color=C_ACCENT, button_hover_color=C_ACCENT2,
                                            dropdown_fg_color=C_PANEL2)
        self.port_menu.grid(row=0, column=1, padx=4, pady=(12, 4), sticky="w")

        ctk.CTkLabel(frm, text="Model", text_color=C_TEXT_DIM,
                     font=ctk.CTkFont(size=12)).grid(row=0, column=2, padx=(20, 6), pady=(12, 4), sticky="w")

        self.model_var = ctk.StringVar(value="965")
        self.model_seg = ctk.CTkSegmentedButton(frm, values=["964", "993", "965"],
                                                 variable=self.model_var,
                                                 selected_color=C_ACCENT,
                                                 selected_hover_color=C_ACCENT2,
                                                 unselected_color=C_PANEL2,
                                                 command=self._on_model_change)
        self.model_seg.grid(row=0, column=3, padx=(4, 16), pady=(12, 4), sticky="w")

        # Row 2: ECU + Connect
        ctk.CTkLabel(frm, text="ECU", text_color=C_TEXT_DIM,
                     font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=(16, 6), pady=(4, 12), sticky="w")

        self.ecu_var = ctk.StringVar()
        self.ecu_menu = ctk.CTkOptionMenu(frm, variable=self.ecu_var, width=250,
                                           fg_color=C_PANEL2,
                                           button_color=C_ACCENT, button_hover_color=C_ACCENT2,
                                           dropdown_fg_color=C_PANEL2)
        self.ecu_menu.grid(row=1, column=1, padx=4, pady=(4, 12), sticky="w")
        self._on_model_change("965")

        self.btn_connect = ctk.CTkButton(frm, text="Connect", width=120, height=36,
                                          fg_color=C_GREEN, hover_color="#00a844",
                                          text_color="#000", font=ctk.CTkFont(size=13, weight="bold"),
                                          corner_radius=6, command=self._toggle_connect)
        self.btn_connect.grid(row=1, column=2, columnspan=2, padx=(20, 16), pady=(4, 12), sticky="e")

    # ── ECU Info ──
    def _build_ecu_info(self):
        self.info_frame = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=8, height=40)
        self.info_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=4)

        self.info_label = ctk.CTkLabel(self.info_frame, text="  Not connected",
                                        text_color=C_TEXT_DIM, anchor="w",
                                        font=ctk.CTkFont(family="Menlo", size=12))
        self.info_label.pack(padx=16, pady=8, fill="x")

    # ── Tabs ──
    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self, fg_color=C_PANEL, corner_radius=8,
                                    segmented_button_fg_color=C_PANEL2,
                                    segmented_button_selected_color=C_ACCENT,
                                    segmented_button_selected_hover_color=C_ACCENT2,
                                    segmented_button_unselected_color=C_PANEL2)
        self.tabs.grid(row=3, column=0, sticky="nsew", padx=12, pady=4)

        # --- Tab: Fault Codes ---
        tab_faults = self.tabs.add("Fault Codes")
        tab_faults.grid_rowconfigure(0, weight=1)
        tab_faults.grid_columnconfigure(0, weight=1)

        self.fault_list = ctk.CTkTextbox(tab_faults, fg_color=C_BG, text_color=C_TEXT,
                                          font=ctk.CTkFont(family="Menlo", size=13),
                                          corner_radius=6, border_width=1, border_color=C_BORDER,
                                          state="disabled")
        self.fault_list.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))

        btn_frm = ctk.CTkFrame(tab_faults, fg_color="transparent")
        btn_frm.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 8))

        self.btn_read_faults = ctk.CTkButton(btn_frm, text="Read Faults", width=130,
                                              fg_color=C_ACCENT, hover_color=C_ACCENT2,
                                              text_color="#000", font=ctk.CTkFont(weight="bold"),
                                              state="disabled", command=self._read_faults)
        self.btn_read_faults.pack(side="left", padx=(0, 8))

        self.btn_clear_faults = ctk.CTkButton(btn_frm, text="Clear Faults", width=130,
                                               fg_color=C_RED, hover_color="#d50032",
                                               text_color="#fff", font=ctk.CTkFont(weight="bold"),
                                               state="disabled", command=self._clear_faults)
        self.btn_clear_faults.pack(side="left")

        # --- Tab: Live Data ---
        tab_live = self.tabs.add("Live Data")
        tab_live.grid_rowconfigure(0, weight=1)
        tab_live.grid_columnconfigure(0, weight=1)

        gauge_frame = ctk.CTkScrollableFrame(tab_live, fg_color=C_BG, corner_radius=6,
                                              border_width=1, border_color=C_BORDER)
        gauge_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        gauge_frame.grid_columnconfigure(0, weight=1)

        for i, (name, info) in enumerate(DEMO_LIVE.items()):
            g = GaugeBar(gauge_frame, name, info["unit"], info["max"])
            g.grid(row=i, column=0, sticky="ew", padx=12, pady=6)
            self.gauges[name] = g

        # --- Tab: Actuators ---
        tab_act = self.tabs.add("Actuators")
        tab_act.grid_columnconfigure(0, weight=1)

        actuators = ["Fresh Air Servo", "Defrost Servo", "Footwell Servo",
                     "Mixer Servo L", "Mixer Servo R", "Condenser Fan",
                     "Oil Cooler Fan", "Rear Blower"]

        for i, name in enumerate(actuators):
            row_frm = ctk.CTkFrame(tab_act, fg_color=C_BG if i % 2 == 0 else C_PANEL2,
                                    corner_radius=4)
            row_frm.grid(row=i, column=0, sticky="ew", padx=8, pady=1)
            row_frm.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(row_frm, text=f"  {i+1:02d}  {name}",
                         font=ctk.CTkFont(family="Menlo", size=13),
                         text_color=C_TEXT, anchor="w").grid(row=0, column=0, sticky="w", padx=4, pady=6)

            btn = ctk.CTkButton(row_frm, text="Test", width=70, height=28,
                                fg_color=C_ACCENT, hover_color=C_ACCENT2,
                                text_color="#000", font=ctk.CTkFont(size=12, weight="bold"),
                                state="disabled")
            btn.grid(row=0, column=1, padx=8, pady=4)

        # --- Tab: Log ---
        tab_log = self.tabs.add("Log")
        tab_log.grid_rowconfigure(0, weight=1)
        tab_log.grid_columnconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(tab_log, fg_color=C_BG, text_color=C_GREEN,
                                       font=ctk.CTkFont(family="Menlo", size=12),
                                       corner_radius=6, border_width=1, border_color=C_BORDER)
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._log("911OT-KKL Scanner ready")
        self._log("Select port and model, then click Connect")

    # ── Status Bar ──
    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, fg_color=C_PANEL, corner_radius=0, height=28)
        bar.grid(row=4, column=0, sticky="ew")

        self.status_dot = ctk.CTkLabel(bar, text="●", text_color=C_RED,
                                        font=ctk.CTkFont(size=14))
        self.status_dot.pack(side="left", padx=(12, 4))

        self.status_text = ctk.CTkLabel(bar, text="Disconnected", text_color=C_TEXT_DIM,
                                         font=ctk.CTkFont(size=12))
        self.status_text.pack(side="left")

        self.status_right = ctk.CTkLabel(bar, text="v1.0", text_color=C_TEXT_DIM,
                                          font=ctk.CTkFont(size=11))
        self.status_right.pack(side="right", padx=12)

    # ── Actions ──
    def _on_model_change(self, model):
        ecus = ECUS.get(model, [])
        names = [f"{name} (0x{addr:02X})" for name, addr, baud in ecus]
        self.ecu_menu.configure(values=names)
        if names:
            self.ecu_var.set(names[0])

    def _toggle_connect(self):
        if not self.connected:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        port = self.port_var.get()
        model = self.model_var.get()
        ecu_str = self.ecu_var.get()

        is_demo = port == "Demo" or port == "(no ports)"

        self._log(f"Connecting to {ecu_str} on {port}...")

        if is_demo:
            self.demo_badge.grid()
            self._log("DEMO MODE - simulated data")

        # Simulate connection
        self.connected = True
        self.btn_connect.configure(text="Disconnect", fg_color=C_RED, hover_color="#d50032")
        self.btn_read_faults.configure(state="normal")
        self.btn_clear_faults.configure(state="normal")

        # ECU info
        ecu_parts = {
            "964": "964.618.124.02  Motronic M2.1",
            "993": "993.618.124.00  Motronic M5.2",
            "965": "965.618.xxx.xx  CCU Climate Control",
        }
        self.info_label.configure(text=f"  ECU: {ecu_parts.get(model, 'Unknown')}",
                                   text_color=C_TEXT)
        self.status_dot.configure(text_color=C_GREEN)
        self.status_text.configure(text=f"Connected | {model} | {ecu_str}")
        self._log(f"Connected to {model} {ecu_str}")

        if is_demo:
            self.demo_running = True
            threading.Thread(target=self._demo_loop, daemon=True).start()

    def _disconnect(self):
        self.connected = False
        self.demo_running = False
        self.btn_connect.configure(text="Connect", fg_color=C_GREEN, hover_color="#00a844")
        self.btn_read_faults.configure(state="disabled")
        self.btn_clear_faults.configure(state="disabled")
        self.info_label.configure(text="  Not connected", text_color=C_TEXT_DIM)
        self.status_dot.configure(text_color=C_RED)
        self.status_text.configure(text="Disconnected")
        self.demo_badge.grid_remove()
        self._log("Disconnected")

    def _read_faults(self):
        self._log("Reading fault codes...")
        self.fault_list.configure(state="normal")
        self.fault_list.delete("1.0", "end")

        self.fault_list.insert("end", f"  {'Code':<8}{'Description':<35}{'Count':>5}\n")
        self.fault_list.insert("end", "  " + "─" * 50 + "\n")
        for code, desc, count in DEMO_FAULTS:
            self.fault_list.insert("end", f"  {code:<8}{desc:<35}{'x'+str(count):>5}\n")

        self.fault_list.insert("end", f"\n  {len(DEMO_FAULTS)} fault(s) found\n")
        self.fault_list.configure(state="disabled")
        self._log(f"Found {len(DEMO_FAULTS)} fault code(s)")

    def _clear_faults(self):
        self.fault_list.configure(state="normal")
        self.fault_list.delete("1.0", "end")
        self.fault_list.insert("end", "\n  Fault memory cleared.\n")
        self.fault_list.configure(state="disabled")
        self._log("Fault memory cleared")

    def _demo_loop(self):
        """Simulate live data updates."""
        while self.demo_running:
            for name, info in DEMO_LIVE.items():
                if not self.demo_running:
                    break
                base = info["value"]
                jitter = base * 0.05
                val = base + random.uniform(-jitter, jitter)
                val = max(0, min(val, info["max"]))

                if name in self.gauges:
                    self.after(0, self.gauges[name].set_value, val, info["fmt"])

            time.sleep(0.3)

    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")


if __name__ == "__main__":
    app = App()
    app.mainloop()
