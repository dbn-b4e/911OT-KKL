"""DTC database parsed from ScanTool Trouble Codes files."""

import os
import re

# Fault code database: section -> {code_str: description}
_DB = {}

# Data directory relative to this file
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "T_OBD_extracted")

_FILES = [
    "Trouble Codes 964.txt",
    "Trouble Codes 993.txt",
]


def _parse_trouble_codes_file(filepath):
    """Parse a ScanTool Trouble Codes file into sections."""
    codes = {}
    current_section = None

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";"):
                    continue

                # Section header: [S00], [M00], etc.
                m = re.match(r"^\[([A-Z0-9]+)\]$", line)
                if m:
                    current_section = m.group(1)
                    if current_section == "Trouble Code Descriptions":
                        current_section = None
                        continue
                    if current_section not in codes:
                        codes[current_section] = {}
                    continue

                if current_section is None:
                    continue

                # Code=Description or Code = Description (with possible unicode separator)
                # Handle both "11=Description" and "11 \x96 Description" formats
                m = re.match(r"^(\d+)\s*[=\x96]\s*(.+)$", line)
                if m:
                    code_str = m.group(1).strip()
                    desc = m.group(2).strip()
                    if desc:
                        codes[current_section][code_str] = desc
    except FileNotFoundError:
        pass

    return codes


def _load_database():
    """Load all trouble code files into the database."""
    global _DB
    if _DB:
        return

    for fname in _FILES:
        path = os.path.join(_DATA_DIR, fname)
        parsed = _parse_trouble_codes_file(path)
        for section, entries in parsed.items():
            if section not in _DB:
                _DB[section] = {}
            _DB[section].update(entries)


def lookup(section, code):
    """Look up a fault code description.

    Args:
        section: Fault code section (e.g. "M00", "S00", "H05")
        code: Fault code number as int or string

    Returns:
        Description string or "Unknown fault code XX"
    """
    _load_database()
    code_str = str(int(code)) if isinstance(code, int) else str(code).strip()
    if section in _DB and code_str in _DB[section]:
        return _DB[section][code_str]
    return f"Unknown fault code {code_str}"


def lookup_for_ecu(model, ecu_address, code):
    """Look up fault code trying all sections for a given ECU.

    Args:
        model: "964", "993", or "965"
        ecu_address: ECU address byte (e.g. 0x10)
        code: Fault code number

    Returns:
        Description string
    """
    from .constants import FAULT_SECTIONS
    _load_database()

    sections = FAULT_SECTIONS.get(model, {}).get(ecu_address, [])
    code_str = str(int(code)) if isinstance(code, int) else str(code).strip()

    for section in sections:
        if section in _DB and code_str in _DB[section]:
            return _DB[section][code_str]

    return f"Unknown fault code {code_str}"


def get_all_sections():
    """Return dict of all loaded sections and their codes."""
    _load_database()
    return dict(_DB)


def get_section_codes(section):
    """Return dict of {code_str: description} for a section."""
    _load_database()
    return dict(_DB.get(section, {}))
