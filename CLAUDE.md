# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based fiscal printer interface that bridges TCPOS (Point of Sale system) and CTS310ii fiscal printers. The application monitors a folder for XML transaction files from TCPOS, parses them, and sends formatted fiscal documents to the printer via serial communication.

## Architecture

### Core Components

**fiscal_printer_hub.py** - Main application entry point
- Loads configuration from `config.json`
- Initializes the printer connection (currently only supports CTS310ii)
- Starts a watchdog thread to monitor TCPOS transaction files
- Runs a system tray icon for the application

**tcpos_parser.py** - TCPOS XML transaction parser
- Monitors a configured folder for `.xml` transaction files
- Parses TCPOS v8.0+ XML format into printer-compatible data structures
- Extracts items, payments, service charges, tips, and discounts
- Handles both single and multiple items/payments in transactions
- Renames processed files with `.processed` or `.skipped` extensions

**cts310ii.py** - CTS310ii fiscal printer driver
- Implements the MHI fiscal printer protocol (see MHI_Programacion_CW_(EN).pdf)
- Handles serial communication with the printer
- Manages printer state machine (standby, sale, payment, etc.)
- Encodes commands in hex format with STX/ETX/ACK/NAK control characters
- Provides functions to: prepare documents, add items, apply discounts/service charges, process payments, close documents

**logger_module.py** - Centralized logging
- Logs to both console and `log.log` file
- Default level: INFO

### Data Flow

1. TCPOS creates XML transaction file in configured folder
2. `tcpos_parser.files_watchdog()` detects the new XML file
3. Parser extracts items, payments, service charges, and tips
4. Parser calls `cts310ii.print_document()` with parsed data
5. Printer driver sends serial commands to CTS310ii device
6. File is renamed to `.processed` or `.skipped` based on outcome

### Configuration

`config.json` structure:
```json
{
    "pos": {
        "name": "tcpos",
        "transactions_folder": "path/to/xml/folder"
    },
    "printer": {
        "name": "cts310ii"
    },
    "client": {
        "NKF": "client fiscal number"
    },
    "miscellaneous": {
        "default_client_name": "Regular client",
        "default_client_crib": "1000000000"
    }
}
```

## Common Commands

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application directly
python fiscal_printer_hub.py

# Build executable
pyinstaller --onefile --icon=printer.ico --noconsole .\fiscal_printer_hub.py
```

### Testing

The `version807 xmls` folder contains sample transaction XML files for testing various scenarios:
- Cash/credit/debit card payments
- Discounts (item-level and whole bill)
- Service charges and tips
- Void transactions
- Cheques and coupons

## Key Implementation Details

### Tax Mapping

The system maps TCPOS VAT percentages to printer tax IDs:
- 6% → Tax ID 1
- 7% → Tax ID 2
- 9% → Tax ID 3

### Number Encoding

Amounts and quantities are encoded as strings without decimal points:
- `"2000"` = 2.000 (3 decimal places for quantities)
- `"155"` = 1.55 (2 decimal places for prices)

### Serial Communication

- Baud rate: 9600
- Timeout: 5 seconds
- Auto-detects printer on available COM ports
- Commands use hex encoding with field separator (FS = 0x1C)

### Printer State Machine

The CTS310ii has specific states that must be followed:
1. Standby (0) → Start of sale (1)
2. Sale (2) → Add items
3. Subtotal (3) → Calculate subtotal
4. Payment (4) → Process payments
5. End of sale (5) → Close document

### Date/Time Synchronization

On startup, the application checks if the printer's datetime differs by more than 120 seconds from system time. If so, it synchronizes the printer's clock.

## Important Notes

- Only TCPOS version 8.0+ XML format is supported
- The application cancels any open document before starting a new one
- Tips are identified by `shortDescription` field values "Tip" or "Tip %"
- Service charges are currently disabled (line 326: `service_charge = None`)
- The application runs as a background service with a system tray icon
- Printer fiscal information (CRIB, business name, tax rates) must be pre-configured on the device

## Troubleshooting

Check `log.log` for detailed operation logs. Common issues:
- Printer not found: Verify USB/serial connection
- Unsupported version: XML file is from TCPOS < v8.0
- Command failures: Check printer state and paper status
- Parse errors: Verify XML structure matches expected TCPOS format
