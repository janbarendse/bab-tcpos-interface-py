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


def print_document(items, payments, service_charge, tips, trans_num="", is_credit_note=False):
    try:
        config = load_config()
        # page 30 of the protocol
        # Use TransNum as POS reference if available
        pos_reference = trans_num if trans_num else "1001"

        # Document type: "1" = Sale, "3" = Return/Credit Note (per MHI protocol)
        doc_type = "3" if is_credit_note else "1"
        if is_credit_note:
            logger.info(f"Processing CREDIT NOTE (void/refund) - TransNum: {trans_num}")

        fiscal_object = {
            "type": doc_type,  # "1" for sale, "3" for return/credit note
            "branch": "9001",
            "POS": pos_reference,  # TCPOS Transaction Number
            "customer_name": config["miscellaneous"]["default_client_name"],
            "customer_CRIB": config["miscellaneous"]["default_client_crib"],
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

        # time.sleep(1)

        for item in items:
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

        if 1:  # total
            subtotal = document_sub_or_total(string_to_hex("0"))
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

        if 1:
            close_document()

        # time.sleep(1)


    except Exception as e:
        logger.error("Error while printing document: " + str(e))

    return None


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









