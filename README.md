# TCPOS Fiscal Printer Interface

A Python-based interface application that bridges TCPOS Point of Sale systems with CTS310ii fiscal printers. The application automatically monitors transaction files from TCPOS and prints them to fiscal printers via serial communication.

## Features

- **Automatic Transaction Monitoring** - Watches a configured folder for new TCPOS transaction XML files
- **Real-time Processing** - Automatically processes and prints transactions as they arrive
- **CTS310ii Support** - Full implementation of the MHI fiscal printer protocol
- **Comprehensive Transaction Handling**:
  - Multiple payment methods (cash, credit card, debit card, cheque, voucher)
  - Item-level and bill-level discounts
  - Service charges and tips
  - Void transactions
  - Tax calculations (supports up to 3 tax rates)
- **System Tray Integration** - Runs as a background service with system tray icon
- **Automatic Time Sync** - Synchronizes printer date/time with system clock
- **Robust Logging** - Detailed logging to both console and file for troubleshooting

## Requirements

- Windows OS (tested on Windows 10/11)
- Python 3.7+ (for development)
- CTS310ii fiscal printer connected via USB/Serial
- TCPOS Point of Sale system version 8.0 or higher

## Installation

### Option 1: Using Pre-built Executable

1. Download the latest release executable
2. Place it in a folder with the `config.json` and `printer.png` files
3. Configure the `config.json` file (see Configuration section)
4. Run the executable

### Option 2: Running from Source

1. Clone the repository:
```bash
git clone <repository-url>
cd bab-tcpos-interface-v251213
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application (see Configuration section)

4. Run the application:
```bash
python fiscal_printer_hub.py
```

## Configuration

Edit the `config.json` file with your settings:

```json
{
    "pos": {
        "name": "tcpos",
        "transactions_folder": "D:\\path\\to\\tcpos\\transactions"
    },
    "printer": {
        "name": "cts310ii"
    },
    "client": {
        "NKF": "1234567890123456789"
    },
    "miscellaneous": {
        "default_client_name": "Regular client",
        "default_client_crib": "1000000000"
    }
}
```

### Configuration Parameters

- **transactions_folder**: Full path to the folder where TCPOS saves transaction XML files
- **NKF**: National Fiscal Key for your business
- **default_client_name**: Default customer name for transactions without customer data
- **default_client_crib**: Default customer CRIB (tax ID) for generic transactions

## Usage

1. **Start the Application**
   - Double-click the executable or run `python fiscal_printer_hub.py`
   - The application will appear in the system tray
   - Check the console or `log.log` file for status messages

2. **Verify Printer Connection**
   - The application automatically detects the CTS310ii printer on available COM ports
   - Check the logs for "Found printer on COMx" message
   - Verify printer fiscal information is configured correctly

3. **Process Transactions**
   - Complete a sale in TCPOS
   - TCPOS will generate an XML file in the configured folder
   - The application automatically detects, parses, and prints the transaction
   - Processed files are renamed with `.processed` extension
   - Failed files are renamed with `.skipped` extension

4. **Monitor Operations**
   - Check `log.log` for detailed operation logs
   - The system tray icon shows the application is running
   - Right-click the tray icon to quit the application

## Building from Source

To create a standalone executable:

```bash
pyinstaller --onefile --icon=printer.ico --noconsole .\fiscal_printer_hub.py
```

The executable will be created in the `dist` folder.

## Printer Configuration

Before first use, ensure your CTS310ii printer is configured with:

- **CRIB** (business tax ID)
- **Business name**
- **Phone number**
- **Address**
- **Tax rates** (typically 6%, 7%, 9%)

The application will alert you if any required fiscal information is missing.

## Supported TCPOS Versions

- TCPOS version 8.0 and higher
- XML transaction format must match TCPOS 8.0+ specification

## Payment Methods Supported

- Cash (00)
- Cheque (01)
- Credit Card (02)
- Debit Card (03)
- Credit Note (04)
- Voucher/Coupon (05)
- Other payment methods (06-09)
- Donations (10)

## Troubleshooting

### Printer Not Found
- Verify the printer is connected via USB/Serial
- Check Device Manager for COM port assignment
- Ensure printer is powered on

### Transactions Not Processing
- Check `transactions_folder` path in `config.json`
- Verify TCPOS is saving XML files to the correct folder
- Check `log.log` for error messages

### Version Error
- Ensure TCPOS is version 8.0 or higher
- Older transaction formats are not supported

### Printer State Errors
- Check printer paper supply
- Verify printer cover is closed
- Ensure no mechanical errors on the printer

## File Structure

```
├── fiscal_printer_hub.py      # Main application entry point
├── tcpos_parser.py             # TCPOS XML parser
├── cts310ii.py                 # CTS310ii printer driver
├── logger_module.py            # Logging configuration
├── config.json                 # Application configuration
├── requirements.txt            # Python dependencies
├── printer.ico                 # Application icon
├── printer.png                 # System tray icon
├── log.log                     # Application logs (generated)
└── version807 xmls/            # Sample transaction files for testing
```

## Technical Details

- **Serial Communication**: 9600 baud, 5-second timeout
- **Protocol**: MHI fiscal printer protocol (see `MHI_Programacion_CW_(EN).pdf`)
- **File Monitoring**: Continuous watchdog with 1-second polling
- **Date/Time Sync**: Automatic if drift exceeds 120 seconds

## License

[Specify your license here]

## Support

For issues and questions:
- Check the `log.log` file for detailed error messages
- Review the sample XML files in `version807 xmls` folder
- Refer to the MHI fiscal printer protocol documentation

## Acknowledgments

Built for integration between TCPOS Point of Sale systems and CTS310ii fiscal printers following Aruban fiscal regulations.
