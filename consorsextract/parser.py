"""
Text cleaning and transaction data extraction for Consorsbank PDFs
"""
import logging

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


def extract_data(block, current_year):
    """
    Extract transaction data from a text block.
    
    Parses transaction date, value date, transaction ID, amount, name, 
    IBAN, and comment from a formatted text block.
    
    Args:
        block (str): Transaction text block
        current_year (str): Year to append to dates (e.g., "2024")
        
    Returns:
        dict: Transaction data with keys: transaction_date, transaction_id, 
              value_date, name, iban, amount, comment
        None: If block cannot be parsed
    """
    # Remove empty lines
    lines = [line.strip() for line in block.split("\n") if line.strip() != ""]
    
    # Extract date, transaction ID, another date, name, IBAN, and amount
    first_line = lines[0].split()
    if len(first_line) < 3:
        logging.error("Invalid first line format")
        return None

    # Parse the concatenated date/ID string from the PDF
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
        logging.error("No IBAN found")
        return None

    iban = extract_iban(iban_line)
    if not iban:
        logging.error("Invalid IBAN format")
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
