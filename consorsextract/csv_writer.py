"""
CSV output formatting and file writing.
"""
import csv

FIELDNAMES = [
    "booking_date",
    "value_date",
    "type",
    "pnnr",
    "name",
    "bic",
    "iban",
    "amount",
    "purpose",
    "source_file",
]


def write_transactions(transactions, csv_file, german=True):
    """Write all transactions to ``csv_file`` (overwrites), with a header row.

    Args:
        transactions: list of transaction dicts.
        csv_file: output path.
        german (bool): if True (default) write in the German spreadsheet
            convention — ``;`` field separator and comma decimal (e.g.
            ``-300,00``) — so LibreOffice/Excel in a German locale recognise the
            amount column as numbers. If False, use ``,`` separator and dot
            decimal (e.g. ``-300.00``).
    """
    delimiter = ";" if german else ","

    with open(csv_file, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=FIELDNAMES, delimiter=delimiter, extrasaction="ignore"
        )
        writer.writeheader()
        for txn in transactions:
            row = dict(txn)
            amount = f"{txn['amount']:.2f}"
            if german:
                amount = amount.replace(".", ",")
            row["amount"] = amount
            writer.writerow(row)
