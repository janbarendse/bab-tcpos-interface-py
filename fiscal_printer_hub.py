import threading
import time
import json
import os
import sys
import queue
from logger_module import logger
from pystray import Menu as menu, MenuItem as item
import pystray
from PIL import Image, ImageDraw

# Queue for main thread communication
modal_queue = queue.Queue()

# Pre-import webview at startup for faster modal opening
try:
    import webview
    logger.info("Webview module pre-loaded for faster UI")
except Exception as e:
    logger.warning(f"Could not pre-load webview module: {e}")


if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)

elif __file__:
    base_dir = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(base_dir, 'config.json')) as json_file:
        return json.load(json_file)


def close_app():
    os._exit(0)


def print_x_report_menu():
    """Handler for Print X-Report menu item"""
    try:
        logger.info("X-Report triggered from tray menu")
        import cts310ii
        result = cts310ii.print_x_report()
        if result.get("success"):
            logger.info("X-Report printed successfully from tray menu")
        else:
            logger.warning(f"X-Report failed from tray menu: {result.get('error')}")
    except Exception as e:
        logger.error(f"Error printing X-Report from tray menu: {e}")


def print_z_report_menu():
    """Handler for Print Z-Report menu item"""
    try:
        logger.info("Z-Report triggered from tray menu")
        import cts310ii
        result = cts310ii.print_z_report()
        if result.get("success"):
            logger.info("Z-Report printed successfully from tray menu")
        else:
            logger.warning(f"Z-Report failed from tray menu: {result.get('error')}")
    except Exception as e:
        logger.error(f"Error printing Z-Report from tray menu: {e}")


def open_fiscal_tools():
    """Handler for Fiscal Tools menu item - signals main thread to open pywebview modal"""
    try:
        logger.info("Fiscal Tools requested - signaling main thread")
        modal_queue.put('open')
    except Exception as e:
        logger.error(f"Error signaling Fiscal Tools: {e}")


icon_menu = menu(
    item('Fiscal Tools', open_fiscal_tools),
    menu.SEPARATOR,
    item('Print X-Report', print_x_report_menu),
    item('Print Z-Report', print_z_report_menu),
    menu.SEPARATOR,
    item('Quit BAB PrintHub', close_app)
)

icon_obj = pystray.Icon(
    name='BAB PrintHub',
    icon=Image.open(os.path.join(base_dir, 'logo.png')),
    title='BAB PrintHub',
    menu=icon_menu
)

# icon_tray_thread = threading.Thread(target=icon_obj.run, daemon=True)
# icon_tray_thread.start()

logger.debug("Starting fiscal printer hub...")
config = load_config()
logger.debug("Config loaded...")


logger.debug("Identifying printer...")
if config['printer']['name'] == 'cts310ii':
    import cts310ii
    while not cts310ii.cts310ii_main():
        time.sleep(1)


logger.debug("Identifying POS...")
if config['pos']['name'] == 'tcpos':
    import tcpos_parser

    tcpos_thread = threading.Thread(target=tcpos_parser.files_watchdog, daemon=True)
    tcpos_thread.start()

    logger.debug("Started TCPOS watchdog...")

# Move tray icon to background thread to keep main thread free for pywebview
icon_thread = threading.Thread(target=icon_obj.run, daemon=True)
icon_thread.start()

logger.info("Tray icon started in background thread")
logger.info("Main thread ready for pywebview modal requests")

# Main thread loop - listens for modal open requests
while True:
    try:
        signal = modal_queue.get(timeout=0.1)
        if signal == 'open':
            try:
                logger.info("Opening Fiscal Tools UI (pywebview) in main thread")

                from salesbook_webview_ui import FiscalToolsAPI, HTML_TEMPLATE

                api = FiscalToolsAPI()
                window = webview.create_window(
                    'Fiscal Tools - BAB PrintHub',
                    html=HTML_TEMPLATE,
                    width=800,
                    height=700,
                    resizable=True,
                    background_color='#ffffff',
                    js_api=api
                )
                api.window = window

                # Blocks until window closes (runs in main thread)
                try:
                    webview.start(gui='edgechromium')
                except:
                    logger.warning("EdgeChromium not available, trying mshtml")
                    webview.start(gui='mshtml')

                logger.info("Fiscal Tools UI closed")

            except Exception as e:
                logger.error(f"Error opening Fiscal Tools: {e}")
    except queue.Empty:
        pass