import os
import serial.tools.list_ports
import json
import datetime
import serial
import time
import sys
from logger_module import logger


"""
Based on the protocol
MHI_Programacion_CW_(EN).pdf
"""

DEBUG = False

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)

elif __file__:
    base_dir = os.path.dirname(os.path.abspath(__file__))

serial_timeout = 5  # seconds
COM_PORT = None
BAUD_RATE = 9600

# symbols in hex
STX = "02"  # start of transmission
ETX = "03"  # end of transmission
ACK = "06"  # positive answer
BEL = "07"  # intermediate response
NAK = "15"  # negative answer
FS = "1C"   # field separator

tax_ids = {
    "6": "1",  # percent : print tax id
    "7": "2",
    "9": "3"
}

payment_types = {
    "void_pay/donation": "0",
    "pay/donation": "1",
}

payment_methods = {
    "cash": "00",
    "check": "01",
    "credit_card": "02",
    "debit_card": "03",
    "credit_note": "04",
    "coupon": "05",
    "other_1": "06",
    "other_2": "07",
    "other_3": "08",
    "other_4": "09",
    "donations": "10",
}

discount_surcharge_types = {
    "discount": "0",
    "surcharge": "1",
    "service_charge": "2",
}

response_codes = {
    "0000": "Last command successful.",
    "0101": "Command invalid in the current state.",
    "0102": "Command invalid in the current document.",
    "0103": "Service jumper connected.",
    "0105": "Command requires service jumper.",
    "0107": "Invalid command.",
    "0108": "Command invalid through USB port.",
    "0109": "Command missing mandatory field.",
    "0110": "Invalid field length.",
    "0111": "Field value is invalid or out of range.",
    "0112": "Inactive TAX rate.",
    "0202": "Printing device out of line.",
    "0204": "Printing device out of paper.",
    "0205": "Invalid speed.",
    "0301": "Set fiscal info error.",
    "0302": "Set date error.",
    "0303": "Invalid date.",
    "0402": "CRIB cannot be modified.",
    "0501": "Transaction memory full.",
    "0503": "Transaction memory not connected",
    "0504": "Read/Write error on transaction memory.",
    "0505": "Invalid transaction memory.",
    "0601": "Command invalid outside of fiscal period.",
    "0602": "Fiscal period not started.",
    "0603": "Fiscal memory full.",
    "0604": "Fiscal memory not connected.",
    "0605": "Invalid fiscal memory.",
    "0606": "Command requires a Z report.",
    "0607": "Cannot find document.",
    "0608": "Fiscal period empty.",
    "0609": "Requested period empty.",
    "060A": "No more data is available.",
    "060B": "No more Z reports can be printed this day.",
    "060C": "Z report could not be saved.",
    "0701": "Total must be greater than zero.",
    "0801": "Reached comment line number limit.",
    "0901": "Reached no sale document line number limit.",
    "FFF0": "Checksum error in set fiscal info command",
    "FFF1": "Missing Checksum in set fiscal info command",
    "FFFF": "Unknown error.",
}


states_codes = {
    "0": "Standby",
    "1": "Start of sale",
    "2": "Sale",
    "3": "Subtotal",
    "4": "Payment",
    "5": "End of sale",
    "6": "Non Fiscal",
    "7": "Reserved",
    "8": "Error",
    "9": "Start of return",
    "10": "Return",
    "11": "Reading fiscal info",
    "12": "Storing logo",
    "13": "Read only",
}


def load_config():
    with open(os.path.join(base_dir, 'config.json')) as json_file:
        return json.load(json_file)


def convert_to_tax(string):
    # 0600 to 6.00 float
    return float(string[0:2] + "." + string[2:4])


def string_to_hex(string):
    return string.encode("utf-8").hex()


def dict_values_to_hex(dictionary):
    for key, value in dictionary.items():
        dictionary[key] = string_to_hex(value)

    return dictionary


def hex_to_string(hex_string):
    return bytes.fromhex(hex_string).decode('ascii')


def string_number_to_number(string, decimals=0):
    """
    Convert a string number to a float number.

    Parameters
    ----------
    string : str
        The string number to convert.
    decimals : int, optional
        The number of decimal places. The default is 0.

    Returns
    -------
    float
        The converted float number.

    Examples
    --------
    >>> string_number_to_number("8000")
    8.0
    >>> string_number_to_number("8000", decimals=2)
    80.0
    >>> string_number_to_number("8000", decimals=3)
    8.000
    """

    length = len(string) - decimals
    integer = string[:length]
    decimal = string[length:]
    # logger.debug(f"Integer: {integer}, Decimal: {decimal}")
    return float(integer + "." + decimal)


def hex_cmd_to_bytes(hex_cmd):
    # convert the command to bytes
    # check if the command length is odd

    try:
        if len(hex_cmd) % 2 == 0:
            # convert to byte array
            bytes_cmd = bytearray.fromhex(hex_cmd)
            # logger.debug(f"Command converted to bytes: {bytes_array}")

            return bytes_cmd
    except Exception as e:
        logger.error("Error while converting command to bytes: " + str(e))
        return None


