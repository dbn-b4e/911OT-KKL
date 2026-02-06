"""K-Line serial port wrapper with 5-baud init via RTS bit-bang."""

import sys
import time
import struct
import serial

from .constants import BIT_TIME_5BAUD, KEYWORD_ACK_DELAY, INTERBYTE_TIMEOUT


class KLineError(Exception):
    """Base exception for K-Line serial errors."""


class KLineTimeoutError(KLineError):
    """Byte read timed out."""


class KLineSerial:
    """PySerial wrapper for K-Line communication with RTS bit-bang 5-baud init.

    The OBDPlot/ScanTool interface uses RTS to drive K-Line:
      SETRTS = K-Line LOW  (inverted logic)
      CLRRTS = K-Line HIGH

    Set rts_inverted=False for direct-logic interfaces.
    """

    def __init__(self, rts_inverted=True):
        self._ser = None
        self._rts_inverted = rts_inverted

    def open(self, port, baudrate=9600):
        """Open serial port. 8N1, no flow control."""
        self._ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=INTERBYTE_TIMEOUT,
            write_timeout=1.0,
            rtscts=False,
            dsrdtr=False,
        )
        self._ser.rts = False
        self._ser.dtr = False
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def close(self):
        """Close serial port."""
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._ser = None

    @property
    def is_open(self):
        return self._ser is not None and self._ser.is_open

    def _set_kline(self, high):
        """Set K-Line level via RTS.

        With rts_inverted=True (OBDPlot interface):
          high=True  -> CLRRTS (rts=False)
          high=False -> SETRTS (rts=True)
        """
        if self._rts_inverted:
            self._ser.rts = not high
        else:
            self._ser.rts = high

    def send_5baud_address(self, address):
        """Send ECU address at 5 baud using RTS bit-bang.

        10 bits total: 1 start (LOW) + 8 data LSB-first + 1 stop (HIGH) = 2 seconds.
        """
        # Start bit (LOW)
        self._set_kline(False)
        time.sleep(BIT_TIME_5BAUD)

        # 8 data bits, LSB first
        for i in range(8):
            bit = (address >> i) & 1
            self._set_kline(bool(bit))
            time.sleep(BIT_TIME_5BAUD)

        # Stop bit (HIGH)
        self._set_kline(True)
        time.sleep(BIT_TIME_5BAUD)

        # Purge any garbage in buffers
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def set_baudrate(self, baudrate):
        """Change baudrate after 5-baud init.

        For 8800 baud on macOS with FTDI, uses IOSSIOSPEED ioctl if standard
        method fails.
        """
        try:
            self._ser.baudrate = baudrate
        except (serial.SerialException, OSError):
            if sys.platform == "darwin" and baudrate == 8800:
                self._set_baudrate_macos(baudrate)
            else:
                raise

    def _set_baudrate_macos(self, baudrate):
        """Set non-standard baudrate on macOS via IOSSIOSPEED ioctl."""
        import fcntl
        import termios
        IOSSIOSPEED = 0x80045402
        buf = struct.pack("I", baudrate)
        fcntl.ioctl(self._ser.fd, IOSSIOSPEED, buf)

    def read_byte(self, timeout=None):
        """Read a single byte with optional timeout override.

        Returns byte value (int) or raises KLineTimeoutError.
        """
        if timeout is not None:
            old_timeout = self._ser.timeout
            self._ser.timeout = timeout

        try:
            data = self._ser.read(1)
            if not data:
                raise KLineTimeoutError("Read timeout")
            return data[0]
        finally:
            if timeout is not None:
                self._ser.timeout = old_timeout

    def write_byte(self, b):
        """Write a single byte."""
        self._ser.write(bytes([b & 0xFF]))
        self._ser.flush()

    def send_byte_with_ack(self, b):
        """Send a byte and wait for ECU to return its complement.

        Returns the ACK byte received.
        Raises KLineTimeoutError if no ACK.
        """
        self.write_byte(b)
        ack = self.read_byte(timeout=INTERBYTE_TIMEOUT)
        expected = (~b) & 0xFF
        if ack != expected:
            raise KLineError(
                f"Bad ACK: sent 0x{b:02X}, expected 0x{expected:02X}, got 0x{ack:02X}")
        return ack

    def recv_byte_with_ack(self):
        """Receive a byte and send its complement back.

        Returns the received byte value.
        """
        b = self.read_byte(timeout=INTERBYTE_TIMEOUT)
        complement = (~b) & 0xFF
        self.write_byte(complement)
        return b

    def perform_handshake(self, baudrate):
        """Perform the KWP1281 handshake after 5-baud init.

        1. Wait for sync byte 0x55
        2. Receive keyword1, send ACK
        3. Receive keyword2, wait 30ms, send ACK (~keyword2)

        Returns (keyword1, keyword2) on success.
        Raises KLineError on failure.
        """
        self.set_baudrate(baudrate)

        # Wait for sync 0x55
        sync = self.read_byte(timeout=1.0)
        if sync != 0x55:
            raise KLineError(f"Expected sync 0x55, got 0x{sync:02X}")

        # Receive keyword1, send complement
        kw1 = self.recv_byte_with_ack()

        # Receive keyword2
        kw2 = self.read_byte(timeout=INTERBYTE_TIMEOUT)

        # Wait 30ms before sending keyword2 ACK
        time.sleep(KEYWORD_ACK_DELAY)

        # Send complement of keyword2
        ack = (~kw2) & 0xFF
        self.write_byte(ack)

        return (kw1, kw2)
