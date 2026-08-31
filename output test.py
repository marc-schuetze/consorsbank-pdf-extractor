import PyPDF2
from consorsextract import extract_pdf_to_text
from consorsextract.parser import clean_text

pdf_path = input("Enter PDF path: ")
text = extract_pdf_to_text(pdf_path)
blocks = clean_text(text)

for i, block in enumerate(blocks[:2]):
    print(f"\n=== BLOCK {i+1} ===")
    print(repr(block))
    print("\n--- FORMATTED ---")
    print(block)