def send_to_serial(hex_cmd, wait_for_response=True):
    try:
        # logger.debug(f"Command: {hex_cmd}")
        if DEBUG:
            logger.debug("Ignoring serial send")
            return f"{STX}{ETX}{ACK}"

        # convert the command to bytes
        bytes_cmd = hex_cmd_to_bytes(hex_cmd)

        if bytes_cmd is not None:
            # send the command
            ser = serial.Serial(COM_PORT, BAUD_RATE)
            ser.timeout = 3.0  # different to the timeout set in the global scope
            ser.write(bytes_cmd)

            if wait_for_response:
                # wait for response
                et = time.time() + serial_timeout
                data = ""
                while time.time() < et:
                    data += ser.read(1).hex()
                    if data.endswith(ETX + ACK) or data.endswith(NAK):
                        break

                logger.debug(f"Response length: {len(data)}")
                # logger.debug(data)
                return data

    except Exception as e:
        logger.error("Serial sending error: " + str(e))
        exit()
        return None


def spot_printer():
    global COM_PORT

    try:
        if DEBUG:
            logger.debug("DEBUG mode, ignoring printer")
            return True

        while 1:
            logger.debug("Spotting printer...")
            ports = serial.tools.list_ports.comports()

            if len(ports) > 0:
                for port in reversed(ports):
                    COM_PORT = port.name
                    logger.debug(f"Checking {COM_PORT} port...")
                    code = "21"
                    cmd = f"{STX}{code}{ETX}"
                    response = send_to_serial(cmd)

                    if is_success_response(response):
                        logger.debug(f"Found printer on {COM_PORT}..")
                        return True

            raise Exception("Printer not found...")
            time.sleep(1)

    except Exception as e:
        logger.error("Error: " + str(e))

    COM_PORT = None
    return False


#!BEGIN DECODERS SECTION
def is_success_response(data):
    # check if the data starts with STX and ends with ETX and ACK
    if data is None:
        return False
    if data.startswith(STX) and data.endswith(ETX + ACK):
        return True
    if data.startswith(BEL) and data.endswith(ETX + ACK):
        return True

    return False


def decode_printer_datetime(data):
    try:
        """
        field 1: date
        field 2: time
        0230333039323032341c3030313132370306
        """

        data = data.upper()
        # logger.debug(f"Data: {data}")

        # remove the STX and ETX from the data
        data = data[2:-4]
        # logger.debug(data)
        # split the data into fields
        fields = data.split(FS)
        # logger.debug(f"Fields: {fields}")
        # convert hex to ascii
        date = hex_to_string(fields[0])  # DDMMYYYY
        time = hex_to_string(fields[1])  # HHMMSS
        # build the datetime object
        datetime_object = datetime.datetime.strptime(date + time, '%d%m%Y%H%M%S')
        # logger.debug(datetime_object)

        return datetime_object

    except Exception as e:
        logger.error("Error while decoding printer datetime: " + str(e))
        return None


def decode_fiscal_information(data):
    """
    023f3f3f3f3f3f3f3f3f1c3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f1c3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f1c3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f1c3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f1c303630301c303730301c303930301c303030301c303030301c303030301c303030301c303030301c303030301c303030300306
    """

    try:
        data = data[2:-4]
        data = data.upper()
        fields = data.split(FS)
        fiscal_information = {
            "CRIB": hex_to_string(fields[0]),
            "business_name": hex_to_string(fields[1]),
            "phone_number": hex_to_string(fields[2]),
            "address1": hex_to_string(fields[3]),
            "address2": hex_to_string(fields[4]),
            "tax1": convert_to_tax(hex_to_string(fields[5])),
            "tax2": convert_to_tax(hex_to_string(fields[6])),
            "tax3": convert_to_tax(hex_to_string(fields[7])),
            "tax4": convert_to_tax(hex_to_string(fields[8])),
            "tax5": convert_to_tax(hex_to_string(fields[9])),
            "tax6": convert_to_tax(hex_to_string(fields[10])),
            "tax7": convert_to_tax(hex_to_string(fields[11])),
            "tax8": convert_to_tax(hex_to_string(fields[12])),
            "tax9": convert_to_tax(hex_to_string(fields[13])),
            "tax10": convert_to_tax(hex_to_string(fields[14])),
        }

        # logger.debug(json.dumps(fiscal_information, indent=4))
        return fiscal_information

    except Exception as e:
        logger.error("Error while decoding fiscal information: " + str(e))
        return None


def decode_printer_status(data):
    """
    Decode printer status response
    """

    try:
        data = data[2:-4]
        data = data.upper()
        # it is just one field of 4 bytes and needs to be converted to bits, so 32 bits
        bits = bin(int(data, 16))[2:].zfill(32)
        # 00110000001100000011000000110000
        printer_status = {
            "online": True if bits[0] == "0" else False,
            "cover": "OK" if bits[1] == "0" else "OPEN",
            "temperature": "OK" if bits[2] == "0" else "HIGH",
            "non_recoverable_error": "OK" if bits[3] == "0" else "ERROR",
            "paper_cutter": "OK" if bits[4] == "0" else "ERROR",
            "buffer_overflow": "OK" if bits[5] == "0" else "ERROR",
            "end_of_paper_sensor": "OK" if bits[6] == "0" else "NO_PAPER",
            "out_of_paper_sensor": "OK" if bits[7] == "0" else "NO_PAPER",
            "station_TOF_detection": "OK" if bits[16] == "0" else "NO_PAPER",
            "station_COF_error": "OK" if bits[17] == "0" else "NO_PAPER",
            "station_BOF_detection": "OK" if bits[18] == "0" else "NO_PAPER",
        }

        return printer_status

    except Exception as e:
        logger.error("Error while decoding printer status: " + str(e))
        return None


