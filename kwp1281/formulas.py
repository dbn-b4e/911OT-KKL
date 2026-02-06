"""Value conversion formulas for Motronic 964/993 registers, ADC channels, CCU."""


def _temp_f(n):
    """Standard temperature formula: ((n*115)/100) - 26 -> degF."""
    return ((n * 115) / 100) - 26


def _temp_c(n):
    """Standard temperature formula -> degC."""
    return (_temp_f(n) - 32) * 5.0 / 9.0


# ── Motronic 964 (M2.1, 8800 baud) ──
# Register -> (name, formula_fn, unit, format_str)
MOTRONIC_964 = {
    0x37: ("Intake Air Temp",    _temp_c,                               "\u00b0C",  "{:.0f}"),
    0x38: ("Cylinder Head Temp", _temp_c,                               "\u00b0C",  "{:.0f}"),
    0x3A: ("RPM",                lambda n: n * 40,                      "rpm",  "{:.0f}"),
    0x42: ("Injector Time",      lambda n: n * 5,                       "ms",   "{:.1f}"),
    0x45: ("AFM Voltage",        lambda n: (n * 500) / 255,             "V",    "{:.2f}"),
    0x5D: ("Ignition Advance",   lambda n: (((n - 0x68) * 2075) / 255) * -1, "\u00b0", "{:.1f}"),
}

# ── Motronic 993 (M5.2, 9600 baud) ──
MOTRONIC_993 = {
    0x36: ("Battery",            lambda n: (n * 682) / 100,             "V",    "{:.1f}"),
    0x37: ("Intake Air Temp",    _temp_c,                               "\u00b0C",  "{:.0f}"),
    0x38: ("Cylinder Head Temp", _temp_c,                               "\u00b0C",  "{:.0f}"),
    0x39: ("RPM",                lambda n: n * 40,                      "rpm",  "{:.0f}"),
    0x3A: ("Ignition Advance",   lambda n: (n * 1) / 2,                "\u00b0", "{:.1f}"),
    0x3D: ("O2 Sensor",          lambda n: n * 3,                       "mV",   "{:.0f}"),
    0x3E: ("Base Inj 8-bit",     lambda n: n * 50,                      "ms",   "{:.1f}"),
    0x47: ("MAF Voltage",        lambda n: (n * 500) / 255,             "V",    "{:.2f}"),
}

# ── ADC Channels 964 ──
ADC_964 = {
    1: ("MAF Sensor",       lambda n: (n * 500) / 255,   "V",    "{:.2f}"),
    2: ("Battery",          lambda n: (n * 682) / 100,   "V",    "{:.1f}"),
    3: ("NTC 1",            lambda n: n,                  "raw",  "{:.0f}"),
    4: ("NTC 2",            lambda n: n,                  "raw",  "{:.0f}"),
    6: ("O2 Sensor",        lambda n: n,                  "raw",  "{:.0f}"),
    7: ("FQS",              lambda n: (n * 500) / 255,   "V",    "{:.2f}"),
    8: ("MAP Sensor",       lambda n: n,                  "raw",  "{:.0f}"),
}

# ── ADC Channels 993 ──
ADC_993 = {
    1: ("Throttle Angle",   lambda n: (n - 0x1A) * 42,  "\u00b0", "{:.1f}"),
    2: ("Battery",          lambda n: (n * 682) / 100,   "V",    "{:.1f}"),
    4: ("en-sen220-10",     lambda n: n,                  "raw",  "{:.0f}"),
    5: ("MAF Sensor",       lambda n: (n * 500) / 255,   "V",    "{:.2f}"),
    7: ("tipIgTmChg",       lambda n: n * 1,              "\u00b0", "{:.1f}"),
    8: ("O2sen 5-170",      lambda n: n,                  "raw",  "{:.0f}"),
}

# ── CCU 993 Actual Values (ReadGroup registers) ──
CCU_993 = {
    0x02: ("Voltage Term X",         lambda n: n,         "V",    "{:.1f}"),
    0x04: ("Inside Temperature",     _temp_c,             "\u00b0C",  "{:.0f}"),
    0x06: ("Rear Blower Temp",       _temp_c,             "\u00b0C",  "{:.0f}"),
    0x08: ("Lt Mixing Temp",         _temp_c,             "\u00b0C",  "{:.0f}"),
    0x10: ("Rt Mixing Temp",         _temp_c,             "\u00b0C",  "{:.0f}"),
    0x1B: ("Front Oil Cooler Temp",  _temp_c,             "\u00b0C",  "{:.0f}"),
    0x1D: ("Evaporator Temp",        _temp_c,             "\u00b0C",  "{:.0f}"),
}

