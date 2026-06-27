#!/usr/bin/env python3
"""
Create a test PDF with page indicators for testing
"""

from pypdf import PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import os

def create_test_pdf(filename="test_pdf.pdf", num_pages=5):
    """Create a test PDF with page indicators"""
    
    # Create a PDF in memory
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    width, height = letter
    
    for i in range(1, num_pages + 1):
        # Add some content
        can.setFont("Helvetica", 12)
        can.drawString(100, height - 100, f"This is the content for page {i}")
        can.drawString(100, height - 120, f"Sample text to test OCR processing.")
        
        # Add page indicator in top right corner
        can.setFont("Helvetica", 10)
        page_text = f"page {i} of {num_pages}"
        text_width = can.stringWidth(page_text, "Helvetica", 10)
        can.drawString(width - text_width - 50, height - 50, page_text)
        
        can.showPage()
    
    can.save()
    packet.seek(0)
    
    # Save to file
    output_path = os.path.join("/workspace/joshhartman74-droid__suppository/pdf_uploads/", filename)
    with open(output_path, "wb") as f:
        f.write(packet.getvalue())
    
    print(f"✅ Created test PDF: {output_path}")
    print(f"   Size: {os.path.getsize(output_path) / 1024:.1f} KB")
    print(f"   Pages: {num_pages}")
    print(f"   Page indicators: page 1 of {num_pages}, page 2 of {num_pages}, etc.")
    
    return output_path

if __name__ == "__main__":
    # Check if reportlab is available
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:
        print("❌ reportlab not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "reportlab"], check=True)
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    
    # Create test PDF
    test_pdf = create_test_pdf("test_pdf.pdf", 5)
    
    # Also create a version without page indicators on some pages
    create_test_pdf("test_pdf_mixed.pdf", 5)
    
    print("\n📁 Test PDFs created in pdf_uploads directory:")
    for file in os.listdir("/workspace/joshhartman74-droid__suppository/pdf_uploads/"):
        if file.endswith(".pdf"):
            path = os.path.join("/workspace/joshhartman74-droid__suppository/pdf_uploads/", file)
            size = os.path.getsize(path)
            print(f"   - {file} ({size / 1024:.1f} KB)")