def decode_printer_state(data):
    """
    Decode printer state response
    """

    try:
        data = data[2:-4]
        data = data.upper()
        # there 3 fields
        fields = data.split(FS)

        response_code = hex(int(hex_to_string(fields[0])))[2:].zfill(4)
        state_code = hex_to_string(fields[1])

        printer_state = {
            "response_code": response_code,
            "response_description": response_codes[response_code] if response_code in response_codes else "unknown_response_code",
            "state_code": state_code,
            "state_description": states_codes[state_code] if state_code in states_codes else "unknown_state_code",
            "fiscal_status": fields[2],  # hex code
        }

        return printer_state

    except Exception as e:
        logger.error("Error while decoding printer state: " + str(e))

    return None


def decode_document_number(data):
    """
    Decode document number response after opening a new document with prepare_document()
    """
    try:
        data = data[2:-4]
        data = data.upper()
        # it has just one field
        fields = data.split(FS)
        document_number = hex_to_string(fields[0])
        return document_number

    except Exception as e:
        logger.error("Error while decoding document number: " + str(e))

    return None


def decode_sub_or_total_response(data):
    """
    02301c33311c321c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c33311c310306
    """
    try:
        data = data[2:-4]
        data = data.upper()
        # it has just one field
        fields = data.split(FS)
        """
        page 33
        """
        a = {
            "total_exempt": string_number_to_number(hex_to_string(fields[0]), decimals=2),
            "total_sale_tax_1": string_number_to_number(hex_to_string(fields[1]), decimals=2),
            "total_tax_1": string_number_to_number(hex_to_string(fields[2]), decimals=2),
            "total_sale_tax_2": string_number_to_number(hex_to_string(fields[3]), decimals=2),
            "total_tax_2": string_number_to_number(hex_to_string(fields[4]), decimals=2),
            "total_sale_tax_3": string_number_to_number(hex_to_string(fields[5]), decimals=2),
            "total_tax_3": string_number_to_number(hex_to_string(fields[6]), decimals=2),
            "total_sale_tax_4": string_number_to_number(hex_to_string(fields[7]), decimals=2),
            "total_tax_4": string_number_to_number(hex_to_string(fields[8]), decimals=2),
            "total_sale_tax_5": string_number_to_number(hex_to_string(fields[9]), decimals=2),
            "total_tax_5": string_number_to_number(hex_to_string(fields[10]), decimals=2),
            "total_sale_tax_6": string_number_to_number(hex_to_string(fields[11]), decimals=2),
            "total_tax_6": string_number_to_number(hex_to_string(fields[12]), decimals=2),
            "total_sale_tax_7": string_number_to_number(hex_to_string(fields[13]), decimals=2),
            "total_tax_7": string_number_to_number(hex_to_string(fields[14]), decimals=2),
            "total_sale_tax_8": string_number_to_number(hex_to_string(fields[15]), decimals=2),
            "total_tax_8": string_number_to_number(hex_to_string(fields[16]), decimals=2),
            "total_sale_tax_9": string_number_to_number(hex_to_string(fields[17]), decimals=2),
            "total_tax_9": string_number_to_number(hex_to_string(fields[18]), decimals=2),
            "total_sale_tax_10": string_number_to_number(hex_to_string(fields[19]), decimals=2),
            "total_tax_10": string_number_to_number(hex_to_string(fields[20]), decimals=2),
            "document_total": string_number_to_number(hex_to_string(fields[21]), decimals=2),
            "item_quantity": string_number_to_number(hex_to_string(fields[22])),

        }

        logger.debug(json.dumps(a, indent=4))
        return a

    except Exception as e:
        logger.error("Error while decoding sub or total response: " + str(e))

    return None


#!END DECODERS SECTION

#########################################################################################

#*BEGIN COMMANDS SECTION
def get_printer_datetime():
    try:
        code = "24"
        cmd = f"{STX}{code}{ETX}"
        response = send_to_serial(cmd)

        if is_success_response(response):
            printer_datetime = decode_printer_datetime(response)
            return printer_datetime

        raise Exception(f"Failed to get printer datetime, response: {response}")

    except Exception as e:
        logger.error("Error: " + str(e))

    return None


def set_printer_datetime(datetime_object):
    try:
        date = string_to_hex(datetime_object.strftime("%d%m%Y"))
        time = string_to_hex(datetime_object.strftime("%H%M%S"))
        # logger.debug(f"Date: {date}, Time: {time}")
        code = "23"
        cmd = f"{STX}{code}{FS}{date}{FS}{time}{ETX}"
        # logger.debug(f"Command: {cmd}")
        response = send_to_serial(cmd)

        if response == ACK:
            logger.debug(f"Printer datetime set successfully to {datetime_object}")
            return True

        raise Exception("Failed to set printer datetime")

    except Exception as e:
        logger.error("Error: " + str(e))
        return False


def get_fiscal_information():
    try:
        code = "26"
        cmd = f"{STX}{code}{ETX}"
        response = send_to_serial(cmd)

        if is_success_response(response):
            fiscal_information = decode_fiscal_information(response)
            return fiscal_information

        raise Exception(f"Failed to get fiscal information, response: {response}")
    except Exception as e:
        logger.error("Error: " + str(e))

    return None


def get_printer_status():
    try:
        code = "3F"
        cmd = f"{STX}{code}{ETX}"
        response = send_to_serial(cmd)

        if is_success_response(response):
            printer_status = decode_printer_status(response)
            return printer_status

        raise Exception(f"Failed to get printer status, response: {response}")

    except Exception as e:
        logger.error("Error: " + str(e))

    return None


