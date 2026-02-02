# 911OT-KKL

Open source K-Line OBD diagnostic tool for Porsche 964 and 993.

## Overview

This project provides complete documentation and tools for building an ESP32-based diagnostic scanner for air-cooled Porsche 911 (964 and 993 models) using the K-Line (ISO 9141) protocol.

## Features

- **Complete protocol documentation** - KWP1281 reverse engineered from ScanTool v3/v4
- **All ECU addresses** - Motronic, ABS, CCU, SRS, Alarm, Tiptronic
- **Fault codes database** - Complete DTC descriptions for all modules
- **Hardware schematics** - Using dedicated K-Line ICs (L9637D, SN65HVDA195)
- **ESP32 implementation guide** - Ready-to-use code examples

## Supported Vehicles

| Model | Years | Motronic | Notes |
|-------|-------|----------|-------|
| 964 Carrera | 1989-1994 | 8800 baud | Full support |
| 964 Turbo (965) | 1991-1994 | N/A | ABS/CCU/SRS only (no K-Line on engine) |
| 993 | 1995-1998 | 9600 baud | Drive Block workaround included |

## Key Differences 964 vs 993

| Module | 964 | 993 |
|--------|-----|-----|
| Motronic | 0x10 @ 8800 | 0x10 @ 9600 |
| ABS | 0x3D @ 4800 | 0x1F @ 9600 |

## Hardware Requirements

### K-Line Interface IC (choose one)
- **L9637D** (STMicroelectronics) - Recommended, ~1€
- **SN65HVDA195** (Texas Instruments) - Modern, better ESD protection
- **MC33290/MC33660** (NXP) - Classic choice

### Warning
Standard ELM327/KKL adapters **DO NOT WORK** with this protocol due to:
- Non-standard baud rate (8800)
- 5-baud init via RTS line
- Inter-byte ACK protocol

## Documentation

See [porsche_964_kline_reverse_engineering.md](porsche_964_kline_reverse_engineering.md) for complete protocol documentation including:
- ECU addresses and baud rates
- KWP1281 block format
- All fault codes
- Hardware schematics
- ESP32 code examples

## Quick Start

```c
// ESP32 - Connect to Motronic 964
#define ECU_MOTRONIC 0x10
#define BAUD_964     8800

send_5baud_address(ECU_MOTRONIC);  // 2 seconds
kwp1281_handshake(BAUD_964);       // Sync + keywords
kwp1281_send_block(0x07, NULL, 0); // Read fault codes
```

## Related Projects

- [OBD2_KLine_Library](https://github.com/muki01/OBD2_KLine_Library) - ESP32 K-Line library
- [VAG_KW1281](https://github.com/muki01/VAG_KW1281) - Similar KWP1281 protocol
- [OBD9141](https://github.com/iwanders/OBD9141) - ISO 9141 library

## Credits

- **Doug Boyce** - Original ScanTool software author
- **BERGVILL F/X** - T-OBD hardware and documentation
- **Rennlist community** - Protocol research and testing

## License

PolyForm Noncommercial License 1.0.0 - See [LICENSE](LICENSE)

**Non-commercial use only.** Personal, educational, and research use permitted.

## Disclaimer

This project is for educational and personal use. Use at your own risk. The authors are not responsible for any damage to vehicles or equipment.
