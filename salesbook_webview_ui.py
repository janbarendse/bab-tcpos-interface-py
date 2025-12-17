"""
Fiscal Tools UI using pywebview - Modern HTML interface for BAB PrintHub
Opens from system tray icon - provides full salesbook functionality
"""

import json
import os
import datetime
from logger_module import logger
import cts310ii


CONFIG_FILE = "config.json"


def load_config():
    """Load configuration from bridge config.json"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    default_fiscal_tools = {
        "Z_report_from": today,
        "last_z_report_print_time": None
    }

    if not os.path.exists(CONFIG_FILE):
        logger.error(f"Config file not found: {CONFIG_FILE}")
        return {"fiscal_tools": default_fiscal_tools}

    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = json.load(f)

        # Ensure fiscal_tools section exists
        if "fiscal_tools" not in config:
            config["fiscal_tools"] = default_fiscal_tools
            save_config(config)

        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {"fiscal_tools": default_fiscal_tools}


def save_config(config):
    """Save configuration to bridge config.json"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {e}")


class FiscalToolsAPI:
    """JavaScript API bridge for fiscal printer operations"""

    def __init__(self):
        self.config = load_config()
        self.window = None  # Set after window creation

    def print_x_report(self):
        """Generate X report"""
        try:
            logger.info("X-Report triggered from webview UI")
            response = cts310ii.print_x_report()
            if response.get("success"):
                logger.info("X-Report printed successfully")
                return {"success": True, "message": "X Report printed successfully"}
            else:
                logger.warning(f"X-Report failed: {response.get('error')}")
                return {"success": False, "error": response.get("error", "Failed to print X Report")}
        except Exception as e:
            logger.error(f"Error printing X-Report: {e}")
            return {"success": False, "error": str(e)}

    def print_z_report(self):
        """Print Z report and close fiscal day"""
        try:
            logger.info("Z-Report (Close Fiscal Day) triggered from webview UI")

            # Send command to printer with close_fiscal_day=True
            # This closes the fiscal period and prints the Z-report
            response = cts310ii.print_z_report(close_fiscal_day=True)

            if response.get("success"):
                logger.info("Z-Report printed successfully (fiscal day closed)")
                return {"success": True, "message": "Z Report printed - Fiscal day closed"}
            else:
                logger.warning(f"Z-Report response: {response.get('error', 'Unknown error')}")
                return {"success": False, "error": response.get('error', 'Failed to print Z Report')}
        except Exception as e:
            logger.error(f"Error printing Z-Report: {e}")
            return {"success": False, "error": str(e)}

    def print_z_report_by_date(self, start_date, end_date):
        """Generate Z reports by date range"""
        try:
            logger.info(f"Z-Report by date range triggered: {start_date} to {end_date}")

            # Convert string dates to date objects
            start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

            response = cts310ii.print_z_report_by_date(start_date_obj, end_date_obj)

            if response.get("success"):
                logger.info("Z-Reports by date printed successfully")
                return {"success": True, "message": response.get("message", "Z Reports printed")}
            else:
                logger.warning(f"Z-Reports by date failed: {response.get('error')}")
                return {"success": False, "error": response.get("error", "Failed to print Z Reports")}
        except Exception as e:
            logger.error(f"Error printing Z-Reports by date: {e}")
            return {"success": False, "error": str(e)}

    def print_z_report_by_number(self, number):
        """Generate Z report by number"""
        try:
            logger.info(f"Z-Report by number triggered: {number}")
            response = cts310ii.print_z_report_by_number(int(number))

            if response.get("success"):
                logger.info("Z-Report by number printed successfully")
                return {"success": True, "message": response.get("message", "Z Report printed")}
            else:
                logger.warning(f"Z-Report by number failed: {response.get('error')}")
                return {"success": False, "error": response.get("error", "Failed to print Z Report")}
        except Exception as e:
            logger.error(f"Error printing Z-Report by number: {e}")
            return {"success": False, "error": str(e)}

    def print_z_report_by_number_range(self, start_number, end_number):
        """Generate Z reports by number range"""
        try:
            logger.info(f"Z-Report by number range triggered: {start_number} to {end_number}")

            start_num = int(start_number)
            end_num = int(end_number)

            if start_num > end_num:
                return {"success": False, "error": "Start number must be less than or equal to end number"}

            response = cts310ii.print_z_report_by_number_range(start_num, end_num)

            if response.get("success"):
                logger.info("Z-Reports by number range printed successfully")
                return {"success": True, "message": response.get("message", "Z Reports printed")}
            else:
                logger.warning(f"Z-Reports by number range failed: {response.get('error')}")
                return {"success": False, "error": response.get("error", "Failed to print Z Reports")}
        except Exception as e:
            logger.error(f"Error printing Z-Reports by number range: {e}")
            return {"success": False, "error": str(e)}

    def reprint_document(self, doc_number):
        """Re-print ticket by number (NO SALE - copy only)"""
        try:
            logger.info(f"Reprint document triggered: {doc_number}")
            response = cts310ii.reprint_document(str(doc_number))

            if response.get("success"):
                logger.info("Document reprinted successfully")
                return {"success": True, "message": response.get("message", "Document re-printed")}
            else:
                logger.warning(f"Reprint document failed: {response.get('error')}")
                return {"success": False, "error": response.get("error", "Failed to re-print document")}
        except Exception as e:
            logger.error(f"Error reprinting document: {e}")
            return {"success": False, "error": str(e)}

    def get_config(self):
        """Return fiscal_tools config section"""
        return self.config.get("fiscal_tools", {})

    def get_min_date(self):
        """Return Z_report_from date"""
        return self.config.get("fiscal_tools", {}).get("Z_report_from", datetime.date.today().strftime("%Y-%m-%d"))

    def close_window(self):
        """Close the modal window"""
        if self.window:
            self.window.destroy()