def get_printer_state():
    try:
        code = "20"
        cmd = f"{STX}{code}{ETX}"
        response = send_to_serial(cmd)

        if is_success_response(response):
            printer_state = decode_printer_state(response)

            return printer_state

        raise Exception(f"Failed to get printer state, response: {response}")

    except Exception as e:
        logger.error("Error: " + str(e))

    return None


def cancel_document(reason="Completed operation"):
    try:
        code = "46"
        cmd = f"{STX}{code}{ETX}"
        response = send_to_serial(cmd)

        if response == f"0707{ACK}":
            logger.debug(f"Document canceled successfully, reason: {reason}")
            return True

        # NAK response means no document to cancel (printer in standby) - this is OK
        if response == NAK:
            logger.debug(f"No document to cancel (printer in standby)")
            return True

        raise Exception(f"Failed to cancel document, response: {response}")

    except Exception as e:
        logger.error("Error: " + str(e))
        return False


def prepare_document(fiscal_object):
    try:
        code = "40"
        a = dict_values_to_hex(fiscal_object)

        cmd = f"{STX}{code}{FS}"
        for k, v in a.items():
            cmd += f"{v}{FS}"

        # remove last FS
        cmd = cmd[:-2]
        cmd += ETX

        logger.debug(f"Document command: {cmd}")

        response = send_to_serial(cmd)

        if is_success_response(response):
            document_number = decode_document_number(response)
            logger.debug("Document prepared successfully")
            logger.debug(f"Document number: {document_number}")
            return document_number

        logger.debug(json.dumps(get_printer_state(), indent=4))


        raise Exception(f"Failed to prepare document, response: {response}")

    except Exception as e:
        logger.error("Error while preparing document: " + str(e))

    return None


def add_item_to_document(item):
    try:
        code = "41"
        a = dict_values_to_hex(item)

        cmd = f"{STX}{code}{FS}"
        for k, v in a.items():
            cmd += f"{v}{FS}"

        # remove last FS
        cmd = cmd[:-2] + "1C321C32"
        cmd += ETX

        logger.debug(f"Item command: {cmd}")

        response = send_to_serial(cmd)

        """
        replies with 02310306
        """

        if is_success_response(response):
            logger.debug("Item added to document successfully")
            return True

        logger.debug(json.dumps(get_printer_state(), indent=4))

        raise Exception(f"Failed to add item to document, response: {response}")

    except Exception as e:
        logger.error("Error while adding item to document: " + str(e))

    return None


def document_sub_or_total(type):
    """
    00 = subtotal
        02301c33311c321c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c33311c310306

    01 = total
        02301c33311c321c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c301c33311c310306
    """
    try:
        code = "42"
        cmd = f"{STX}{code}{FS}{type}{ETX}"
        logger.debug(f"Document subtotal/total command: {cmd}")

        response = send_to_serial(cmd)

        if is_success_response(response):
            a = "subtotal" if type == "0" else "total"
            logger.debug(f"Document {a} amount calculation updated successfully")
            totals = decode_sub_or_total_response(response)
            return totals  # document totals, subtotal, taxes, etc

        logger.debug(json.dumps(get_printer_state(), indent=4))

        raise Exception(f"Failed to update document subtotal, response: {response}")

    except Exception as e:
        logger.error("Error while updating document subtotal/total type: " + str(type) + ": " + str(e))

    return None


def discount_surcharge_service(data):
    try:
        code = "43"
        cmd = f"{STX}{code}{FS}"
        a = dict_values_to_hex(data)

        cmd = f"{STX}{code}{FS}"
        for k, v in a.items():
            cmd += f"{v}{FS}"

        # remove last FS
        cmd = cmd[:-2]
        cmd += ETX

        logger.info(f"Discount/surcharge/service data: {json.dumps(data, indent=2)}")
        logger.debug(f"Discount/surcharge/service command: {cmd}")

        response = send_to_serial(cmd)

        if is_success_response(response):
            logger.debug("Discount/surcharge/service added successfully")
            return response  # document subtotal after discount, etc

        logger.debug(json.dumps(get_printer_state(), indent=4))

        raise Exception(f"Failed to add discount/surcharge/service, response: {response}")

    except Exception as e:
        logger.error("Error while adding discount/surcharge/service: type: " + str(data["type"]) + ": " + str(e))

    return None


def payment(data):
    try:
        code = "44"
        cmd = f"{STX}{code}{FS}"

        a = dict_values_to_hex(data)

        cmd = f"{STX}{code}{FS}"
        for k, v in a.items():
            cmd += f"{v}{FS}"

        # remove last FS
        cmd = cmd[:-2]
        cmd += ETX

        logger.debug(f"Payment method command: {cmd}")

        response = send_to_serial(cmd)

        if is_success_response(response):
            """
            02301c313936390306
            """

            logger.debug("Payment method added successfully")
            return response  # amount left to pay, change

        logger.debug(json.dumps(get_printer_state(), indent=4))

        raise Exception(f"Failed to add payment method, response: {response}")

    except Exception as e:
        logger.error("Error while adding payment method: type: " + str(data["type"]) + ": " + str(e))

    return None


