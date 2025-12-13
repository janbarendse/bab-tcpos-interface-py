from packaging.version import Version
import traceback
import threading
import time
import xml.etree.ElementTree as ET
import json
import xmltodict
import os
import sys
from logger_module import logger


if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)

elif __file__:
    base_dir = os.path.dirname(os.path.abspath(__file__))


transaction_uuid = None
supported_version = "8.0"

tax_ids = {
    "6": "1",  # tax percent : printer tax id
    "7": "2",
    "9": "3"
}

payment_methods = {
    "Cash": "00",
    "Cheque": "01",
    "CreditCard": "02",
    "DebitCard": "03",
    "credit_note": "04",
    "Voucher": "05",
    "other_1": "06",
    "other_2": "07",
    "other_3": "08",
    "other_4": "09",
    "donations": "10",
}


def get_transaction_uuid(xml_json_object):
    logger.debug("Getting transaction uuid...")
    # loop through keys values
    for key, value in xml_json_object.items():
        return key


def get_vat_information(xml_json_object):
    """
    returns a dictionary with vat IDs and percents
    """

    vat_information = {}
    for vat in xml_json_object[transaction_uuid]['data']['VatDetails']['TCPOS.FrontEnd.BusinessLogic.VatDetail']:
        vat_information[vat['Data']['@ID']] = vat['Data']['@Percent']

    # logger.debug(json.dumps(vat_information, indent=4))
    return vat_information


def encode_float_number(number, decimal_places):
    # 2.000
    # check if there is a dot
    if '.' in number:
        # make sure it has three decimal places
        if not len(number.split('.')[1]) == decimal_places:
            # add zeroes
            number += '0' * (decimal_places - len(number.split('.')[1]))

        # remove the dot
        number = number.replace('.', '')

    else:
        number += '0' * decimal_places

    return number


def encode_measurement_unit(measurement_unit):
    if measurement_unit == 'pcs':
        return "Units"

    else:
        return "Units"


def check_file_version(xml_json_object):
    version = xml_json_object[transaction_uuid]['data']["@SoftwareVersion"]

    if Version(version) < Version(supported_version):
        raise Exception(f"Unsupported version: {xml_json_object[transaction_uuid]['@_version']}")
        # print(f"Unsupported version: {version}")


def process_discount_surcharge(item):
    if "DiscountValues" not in item:
        return None

    # loop through discount values and keys
    target_key = ""
    for key, value in item['DiscountValues'].items():
        if key.startswith('DiscountValue-'):
            target_key = key
            break

    if target_key == "":
        return None

    return {
        "type": "1",
        "amount": encode_float_number(item['DiscountValues'][target_key]["@Amount"][1:], 2),
        "percent": "000",
    }


