# Consorsbank PDF Extractor

Extract transaction data from [Consorsbank](https://www.consorsbank.de/home) PDF statements and convert to CSV format for tax preparation and financial analysis.

## What it does

This tool processes PDF bank statements from [Consorsbank](https://www.consorsbank.de/home) and extracts transaction information into a clean CSV format. Perfect for tax preparation, expense tracking, or importing into accounting software.

## Features

- ✅ Extract transactions from Consorsbank PDF statements
- ✅ Handle VISA card transactions and regular bank transfers
- ✅ Clean German formatting (amounts, dates)
- ✅ Command-line interface with progress reporting
- ✅ Detailed logging for troubleshooting

## Installation

### Option 1: Using Poetry (recommended)
```bash
git clone https://github.com/scharc/consorsbank-pdf-extractor.git
cd consorsbank-pdf-extractor
poetry install
```

### Option 2: Using pip
```bash
git clone https://github.com/scharc/consorsbank-pdf-extractor.git
cd consorsbank-pdf-extractor
pip install -r requirements.txt
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

- `--input`, `-i`: Directory containing PDF files (default: `pdfs/`)
- `--output`, `-o`: Output CSV file (default: `output.csv`)
- `--verbose`, `-v`: Enable detailed logging
- `--help`, `-h`: Show help message

## CSV Output Format

The generated CSV contains these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `transaction_date` | When the transaction occurred | `01.02.2024` |
| `transaction_id` | Bank reference number | `12345` |
| `value_date` | When money was actually moved | `03.02.2024` |
| `name` | Recipient or sender name | `REWE Supermarket` |
| `iban` | IBAN or card reference | `DE89370400440532013000` |
| `amount` | Transaction amount (negative = debit) | `-45.67` |
| `comment` | Additional transaction details | `Payment for groceries` |

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
├── consorsextract/           # Main package
│   ├── __init__.py          # PDF reading functions
│   ├── parser.py            # Text cleaning and data extraction
│   └── csv_writer.py        # CSV output formatting
├── extract.py               # CLI interface
├── pdfs/                    # Place your PDF files here
├── requirements.txt         # Dependencies for pip users
└── pyproject.toml          # Poetry configuration
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