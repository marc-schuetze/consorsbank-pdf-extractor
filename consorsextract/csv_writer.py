"""
CSV output formatting and file writing
"""
import csv


def write_to_csv(data, csv_file):
    """
    Write transaction data to CSV file.
    
    Creates the file with headers if it doesn't exist, otherwise appends data.
    
    Args:
        data (dict): Transaction data with keys: transaction_date, transaction_id,
                    value_date, name, iban, amount, comment
        csv_file (str): Path to output CSV file
    """
    if data is None:
        return

    with open(csv_file, "a", newline="", encoding="utf-8") as file:
        fieldnames = [
            "transaction_date", 
            "transaction_id", 
            "value_date", 
            "name", 
            "iban", 
            "amount", 
            "comment"
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write header if file is empty
        if file.tell() == 0:
            writer.writeheader()

        writer.writerow(data)