def get_sub_items(xml_json_object):
    try:
        """
        {
                    "type": "00",  # 0 = normal item, 1 = void item
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

        """
        logger.debug("Getting sub items...")
        sub_items = []
        tips = []
        if type(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransArticle']) is list:
            for item in xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransArticle']:
                void_item = False
                tax_exempt = False

                # check if item was deleted
                if "@deleteOperatorID" in item:
                    void_item = True

                if "@_vatPercent" not in item:
                    tax_exempt = True

                if "@shortDescription" in item['Data']:
                    if item['Data']['@shortDescription'] == "Tip" or item['Data']['@shortDescription'] == "Tip %":
                        tips.append({
                            "type": "1",
                            "method": "10",
                            "description": "Tip",
                            "amount": encode_float_number(item['@_enteredPrice'], 2),
                        })

                        continue

                discount_or_surcharge = process_discount_surcharge(item)

                if "@_enteredPrice" not in item:
                    price = item['prices']['index_0']['@Price']

                else:
                    price = item['@_enteredPrice']

                sub_items.append({
                    "type": "02" if void_item else "01",
                    "extra_description_1": "",
                    "extra_description_2": "",
                    "item_description": item['Data']['@Description'],
                    "product_code": item['Data']['@Code'],
                    "quantity": encode_float_number(item['@quantityWithPrecision'], 3),  # 2.000
                    # "unit_price": encode_float_number(item['prices']['index_0']['@Price'], 2),  # 1.55
                    "unit_price": encode_float_number(price, 2),  # 1.55
                    "unit": encode_measurement_unit(item['measureUnit']['@Code']),  # Units Kilos Grams Pounds Boxes
                    "tax": tax_ids[item['@_vatPercent']] if not tax_exempt else "0",  # tax id
                    "discount_type": discount_or_surcharge['type'] if discount_or_surcharge else "0",
                    "discount_amount": discount_or_surcharge['amount'] if discount_or_surcharge else "000",
                    "discount_percent": discount_or_surcharge['percent'] if discount_or_surcharge else "000",  # 10.50%
                })

        elif type(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransArticle']) is dict:
            item = xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransArticle']

            void_item = False
            tax_exempt = False

            # check if item was deleted
            if "@deleteOperatorID" in item:
                void_item = True

            if "@_vatPercent" not in item:
                tax_exempt = True

            if "@shortDescription" in item['Data']:
                if item['Data']['@shortDescription'] == "Tip" or item['Data']['@shortDescription'] == "Tip %":
                    tips.append({
                        "type": "1",
                        "method": "10",
                        "description": "Tip",
                        "amount": encode_float_number(item['@_enteredPrice'], 2),
                    })

            else:
                discount_or_surcharge = process_discount_surcharge(item)

                sub_items.append({
                    "type": "02" if void_item else "01",
                    "extra_description_1": "Discount" if discount_or_surcharge else "",
                    "extra_description_2": "",
                    "item_description": item['Data']['@Description'],
                    "product_code": item['Data']['@Code'],
                    "quantity": encode_float_number(item['@quantityWithPrecision'], 3),  # 2.000
                    "unit_price": encode_float_number(item['prices']['index_0']['@Price'], 2),  # 1.55
                    "unit": encode_measurement_unit(item['measureUnit']['@Code']),  # Units Kilos Grams Pounds Boxes
                    "tax": tax_ids[item['@_vatPercent']] if not tax_exempt else "0",  # tax id
                    "discount_type": discount_or_surcharge['type'] if discount_or_surcharge else "0",
                    "discount_amount": discount_or_surcharge['amount'] if discount_or_surcharge else "000",
                    "discount_percent": discount_or_surcharge['percent'] if discount_or_surcharge else "000",  # 10.50%
                })

        logger.debug("Sub items:")
        logger.debug(json.dumps(sub_items, indent=4))
        logger.debug("Tips:")
        logger.debug(json.dumps(tips, indent=4))
        return sub_items, tips

    except Exception as e:
        logger.error("Error while getting sub items: " + str(e))
        logger.error(traceback.format_exc())

        return None, None


def get_service_charge(xml_json_object):
    logger.debug("Getting service charge...")
    # check if there is any service
    if "TCPOS.FrontEnd.BusinessLogic.TransServiceSupplement" in xml_json_object[transaction_uuid]['data']['subItems']:
        service = {
            "type": "2",
            "description": "Service charge",
            "amount": "000",
            "percent": encode_float_number(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransServiceSupplement']['@servicePercent'], 2),
        }

        logger.debug("Service charge:")
        logger.debug(json.dumps(service, indent=4))

        return service

    return None


def get_payment_details(xml_json_object):
    logger.debug("Getting payment details...")
    try:
        payment_details = []

        if type(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']) is list:

            for payment in xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']:
                payment_details.append({
                    "type": "1",
                    "method": payment_methods[payment['Data']['@Type']],
                    "description": payment['Data']['@Type'],
                    "amount": encode_float_number(payment['@amount'], 2),
                })

        elif type(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']) is dict:
            payment_details.append({
                "type": "1",
                "method": payment_methods[xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']['Data']['@Type']],
                "description": xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']['Data']['@Type'],
                "amount": encode_float_number(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']['@amount'], 2),
            })

        logger.debug("Payment details:")
        logger.debug(json.dumps(payment_details, indent=4))
        return payment_details

    except Exception as e:
        logger.error("Error: " + str(e))

    return None


def tcpos_parse_transaction(filename):
    global transaction_uuid

    # filename = "TIP PERCENT-Trn 19-22-28 #37"
    # filename += ".xml"
    try:
        with open(filename, 'r', encoding='utf-8') as xml_file:
            xml_tree = ET.parse(xml_file)

        xml_data = xml_tree.getroot()
        xmlstr = ET.tostring(xml_data, encoding='utf-8', method='xml')
        xml_json_object = xmltodict.parse(xmlstr)
        logger.info(f"File: {filename}")

        if 0:
            # save to file
            with open(os.path.join(base_dir, 'xmls', filename + '.json'), 'w') as outfile:
                json.dump(xml_json_object, outfile, indent=4)


        transaction_uuid = get_transaction_uuid(xml_json_object)
        logger.debug(f"Transaction UUID: {transaction_uuid}")
        # vat_information = get_vat_information(xml_json_object)
        # logger.debug(f"VAT information: {vat_information}")
        # check version
        version = xml_json_object[transaction_uuid]['data']["@SoftwareVersion"]

        if Version(version) < Version(supported_version):
            raise Exception(f"Unsupported version: {xml_json_object[transaction_uuid]['data']['@SoftwareVersion']}, file: {filename}")

        items, tips = get_sub_items(xml_json_object)
        payments = get_payment_details(xml_json_object)
        service_charge = get_service_charge(xml_json_object)
        service_charge = None

        return items, payments, service_charge, tips

    except Exception as e:
        logger.error("Error: " + str(e))

    return None, None, None, None


def files_watchdog():
    config = json.load(open('config.json'))

    if config['printer']['name'] == 'cts310ii':
        import cts310ii

    while True:
        for root, dirs, files in os.walk(config['pos']['transactions_folder']):
            for file in files:
                try:
                    if file.endswith('.xml'):
                        logger.debug("File found: " + os.path.join(root, file))
                        items, payments, service_charge, tips = tcpos_parse_transaction(os.path.join(root, file))

                        if items and payments:
                            cts310ii.print_document(items, payments, service_charge, tips)

                            if 1:
                                # check if file exists
                                if os.path.exists(os.path.join(root, file + '.processed')):
                                    os.remove(os.path.join(root, file + '.processed'))

                                os.rename(
                                    os.path.join(root, file),
                                    os.path.join(root, f'{file}.processed')
                                )
                            logger.info(f"File processed: {file}")

                        else:
                            logger.debug("File skipped: " + os.path.join(root, file))
                            if 1:
                                os.rename(
                                    os.path.join(root, file),
                                    os.path.join(root, f'{file}.skipped')
                                )
                            logger.info(f"File skipped: {file}")

                        time.sleep(1)

                except Exception as e:
                    logger.error("Watchdog error: " + str(e))
                    pass

        time.sleep(1)


if 0:
    tcpos_thread = threading.Thread(target=files_watchdog, daemon=True)
    tcpos_thread.start()

    while 1:
        time.sleep(1)
