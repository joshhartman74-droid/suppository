#!/usr/bin/env python3
"""
Script to extract the first 200 pages of a PDF into an Excel file.
- Column A: Page Number
- Column B: Total Pages (200)
- Column C: Full text content of each page
"""

import pdfplumber
import openpyxl
from openpyxl import Workbook

def extract_pdf_to_excel(pdf_path, output_excel_path, start_page=1, end_page=200):
    """
    Extract text from PDF pages and save to Excel.
    """
    print(f"Opening PDF: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages in PDF: {total_pages}")
        
        # Limit end_page to the actual number of pages
        end_page = min(end_page, total_pages)
        
        # Create a new Excel workbook
        wb = Workbook()
        ws = wb.active
        
        # Write headers
        ws.append(["Page Number", "Total Pages", "Page Text"])
        
        # Process each page
        for page_num in range(start_page, end_page + 1):
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            
            # Write to Excel
            ws.append([page_num, end_page, text])
            
            # Print progress
            if page_num % 10 == 0:
                print(f"Processed page {page_num}/{end_page}")
        
        # Save the Excel file
        wb.save(output_excel_path)
        print(f"Excel file saved to: {output_excel_path}")

if __name__ == "__main__":
    pdf_path = "pdf_uploads/output_bookmarked.pdf"
    output_excel_path = "pdf_uploads/output_bookmarked_first_200.xlsx"
    
    extract_pdf_to_excel(pdf_path, output_excel_path, start_page=1, end_page=200)
