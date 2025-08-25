"""
Consorsbank PDF Extractor Package

Extract transaction data from Consorsbank PDF statements and convert to CSV format.
"""

import logging
import PyPDF2

def extract_pdf_to_text(pdf_file_path):
    """
    Extract text content from a PDF file using PyPDF2 v3.x.
    
    Args:
        pdf_file_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text content, or None if extraction fails
    """
    try:
        with open(pdf_file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                logging.error(f"PDF file {pdf_file_path} is password-protected")
                return None
            
            text_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    text_parts.append(page_text)
                except Exception as e:
                    logging.warning(f"Could not extract text from page {page_num + 1}: {e}")
                    continue
            
            extracted_text = '\n'.join(text_parts)
            
            if not extracted_text.strip():
                logging.error(f"No text content extracted from {pdf_file_path}")
                return None
                
            logging.debug(f"Extracted {len(extracted_text)} characters from {pdf_file_path}")
            return extracted_text
            
    except FileNotFoundError:
        logging.error(f"PDF file not found: {pdf_file_path}")
        return None
    except Exception as e:
        logging.error(f"Error reading PDF file {pdf_file_path}: {e}")
        return None