def close_document(reason="Completed operation"):
    """
    This command closes a fiscal document and saves it in the transaction memory.
    """
    try:
        code = "45"
        cmd = f"{STX}{code}{ETX}"

        logger.debug(f"Close document command: {cmd}")

        response = send_to_serial(cmd)
        logger.debug(f"Close document response: {response}")

        if is_success_response(response):
            """
            070707070702303034333732303030303030303032351c33310306
            070707070702303034333732303030303030303033341c3331300306
            """

            logger.debug(f"Document closed successfully, reason: {reason}")
            return response  # document number and total amount
        else:
            # get the printer state
            logger.debug(json.dumps(get_printer_state(), indent=4))

        if cancel_document(f"Document canceled due to an error in close document reason: {reason}"):
            logger.debug("Document canceled successfully due to a error in close document")
            close_document("Document canceled due to an error in close document")

        raise Exception(f"Failed to close document, response: {response}")

    except Exception as e:
        logger.error("Error while closing document: " + str(e))

    return None


def add_comment(comment):
    """
    Adds a text line to the document as a comment.
    Command 4A - Add comment line
    """
    try:
        # Convert the comment text to hex
        text_hex = string_to_hex(comment)

        # Construct the command according to the protocol
        code = "4A"  # Command for comment line
        cmd = f"{STX}{code}{FS}{text_hex}{ETX}"

        logger.debug(f"Adding comment: {comment}")

        # Send the command to the printer
        response = send_to_serial(cmd)

        # Check for success (either full response or just ACK)
        if is_success_response(response) or response == ACK:
            logger.debug(f"Comment added successfully")
            return True
        else:
            logger.error(f"Failed to add comment, response: {response}")
            return False

    except Exception as e:
        logger.error(f"Error while adding comment: {str(e)}")
        return False


def split_comment_into_lines(comment, max_chars=48):
    """
    Split a long comment into multiple lines of max_chars length.
    Splits on word boundaries to avoid breaking mid-word.
    Returns a list of strings, each max_chars long.
    """
    if not comment or not comment.strip():
        return []

    words = comment.strip().split()
    lines = []
    current_line = ""

    for word in words:
        # Check if adding this word would exceed max_chars
        if current_line and len(current_line) + 1 + len(word) <= max_chars:
            current_line += " " + word
        elif not current_line and len(word) <= max_chars:
            current_line = word
        elif not current_line and len(word) > max_chars:
            # Single word is too long, split it forcefully
            current_line = word[:max_chars]
            words.insert(words.index(word) + 1, word[max_chars:])
        else:
            # Current line is full, start a new one
            lines.append(current_line)
            current_line = word

    # Add the last line if not empty
    if current_line:
        lines.append(current_line)

    return lines


def print_document(items, payments, service_charge, tips, trans_num="", is_credit_note=False, discount=None, comment="", customer=None):
    try:
        config = load_config()
        # page 30 of the protocol
        # Use TransNum as POS reference if available
        pos_reference = trans_num if trans_num else "1001"

        # Use customer name and code if provided, otherwise use defaults
        customer_name = config["miscellaneous"]["default_client_name"]
        customer_crib = config["miscellaneous"]["default_client_crib"]
        has_customer = False

        if customer:
            has_customer = True
            if customer.get("name"):
                customer_name = customer["name"]
                logger.info(f"Using customer name: {customer_name}")
            if customer.get("code"):
                customer_crib = customer["code"]
                logger.info(f"Using customer CRIB: {customer_crib}")

        # Document type based on customer presence and credit note status:
        # No customer: 1 = Invoice Final Consumer, 3 = Credit Note For Invoice Final Consumer
        # With customer: 2 = Invoice Fiscal Credit, 4 = Credit Note For Invoice With Fiscal Value
        if has_customer:
            doc_type = "4" if is_credit_note else "2"
        else:
            doc_type = "3" if is_credit_note else "1"

        if is_credit_note:
            logger.info(f"Processing CREDIT NOTE (Type {doc_type}) - TransNum: {trans_num}")
        else:
            logger.info(f"Processing INVOICE (Type {doc_type}) - TransNum: {trans_num}")

        fiscal_object = {
            "type": doc_type,  # "1" for sale, "3" for return/credit note
            "branch": "9001",
            "POS": pos_reference,  # TCPOS Transaction Number
            "customer_name": customer_name,
            "customer_CRIB": customer_crib,
            "NKF": config["client"]["NKF"],
            "NKF_affected": config["client"]["NKF"],
        }

        # page 32 of the protocol
        """

            {
                "type": "00",
                "extra_description_1": "",
                "extra_description_2": "",
                "item_description": "c",
                "product_code": "123",
                "quantity": "800",
                "unit_price": "155",
                "tax": "1",  # tax id
                "discount_type": "1",
                "discount_amount": "100",
                "discount_percent": "01050",  # 10.50%
            }
        """
        items_list = [
            {
                "type": "01",
                "extra_description_1": "",
                "extra_description_2": "",
                "item_description": "a",
                "product_code": "123",
                "quantity": "2000",  # 2.000
                "unit_price": "155",  # 1.55
                "unit": "Units",  # Units Kilos Grams Pounds Boxes
                "tax": "1",  # tax id
                "discount_type": "0",
                "discount_amount": "000",
                "discount_percent": "000",  # 10.50%
            }
        ]

        # cancel any document before printing a new one
        cancel_document()

        # time.sleep(1)

        if 1:
            document_number = prepare_document(fiscal_object)
            # logger.debug(f"Document number: {document_number}")

        # Add separator line after customer details (header) and before items
        if has_customer:
            add_comment("------------------------------------------------")

        # time.sleep(1)

        for item in items:
            # Use space as product code to hide article number on printout
            item['product_code'] = " "
            add_item_to_document(item)

        # time.sleep(1)

        if service_charge:
            data = {
                "type": "0",
                "description": "Discount",
                "amount": "000",
                "percent": "1000",
            }
            discount_surcharge_service(service_charge)

            """
            02431c301c446973636f756e741c3030301c3130303003

            02431C301C446973636f756e741C3030301C3130303003
            """

        # time.sleep(1)

        # Calculate SUBTOTAL first
        if 1:
            subtotal = document_sub_or_total(string_to_hex("0"))

        # Apply discount at SUBTOTAL level (after items, before total)
        if discount:
            discount_surcharge_service(discount)
            logger.info(f"Applied transaction discount: {discount['description']} - {discount['amount']}")
        else:
            logger.debug("No transaction discount to apply")

        # Now calculate TOTAL (after discount)
        if 1:
            total = document_sub_or_total(string_to_hex("1"))

        # time.sleep(1)

        if 1:
            data = {
                "type": "1",
                "method": "03",
                "description": "Paydebit",
                "amount": "2000"  # 20.00
            }
            """
            02441c 31 1c30331c50617964656269741c3230303003
            02441C311C30331C50617964656269741C3230303003
            """

            for pay in payments:
                payment(pay)

        # time.sleep(1)

        if 0:
            tip = {
                "type": "1",
                "method": "10",
                "description": "Tip",
                "amount": "500"  # 5.00
            }
            payment(tip)

        if 1:
            for tip in tips:
                payment(tip)

        # time.sleep(1)

        # Add TCPOS check number as a comment line before closing
        if trans_num:
            add_comment(f"TCPOS Check #{trans_num}")

        # Add multi-line comment from transaction if present
        if comment:
            add_comment("------------------------------------------------")
            comment_lines = split_comment_into_lines(comment, max_chars=48)
            for line in comment_lines:
                add_comment(line)
            add_comment("------------------------------------------------")

        if 1:
            close_document()

        # time.sleep(1)


    except Exception as e:
        logger.error("Error while printing document: " + str(e))

    return None


