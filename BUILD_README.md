# BAB PrintHub - Build & Deployment Guide

## 📦 Build Information

**Executable:** `dist\BAB_PrintHub.exe`
**Size:** ~21 MB (includes all dependencies)
**Build Tool:** PyInstaller 6.10.0
**Python Version:** 3.13.7

## 🔨 Building the Executable

### Quick Build
Run `build.bat` to compile the application:
```batch
build.bat
```

This will:
- Clean previous build artifacts
- Compile `fiscal_printer_hub.py` into a standalone executable
- Include all dependencies (pywebview, pystray, Pillow, pyserial, etc.)
- Embed `logo.png` and `config.json` as resources
- Create `dist\BAB_PrintHub.exe`

### Build Process Details
The build script uses PyInstaller with the following options:
- `--onefile` - Single executable file
- `--noconsole` - No console window (Windows GUI app)
- `--icon=logo.png` - Application icon
- `--add-data` - Embed logo.png and config.json
- `--hidden-import` - Include pywebview and pythonnet modules
- `--collect-all` - Collect all pywebview and bottle files

### Build Requirements
- Python 3.x
- PyInstaller (`pip install pyinstaller`)
- All dependencies in `requirements.txt`

## 💾 Installing on Other Machines

### Using setup.bat (Recommended)

1. **Copy files to target machine:**
   - `dist\BAB_PrintHub.exe`
   - `logo.png`
   - `config.json`
   - `setup.bat`

2. **Run setup.bat as Administrator:**
   ```batch
   Right-click setup.bat → Run as Administrator
   ```

3. **Follow the prompts:**
   - Default installation: `C:\Program Files\BAB PrintHub`
   - Or choose a custom directory
   - Setup will create desktop and Start Menu shortcuts

### Manual Installation

1. **Create installation folder:**
   ```batch
   mkdir "C:\Program Files\BAB PrintHub"
   ```

2. **Copy files:**
   ```batch
   copy BAB_PrintHub.exe "C:\Program Files\BAB PrintHub\"
   copy logo.png "C:\Program Files\BAB PrintHub\"
   copy config.json "C:\Program Files\BAB PrintHub\"
   ```

3. **Create shortcuts manually** (optional)

## ⚙️ Configuration

### Before First Run

Edit `config.json` in the installation directory:

```json
{
  "pos": {
    "name": "tcpos",
    "transactions_folder": "C:\\TCPOS.NET\\TCPOSBKDEMO807\\FrontEnd\\Transactions"
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
  },
  "fiscal_tools": {
    "Z_report_from": "2024-01-01",
    "last_z_report_print_time": null
  }
}
```

**Important:**
1. Update `transactions_folder` to match your TCPOS installation path
2. Update `NKF` with your business fiscal number
3. Update `default_client_crib` with default client ID
4. Set `Z_report_from` to your desired historical report start date

## 🚀 Running the Application

### From Installation
- **Desktop:** Double-click "BAB PrintHub" shortcut
- **Start Menu:** Programs → BAB PrintHub → BAB PrintHub
- **Direct:** Navigate to installation folder and run `BAB_PrintHub.exe`

### System Tray
The application runs in the system tray (bottom-right corner of taskbar).

**Right-click the icon to access:**
- **Fiscal Tools** - Opens modern HTML modal for report management
- **Print X-Report** - Quick print current shift report
- **Print Z-Report** - Quick print fiscal day closure report
- **Quit BAB PrintHub** - Exit the application

### Fiscal Tools Modal
Click "Fiscal Tools" to open the comprehensive UI:
- **Today's Reports:**
  - X Report (Today) - Current shift without closing
  - Z Report (Today) - Close fiscal day (⚠️ irreversible)
- **Historical Reports:**
  - Z Reports by Date Range
  - Z Reports by Number Range
- **Receipt Copy** - Reprint any document by number

## 🖨️ Printer Requirements

