#!/usr/bin/env python3
"""
Consorsbank PDF Extractor

Extract transaction data from Consorsbank PDF statements and convert to CSV.
"""
import argparse
import logging
import os
import sys

from consorsextract import extract_pdf_to_text
from consorsextract.parser import clean_text, extract_data, find_current_year_from_text
from consorsextract.csv_writer import write_to_csv


def setup_logging(verbose=False):
    """
    Set up logging configuration.
    
    Args:
        verbose (bool): Enable debug-level logging if True
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=log_level,
        handlers=[
            logging.FileHandler('pdf_to_csv.log'),
            logging.StreamHandler()
        ]
    )


def process_pdf_file(pdf_file_path, csv_file):
    """
    Process a single PDF file and extract transactions to CSV.
    
    Args:
        pdf_file_path (str): Path to the PDF file
        csv_file (str): Path to output CSV file
        
    Returns:
        int: Number of transactions extracted
    """
    logging.info(f"Processing PDF: {pdf_file_path}")
    
    # Extract text from PDF
    extracted_text = extract_pdf_to_text(pdf_file_path)
    if not extracted_text:
        logging.error(f"Failed to extract text from {pdf_file_path}")
        return 0

    # Find the current year from the PDF
    current_year = find_current_year_from_text(extracted_text)

    # Clean the extracted text and separate into blocks
    blocks = clean_text(extracted_text)
    
    # Extract data from each block and write to CSV
    transaction_count = 0
    for block in blocks:
        data = extract_data(block, current_year)
        if data:
            write_to_csv(data, csv_file)
            transaction_count += 1
    
    logging.info(f"Extracted {transaction_count} transactions from {pdf_file_path}")
    return transaction_count


def main():
    """
    Main function to handle CLI arguments and process PDFs.
    """
    parser = argparse.ArgumentParser(
        description="Extract transaction data from Consorsbank PDF statements to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract.py --input pdfs/ --output transactions.csv
  python extract.py -i statements/ -o 2024_taxes.csv --verbose
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        default='pdfs',
        help='Directory containing PDF files (default: pdfs/)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='output.csv',
        help='Output CSV file (default: output.csv)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Check if input directory exists
    if not os.path.exists(args.input):
        logging.error(f"Input directory '{args.input}' does not exist")
        sys.exit(1)
    
    if not os.path.isdir(args.input):
        logging.error(f"'{args.input}' is not a directory")
        sys.exit(1)
    
    # Find all PDF files in the input directory
    pdf_files = []
    for filename in os.listdir(args.input):
        if filename.lower().endswith(".pdf"):
            pdf_files.append(os.path.join(args.input, filename))
    
    if not pdf_files:
        logging.error(f"No PDF files found in '{args.input}'")
        sys.exit(1)
    
    logging.info(f"Found {len(pdf_files)} PDF file(s) to process")
    
    # Remove existing output file to start fresh
    if os.path.exists(args.output):
        os.remove(args.output)
        logging.info(f"Removed existing output file: {args.output}")
    
    # Process each PDF file
    total_transactions = 0
    successful_files = 0
    
    for pdf_file in pdf_files:
        try:
            transaction_count = process_pdf_file(pdf_file, args.output)
            total_transactions += transaction_count
            if transaction_count > 0:
                successful_files += 1
        except Exception as e:
            logging.error(f"Error processing {pdf_file}: {e}")
    
    # Summary
    logging.info(f"Processing complete:")
    logging.info(f"  Files processed successfully: {successful_files}/{len(pdf_files)}")
    logging.info(f"  Total transactions extracted: {total_transactions}")
    logging.info(f"  Output written to: {args.output}")
    
    if successful_files == 0:
        logging.error("No files were processed successfully")
        sys.exit(1)


if __name__ == "__main__":
    main()
