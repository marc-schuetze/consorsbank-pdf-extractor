"""
Text cleaning and transaction data extraction for Consorsbank PDFs
Supports both 2016 format (multi-line) and 2021+ format (flattened)
"""
import logging
import re

# Consorsbank-specific text patterns
BANK_HEADER_PATTERN = "ConsorsbankisteineeingetrageneMarkederBNPParibasS.A."
TEXT_PURPOSE_PATTERN = "Text/Verwendungszweck"
NOTICE_PATTERN = "HinweisfürKontoauszüge"
DATE_HEADER_PREFIX = "Datum "


def clean_text(text):
    """
    Clean extracted PDF text and separate into transaction blocks.
    
    Removes Consorsbank header text, notices, and other non-transaction content.
    
    Args:
        text (str): Raw text extracted from PDF
        
    Returns:
        list: List of cleaned transaction blocks
    """
    cleaned_lines = []
    remove_block = False
    skip_block = False
    
    for line in text.split('\n'):
        if line.startswith(BANK_HEADER_PATTERN):
            remove_block = True
        elif TEXT_PURPOSE_PATTERN in line:
            remove_block = False
            cleaned_lines.append("\n")  # Add a new line after the removed block
        elif NOTICE_PATTERN in line:
            skip_block = True
        elif skip_block and line.strip() == "":
            skip_block = False
            cleaned_lines.append("\n")  # Add a new line after the removed block
        elif not remove_block and not skip_block:
            cleaned_lines.append(line)
    
    # Remove lines starting with "***"
    cleaned_lines = [line for line in cleaned_lines if not line.startswith("***")]
    # Remove empty lines
    cleaned_lines = [line for line in cleaned_lines if line.strip() != ""]
    # Separate the blocks
    blocks = separate_blocks(cleaned_lines)
    return blocks


def separate_blocks(cleaned_lines):
    """
    Separate cleaned lines into individual transaction blocks.
    
    Blocks are identified by lines containing '<' (IBAN) or 'VISA' markers.
    
    Args:
        cleaned_lines (list): List of cleaned text lines
        
    Returns:
        list: List of transaction blocks as strings
    """
    blocks = []
    start_index = 0
    
    # Iterate over the lines to find the start of each block
    for i, line in enumerate(cleaned_lines):
        if "<" in line or "VISA" in line:
            # If we find a '<', check if it's the first block or not
            if start_index != 0:
                # Extract the previous block and add it to the list of blocks
                block = "\n".join(cleaned_lines[start_index:i-2])
                blocks.append(block)
            # Update the start index for the next block
            start_index = i - 2 if i - 2 >= 0 else 0
    
    # Handle the last block if it doesn't contain a '<'
    if start_index < len(cleaned_lines):
        last_block = "\n".join(cleaned_lines[start_index:])
        blocks.append(last_block)
    
    return blocks


def detect_format(block):
    """
    Detect transaction format version (2016 vs 2021+).
    
    2016 format: Multi-line with transaction type on first line, BIC/IBAN on separate line
    2021+ format: Flattened, date concatenated with ID and amount
    
    Args:
        block (str): Transaction text block
        
    Returns:
        str: "2016" or "2021" indicating format version
    """
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    
    if not lines:
        return None
    
    first_line = lines[0]
    
    # 2021+ format: starts with date like "30.09.21 . 2021" OR has pattern with dates and amount
    if re.match(r'^\d{2}\.\d{2}\.\d{2}\s*\.\s*\d{4}', first_line):
        return "2021"
    
    # 2021+ format variant: TYPE followed by dates and amounts (e.g., GEBUEHREN, DAUERAUFTRAGNR, GEHALT/RENTE)
    if re.search(r'\d{2}\.\d{2}\.\d{4,5}\d{2}\.\d{2}\.\s*[\d.,+-]+', first_line):
        return "2021"
    
    # 2016 format: starts with transaction type (LASTSCHRIFT, EURO-UEBERW., etc)
    if any(t in first_line for t in ["LASTSCHRIFT", "EURO-UEBERW.", "UEBERWEISUNG"]):
        return "2016"
    
    return None


def extract_data(block, current_year):
    """
    Extract transaction data from a text block.
    
    Auto-detects format and routes to appropriate parser.
    
    Args:
        block (str): Transaction text block
        current_year (str): Year to append to dates (e.g., "2024")
        
    Returns:
        dict: Transaction data with keys: transaction_date, transaction_id,
              value_date, name, iban, amount, comment
        None: If block cannot be parsed
    """
    fmt = detect_format(block)
    
    if fmt == "2016":
        return extract_data_2016(block, current_year)
    elif fmt == "2021":
        return extract_data_2021(block, current_year)
    else:
        logging.warning(f"Unknown format in block: {block[:50]}")
        return None


