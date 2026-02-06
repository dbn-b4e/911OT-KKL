"""KWP1281 protocol state machine - connection, commands, keep-alive."""

import time
import threading
import logging

from .serial_port import KLineSerial, KLineError, KLineTimeoutError
from .constants import (
    CMD_GET_ECU_ID, CMD_VALUE_REQ, CMD_CLEAR_FAULTS, CMD_END_COMM,
    CMD_READ_FAULTS, CMD_ADC_READ, CMD_ACK, CMD_ACTUATOR,
    CMD_BASIC_SET, CMD_READ_GROUP, CMD_LOGIN, CMD_READ_ADAPT, CMD_WRITE_ADAPT,
    RSP_ACK, RSP_NAK, RSP_ASCII_ID, RSP_FAULT_CODES, RSP_BINARY_DATA,
    RSP_GROUP_DATA, RSP_ADAPT_RESP, RSP_ADC_RESP,
    ETX, KEEPALIVE_INTERVAL, MAX_INIT_RETRIES,
    FAULT_SECTIONS,
)
from . import fault_codes
from .formulas import get_live_params

log = logging.getLogger(__name__)


class ProtocolError(Exception):
    """Protocol-level error."""


class ConnectionLostError(ProtocolError):
    """Connection to ECU was lost."""