# ── ABS 993 Actual Values ──
ABS_993 = {
    0x02: ("Stop Light SW",    lambda n: n, "", "{}"),
    0x04: ("Valve Relay",      lambda n: n, "", "{}"),
    0x06: ("Return Pump",      lambda n: n, "", "{}"),
    0x08: ("Speed Vehicle",    lambda n: n, "km/h", "{:.0f}"),
    0x10: ("Front Left",       lambda n: n, "km/h", "{:.0f}"),
    0x1B: ("Front Right",      lambda n: n, "km/h", "{:.0f}"),
    0x1D: ("Rear Left",        lambda n: n, "km/h", "{:.0f}"),
    0x1F: ("Rear Right",       lambda n: n, "km/h", "{:.0f}"),
}

# ── Default live data params per model/ECU for GUI ──
# (name, register, formula_fn, min_display, max_display, unit, fmt)
LIVE_PARAMS = {
    ("964", 0x10): [
        ("RPM",           0x3A, lambda n: n * 40,                       0, 7000, "rpm",  "{:.0f}"),
        ("Head Temp",     0x38, _temp_c,                                0, 130,  "\u00b0C",  "{:.0f}"),
        ("Intake Temp",   0x37, _temp_c,                                0, 100,  "\u00b0C",  "{:.0f}"),
        ("AFM Voltage",   0x45, lambda n: (n * 500) / 255,             0, 5.0,  "V",    "{:.2f}"),
        ("Injector Time", 0x42, lambda n: n * 5,                       0, 20.0, "ms",   "{:.1f}"),
        ("Timing",        0x5D, lambda n: (((n - 0x68) * 2075) / 255) * -1, 0, 50, "\u00b0", "{:.1f}"),
    ],
    ("993", 0x10): [
        ("RPM",           0x39, lambda n: n * 40,                       0, 7000, "rpm",  "{:.0f}"),
        ("Head Temp",     0x38, _temp_c,                                0, 130,  "\u00b0C",  "{:.0f}"),
        ("Intake Temp",   0x37, _temp_c,                                0, 100,  "\u00b0C",  "{:.0f}"),
        ("Battery",       0x36, lambda n: (n * 682) / 100,             10, 16,   "V",    "{:.1f}"),
        ("O2 Sensor",     0x3D, lambda n: n * 3,                       0, 1000,  "mV",   "{:.0f}"),
        ("MAF Voltage",   0x47, lambda n: (n * 500) / 255,             0, 5.0,  "V",    "{:.2f}"),
    ],
}

# Default params for ECUs without specific live data (used for demo)
LIVE_PARAMS_GENERIC = [
    ("Value 1", 0x01, lambda n: n, 0, 255, "raw", "{:.0f}"),
    ("Value 2", 0x02, lambda n: n, 0, 255, "raw", "{:.0f}"),
]


def get_live_params(model, ecu_address):
    """Get live data parameter definitions for a model/ECU combo."""
    return LIVE_PARAMS.get((model, ecu_address), LIVE_PARAMS_GENERIC)


def convert_value(register, raw_byte, model="964"):
    """Convert a raw register byte to a human-readable value.

    Returns (name, value, unit, formatted_str) or None if register unknown.
    """
    if model == "964":
        reg_map = MOTRONIC_964
    elif model == "993":
        reg_map = MOTRONIC_993
    else:
        return None

    if register not in reg_map:
        return None

    name, formula, unit, fmt = reg_map[register]
    value = formula(raw_byte)
    return (name, value, unit, fmt.format(value))


def convert_adc(channel, raw_value, model="964"):
    """Convert a raw ADC channel value.

    Returns (name, value, unit, formatted_str) or None.
    """
    adc_map = ADC_964 if model == "964" else ADC_993
    if channel not in adc_map:
        return None

    name, formula, unit, fmt = adc_map[channel]
    value = formula(raw_value)
    return (name, value, unit, fmt.format(value))
