# Consorsbank PDF Extractor

Extract transaction data from [Consorsbank](https://www.consorsbank.de/home) PDF statements and convert to CSV format for tax preparation and financial analysis.

## What it does

This tool processes PDF bank statements from [Consorsbank](https://www.consorsbank.de/home) and extracts transaction information into a clean CSV format. Perfect for tax preparation, expense tracking, or importing into accounting software.

## Features

- ✅ Extract transactions from Consorsbank Girokonto PDF statements
- ✅ Handles **both statement layouts** (pre-2025 spaced and 2025+ compact)
- ✅ Handles transfers, direct debits, VISA card debits, standing orders, fees
- ✅ Clean German formatting → signed decimal amounts, ISO-style fields
- ✅ **Balance reconciliation**: every statement is checked against its own
  printed opening/closing balance, so missed or misread transactions are flagged
- ✅ Recursive input scan, single combined CSV, detailed logging

## How it works

Text is extracted with poppler's `pdftotext -layout`, which preserves the
column layout of the statement. Consorsbank changed its PDF format over the
years — older statements keep spaces between fields while newer ones run numbers
together — and `-layout` normalises both into the same aligned text so one
parser handles every era. There are **no Python package dependencies**.

## Installation

### Prerequisite: poppler (`pdftotext`)
```bash
sudo apt install poppler-utils      # Debian/Ubuntu
brew install poppler                # macOS
```

### Then clone (Poetry optional — the code is pure stdlib)
```bash
git clone https://github.com/scharc/consorsbank-pdf-extractor.git
cd consorsbank-pdf-extractor
poetry install        # optional; or just run with system python3
```

## Usage

### Basic usage
```bash
python extract.py --input pdfs/ --output transactions.csv
```

### With options
```bash
python extract.py --input statements/ --output 2024_taxes.csv --verbose
```

### CLI Options

- `--input`, `-i`: Directory containing PDF files, **searched recursively** (default: `pdfs/`)
- `--output`, `-o`: Output CSV file (default: `output.csv`)
- `--verbose`, `-v`: Enable detailed logging
- `--help`, `-h`: Show help message

## CSV Output Format

The generated CSV contains these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `booking_date` | Buchungsdatum (Datum) | `01.02.2024` |
| `value_date` | Valutadatum (Wert) | `03.02.2024` |
| `type` | Buchungsart | `EURO-UEBERW.` |
| `pnnr` | Posting code (PNNr) | `8420` |
| `name` | Recipient or sender name | `REWE Supermarket` |
| `bic` | BIC of counterparty | `GENODEF1S15` |
| `iban` | IBAN of counterparty (empty for VISA card debits) | `DE89370400440532013000` |
| `amount` | Signed decimal amount (negative = debit) | `-45.67` |
| `purpose` | Verwendungszweck / details | `Payment for groceries` |
| `source_file` | Originating PDF filename | `KONTOAUSZUG_..._dat20240201_id....pdf` |

Rows are sorted chronologically by booking date across all statements.

## Supported Transaction Types

- ✅ Regular bank transfers (SEPA)
- ✅ VISA card payments
- ✅ Direct debits
- ✅ Standing orders

## Limitations

- **Consorsbank only**: Designed specifically for [Consorsbank](https://www.consorsbank.de/home) PDF statement format
- **German PDFs**: Expects German date/amount formatting
- **Limited transaction types**: May not handle securities trading or complex transactions
- **Manual verification recommended**: Always check extracted data against original statements

## Troubleshooting

### No transactions extracted
- Check that PDFs are from Consorsbank
- Ensure PDFs contain transaction data (not just account summary)
- Run with `--verbose` to see detailed processing information

### Incorrect amounts or dates
- Verify the PDF uses standard German formatting
- Check the log file for parsing errors

### Processing errors
- Ensure PDFs are not password-protected
- Check that PDF files are not corrupted

## File Structure

```
consorsbank-pdf-extractor/
├── consorsextract/          # Main package
│   ├── __init__.py          # PDF → text via `pdftotext -layout`
│   ├── parser.py            # Transaction parsing + balance reconciliation
│   └── csv_writer.py        # CSV output formatting
├── extract.py               # CLI interface
├── pdfs/                    # Place your PDF files here (scanned recursively)
└── pyproject.toml           # Poetry configuration (no runtime deps)
```

## Contributing

Found a bug or want to add support for other transaction types? Feel free to:

1. Open an issue describing the problem
2. Submit a pull request with improvements
3. Share sample data (anonymized) that fails to parse correctly

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is provided as-is for convenience. Always verify extracted data against your original bank statements for accuracy, especially when using for tax purposes or financial reporting.

## Development

### Adding new transaction types
1. Check the parsing logic in `consorsextract/parser.py`
2. Add new patterns to handle different transaction formats
3. Test with sample PDFs
4. Update documentation

### Running tests
```bash
# Test with your own PDFs
python extract.py --input test_pdfs/ --output test_output.csv --verbose
```