def extract_data_2016(block, current_year):
    """
    Extract transaction data from 2016 format (multi-line).
    
    Extracts: date, amount, name, comment. IBAN left empty.
    
    Format:
        TRANSACTION_TYPE DATE PNNUM DATE AMOUNT
            RECIPIENT_NAME
           <BIC_CODE>    IBAN
           REFERENCE_LINES...
    
    Args:
        block (str): Transaction text block
        current_year (str): Year to append to dates
        
    Returns:
        dict: Transaction data or None if parsing fails
    """
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    
    if len(lines) < 2:
        logging.error("2016 format: Block too short")
        return None
    
    try:
        # Parse first line: extract date and amount
        # Format varies, but typically: TYPE DATE PNNUM DATE AMOUNT
        first_line = lines[0]
        
        # Extract dates and amount using regex to be robust
        # Look for patterns like "15.11." and amounts like "98,61-" or "1.250,00-"
        date_pattern = r'(\d{2}\.\d{2}\.)'
        amount_pattern = r'(\d+[.,]\d+[+-]?)'
        
        dates = re.findall(date_pattern, first_line)
        amounts = re.findall(amount_pattern, first_line)
        
        if len(dates) < 2 or not amounts:
            logging.error(f"2016 format: Could not parse dates/amount from: {first_line}")
            return None
        
        transaction_date_str = dates[0]  # First date
        value_date_str = dates[1]  # Second date
        amount_str = amounts[-1]  # Last amount found
        
        # Add year to dates
        transaction_date = transaction_date_str + current_year
        value_date = value_date_str + current_year
        
        # Parse amount (German format: comma as decimal, +/- for sign)
        amount = amount_str.replace(".", "").replace(",", ".")
        if amount.endswith("-"):
            amount = "-" + amount[:-1]
        elif amount.endswith("+"):
            amount = amount[:-1]
        
        # Extract recipient name (line 2)
        name = lines[1]
        
        # Extract comment from lines 3 onwards
        comment_lines = lines[2:]
        comment = " ".join(comment_lines)
        
        # Simple transaction ID from first line parts
        transaction_id = ""
        
        return {
            "transaction_date": transaction_date,
            "transaction_id": transaction_id,
            "value_date": value_date,
            "name": name,
            "iban": "",  # Not extracted for 2016
            "amount": amount,
            "comment": comment,
        }
        
    except Exception as e:
        logging.error(f"2016 format: Error parsing block: {e}")
        return None


def extract_data_2021(block, current_year):
    """
    Extract transaction data from 2021+ format (flattened).
    
    Format: DATE . YEAR RECIPIENT NAME IBAN AMOUNT RECIPIENT REFERENCE...
    
    Args:
        block (str): Transaction text block
        current_year (str): Year to append to dates
        
    Returns:
        dict: Transaction data or None if parsing fails
    """
    lines = [line.strip() for line in block.split("\n") if line.strip() != ""]
    
    if len(lines) < 1:
        logging.error("2021 format: Empty block")
        return None
    
    try:
        # Parse the concatenated date/ID string from the PDF
        first_line = lines[0].split()
        if len(first_line) < 3:
            logging.error("2021 format: Invalid first line format")
            return None

        date_value = first_line[1]
        transaction_date = date_value[:5] + "." + current_year
        transaction_id = date_value[5:10]
        value_date = date_value[10:] + current_year

        # Parse amount with German formatting
        amount = first_line[2]
        amount = amount.replace(".", "").strip()
        if amount.endswith("-"):
            amount = "-" + amount[:-1]
        elif amount.endswith("+"):
            amount = amount[:-1]

        # Extract recipient/sender name
        name = lines[1]

        # Extract IBAN or card reference
        iban_line = None
        for line in lines:
            if "<" in line:
                iban_line = line
                break
            elif "VISA" in line:
                iban_line = line
                break
        
        if iban_line is None:
            logging.error("2021 format: No IBAN found")
            return None

        iban = extract_iban(iban_line)
        if not iban:
            logging.error("2021 format: Invalid IBAN format")
            return None

        # Extract comment from remaining lines
        comment_lines = lines[3:]
        comment = " ".join(comment_lines)

        return {
            "transaction_date": transaction_date,
            "transaction_id": transaction_id,
            "value_date": value_date,
            "name": name,
            "iban": iban,
            "amount": amount,
            "comment": comment,
        }
        
    except Exception as e:
        logging.error(f"2021 format: Error parsing block: {e}")
        return None


def extract_iban(line):
    """
    Extract IBAN or card reference from a line containing angle brackets.
    
    Args:
        line (str): Text line containing IBAN in format <IBAN> or <VISA...>
        
    Returns:
        str: Extracted IBAN or card reference
    """
    return line.split('<')[-1].replace('>', '').strip()


def find_current_year_from_text(extracted_text):
    """
    Extract the current year from the PDF's date header.
    
    Looks for lines starting with "Datum " and extracts the year.
    
    Args:
        extracted_text (str): Full PDF text content
        
    Returns:
        str: Four-digit year (e.g., "2024")
    """
    current_date_line = None
    for line in extracted_text.split('\n'):
        if line.startswith(DATE_HEADER_PREFIX):
            current_date_line = line
            break
    
    if current_date_line:
        date_str = current_date_line.split()[1]
        day, month, year = date_str.split('.')
        current_date = f"{day}.{month}.{year}"
        logging.info(f"Current date: {current_date}")
        current_year = "20" + year
        return current_year
    else:
        logging.error("No current date found")
        return "2023"  # default year if not found