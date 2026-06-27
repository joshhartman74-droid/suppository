#!/usr/bin/env python3
"""
Example usage of the PDF Page Filter

This script demonstrates how to use the pdf_page_filter_practical.py module
to filter PDF pages based on page indicators.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from pdf_page_filter_practical import (
    main_async, 
    OCRBackend, 
    PDFPageProcessor, 
    TesseractOCRClient,
    MistralOCRClient,
    EasyOCRClient
)


async def example_with_tesseract():
    """Example using Tesseract OCR (local, no API key needed)"""
    print("=== Example with Tesseract OCR ===")
    
    # You would need a sample PDF file
    pdf_path = "sample.pdf"  # Replace with your PDF path
    output_pdf = "filtered_tesseract.pdf"
    output_json = "page_schemas_tesseract.json"
    
    if not os.path.exists(pdf_path):
        print(f"Sample PDF not found: {pdf_path}")
        print("Please create a sample.pdf file or specify the path to your PDF")
        return
    
    try:
        await main_async(
            pdf_path=pdf_path,
            output_pdf=output_pdf,
            backend="tesseract",
            output_json=output_json,
            max_workers=2,
            dpi=200  # Lower DPI for faster processing
        )
    except Exception as e:
        print(f"Error: {e}")


async def example_with_mistral(api_key: str):
    """Example using Mistral AI API"""
    print("=== Example with Mistral OCR ===")
    
    pdf_path = "sample.pdf"  # Replace with your PDF path
    output_pdf = "filtered_mistral.pdf"
    output_json = "page_schemas_mistral.json"
    
    if not os.path.exists(pdf_path):
        print(f"Sample PDF not found: {pdf_path}")
        return
    
    try:
        await main_async(
            pdf_path=pdf_path,
            output_pdf=output_pdf,
            api_key=api_key,
            backend="mistral",
            output_json=output_json,
            max_workers=4
        )
    except Exception as e:
        print(f"Error: {e}")


async def example_with_easyocr():
    """Example using EasyOCR"""
    print("=== Example with EasyOCR ===")
    
    pdf_path = "sample.pdf"  # Replace with your PDF path
    output_pdf = "filtered_easyocr.pdf"
    output_json = "page_schemas_easyocr.json"
    
    if not os.path.exists(pdf_path):
        print(f"Sample PDF not found: {pdf_path}")
        return
    
    try:
        await main_async(
            pdf_path=pdf_path,
            output_pdf=output_pdf,
            backend="easyocr",
            output_json=output_json,
            max_workers=2
        )
    except Exception as e:
        print(f"Error: {e}")


def create_sample_pdf():
    """Create a sample PDF for testing"""
    from pypdf import PdfWriter
    import io
    from reportlab.pdfgen import canvas
    import tempfile
    
    print("Creating sample PDF for testing...")
    
    # Create a simple PDF with page indicators
    packet = io.BytesIO()
    can = canvas.Canvas(packet)
    
    # Create 5 pages, but only pages 1, 3, and 5 have proper page indicators
    for i in range(1, 6):
        can.setFont("Helvetica", 12)
        can.drawString(100, 750, f"This is page {i} content")
        
        # Add page indicator in top right for pages 1, 3, 5
        if i in [1, 3, 5]:
            can.setFont("Helvetica", 10)
            can.drawString(450, 800, f"page {i} of 5")
        
        can.showPage()
    
    can.save()
    packet.seek(0)
    
    # Save to file
    with open("sample.pdf", "wb") as f:
        f.write(packet.getvalue())
    
    print("Created sample.pdf with 5 pages (pages 1, 3, 5 have page indicators)")


def main():
    """Main example function"""
    print("PDF Page Filter - Example Usage")
    print("=" * 50)
    
    # Check if we should create a sample PDF
    if not os.path.exists("sample.pdf"):
        create_sample_pdf()
    
    # Ask user which example to run
    print("\nChoose an example:")
    print("1. Tesseract OCR (local, no API key needed)")
    print("2. Mistral OCR (requires API key)")
    print("3. EasyOCR (local, requires easyocr package)")
    print("4. Create sample PDF")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        asyncio.run(example_with_tesseract())
    elif choice == "2":
        api_key = input("Enter your Mistral AI API key: ").strip()
        if api_key:
            asyncio.run(example_with_mistral(api_key))
        else:
            print("API key is required for Mistral OCR")
    elif choice == "3":
        asyncio.run(example_with_easyocr())
    elif choice == "4":
        create_sample_pdf()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()