### CTS310ii Fiscal Printer
- Connect via USB or Serial port
- Ensure printer is powered on before starting application
- Driver installation not required (uses serial communication)

### First-Time Setup
On first run, the application will:
1. Search for the printer on available COM ports
2. Synchronize printer date/time (if needed)
3. Display printer status in system tray

## 📋 System Requirements

### Target Machine Requirements
- **OS:** Windows 10/11 (64-bit)
- **RAM:** 100 MB available
- **Disk:** 50 MB free space
- **Ports:** USB or Serial port for fiscal printer
- **.NET Framework:** Not required (embedded)
- **Python:** Not required (standalone executable)

### Dependencies (Included in Executable)
All dependencies are bundled - no installation needed:
- Python 3.13 runtime
- PyWebView 6.1 (Edge WebView2 or IE fallback)
- Pystray 0.19.5
- Pillow 10.4.0
- PySerial 3.5
- PythonNet 3.0.5
- Bottle 0.13.4
- XML parsing libraries

## 🔧 Troubleshooting

### Application Won't Start
1. **Check config.json** - Ensure valid JSON syntax
2. **Check permissions** - Run as Administrator if in Program Files
3. **Check Event Viewer** - Windows Logs → Application

### Printer Not Found
1. **Verify connection** - Check USB/Serial cable
2. **Check COM ports** - Device Manager → Ports (COM & LPT)
3. **Restart printer** - Power cycle the fiscal printer
4. **Check logs** - Review `log.log` in application folder

### Modal Won't Open
1. **WebView2 missing** - Install Microsoft Edge (comes with Windows 11)
2. **Permissions** - Allow application through Windows Firewall
3. **Antivirus** - Whitelist BAB_PrintHub.exe

### Reports Not Printing
1. **Printer state** - Ensure not in error state
2. **Paper** - Check printer has paper
3. **Fiscal memory** - Ensure printer fiscal memory not full
4. **Date/time** - Verify printer date/time is correct

## 📁 File Structure

### Development
```
managedcode/
├── fiscal_printer_hub.py       # Main application
├── cts310ii.py                  # Printer driver
├── salesbook_webview_ui.py      # Modal UI
├── tcpos_parser.py              # TCPOS XML parser
├── logger_module.py             # Logging
├── config.json                  # Configuration
├── logo.png                     # Application icon
├── requirements.txt             # Dependencies
├── build.bat                    # Build script
├── setup.bat                    # Installation script
└── BUILD_README.md              # This file
```

### Build Output
```
build/                           # Build artifacts (temporary)
├── BAB_PrintHub/
└── ...

dist/                            # Distribution
└── BAB_PrintHub.exe             # Final executable (21 MB)

BAB_PrintHub.spec                # PyInstaller specification
```

### Installation
```
C:\Program Files\BAB PrintHub\
├── BAB_PrintHub.exe
├── logo.png
├── config.json
└── log.log                      # Created at runtime
```

## 🔄 Updating

### To update on an existing installation:

1. **Build new version** using `build.bat`
2. **Stop the running application** (Right-click tray → Quit)
3. **Run setup.bat** (it preserves existing config.json)
4. **Start the application**

**Note:** setup.bat automatically preserves your existing `config.json` to avoid losing configuration.

## 📝 Changelog

### Version 1.0 - Initial Release
- ✅ TCPOS XML transaction processing
- ✅ Fiscal printer integration (CTS310ii)
- ✅ System tray with logo.png icon
- ✅ PyWebView modal UI
- ✅ X-Report and Z-Report generation
- ✅ Historical report queries (date/number range)
- ✅ Document reprint functionality
- ✅ Real-time status feedback
- ✅ Duplicate Z-report prevention

## 🆘 Support

For issues or questions:
1. Check `log.log` in the application folder
2. Review this README
3. Contact: support@solutech.com (example)

## 📄 License

Proprietary - Solutech BAB PrintHub
All rights reserved.
