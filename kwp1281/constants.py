"""KWP1281 protocol constants - commands, responses, ECU database, timing."""

# ── Block Title: Commands (Tool -> ECU) ──
CMD_GET_ECU_ID   = 0x00
CMD_VALUE_REQ    = 0x01
CMD_CLEAR_FAULTS = 0x05
CMD_END_COMM     = 0x06
CMD_READ_FAULTS  = 0x07
CMD_ADC_READ     = 0x08
CMD_ACK          = 0x09
CMD_ACTUATOR     = 0x10
CMD_BASIC_SET    = 0x28
CMD_READ_GROUP   = 0x29
CMD_LOGIN        = 0x2A
CMD_READ_ADAPT   = 0x2B
CMD_WRITE_ADAPT  = 0x2C

# ── Block Title: Responses (ECU -> Tool) ──
RSP_ACK          = 0x09
RSP_NAK          = 0x0A
RSP_GROUP_DATA   = 0xE7
RSP_ADAPT_RESP   = 0xF4
RSP_ADAPT_WRITE  = 0xF5
RSP_ASCII_ID     = 0xF6
RSP_ADC_RESP     = 0xFB
RSP_FAULT_CODES  = 0xFC
RSP_ADAPT_CHAN   = 0xFD
RSP_BINARY_DATA  = 0xFE

ETX = 0x03
SYNC_BYTE = 0x55

# ── Timing (milliseconds) ──
BIT_TIME_5BAUD       = 0.200   # 200ms per bit at 5 baud
KEYWORD_ACK_DELAY    = 0.030   # 30ms before sending keyword2 ACK
INTERBYTE_TIMEOUT    = 0.100   # 100ms inter-byte timeout
BLOCK_TIMEOUT        = 1.0     # 1s block receive timeout
KEEPALIVE_INTERVAL   = 4.0     # 4s between keep-alive ACKs
INIT_RETRY_TIMEOUT   = 1.0     # 1s before retrying init
ADAPTATION_TIMEOUT   = 60.0    # 60s for adaptation (v4)

# ── ECU Database ──
# (name, address, baudrate)
ECUS = {
    "964": [
        ("Motronic M2.1",  0x10, 8800),
        ("ABS (C4 only)",  0x3D, 4800),
        ("CCU (Climate)",  0x51, 4800),
        ("SRS (Airbag)",   0x57, 9600),
        ("Alarm",          0x40, 9600),
        ("TIP (Tiptronic)",0x29, 4800),
    ],
    "993": [
        ("Motronic M5.2",  0x10, 9600),
        ("ABS",            0x1F, 9600),
        ("CCU (Climate)",  0x51, 4800),
        ("SRS (Airbag)",   0x57, 9600),
        ("Alarm",          0x40, 9600),
        ("TIP (Tiptronic)",0x29, 4800),
    ],
    "965": [
        ("CCU (Climate)",  0x51, 4800),
        ("SRS (Airbag)",   0x57, 9600),
        ("Alarm",          0x40, 9600),
        ("ABS",            0x3D, 4800),
    ],
}

# ECU address -> fault code section(s) per model
FAULT_SECTIONS = {
    "964": {
        0x10: ["M00"],
        0x3D: ["S00"],
        0x51: ["H00", "H03"],
        0x57: ["B02"],
        0x40: ["I00"],
        0x29: ["G00"],
    },
    "993": {
        0x10: ["M04", "M06"],
        0x1F: ["ABS5"],
        0x51: ["H05", "H06", "H08"],
        0x57: ["B02", "B03"],
        0x40: ["I00", "I01"],
        0x29: ["G00"],
    },
    "965": {
        0x51: ["H00", "H03"],
        0x57: ["B02"],
        0x40: ["I00"],
        0x3D: ["S00"],
    },
}

# ── CCU Actuator names (test numbers 1-16) ──
CCU_ACTUATORS = {
    1:  "Fresh Air Servo",
    2:  "Defrost Servo",
    3:  "Footwell Servo",
    4:  "Mixer Servo Left",
    5:  "Mixer Servo Right",
    6:  "Left Heater Blower",
    7:  "Right Heater Blower",
    8:  "Condenser Fan",
    9:  "Oil Cooler Fan",
    10: "Rear Blower Speed 1",
    11: "Rear Blower Speed 2",
    12: "Inside Sensor Blower",
    13: "Actuator 13 (?)",
    14: "Actuator 14 (?)",
    15: "Actuator 15 (?)",
    16: "Actuator 16 (?)",
}

# ── Demo ECU part numbers ──
DEMO_PART_NUMBERS = {
    "964": {0x10: "964.618.124.02", 0x3D: "964.355.755.02", 0x51: "964.624.911.00",
            0x57: "964.618.223.00", 0x40: "964.618.261.00", 0x29: "964.618.901.00"},
    "993": {0x10: "993.618.124.00", 0x1F: "993.355.755.00", 0x51: "993.624.911.00",
            0x57: "993.618.223.00", 0x40: "993.618.261.00", 0x29: "993.618.901.00"},
    "965": {0x51: "965.624.911.00", 0x57: "965.618.223.00", 0x40: "965.618.261.00",
            0x3D: "965.355.755.00"},
}

MAX_INIT_RETRIES = 3
