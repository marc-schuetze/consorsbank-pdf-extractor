#!/usr/bin/env python3
"""
Consorsbank PDF Extractor

Extract transaction data from Consorsbank Girokonto PDF statements into one CSV,
reconciling each statement against its printed running balances.
"""
import argparse
import logging
import os
import sys

from consorsextract import extract_pdf_to_text, PdftotextNotFound
from consorsextract.parser import (
    find_balance_after_label,
    find_current_year_from_text,
    parse_statement,
    reconcile,
)
from consorsextract.csv_writer import write_transactions


def setup_logging(verbose=False):
    """Configure logging to stderr and a log file."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=log_level,
        handlers=[logging.FileHandler("pdf_to_csv.log"), logging.StreamHandler()],
    )


def find_pdf_files(input_dir):
    """Return a sorted list of all .pdf paths under ``input_dir`` (recursive)."""
    pdf_files = []
    for root, _dirs, files in os.walk(input_dir):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, filename))
    return sorted(pdf_files)


def process_pdf_file(pdf_file_path):
    """Extract and reconcile a single statement.

    Returns:
        tuple(list[dict], dict): (transactions, reconciliation summary). The
        summary has: checkpoints, mismatches (count), has_balances (bool).
    """
    filename = os.path.basename(pdf_file_path)
    logging.info(f"Processing: {filename}")

    text = extract_pdf_to_text(pdf_file_path)
    if not text:
        logging.error(f"Failed to extract text from {filename}")
        return [], {"balance_ok": None, "cp_mismatches": 0, "has_balances": False}

    year = find_current_year_from_text(text)
    if year is None:
        # Statements without a transaction body (closing-statement / interest
        # documents) have no date header — skip them quietly.
        logging.debug(f"No statement date header in {filename}; skipping")
        return [], {"balance_ok": None, "cp_mismatches": 0, "has_balances": False}

    transactions, checkpoints = parse_statement(text, year, filename)
    opening = find_balance_after_label(text, "Buchungssaldo alt")
    closing = find_balance_after_label(text, "Buchungssaldo neu")

    # Authoritative check: opening balance + all transactions == closing balance.
    balance_ok = None
    if opening is not None and closing is not None:
        computed = opening + sum(t["amount"] for t in transactions)
        balance_ok = abs(computed - closing) < 0.005
        if not balance_ok:
            logging.warning(
                f"  BALANCE MISMATCH {filename}: "
                f"opening {opening:.2f} + transactions = {computed:.2f}, "
                f"but closing balance is {closing:.2f} "
                f"(diff {computed - closing:+.2f})"
            )

    # Secondary check: each printed running checkpoint. These can occasionally
    # disagree with the closing balance due to a bank-side value-date ordering
    # quirk even when the statement is fully captured, so they are advisory only.
    results = reconcile(transactions, checkpoints, opening_balance=opening)
    cp_mismatches = [r for r in results if not r["ok"]]
    for r in cp_mismatches:
        logging.debug(
            f"  checkpoint diff {filename} @ {r['date']}: "
            f"computed {r['actual']:.2f} vs printed {r['expected']:.2f}"
        )

    logging.info(
        f"  {len(transactions)} transactions, balance_ok={balance_ok}, "
        f"{len(cp_mismatches)} checkpoint diff(s)"
    )
    return transactions, {
        "balance_ok": balance_ok,
        "cp_mismatches": len(cp_mismatches),
        "has_balances": opening is not None and closing is not None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract transactions from Consorsbank PDF statements to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract.py --input pdfs/ --output transactions.csv
  python extract.py -i statements/ -o 2024_taxes.csv --verbose
        """,
    )
    parser.add_argument("--input", "-i", default="pdfs",
                        help="Directory containing PDF files, searched recursively (default: pdfs/)")
    parser.add_argument("--output", "-o", default="output.csv",
                        help="Output CSV file (default: output.csv)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--format", choices=["de", "en"], default="de",
                        help="CSV number/separator format: 'de' (semicolon, "
                             "comma decimal — LibreOffice/Excel in a German "
                             "locale; default) or 'en' (comma, dot decimal)")
    args = parser.parse_args()

    setup_logging(args.verbose)

    if not os.path.isdir(args.input):
        logging.error(f"Input '{args.input}' is not a directory")
        sys.exit(1)

    pdf_files = find_pdf_files(args.input)
    if not pdf_files:
        logging.error(f"No PDF files found under '{args.input}'")
        sys.exit(1)

    logging.info(f"Found {len(pdf_files)} PDF file(s) to process")

    all_transactions = []
    files_with_txns = 0
    files_balance_failed = 0
    files_unverified = 0

    for pdf_file in pdf_files:
        try:
            transactions, summary = process_pdf_file(pdf_file)
        except PdftotextNotFound as e:
            logging.error(str(e))
            sys.exit(2)
        except Exception as e:
            logging.error(f"Error processing {os.path.basename(pdf_file)}: {e}")
            continue

        if transactions:
            files_with_txns += 1
            all_transactions.extend(transactions)
        if summary["balance_ok"] is False:
            files_balance_failed += 1
        if transactions and not summary["has_balances"]:
            files_unverified += 1

    # Sort chronologically by booking date (DD.MM.YYYY) then keep statement order.
    def sort_key(t):
        d, m, y = t["booking_date"].split(".")
        return (y, m, d)

    all_transactions.sort(key=sort_key)

    write_transactions(all_transactions, args.output, german=(args.format == "de"))

    total = sum(t["amount"] for t in all_transactions)
    logging.info("Processing complete:")
    logging.info(f"  PDFs scanned:                  {len(pdf_files)}")
    logging.info(f"  Statements with transactions:  {files_with_txns}")
    logging.info(f"  Total transactions:            {len(all_transactions)}")
    logging.info(f"  Net sum of all amounts:        {total:,.2f} EUR")
    logging.info(f"  Statements failing balance check: {files_balance_failed}")
    if files_unverified:
        logging.info(f"  Statements not balance-verified:  {files_unverified}")
    logging.info(f"  Output written to:             {args.output}")

    if files_balance_failed:
        logging.warning("Some statements did not reconcile - review the warnings above.")


if __name__ == "__main__":
    main()
