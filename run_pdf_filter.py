#!/usr/bin/env python3
"""
Run the PDF page filter with your uploaded PDF
"""

import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from pdf_page_filter_practical import main_async

async def run_filter():
    """Run the PDF filter with your settings"""
    
    # Check for uploaded PDFs
    upload_dir = "/workspace/joshhartman74-droid__suppository/pdf_uploads"
    pdf_files = [f for f in os.listdir(upload_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("❌ No PDF files found in uploads directory!")
        print(f"Upload your PDF to: {upload_dir}")
        return
    
    print("Available PDF files:")
    for i, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(upload_dir, pdf_file)
        size = os.path.getsize(pdf_path)
        print(f"  {i}. {pdf_file} ({size / (1024*1024):.1f} MB)")
    
    # Let user choose which PDF to process
    if len(pdf_files) > 1:
        choice = input(f"\nWhich PDF to process? (1-{len(pdf_files)}): ").strip()
        try:
            selected_index = int(choice) - 1
            if 0 <= selected_index < len(pdf_files):
                selected_pdf = pdf_files[selected_index]
            else:
                print("Invalid choice, using first PDF")
                selected_pdf = pdf_files[0]
        except ValueError:
            print("Invalid input, using first PDF")
            selected_pdf = pdf_files[0]
    else:
        selected_pdf = pdf_files[0]
    
    pdf_path = os.path.join(upload_dir, selected_pdf)
    output_pdf = os.path.join(upload_dir, f"filtered_{selected_pdf}")
    output_json = os.path.join(upload_dir, f"schemas_{selected_pdf.replace('.pdf', '.json')}")
    
    print(f"\n🚀 Processing: {selected_pdf}")
    print(f"   Input: {pdf_path}")
    print(f"   Output PDF: {output_pdf}")
    print(f"   Output JSON: {output_json}")
    
    # Read API key
    with open(".mistral_api_key", "r") as f:
        api_key = f.read().strip()
    
    # Use mistral-medium-latest which we confirmed works
    model = "mistral-medium-latest"
    
    try:
        await main_async(
            pdf_path=pdf_path,
            output_pdf=output_pdf,
            api_key=api_key,
            backend="mistral",
            output_json=output_json,
            max_workers=2,  # Start with 2 workers for testing
            dpi=200  # Use 200 DPI for balance between quality and speed
        )
        
        print(f"\n✅ Processing complete!")
        print(f"   Filtered PDF: {output_pdf}")
        print(f"   Page schemas: {output_json}")
        
        # Show results
        if os.path.exists(output_json):
            import json
            with open(output_json, 'r') as f:
                schemas = json.load(f)
            
            kept_pages = [s for s in schemas if s.get('is_valid_page')]
            removed_pages = [s for s in schemas if not s.get('is_valid_page')]
            
            print(f"\n📊 Results:")
            print(f"   Total pages processed: {len(schemas)}")
            print(f"   Pages kept: {len(kept_pages)}")
            print(f"   Pages removed: {len(removed_pages)}")
            
            if kept_pages:
                print(f"\n   Kept pages: {', '.join(str(s['page_number']) for s in kept_pages)}")
            if removed_pages:
                print(f"   Removed pages: {', '.join(str(s['page_number']) for s in removed_pages)}")
    
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("PDF Page Filter - Ready to Process Your PDF")
    print("=" * 50)
    print(f"Upload directory: /workspace/joshhartman74-droid__suppository/pdf_uploads/")
    print(f"API key: Stored securely")
    print(f"OCR model: mistral-medium-latest (confirmed working)")
    print()
    
    asyncio.run(run_filter())