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


def split_printout_notes(printout_notes, max_chars=48):
    """
    Split printout notes into chunks of max_chars.
    Returns tuple: (line1, line2) where each line is max 48 chars
    Line 1 is the first part, Line 2 is the continuation
    """
    if not printout_notes:
        return ("", "")

    # Split into words to avoid breaking mid-word
    words = printout_notes.split()
    line1 = ""
    line2 = ""

    # Build line 1
    for word in words:
        if len(line1) + len(word) + (1 if line1 else 0) <= max_chars:
            line1 += (" " if line1 else "") + word
        else:
            # Start filling line 2
            if len(line2) + len(word) + (1 if line2 else 0) <= max_chars:
                line2 += (" " if line2 else "") + word
            else:
                # Can't fit more, truncate
                break

    return (line1, line2)


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

                # Don't apply discount at item level - it will be applied at subtotal level
                discount_or_surcharge = None

                if "@_enteredPrice" not in item:
                    price = item['prices']['index_0']['@Price']

                else:
                    price = item['@_enteredPrice']

                # Extract PrintoutNotes if available
                product_title = item['Data']['@Description']
                printout_notes = item['Data'].get('@PrintoutNotes', '')

                # Smart layout strategy (lines print top to bottom: 1, 2, 3):
                # Case 1: No notes -> Title on line 3 (mandatory)
                # Case 2: Notes ≤48 chars -> Title on line 2, Notes on line 3
                # Case 3: Notes >48 chars -> Title on line 1, Notes split on lines 2&3
                if not printout_notes:
                    # No notes: use only line 3 (mandatory)
                    line1 = ""
                    line2 = ""
                    line3 = product_title
                elif len(printout_notes) <= 48:
                    # Short notes: title on line 2, notes on line 3
                    line1 = ""
                    line2 = product_title
                    line3 = printout_notes
                else:
                    # Long notes: split and check if we actually got 2 lines
                    notes_line1, notes_line2 = split_printout_notes(printout_notes)

                    if notes_line2:
                        # Two lines of notes: title on 1, notes on 2&3
                        line1 = product_title
                        line2 = notes_line1
                        line3 = notes_line2
                    else:
                        # Split returned only one line: treat like short notes
                        line1 = ""
                        line2 = product_title
                        line3 = notes_line1

                # For credit notes, quantities and prices may be negative - strip minus signs
                quantity_str = str(item['@quantityWithPrecision'])
                if quantity_str.startswith('-'):
                    quantity_str = quantity_str[1:]

                price_str = str(price)
                if price_str.startswith('-'):
                    price_str = price_str[1:]

                sub_items.append({
                    "type": "02" if void_item else "01",
                    "extra_description_2": line1,  # Line 1 (top)
                    "extra_description_1": line2,  # Line 2 (middle)
                    "item_description": line3,     # Line 3 (bottom, mandatory)
                    "product_code": item['Data']['@Code'],
                    "quantity": encode_float_number(quantity_str, 3),  # 2.000
                    # "unit_price": encode_float_number(item['prices']['index_0']['@Price'], 2),  # 1.55
                    "unit_price": encode_float_number(price_str, 2),  # 1.55
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
                # Don't apply discount at item level - it will be applied at subtotal level
                discount_or_surcharge = None

                # Extract PrintoutNotes if available
                product_title = item['Data']['@Description']
                printout_notes = item['Data'].get('@PrintoutNotes', '')

                # Smart layout strategy (lines print top to bottom: 1, 2, 3):
                # Case 1: No notes -> Title on line 3 (mandatory)
                # Case 2: Notes ≤48 chars -> Title on line 2, Notes on line 3
                # Case 3: Notes >48 chars -> Title on line 1, Notes split on lines 2&3
                if not printout_notes:
                    # No notes: use only line 3 (mandatory)
                    line1 = ""
                    line2 = ""
                    line3 = product_title
                elif len(printout_notes) <= 48:
                    # Short notes: title on line 2, notes on line 3
                    line1 = ""
                    line2 = product_title
                    line3 = printout_notes
                else:
                    # Long notes: split and check if we actually got 2 lines
                    notes_line1, notes_line2 = split_printout_notes(printout_notes)

                    if notes_line2:
                        # Two lines of notes: title on 1, notes on 2&3
                        line1 = product_title
                        line2 = notes_line1
                        line3 = notes_line2
                    else:
                        # Split returned only one line: treat like short notes
                        line1 = ""
                        line2 = product_title
                        line3 = notes_line1

                # For credit notes, quantities and prices may be negative - strip minus signs
                quantity_str = str(item['@quantityWithPrecision'])
                if quantity_str.startswith('-'):
                    quantity_str = quantity_str[1:]

                price_str = str(item['prices']['index_0']['@Price'])
                if price_str.startswith('-'):
                    price_str = price_str[1:]

                sub_items.append({
                    "type": "02" if void_item else "01",
                    "extra_description_2": line1,  # Line 1 (top)
                    "extra_description_1": line2,  # Line 2 (middle)
                    "item_description": line3,     # Line 3 (bottom, mandatory)
                    "product_code": item['Data']['@Code'],
                    "quantity": encode_float_number(quantity_str, 3),  # 2.000
                    "unit_price": encode_float_number(price_str, 2),  # 1.55
                    "unit": encode_measurement_unit(item['measureUnit']['@Code']),  # Units Kilos Grams Pounds Boxes
                    "tax": tax_ids[item['@_vatPercent']] if not tax_exempt else "0",  # tax id
                    "discount_type": discount_or_surcharge['type'] if discount_or_surcharge else "0",
                    "discount_amount": discount_or_surcharge['amount'] if discount_or_surcharge else "000",
                    "discount_percent": discount_or_surcharge['percent'] if discount_or_surcharge else "000",  # 10.50%
                })

        # Process TransMenu (combo deals/menus)
        if "TCPOS.FrontEnd.BusinessLogic.TransMenu" in xml_json_object[transaction_uuid]['data']['subItems']:
            menus = xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransMenu']
            # Handle both single menu and list of menus
            if not isinstance(menus, list):
                menus = [menus]

            for menu in menus:
                # Get menu description and price
                menu_description = menu['Data']['@Description']
                menu_price = menu['prices']['index_0']['@Price']
                menu_quantity = menu.get('@quantity', '1')
                print_details = menu['Data'].get('@PrintDetails', 'false') == 'true'

                # Extract sub-item names if PrintDetails is true
                sub_item_names = []
                if print_details and 'subItems' in menu:
                    menu_items = menu['subItems']['TCPOS.FrontEnd.BusinessLogic.TransMenuItem']
                    if not isinstance(menu_items, list):
                        menu_items = [menu_items]

                    for menu_item in menu_items:
                        if 'subItems' in menu_item:
                            articles = menu_item['subItems']['TCPOS.FrontEnd.BusinessLogic.TransArticle']
                            if not isinstance(articles, list):
                                articles = [articles]
                            for article in articles:
                                sub_item_names.append(article['Data']['@Description'])

                # Build description lines (menu name on line 1, sub-items on lines 2 and 3)
                line1 = menu_description  # Menu name at the top
                line2 = ""
                line3 = ""  # Must have content (mandatory)

                if sub_item_names:
                    # Concatenate sub-items with ", "
                    items_text = ", ".join(sub_item_names)
                    # Split into two lines if needed (max 48 chars per line)
                    if len(items_text) <= 48:
                        # Fits on one line - put on line 3 (mandatory)
                        line3 = items_text
                    else:
                        # Split at comma boundary near 48 chars
                        words = items_text.split(", ")
                        line2_parts = []
                        line3_parts = []
                        current_line = 2
                        current_length = 0

                        for word in words:
                            word_with_comma = word if word == words[-1] else word + ", "
                            if current_line == 2:
                                if current_length + len(word_with_comma) <= 48:
                                    line2_parts.append(word)
                                    current_length += len(word_with_comma)
                                else:
                                    current_line = 3
                                    line3_parts.append(word)
                                    current_length = len(word_with_comma)
                            else:
                                if current_length + len(word_with_comma) <= 48:
                                    line3_parts.append(word)
                                    current_length += len(word_with_comma)
                                else:
                                    break  # No more space

                        line2 = ", ".join(line2_parts) if line2_parts else ""
                        line3 = ", ".join(line3_parts) if line3_parts else ""

                # Ensure line3 is never empty (mandatory field)
                if not line3:
                    line3 = " "  # Space character if no sub-items

                # Strip negative signs for credit notes
                menu_quantity_str = str(menu_quantity)
                if menu_quantity_str.startswith('-'):
                    menu_quantity_str = menu_quantity_str[1:]

                menu_price_str = str(menu_price)
                if menu_price_str.startswith('-'):
                    menu_price_str = menu_price_str[1:]

                # Add the menu as a single line item with sub-items as descriptions
                sub_items.append({
                    "type": "01",
                    "extra_description_2": line1,  # Line 1 (top) - first part of sub-items
                    "extra_description_1": line2,  # Line 2 (middle) - second part of sub-items
                    "item_description": line3,     # Line 3 (bottom, mandatory) - menu name
                    "product_code": menu['Data'].get('@Code', ''),
                    "quantity": encode_float_number(menu_quantity_str, 3),
                    "unit_price": encode_float_number(menu_price_str, 2),
                    "unit": "Units",
                    "tax": "1",  # Assuming tax ID 1 (9%)
                    "discount_type": "0",
                    "discount_amount": "000",
                    "discount_percent": "000",
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


def get_discount(xml_json_object):
    """
    Extract transaction-level discount from TransDiscount element.
    Returns discount object for subtotal-level application.
    """
    logger.debug("Getting transaction discount...")
    try:
        # Check if there is a transaction-level discount
        if "TCPOS.FrontEnd.BusinessLogic.TransDiscount" in xml_json_object[transaction_uuid]['data']['subItems']:
            discount_element = xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransDiscount']

            # Extract the total discount amount (UnitDiscount)
            discount_amount = discount_element.get('@UnitDiscount', '0')

            # Strip negative sign for encoding
            if discount_amount.startswith('-'):
                discount_amount = discount_amount[1:]

            # Check if amount is zero
            if float(discount_amount) == 0:
                logger.debug("Discount amount is zero, skipping")
                return None

            discount = {
                "type": "0",  # Discount type
                "description": discount_element['Data'].get('@Description', 'Discount'),
                "amount": encode_float_number(discount_amount, 2),
                "percent": "000",  # Using amount, not percent
            }

            logger.debug("Transaction discount:")
            logger.debug(json.dumps(discount, indent=4))

            return discount

    except Exception as e:
        logger.error(f"Error extracting discount: {str(e)}")
        logger.error(traceback.format_exc())

    return None


def get_payment_details(xml_json_object):
    logger.debug("Getting payment details...")
    try:
        payment_details = []

        if type(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']) is list:

            for payment in xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']:
                # For credit notes, payment amounts are negative - strip the minus sign
                amount_str = str(payment['@amount'])
                if amount_str.startswith('-'):
                    amount_str = amount_str[1:]  # Remove leading minus
                    logger.debug(f"Credit note payment: stripped negative sign from {payment['@amount']} -> {amount_str}")

                payment_details.append({
                    "type": "1",
                    "method": payment_methods[payment['Data']['@Type']],
                    "description": payment['Data']['@Type'],
                    "amount": encode_float_number(amount_str, 2),
                })

        elif type(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']) is dict:
            # For credit notes, payment amounts are negative - strip the minus sign
            amount_str = str(xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']['@amount'])
            if amount_str.startswith('-'):
                amount_str = amount_str[1:]  # Remove leading minus
                logger.debug(f"Credit note payment: stripped negative sign from {xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']['@amount']} -> {amount_str}")

            payment_details.append({
                "type": "1",
                "method": payment_methods[xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']['Data']['@Type']],
                "description": xml_json_object[transaction_uuid]['data']['subItems']['TCPOS.FrontEnd.BusinessLogic.TransPayment']['Data']['@Type'],
                "amount": encode_float_number(amount_str, 2),
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
        discount = get_discount(xml_json_object)

        # Extract TransNum (TCPOS transaction/receipt number)
        trans_num = xml_json_object[transaction_uuid]['data'].get('@TransNum', '')

        # Check if this is a void/credit note transaction
        # A credit note has: negative total, OR StornoType="StornoChild", OR DeleteType with negative amounts
        is_credit_note = False

        # Method 1: Check for negative total (most reliable)
        total_str = xml_json_object[transaction_uuid]['data'].get('@total', '0')
        try:
            total_amount = float(total_str)
            if total_amount < 0:
                is_credit_note = True
                logger.info(f"Credit note detected via negative total: {total_amount}")
        except (ValueError, TypeError):
            pass

        # Method 2: Check for StornoChild (backup detection)
        if not is_credit_note:
            storno_details = xml_json_object[transaction_uuid]['data'].get('StornoDetails', {})
            if isinstance(storno_details, dict):
                storno_type = storno_details.get('@StornoType', '')
                if storno_type == 'StornoChild':
                    is_credit_note = True
                    logger.info(f"Credit note detected via StornoType: {storno_type}")

        return items, payments, service_charge, tips, trans_num, is_credit_note, discount

    except Exception as e:
        logger.error("Error: " + str(e))

    return None, None, None, None, None, False, None


def migrate_renamed_files(transactions_folder):
    """
    One-time migration: Convert old renamed files back to original names
    and create marker files instead
    """
    for root, dirs, files in os.walk(transactions_folder):
        for file in files:
            # Handle .xml.processed files
            if file.endswith('.xml.processed'):
                original_name = file[:-10]  # Remove .processed
                old_path = os.path.join(root, file)
                new_path = os.path.join(root, original_name)
                marker_path = os.path.join(root, original_name + '.processed')

                # Rename back to original
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    # Create marker
                    with open(marker_path, 'w') as f:
                        f.write(f"Migrated at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"Migrated: {file} -> {original_name}")

            # Handle .xml.skipped files
            elif file.endswith('.xml.skipped'):
                original_name = file[:-8]  # Remove .skipped
                old_path = os.path.join(root, file)
                new_path = os.path.join(root, original_name)
                marker_path = os.path.join(root, original_name + '.skipped')

                # Rename back to original
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    # Create marker
                    with open(marker_path, 'w') as f:
                        f.write(f"Migrated at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"Migrated: {file} -> {original_name}")


def files_watchdog():
    config = json.load(open('config.json'))

    if config['printer']['name'] == 'cts310ii':
        import cts310ii

    # Run one-time migration
    logger.info("Running file migration...")
    migrate_renamed_files(config['pos']['transactions_folder'])
    logger.info("File migration complete")

    while True:
        for root, dirs, files in os.walk(config['pos']['transactions_folder']):
            for file in files:
                try:
                    if file.endswith('.xml'):
                        # Skip if already processed or skipped (marker file exists)
                        marker_processed = os.path.join(root, file + '.processed')
                        marker_skipped = os.path.join(root, file + '.skipped')

                        if os.path.exists(marker_processed) or os.path.exists(marker_skipped):
                            continue  # Already processed, skip

                        logger.debug("File found: " + os.path.join(root, file))
                        items, payments, service_charge, tips, trans_num, is_credit_note, discount = tcpos_parse_transaction(os.path.join(root, file))

                        if items and payments:
                            cts310ii.print_document(items, payments, service_charge, tips, trans_num, is_credit_note, discount)

                            # Create marker file (keep original for TCPOS refunds)
                            with open(marker_processed, 'w') as f:
                                f.write(f"Processed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                            logger.info(f"File processed: {file}")

                        else:
                            logger.debug("File skipped: " + os.path.join(root, file))
                            # Create skipped marker file
                            with open(marker_skipped, 'w') as f:
                                f.write(f"Skipped at {time.strftime('%Y-%m-%d %H:%M:%S')}")
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