# HTML Template - embedded for easier packaging
HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAB Fiscal PrintHub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        body {
            font-family: 'Inter', sans-serif;
        }
    </style>
</head>
<body class="bg-gray-100 p-3">
    <div class="bg-white rounded-2xl shadow-2xl max-w-4xl mx-auto">

        <!-- Header with Logo -->
        <div class="bg-gradient-to-r from-red-700 to-red-800 p-4 rounded-t-2xl">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <div class="bg-white p-3 rounded-lg shadow-lg">
                        <div class="text-center">
                            <div class="text-red-700 font-black text-2xl leading-none">SOLU</div>
                            <div class="bg-gray-800 text-white font-black text-xl px-2 py-1 mt-1 rounded">TECH</div>
                            <div class="text-gray-800 font-bold text-xs mt-1">BAB REPORTING</div>
                        </div>
                    </div>
                    <div>
                        <h1 class="text-2xl font-bold text-white">Fiscal PrintHub</h1>
                        <p class="text-red-100 text-sm">Quick Report Generation</p>
                    </div>
                </div>

                <!-- Receipt Copy in Header -->
                <div class="bg-white/10 backdrop-blur-sm rounded-xl p-3 border border-white/20">
                    <p class="text-xs text-white/90 mb-2 font-semibold">Receipt Copy</p>
                    <div class="flex gap-2">
                        <input type="text" id="check-number" class="w-32 p-2 border-0 rounded-lg text-sm" placeholder="Doc #">
                        <button onclick="printCheckCopy()" class="bg-white text-red-700 hover:bg-red-50 font-semibold px-4 py-2 rounded-lg transition duration-150 text-sm whitespace-nowrap">
                            Print Copy
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="p-4 space-y-4">

            <!-- Primary Actions - Today's Reports -->
            <div class="space-y-3">
                <h2 class="text-lg font-bold text-gray-800 pb-2">Today's Reports</h2>

                <!-- Desktop: side by side, Mobile: stacked -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <!-- Z Report - Most Important -->
                    <div class="bg-red-50 border-2 border-red-600 rounded-xl p-4 shadow-md flex flex-col">
                        <div class="mb-3 flex-grow">
                            <h3 class="text-xl font-bold text-red-800 mb-1">Z Report (Today)</h3>
                            <p class="text-sm text-gray-600">Closes the fiscal day and prints the Z Report. Printer will only print if there are transactions.</p>
                        </div>
                        <button id="z-report-btn" onclick="printZReport()" class="w-full bg-red-700 hover:bg-red-800 text-white font-bold py-4 rounded-lg transition duration-150 shadow-lg hover:shadow-xl transform hover:scale-[1.02] mt-auto">
                            <span class="text-lg">Close Fiscal Day - Z Report</span>
                        </button>
                    </div>

                    <!-- X Report -->
                    <div class="bg-gray-50 border-2 border-gray-400 rounded-xl p-4 shadow-md flex flex-col">
                        <div class="mb-3 flex-grow">
                            <h3 class="text-lg font-bold text-gray-800 mb-1">X Report (Today)</h3>
                            <p class="text-sm text-gray-600">Current shift status without closing the fiscal day.</p>
                        </div>
                        <button onclick="printXReport()" class="w-full bg-gray-700 hover:bg-gray-800 text-white font-bold py-4 rounded-lg transition duration-150 shadow-md hover:shadow-lg mt-auto">
                            <span class="text-lg">Print X Report</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Historical Reports -->
            <div class="space-y-3">
                <h2 class="text-lg font-bold text-gray-800 pb-2">Historical Reports</h2>

                <!-- Desktop: side by side, Mobile: stacked -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <!-- Date Range -->
                    <div class="bg-white border border-gray-300 rounded-xl p-4 shadow-sm">
                        <label class="block text-sm font-bold text-gray-700 mb-3">Z Reports by Date Range</label>
                        <div class="space-y-3">
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">From</label>
                                    <input type="date" id="start-date" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm">
                                </div>
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">To</label>
                                    <input type="date" id="end-date" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm">
                                </div>
                            </div>
                            <button onclick="printZByDateRange()" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2.5 rounded-lg transition duration-150 shadow-md text-sm">
                                Print Date Range
                            </button>
                        </div>
                    </div>

                    <!-- Number Range -->
                    <div class="bg-white border border-gray-300 rounded-xl p-4 shadow-sm">
                        <label class="block text-sm font-bold text-gray-700 mb-3">Z Reports by Number Range</label>
                        <div class="space-y-3">
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">Start #</label>
                                    <input type="number" id="start-number" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm" placeholder="100" min="1">
                                </div>
                                <div>
                                    <label class="block text-xs font-medium text-gray-600 mb-1">End #</label>
                                    <input type="number" id="end-number" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm" placeholder="150" min="1">
                                </div>
                            </div>
                            <button onclick="printZByNumberRange()" class="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2.5 rounded-lg transition duration-150 shadow-md text-sm">
                                Print Number Range
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Status Display -->
            <div id="status-message" class="hidden p-4 rounded-lg text-sm font-medium"></div>
        </div>

        <!-- Footer -->
        <div class="bg-gray-50 px-4 py-3 rounded-b-2xl border-t border-gray-200">
            <button onclick="closeModal()" class="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2.5 rounded-lg transition duration-150">
                Close
            </button>
        </div>
    </div>

    <script>
        // Status message helper
        function showStatus(message, type = 'info') {
            const statusEl = document.getElementById('status-message');
            statusEl.classList.remove('hidden', 'bg-green-100', 'text-green-800', 'bg-red-100', 'text-red-800', 'bg-blue-100', 'text-blue-800');

            if (type === 'success') {
                statusEl.classList.add('bg-green-100', 'text-green-800');
            } else if (type === 'error') {
                statusEl.classList.add('bg-red-100', 'text-red-800');
            } else {
                statusEl.classList.add('bg-blue-100', 'text-blue-800');
            }

            statusEl.textContent = message;

            setTimeout(() => {
                statusEl.classList.add('hidden');
            }, 5000);
        }

        // Initialize on load
        window.addEventListener('pywebviewready', function() {
            initializeUI();
        });

        async function initializeUI() {
            try {
                const config = await pywebview.api.get_config();
                const minDate = await pywebview.api.get_min_date();

                // Set date constraints
                const today = new Date().toISOString().split('T')[0];
                const yesterday = new Date();
                yesterday.setDate(yesterday.getDate() - 1);
                const yesterdayStr = yesterday.toISOString().split('T')[0];

                document.getElementById('start-date').min = minDate;
                document.getElementById('start-date').max = yesterdayStr;
                document.getElementById('start-date').value = yesterdayStr;

                document.getElementById('end-date').min = minDate;
                document.getElementById('end-date').max = yesterdayStr;
                document.getElementById('end-date').value = yesterdayStr;
            } catch (error) {
                console.error('Error initializing UI:', error);
                showStatus('Error loading configuration', 'error');
            }
        }

        // Main functions
        async function printZReport() {
            showStatus('Processing Z Report (closing fiscal day)...', 'info');
            try {
                const result = await pywebview.api.print_z_report();
                if (result.success) {
                    showStatus('✓ ' + result.message, 'success');
                } else {
                    showStatus('✗ ' + result.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error, 'error');
            }
        }

        async function printXReport() {
            showStatus('Processing X Report...', 'info');
            try {
                const result = await pywebview.api.print_x_report();
                if (result.success) {
                    showStatus('✓ ' + result.message, 'success');
                } else {
                    showStatus('✗ ' + result.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error, 'error');
            }
        }

        async function printZByDateRange() {
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;

            if (!startDate || !endDate) {
                showStatus('Please select both start and end dates.', 'error');
                return;
            }

            showStatus(`Processing Z Reports from ${startDate} to ${endDate}...`, 'info');
            try {
                const result = await pywebview.api.print_z_report_by_date(startDate, endDate);
                if (result.success) {
                    showStatus('✓ ' + result.message, 'success');
                } else {
                    showStatus('✗ ' + result.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error, 'error');
            }
        }

        async function printZByNumberRange() {
            const startNum = document.getElementById('start-number').value;
            const endNum = document.getElementById('end-number').value;

            if (!startNum || !endNum) {
                showStatus('Please enter both start and end numbers.', 'error');
                return;
            }

            showStatus(`Processing Z Reports #${startNum} to #${endNum}...`, 'info');
            try {
                const result = await pywebview.api.print_z_report_by_number_range(startNum, endNum);
                if (result.success) {
                    showStatus('✓ ' + result.message, 'success');
                } else {
                    showStatus('✗ ' + result.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error, 'error');
            }
        }

        async function printCheckCopy() {
            const checkNumber = document.getElementById('check-number').value.trim();

            if (!checkNumber) {
                showStatus('Document number is required.', 'error');
                return;
            }

            showStatus(`Printing copy of document ${checkNumber}...`, 'info');
            try {
                const result = await pywebview.api.reprint_document(checkNumber);
                if (result.success) {
                    showStatus('✓ ' + result.message, 'success');
                } else {
                    showStatus('✗ ' + result.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error, 'error');
            }
        }

        function closeModal() {
            pywebview.api.close_window();
        }
    </script>
</body>
</html>
'''