def print_x_report():
    """
    Print X Report (daily sales without closing fiscal day)
    Returns: dict with success status and error message if applicable
    """
    try:
        logger.info("Generating X Report")
        code = "71"  # X Report command
        cmd = f"{STX}{code}{ETX}"
        response = send_to_serial(cmd)

        if is_success_response(response):
            logger.info("X Report printed successfully")
            return {"success": True}
        else:
            # NAK response usually means: no transactions to report, or printer not ready
            error_msg = "Printer rejected X-Report (NAK response)"
            if response == "15":
                error_msg += " - Likely no transactions to report or fiscal day already closed"
            logger.warning(error_msg)
            return {"success": False, "error": error_msg}
    except Exception as e:
        logger.error(f"Exception during X Report: {e}")
        return {"success": False, "error": str(e)}


def print_z_report(close_fiscal_day=False):
    """
    Print Z Report

    Args:
        close_fiscal_day: If True, closes the fiscal period (can only be done once per day).
                         If False, prints a copy without closing (can be done multiple times).

    Returns: dict with success status and error message if applicable
    """
    try:
        action = "closing fiscal period" if close_fiscal_day else "printing copy"
        logger.info(f"Generating Z Report ({action})")
        code = "70"  # Z Report command
        param_value = "1" if close_fiscal_day else "0"  # 1 = Close fiscal day, 0 = Print copy only
        param = string_to_hex(param_value)  # Convert to hex
        cmd = f"{STX}{code}{FS}{param}{ETX}"
        response = send_to_serial(cmd)

        if response is None:
            error_msg = "Failed to print Z Report - No response from printer"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        if is_success_response(response):
            logger.info(f"Z Report printed successfully ({action})")
            return {"success": True}
        else:
            # Provide helpful error message
            error_msg = "Failed to print Z Report"
            if response == NAK or response == "15":
                error_msg += " - No transactions to report or fiscal day already closed"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    except Exception as e:
        logger.error(f"Exception during Z Report: {e}")
        return {"success": False, "error": str(e)}