class KWP1281Protocol:
    """KWP1281 protocol implementation for Porsche 964/993/965.

    Usage:
        proto = KWP1281Protocol(on_log=print)
        proto.connect("/dev/ttyUSB0", "964", "Motronic M2.1", 0x10, 8800)
        faults = proto.read_faults()
        proto.disconnect()
    """

    def __init__(self, on_log=None, on_state_change=None, rts_inverted=True):
        self.on_log = on_log or (lambda msg: None)
        self.on_state_change = on_state_change or (lambda state: None)

        self.connected = False
        self.model = ""
        self.ecu_address = 0
        self.ecu_name = ""
        self.part_number = ""

        self._kline = KLineSerial(rts_inverted=rts_inverted)
        self._counter = 0
        self._lock = threading.Lock()
        self._keepalive_thread = None
        self._keepalive_stop = threading.Event()
        self._cmd_active = threading.Event()  # set when a command is running

    # ── Connection ──

    def connect(self, port, model, ecu_name, ecu_address, baudrate):
        """Connect to ECU via K-Line.

        Performs 5-baud init, handshake, and reads ECU identification.
        Returns part number string on success.
        """
        self.model = model
        self.ecu_address = ecu_address
        self.ecu_name = ecu_name
        self._counter = 0

        last_error = None
        for attempt in range(1, MAX_INIT_RETRIES + 1):
            try:
                self.on_log(f"Connection attempt {attempt}/{MAX_INIT_RETRIES}...")
                self.on_state_change("connecting")

                # Open serial port at a dummy baudrate
                self._kline.open(port, baudrate=9600)

                # 5-baud init
                self.on_log(f"Sending 5-baud address 0x{ecu_address:02X}...")
                self._kline.send_5baud_address(ecu_address)

                # Handshake
                self.on_log(f"Waiting for sync @ {baudrate} baud...")
                kw1, kw2 = self._kline.perform_handshake(baudrate)
                self.on_log(f"Keywords: 0x{kw1:02X} 0x{kw2:02X}")

                # Read ECU ident block(s)
                self.part_number = self._read_ident_blocks()
                self.on_log(f"ECU ID: {self.part_number}")

                self.connected = True
                self.on_state_change("connected")

                # Start keep-alive
                self._start_keepalive()

                return self.part_number

            except (KLineError, KLineTimeoutError, ProtocolError, OSError) as e:
                last_error = e
                self.on_log(f"Attempt {attempt} failed: {e}")
                self._kline.close()
                if attempt < MAX_INIT_RETRIES:
                    time.sleep(1.0)

        self.on_state_change("disconnected")
        raise ConnectionLostError(f"Failed after {MAX_INIT_RETRIES} attempts: {last_error}")

    def disconnect(self):
        """Send EndComm and close connection."""
        self._stop_keepalive()

        if self.connected:
            try:
                with self._lock:
                    self.on_log("Sending EndComm...")
                    self._send_block(CMD_END_COMM)
            except Exception as e:
                self.on_log(f"EndComm error (ignored): {e}")

        self.connected = False
        self._kline.close()
        self.on_state_change("disconnected")
        self.on_log("Disconnected")

    # ── Block send/receive ──

    def _send_block(self, title, data=b""):
        """Send a KWP1281 block with inter-byte ACK protocol.

        Block format: [Length, Counter, Title, ...Data, 0x03]
        Each byte except ETX requires ECU to ACK with complement.
        """
        length = len(data) + 3  # length + counter + title + ETX (length includes itself)
        block = bytes([length + 1, self._counter, title]) + data + bytes([ETX])

        self._log_hex("TX", block)

        # Send each byte, wait for ACK on all except last (ETX)
        for i, b in enumerate(block):
            if i < len(block) - 1:
                self._kline.send_byte_with_ack(b)
            else:
                self._kline.write_byte(b)  # ETX: no ACK expected

        self._counter = (self._counter + 1) & 0xFF

    def _recv_block(self):
        """Receive a KWP1281 block with inter-byte ACK protocol.

        Returns (title, data_bytes).
        """
        # Receive length byte, send ACK
        length = self._kline.recv_byte_with_ack()

        # Receive counter, send ACK
        counter = self._kline.recv_byte_with_ack()

        # Receive title, send ACK
        title = self._kline.recv_byte_with_ack()

        # Receive data bytes (length - 3 = data + ETX, so data = length - 3 - 1)
        # Actually: block = [Len, Cnt, Title, ...Data, ETX]
        # Len counts from Len to ETX inclusive, so data_len = Len - 3
        # But the -1 for ETX is separate
        data_count = length - 3  # number of remaining bytes including ETX
        data = bytearray()
        for i in range(data_count):
            if i < data_count - 1:
                # Data byte: receive and ACK
                data.append(self._kline.recv_byte_with_ack())
            else:
                # Last byte should be ETX: receive but don't ACK
                etx = self._kline.read_byte(timeout=0.1)
                if etx != ETX:
                    self.on_log(f"Warning: expected ETX 0x03, got 0x{etx:02X}")

        block = bytes([length, counter, title]) + bytes(data) + bytes([ETX])
        self._log_hex("RX", block)

        self._counter = (counter + 1) & 0xFF
        return (title, bytes(data))

    def _send_ack(self):
        """Send ACK block (keep-alive)."""
        self._send_block(CMD_ACK)

    def _expect_ack(self):
        """Receive a block and verify it's ACK."""
        title, data = self._recv_block()
        if title == RSP_NAK:
            raise ProtocolError("ECU responded with NAK")
        if title != RSP_ACK:
            raise ProtocolError(f"Expected ACK (0x09), got 0x{title:02X}")
        return True

    # ── Ident blocks ──

    def _read_ident_blocks(self):
        """Read ECU identification blocks after handshake.

        The ECU sends one or more 0xF6 (ASCII ID) blocks followed by ACK.
        We ACK each one until we get ACK from ECU.
        """
        parts = []
        while True:
            title, data = self._recv_block()
            if title == RSP_ASCII_ID:
                # ASCII identification string
                text = data.decode("ascii", errors="replace").strip()
                parts.append(text)
                # ACK to request next block
                self._send_ack()
            elif title == RSP_ACK:
                break
            else:
                self.on_log(f"Unexpected block 0x{title:02X} during ident")
                self._send_ack()
                break

        return " ".join(parts) if parts else "Unknown"

    # ── Commands ──

    def read_faults(self):
        """Read fault codes from ECU.

        Returns list of (code_str, description, count) tuples.
        """
        with self._lock:
            self._pause_keepalive()
            try:
                self._send_block(CMD_READ_FAULTS)
                title, data = self._recv_block()

                if title != RSP_FAULT_CODES:
                    self._send_ack()
                    raise ProtocolError(f"Expected FaultCodes (0xFC), got 0x{title:02X}")

                faults = self._parse_faults(data)

                # ACK the fault response
                self._send_ack()
                # Receive ECU's ACK
                self._recv_block()

                return faults
            finally:
                self._resume_keepalive()

    def _parse_faults(self, data):
        """Parse fault code response data.

        Data format: pairs of (code_byte, status_byte).
        Single 0x00 byte means no faults.
        """
        if len(data) == 1 and data[0] == 0x00:
            return []

        faults = []
        i = 0
        while i + 1 < len(data):
            code_byte = data[i]
            status_byte = data[i + 1]
            i += 2

            if code_byte == 0x00:
                continue

            count = status_byte & 0x3F
            code_str = str(code_byte)
            desc = fault_codes.lookup_for_ecu(self.model, self.ecu_address, code_byte)
            faults.append((code_str, desc, count))

        return faults

    def clear_faults(self):
        """Clear fault memory. Returns True on success."""
        with self._lock:
            self._pause_keepalive()
            try:
                self._send_block(CMD_CLEAR_FAULTS)
                self._expect_ack()
                return True
            except ProtocolError as e:
                self.on_log(f"Clear faults failed: {e}")
                return False
            finally:
                self._resume_keepalive()

    def read_value(self, register):
        """Read a single value from Motronic (OBDPlot Value Request 0x01).

        Args:
            register: Register address byte (e.g. 0x3A for RPM on 964)

        Returns raw byte value (int) or None on error.
        """
        with self._lock:
            self._pause_keepalive()
            try:
                # Value Request: [0x01, 0x01, 0x00, register]
                data = bytes([0x01, 0x00, register])
                self._send_block(CMD_VALUE_REQ, data)
                title, resp_data = self._recv_block()

                if title == RSP_BINARY_DATA and len(resp_data) >= 1:
                    self._send_ack()
                    self._recv_block()  # ECU ACK
                    return resp_data[0]
                elif title == RSP_ACK:
                    return None
                else:
                    self._send_ack()
                    return None
            except (KLineError, ProtocolError) as e:
                self.on_log(f"Read value error: {e}")
                return None
            finally:
                self._resume_keepalive()

    def read_live_values(self):
        """Read all live data parameters for current ECU.

        Returns list of (name, value, unit, formatted, ratio) tuples.
        """
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

    def read_adc(self, channel):
        """Read ADC channel value.

        Returns 16-bit value or None.
        """
        with self._lock:
            self._pause_keepalive()
            try:
                self._send_block(CMD_ADC_READ, bytes([channel]))
                title, data = self._recv_block()

                if title == RSP_ADC_RESP and len(data) >= 2:
                    value = (data[0] << 8) | data[1]
                    self._send_ack()
                    self._recv_block()
                    return value
                else:
                    self._send_ack()
                    return None
            except (KLineError, ProtocolError) as e:
                self.on_log(f"ADC read error: {e}")
                return None
            finally:
                self._resume_keepalive()

    def actuator_test(self, num):
        """Start actuator test.

        Args:
            num: Actuator number (1-16)

        Returns True on success.
        """
        with self._lock:
            self._pause_keepalive()
            try:
                self._send_block(CMD_ACTUATOR, bytes([num]))
                title, data = self._recv_block()

                # Accept ACK or actuator-specific response
                if title in (RSP_ACK, 0xF5):
                    if title != RSP_ACK:
                        self._send_ack()
                        self._recv_block()
                    return True
                else:
                    self._send_ack()
                    return False
            except (KLineError, ProtocolError) as e:
                self.on_log(f"Actuator test error: {e}")
                return False
            finally:
                self._resume_keepalive()

    def read_group(self, group):
        """Read measurement group.

        Returns list of up to 4 (formula_id, value_a, value_b) tuples.
        """
        with self._lock:
            self._pause_keepalive()
            try:
                self._send_block(CMD_READ_GROUP, bytes([group]))
                title, data = self._recv_block()

                if title == RSP_GROUP_DATA:
                    # 4 values x 3 bytes = 12 bytes
                    values = []
                    i = 0
                    while i + 2 < len(data):
                        f_id = data[i]
                        va = data[i + 1]
                        vb = data[i + 2]
                        values.append((f_id, va, vb))
                        i += 3
                    self._send_ack()
                    self._recv_block()
                    return values
                else:
                    self._send_ack()
                    return []
            except (KLineError, ProtocolError) as e:
                self.on_log(f"ReadGroup error: {e}")
                return []
            finally:
                self._resume_keepalive()

    def login(self, pin_hi, pin_lo, workshop=0x00):
        """Send Login command (for 993 Drive Block workaround).

        Returns True on ACK.
        """
        with self._lock:
            self._pause_keepalive()
            try:
                self._send_block(CMD_LOGIN, bytes([pin_hi, pin_lo, workshop]))
                self._expect_ack()
                return True
            except ProtocolError as e:
                self.on_log(f"Login failed: {e}")
                return False
            finally:
                self._resume_keepalive()

    def read_adaptation(self, channel):
        """Read adaptation channel.

        Returns (channel, value_16bit) or None.
        """
        with self._lock:
            self._pause_keepalive()
            try:
                self._send_block(CMD_READ_ADAPT, bytes([channel]))
                title, data = self._recv_block()

                if title == RSP_ADAPT_RESP and len(data) >= 3:
                    ch = data[0]
                    val = (data[1] << 8) | data[2]
                    self._send_ack()
                    self._recv_block()
                    return (ch, val)
                else:
                    self._send_ack()
                    return None
            except (KLineError, ProtocolError) as e:
                self.on_log(f"ReadAdapt error: {e}")
                return None
            finally:
                self._resume_keepalive()

    def write_adaptation(self, channel, value):
        """Write adaptation channel value.

        Args:
            channel: Channel number (0-255)
            value: 16-bit value

        Returns True on ACK.
        """
        with self._lock:
            self._pause_keepalive()
            try:
                v_hi = (value >> 8) & 0xFF
                v_lo = value & 0xFF
                self._send_block(CMD_WRITE_ADAPT, bytes([channel, v_hi, v_lo]))
                self._expect_ack()
                return True
            except ProtocolError as e:
                self.on_log(f"WriteAdapt failed: {e}")
                return False
            finally:
                self._resume_keepalive()

    # ── Keep-alive ──

    def _start_keepalive(self):
        """Start keep-alive daemon thread."""
        self._keepalive_stop.clear()
        self._keepalive_thread = threading.Thread(
            target=self._keepalive_loop, daemon=True, name="kwp1281-keepalive")
        self._keepalive_thread.start()

    def _stop_keepalive(self):
        """Stop keep-alive thread."""
        self._keepalive_stop.set()
        if self._keepalive_thread and self._keepalive_thread.is_alive():
            self._keepalive_thread.join(timeout=2.0)
        self._keepalive_thread = None

    def _pause_keepalive(self):
        """Pause keep-alive while a command is active."""
        self._cmd_active.set()

    def _resume_keepalive(self):
        """Resume keep-alive after command completes."""
        self._cmd_active.clear()

    def _keepalive_loop(self):
        """Send ACK blocks every KEEPALIVE_INTERVAL seconds when idle."""
        while not self._keepalive_stop.is_set():
            self._keepalive_stop.wait(KEEPALIVE_INTERVAL)
            if self._keepalive_stop.is_set():
                break

            # Skip if a command is running
            if self._cmd_active.is_set():
                continue

            try:
                with self._lock:
                    self._send_ack()
                    title, _ = self._recv_block()
                    if title != RSP_ACK:
                        self.on_log(f"Keep-alive: unexpected response 0x{title:02X}")
            except Exception as e:
                self.on_log(f"Keep-alive failed: {e}")
                self.connected = False
                self.on_state_change("disconnected")
                break

    # ── Helpers ──

    def _log_hex(self, direction, data):
        """Log a block as hex dump."""
        hex_str = " ".join(f"{b:02X}" for b in data)
        self.on_log(f"  {direction}: [{hex_str}]")

    def stop_live(self):
        """No-op for API compatibility with DemoProtocol."""
        pass
