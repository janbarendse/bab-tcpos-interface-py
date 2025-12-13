import threading
import time
import json
import os
import sys
from logger_module import logger
from pystray import Menu as menu, MenuItem as item
import pystray
from PIL import Image, ImageDraw


if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)

elif __file__:
    base_dir = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(base_dir, 'config.json')) as json_file:
        return json.load(json_file)


def close_app():
    os._exit(0)


icon_menu = menu(
    item(
        'Quit TCPOS Printer Hub',
        close_app
    )
)

icon_obj = pystray.Icon(
    name='TCPOS Printer Hub',
    icon=Image.open(os.path.join(base_dir, 'printer.png')),
    title='TCPOS Printer Hub',
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


icon_obj.run()

if 0:
    while 1:
        time.sleep(1)