def print_z_report_by_date(start_date, end_date=None):
    """Print Z Reports for a date range

    Note: This function uses the combined Z reports protocol (0x74)
    which retrieves ALL Z reports in a date range.

    Args:
        start_date: Start date for the range (datetime.date object)
        end_date: End date for the range (defaults to today if not provided)

    Returns:
        dict: Response with success status, message, and report count
    """
    try:
        if end_date is None:
            end_date = datetime.date.today()

        start_date_str = start_date.strftime("%d%m%Y")
        end_date_str = end_date.strftime("%d%m%Y")

        logger.info(f"Generating Z Reports for date range: {start_date_str} - {end_date_str}")

        reserved_field = string_to_hex("0")
        start_hex = string_to_hex(start_date_str)
        end_hex = string_to_hex(end_date_str)

        code = "74"  # z_report_by_date command
        cmd = f"{STX}{code}{FS}{reserved_field}{FS}{start_hex}{FS}{end_hex}{ETX}"

        logger.debug(f"Sending Z report by date command: {cmd}")
        response = send_to_serial(cmd)
        logger.debug(f"Received response: {response}")

        if not is_success_response(response):
            logger.error(f"Failed to initialize Z reports by date - Response: {response}")
            return {"success": False, "error": f"Failed to initialize Z reports by date. The printer may not have Z reports for this date range, or the dates may be invalid."}

        reports_count = 0
        while True:
            get_code = "76"  # get_next_z_report command
            get_cmd = f"{STX}{get_code}{ETX}"
            report_response = send_to_serial(get_cmd)

            if report_response and report_response.endswith(NAK):
                logger.info(f"Retrieved {reports_count} Z report(s)")
                break

            if is_success_response(report_response):
                reports_count += 1
            else:
                logger.warning("Failed to get next Z report")
                break

        end_code = "77"  # z_reports_end command
        end_cmd = f"{STX}{end_code}{ETX}"
        end_response = send_to_serial(end_cmd)

        if is_success_response(end_response):
            logger.info("Combined Z reports completed")

        if reports_count > 0:
            message = f"Printed {reports_count} Z report(s) from {start_date_str} to {end_date_str}"
            logger.info(message)
            return {
                "success": True,
                "message": message,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "reports_count": reports_count
            }
        else:
            logger.warning(f"No Z reports found for date range {start_date_str} - {end_date_str}")
            return {
                "success": False,
                "error": f"No Z reports found for date range {start_date_str} - {end_date_str}"
            }

    except Exception as e:
        logger.error(f"Error printing Z Reports by date: {e}")
        return {"success": False, "error": str(e)}


def print_z_report_by_number(report_number):
    """Print Z Report by sequential number

    Args:
        report_number: The sequential Z report number to print

    Returns:
        dict: Response with success status and message
    """
    try:
        logger.info(f"Generating Z Report by number: {report_number}")

        number_hex = string_to_hex(str(report_number).zfill(4))

        code = "75"  # z_report_by_number command
        cmd = f"{STX}{code}{FS}{number_hex}{FS}{number_hex}{ETX}"
        response = send_to_serial(cmd)

        if not is_success_response(response):
            logger.error("Failed to initialize Z report by number")
            return {"success": False, "error": "Failed to initialize Z report by number"}

        get_code = "76"  # get_next_z_report command
        get_cmd = f"{STX}{get_code}{ETX}"
        report_response = send_to_serial(get_cmd)

        end_code = "77"  # z_reports_end command
        end_cmd = f"{STX}{end_code}{ETX}"
        send_to_serial(end_cmd)

        if report_response and report_response.endswith(NAK):
            logger.warning(f"Z report #{report_number} not found")
            return {"success": False, "error": f"Z report #{report_number} not found"}

        if is_success_response(report_response):
            logger.info(f"Z report #{report_number} printed successfully")
            return {
                "success": True,
                "message": f"Z Report #{report_number} printed successfully",
                "report_number": report_number
            }
        else:
            logger.error("Failed to print Z report by number")
            return {"success": False, "error": "Failed to print Z report by number"}

    except Exception as e:
        logger.error(f"Error printing Z Report by number: {e}")
        return {"success": False, "error": str(e)}


def print_z_report_by_number_range(start_number, end_number):
    """Print Z Reports by sequential number range

    Args:
        start_number: The starting sequential Z report number
        end_number: The ending sequential Z report number

    Returns:
        dict: Response with success status and message
    """
    try:
        logger.info(f"Generating Z Reports by number range: {start_number} to {end_number}")

        start_hex = string_to_hex(str(start_number).zfill(4))
        end_hex = string_to_hex(str(end_number).zfill(4))

        # Initialize the range
        code = "75"  # z_report_by_number command
        cmd = f"{STX}{code}{FS}{start_hex}{FS}{end_hex}{ETX}"
        response = send_to_serial(cmd)

        if not is_success_response(response):
            logger.error("Failed to initialize Z report range")
            return {"success": False, "error": "Failed to initialize Z report range"}

        # Get all reports in the range
        get_code = "76"  # get_next_z_report command
        get_cmd = f"{STX}{get_code}{ETX}"

        reports_printed = 0
        expected_count = end_number - start_number + 1

        for i in range(expected_count):
            report_response = send_to_serial(get_cmd)

            if report_response and report_response.endswith(NAK):
                logger.warning(f"Z report not found at position {i+1}")
                break

            if is_success_response(report_response):
                reports_printed += 1
                logger.info(f"Z report {i+1}/{expected_count} printed")
            else:
                logger.warning(f"Failed to print Z report at position {i+1}")
                break

        # End the sequence
        end_code = "77"  # z_reports_end command
        end_cmd = f"{STX}{end_code}{ETX}"
        send_to_serial(end_cmd)

        if reports_printed > 0:
            logger.info(f"{reports_printed} Z reports printed successfully")
            return {
                "success": True,
                "message": f"{reports_printed} Z Report(s) printed successfully (#{start_number} to #{end_number})",
                "start_number": start_number,
                "end_number": end_number,
                "reports_printed": reports_printed
            }
        else:
            logger.warning("No Z reports found in the specified range")
            return {"success": False, "error": "No Z reports found in the specified range"}

    except Exception as e:
        logger.error(f"Error printing Z Reports by range: {e}")
        return {"success": False, "error": str(e)}


