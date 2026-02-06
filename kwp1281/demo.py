"""Demo/simulator backend - fake ECU responses for testing without hardware."""

import time
import random
import threading

from . import fault_codes
from .constants import (
    ECUS, FAULT_SECTIONS, DEMO_PART_NUMBERS, CCU_ACTUATORS,
)
from .formulas import get_live_params


class DemoProtocol:
    """Simulated KWP1281 protocol with same interface as KWP1281Protocol."""

    def __init__(self, on_log=None, on_state_change=None):
        self.on_log = on_log or (lambda msg: None)
        self.on_state_change = on_state_change or (lambda state: None)

        self.connected = False
        self.model = "965"
        self.ecu_address = 0x51
        self.ecu_name = ""
        self.part_number = ""
        self._lock = threading.Lock()
        self._live_running = False
        self._stored_faults = None  # cached faults, generated once at first read

    def connect(self, port, model, ecu_name, ecu_address, baudrate):
        """Simulate ECU connection with delay."""
        self.model = model
        self.ecu_address = ecu_address
        self.ecu_name = ecu_name

        self.on_log(f"[DEMO] Connecting to {ecu_name} (0x{ecu_address:02X})...")
        self.on_state_change("connecting")
        time.sleep(0.5)  # simulate handshake delay

        self.on_log("[DEMO] Sending 5-baud init...")
        time.sleep(0.8)

        self.on_log("[DEMO] Sync 0x55 received")
        self.on_log("[DEMO] Keywords: 0x0B 0x02")
        time.sleep(0.2)

        # Get demo part number
        pn = DEMO_PART_NUMBERS.get(model, {}).get(ecu_address, "XXX.XXX.XXX.XX")
        self.part_number = pn
        self.on_log(f"[DEMO] ECU ID: {pn}")

        self.connected = True
        self.on_state_change("connected")
        self.on_log(f"[DEMO] Connected to {ecu_name}")
        return pn

    def disconnect(self):
        """Simulate disconnection."""
        self._live_running = False
        if self.connected:
            self.on_log("[DEMO] Sending EndComm...")
            time.sleep(0.1)
            self.connected = False
            self.on_state_change("disconnected")
            self.on_log("[DEMO] Disconnected")

    def _generate_faults(self):
        """Generate a fixed set of demo faults from all available sections."""
        faults = []
        sections = FAULT_SECTIONS.get(self.model, {}).get(self.ecu_address, [])

        for section in sections:
            all_codes = fault_codes.get_section_codes(section)
            if not all_codes:
                continue
            code_items = list(all_codes.items())
            # Take up to 8 codes per section to get a good scrollable list
            num = min(8, len(code_items))
            picked = random.sample(code_items, num)
            for code_str, desc in picked:
                count = random.randint(1, 12)
                faults.append((code_str, desc, count))

        # Sort by code number
        faults.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)
        return faults

    def read_faults(self):
        """Return simulated fault codes (same list until cleared).

        Returns list of (code_str, description, count) tuples.
        """
        if not self.connected:
            return []

        self.on_log("[DEMO] Reading fault codes...")
        time.sleep(0.3)

        # Generate once, return same list on every read
        if self._stored_faults is None:
            self._stored_faults = self._generate_faults()

        self.on_log(f"[DEMO] Found {len(self._stored_faults)} fault(s)")
        for code, desc, cnt in self._stored_faults:
            self.on_log(f"  #{code}: {desc} (x{cnt})")

        return list(self._stored_faults)

    def clear_faults(self):
        """Simulate clearing fault memory."""
        if not self.connected:
            return False
        self.on_log("[DEMO] Clearing fault memory...")
        time.sleep(0.3)
        self._stored_faults = []  # cleared - next read returns empty
        self.on_log("[DEMO] Fault memory cleared (ACK)")
        return True

    def read_value(self, register):
        """Simulate reading a single value register.

        Returns raw byte value (0-255).
        """
        if not self.connected:
            return None

        # Generate plausible values based on register
        base_values = {
            0x37: 140,   # intake temp ~80F
            0x38: 180,   # head temp ~180F
            0x39: 21,    # RPM ~840
            0x3A: 21,    # RPM 964 ~840
            0x42: 64,    # injector time
            0x45: 92,    # AFM ~1.8V
            0x5D: 80,    # timing advance
            0x36: 204,   # battery ~13.9V
            0x3D: 50,    # O2 ~150mV
            0x47: 51,    # MAF ~1V
        }
        base = base_values.get(register, 128)
        jitter = max(1, int(base * 0.05))
        val = max(0, min(255, base + random.randint(-jitter, jitter)))
        return val

    def read_live_values(self):
        """Read all live data parameters for current ECU.

        Returns list of (name, value, unit, formatted, ratio) tuples.
        """
        if not self.connected:
            return []

        params = get_live_params(self.model, self.ecu_address)
        results = []
        for name, reg, formula, mn, mx, unit, fmt in params:
            raw = self.read_value(reg)
            if raw is None:
                continue
            val = formula(raw)
            ratio = min(max((val - mn) / (mx - mn), 0), 1.0) if mx > mn else 0
            formatted = fmt.format(val)
            results.append((name, val, unit, formatted, ratio))

        return results

    def actuator_test(self, num):
        """Simulate actuator test.

        Returns True on success.
        """
        if not self.connected:
            return False

        name = CCU_ACTUATORS.get(num, f"Actuator {num}")
        self.on_log(f"[DEMO] Actuator test #{num:02d}: {name}")
        time.sleep(0.5)
        self.on_log(f"[DEMO] Actuator #{num:02d} responded OK")
        return True

    def read_group(self, group):
        """Simulate ReadGroup response.

        Returns list of 4 (formula_id, value_a, value_b) tuples.
        """
        if not self.connected:
            return []

        self.on_log(f"[DEMO] ReadGroup {group:02X}")
        time.sleep(0.2)
        return [
            (1, random.randint(0, 255), random.randint(0, 255)),
            (1, random.randint(0, 255), random.randint(0, 255)),
            (1, random.randint(0, 255), random.randint(0, 255)),
            (1, random.randint(0, 255), random.randint(0, 255)),
        ]

    def login(self, pin_hi, pin_lo, workshop=0x00):
        """Simulate login."""
        if not self.connected:
            return False
        self.on_log(f"[DEMO] Login PIN={pin_hi:02X}{pin_lo:02X} WS={workshop:02X}")
        time.sleep(0.3)
        self.on_log("[DEMO] Login accepted (ACK)")
        return True

    def read_adaptation(self, channel):
        """Simulate reading adaptation channel.

        Returns (channel, value_16bit).
        """
        if not self.connected:
            return None
        self.on_log(f"[DEMO] ReadAdapt channel {channel:02X}")
        time.sleep(0.2)
        return (channel, random.randint(0, 65535))

    def write_adaptation(self, channel, value):
        """Simulate writing adaptation channel."""
        if not self.connected:
            return False
        self.on_log(f"[DEMO] WriteAdapt ch={channel:02X} val={value}")
        time.sleep(0.3)
        self.on_log("[DEMO] Adaptation written (ACK)")
        return True

    def stop_live(self):
        """Stop live data polling."""
        self._live_running = False