def reprint_document(document_number):
    """Re-print a document/ticket (NO SALE - copy only)

    Command 0xA8 (168 decimal) - Search document/Print Copy
    Mode='1' (Printed) to print a copy directly

    Args:
        document_number: The document number to re-print (string or integer)
                        If string, leading zeros are preserved

    Returns:
        dict: Response with success status and message
    """
    try:
        # Convert to string and preserve leading zeros
        doc_num_str = str(document_number)
        logger.info(f"Re-printing document number: {doc_num_str}")

        code = "A8"
        mode_hex = string_to_hex("1")  # '1' = Print copy
        doc_num_hex = string_to_hex(doc_num_str)

        # Try different document types (manual says Field 2 is 2 characters!)
        # Document types from manual (Section 6.8):
        # 01 = Invoice Final Consumer
        # 02 = Invoice Fiscal Credit
        # 03-09 = Other invoice types
        # 10 = No Sale document
        for doc_type in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]:
            doc_type_hex = string_to_hex(doc_type)  # Now 2 chars as per manual
            cmd = f"{STX}{code}{FS}{mode_hex}{FS}{doc_type_hex}{FS}{doc_num_hex}{ETX}"

            logger.debug(f"Trying document type {doc_type}:")
            logger.debug(f"  Full command: {cmd}")

            response = send_to_serial(cmd)

            if response and not response.endswith(NAK):
                # Found it!
                if is_success_response(response):
                    logger.info(f"Document {doc_num_str} found with type {doc_type} and re-printed successfully")
                    return {
                        "success": True,
                        "message": f"Document {doc_num_str} re-printed successfully (NO SALE)",
                        "document_number": doc_num_str,
                        "document_type": doc_type
                    }

        # Not found with any document type
        logger.warning(f"Document {doc_num_str} not found (tried all document types 01-10)")
        return {
            "success": False,
            "error": f"Document {doc_num_str} not found (tried all document types)"
        }

    except Exception as e:
        logger.error(f"Error re-printing document: {e}")
        return {"success": False, "error": str(e)}


#*END COMMANDS SECTION


def cts310ii_main():
    spotted = spot_printer()
    if not spotted:
        return False

    if 0:
        # cancel_document()
        print_document(1)

    if 1 and not DEBUG:
        # get printer state
        logger.info("Printer state:")
        logger.info(json.dumps(get_printer_state(), indent=4))


    if 1 and not DEBUG:
        printer_status = get_printer_status()
        logger.info("Printer status:")
        logger.info(json.dumps(printer_status, indent=4))


    if 1 and not DEBUG:
        # get printer datetime
        printer_datetime = get_printer_datetime()

        # if printer_datetime is not synchronized at least 5 seconds before or after the current time, set it
        if printer_datetime < datetime.datetime.now() - datetime.timedelta(seconds=120) or printer_datetime > datetime.datetime.now() + datetime.timedelta(seconds=120):
            logger.debug("Printer datetime is not synchronized")
            logger.debug(f"Current datetime: {datetime.datetime.now()}")
            logger.debug(f"Printer datetime: {printer_datetime}")
            set_printer_datetime(datetime.datetime.now())

        else:
            logger.debug("Printer datetime is synchronized")
            logger.debug(f"Current datetime: {datetime.datetime.now()}")
            logger.debug(f"Printer datetime: {printer_datetime}")


    if 1 and not DEBUG:
        fiscal_information = get_fiscal_information()

        if fiscal_information:
            # check if the printer was configured
            # if CRIB doesn't starts with ?
            if fiscal_information['CRIB'].startswith("?"):
                logger.error("ALERT: Printer CRIB is not configured")
            else:
                logger.info(f"CRIB: {fiscal_information['CRIB']}")

            if fiscal_information['business_name'].startswith("?"):
                logger.error("ALERT: Printer business name is not configured")
            else:
                logger.info(f"Business name: {fiscal_information['business_name']}")

            if fiscal_information['phone_number'].startswith("?"):
                logger.error("ALERT: Printer phone number is not configured")
            else:
                logger.info(f"Phone number: {fiscal_information['phone_number']}")

            if fiscal_information['address1'].startswith("?"):
                logger.error("ALERT: Printer address1 is not configured")
            else:
                logger.info(f"Address: {fiscal_information['address1']}")

            if fiscal_information['address2'].startswith("?"):
                logger.error("ALERT: Printer address2 is not configured")
            else:
                logger.info(f"Address: {fiscal_information['address2']}")

            logger.info("TAX settings:")
            logger.info(f"    Tax 1: {fiscal_information['tax1']}")
            logger.info(f"    Tax 2: {fiscal_information['tax2']}")
            logger.info(f"    Tax 3: {fiscal_information['tax3']}")
            logger.info(f"    Tax 4: {fiscal_information['tax4']}")
            logger.info(f"    Tax 5: {fiscal_information['tax5']}")
            logger.info(f"    Tax 6: {fiscal_information['tax6']}")
            logger.info(f"    Tax 7: {fiscal_information['tax7']}")
            logger.info(f"    Tax 8: {fiscal_information['tax8']}")
            logger.info(f"    Tax 9: {fiscal_information['tax9']}")
            logger.info(f"    Tax 10: {fiscal_information['tax10']}")

            """
            CRIB: 102314329
            Business name:                     Kome BV
            Phone number: 4650413
            4.
            Address: Johan van Walbeeckplein 6
            Address:
            TAX settings:
                Tax 1: 6.0
                Tax 2: 7.0
                Tax 3: 9.0
                Tax 4: 0.0
                Tax 5: 0.0
                Tax 6: 0.0
                Tax 7: 0.0
                Tax 8: 0.0
                Tax 9: 0.0
                Tax 10: 0.0

            """

    return True









