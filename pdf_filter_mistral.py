#!/usr/bin/env python3
"""
PDF Page Filter using Mistral AI OCR

This is a streamlined version specifically for your use case:
- Uses Mistral AI API with your provided key
- Uses mistral-medium-latest model (confirmed working)
- Filters pages based on "page X of Y" in top right corner
- Creates JSON schema for each page
- Parallel processing for efficiency

Usage:
    python pdf_filter_mistral.py --pdf your_file.pdf --output filtered.pdf
"""

import argparse
import asyncio
import base64
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import httpx
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_path


@dataclass
class PageSchema:
    """JSON Schema for each PDF page"""
    page_number: int
    total_pages: int
    page_text: str = ""
    has_page_indicator: bool = False
    page_indicator_text: Optional[str] = None
    top_right_text: str = ""
    is_valid_page: bool = False
    confidence: float = 0.0
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "total_pages": self.total_pages,
            "page_text": self.page_text,
            "has_page_indicator": self.has_page_indicator,
            "page_indicator_text": self.page_indicator_text,
            "top_right_text": self.top_right_text,
            "is_valid_page": self.is_valid_page,
            "confidence": round(self.confidence, 3),
            "processing_time": round(self.processing_time, 3)
        }


class MistralOCRClient:
    """Mistral AI OCR Client using mistral-medium-latest"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.mistral.ai/v1"
        self.model = "mistral-medium-latest"  # Confirmed working model
        self.client = httpx.AsyncClient(timeout=120.0)  # Longer timeout for large images
        
    async def close(self):
        await self.client.aclose()
        
    async def extract_text_from_image(self, image_data: bytes, page_num: int = 1) -> Tuple[str, float]:
        """
        Extract text from an image using Mistral AI
        
        Args:
            image_data: Raw image bytes
            page_num: Page number for context
            
        Returns:
            Tuple of (extracted_text, confidence)
        """
        # Encode image as base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Extract all text from this PDF page (page {page_num}). Pay special attention to any page indicators like 'page X of Y' or similar patterns in the top right corner. Return only the extracted text without any commentary."
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{image_base64}"
                        }
                    ]
                }
            ],
            "max_tokens": 2000,  # Allow for more text
            "temperature": 0.0  # More deterministic
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            start_time = time.time()
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Clean up the text
            text = text.strip()
            
            # Estimate confidence based on response
            confidence = 0.95 if text else 0.0
            processing_time = time.time() - start_time
            
            return text, confidence, processing_time
            
        except Exception as e:
            print(f"Error in OCR extraction: {e}")
            return "", 0.0, 0.0


class PDFPageProcessor:
    """Process PDF pages and extract page information"""
    
    def __init__(self, ocr_client: MistralOCRClient):
        self.ocr_client = ocr_client
        # Pattern to match various page indicator formats
        self.page_indicator_pattern = re.compile(
            r'(?:page|p|pg|Page|P|PG)\s*[\-:]?\s*(\d+)\s*(?:of|/|\-|to|O|o|F|f)\s*(\d+)'
            r'|(\d+)\s*(?:of|/|\-|to|O|o|F|f)\s*(\d+)'
            r'|(\d+)/(\d+)',
            re.IGNORECASE
        )
        
    async def process_page(self, page_image: bytes, page_num: int, total_pages: int) -> PageSchema:
        """
        Process a single page and create its schema
        
        Args:
            page_image: Rendered page as image bytes
            page_num: Page number (1-indexed)
            total_pages: Total number of pages in the PDF
            
        Returns:
            PageSchema object
        """
        start_time = time.time()
        
        try:
            # Extract text using OCR
            text, confidence, ocr_time = await self.ocr_client.extract_text_from_image(page_image, page_num)
            
            # Extract top right text (heuristic approach)
            top_right_text = self._extract_top_right_text(text)
            
            # Find page indicator
            page_indicator, indicator_text = self._find_page_indicator(text)
            
            # Determine if page should be kept
            if page_indicator:
                current, total = page_indicator
                is_valid = (current == page_num)
            else:
                # Check if top right text contains page indicator
                indicator_in_top_right = self._find_page_indicator(top_right_text)[0]
                if indicator_in_top_right:
                    current, total = indicator_in_top_right
                    is_valid = (current == page_num)
                    indicator_text = f"page {current} of {total}"
                else:
                    is_valid = False
            
            processing_time = time.time() - start_time
            
            return PageSchema(
                page_number=page_num,
                total_pages=total_pages,
                page_text=text,
                has_page_indicator=page_indicator is not None,
                page_indicator_text=indicator_text,
                top_right_text=top_right_text,
                is_valid_page=is_valid,
                confidence=confidence,
                processing_time=processing_time
            )
            
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            return PageSchema(
                page_number=page_num,
                total_pages=total_pages,
                is_valid_page=False
            )
    
    def _extract_top_right_text(self, text: str) -> str:
        """
        Extract text likely to be in the top right corner
        """
        if not text:
            return ""
        
        lines = text.split('\n')
        
        # Look for short lines that might be page indicators
        short_lines = []
        for line in lines[:8]:  # Check first 8 lines
            line = line.strip()
            if line and len(line) < 100:  # Reasonable length for page indicator
                short_lines.append(line)
        
        return ' '.join(short_lines)
    
    def _find_page_indicator(self, text: str) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
        """
        Find page indicator pattern in text
        Returns (page_indicator_tuple, indicator_text) where page_indicator_tuple is (current, total)
        """
        if not text:
            return None, None
        
        match = self.page_indicator_pattern.search(text)
        if match:
            groups = match.groups()
            # Try different capture groups
            for i in range(0, len(groups), 2):
                if groups[i] and groups[i+1]:
                    try:
                        current = int(groups[i])
                        total = int(groups[i+1])
                        indicator_text = f"page {current} of {total}"
                        return (current, total), indicator_text
                    except ValueError:
                        continue
        
        return None, None


class PDFRenderer:
    """Render PDF pages as images for OCR processing"""
    
    def __init__(self, dpi: int = 200):
        self.dpi = dpi
        
    def render_page(self, pdf_path: str, page_num: int) -> bytes:
        """
        Render a specific PDF page as an image
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            
        Returns:
            Image as bytes (PNG format)
        """
        try:
            # Convert specific page to image
            images = convert_from_path(
                pdf_path, 
                dpi=self.dpi, 
                first_page=page_num, 
                last_page=page_num,
                fmt='png',
                use_pdftocairo=True  # Use pdftocairo for better quality
            )
            
            if images:
                # Convert PIL Image to bytes
                import io
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='PNG')
                return img_byte_arr.getvalue()
            else:
                return b""
                
        except Exception as e:
            print(f"Error rendering page {page_num}: {e}")
            return b""


async def process_pdf_parallel(
    pdf_path: str,
    ocr_client: MistralOCRClient,
    max_workers: int = 2
) -> List[PageSchema]:
    """
    Process all pages of a PDF in parallel
    
    Args:
        pdf_path: Path to the PDF file
        ocr_client: Mistral OCR client
        max_workers: Maximum number of parallel workers
        
    Returns:
        List of PageSchema objects for all pages
    """
    # Read PDF and get page count
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    processor = PDFPageProcessor(ocr_client)
    renderer = PDFRenderer()
    
    page_schemas = []
    
    # Process pages sequentially to avoid API rate limits
    # For large PDFs, we'll process in small batches
    batch_size = max_workers
    
    for batch_start in range(0, total_pages, batch_size):
        batch_end = min(batch_start + batch_size, total_pages)
        batch_tasks = []
        
        print(f"Processing pages {batch_start + 1}-{batch_end} of {total_pages}...")
        
        for page_num in range(batch_start, batch_end):
            # Get the actual page (0-indexed in PyPDF)
            page = reader.pages[page_num]
            
            # Render page as image
            page_image = renderer.render_page(pdf_path, page_num + 1)
            
            if not page_image:
                print(f"Warning: Could not render page {page_num + 1}")
                page_schemas.append(PageSchema(
                    page_number=page_num + 1,
                    total_pages=total_pages,
                    is_valid_page=False
                ))
                continue
            
            # Create async task for this page
            task = asyncio.create_task(
                processor.process_page(page_image, page_num + 1, total_pages)
            )
            batch_tasks.append(task)
        
        # Wait for this batch to complete
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"Error processing page: {result}")
                # Create a placeholder schema for failed pages
                page_schemas.append(PageSchema(page_number=0, is_valid_page=False))
            else:
                page_schemas.append(result)
        
        # Be gentle with API rate limits
        if batch_end < total_pages:
            print(f"Pausing before next batch...")
            await asyncio.sleep(2)  # 2 second pause between batches
    
    return page_schemas


def filter_valid_pages(page_schemas: List[PageSchema]) -> List[PageSchema]:
    """Filter pages that have valid page indicators"""
    return [schema for schema in page_schemas if schema.is_valid_page]


def create_output_pdf(input_pdf: str, valid_page_numbers: List[int], output_pdf: str):
    """Create a new PDF with only the valid pages"""
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    
    # Sort page numbers and remove duplicates
    valid_page_numbers = sorted(set(valid_page_numbers))
    
    for page_num in valid_page_numbers:
        if 1 <= page_num <= len(reader.pages):
            writer.add_page(reader.pages[page_num - 1])
    
    with open(output_pdf, 'wb') as f:
        writer.write(f)
    
    print(f"Created filtered PDF with {len(valid_page_numbers)} pages: {output_pdf}")


def save_page_schemas(page_schemas: List[PageSchema], output_json: str):
    """Save page schemas to JSON file"""
    schemas_dict = [schema.to_dict() for schema in page_schemas]
    
    with open(output_json, 'w') as f:
        json.dump(schemas_dict, f, indent=2)
    
    print(f"Saved page schemas to: {output_json}")


async def main(
    pdf_path: str,
    output_pdf: str,
    api_key: str,
    output_json: Optional[str] = None,
    max_workers: int = 2,
    dpi: int = 200
):
    """
    Main function to process PDF and filter pages
    
    Args:
        pdf_path: Input PDF file path
        output_pdf: Output filtered PDF file path
        api_key: Mistral AI API key
        output_json: Optional path to save page schemas JSON
        max_workers: Maximum number of parallel workers
        dpi: DPI for PDF to image conversion
    """
    # Validate inputs
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not api_key:
        raise ValueError("Mistral AI API key is required")
    
    # Initialize OCR client
    ocr_client = MistralOCRClient(api_key)
    
    try:
        print(f"Processing PDF: {pdf_path}")
        print(f"Using Mistral model: mistral-medium-latest")
        print(f"Using {max_workers} parallel workers")
        print(f"DPI: {dpi}")
        
        # Get file size
        file_size = os.path.getsize(pdf_path)
        print(f"File size: {file_size / (1024*1024):.1f} MB")
        
        # Process all pages
        page_schemas = await process_pdf_parallel(
            pdf_path, ocr_client, max_workers
        )
        
        print(f"Processed {len(page_schemas)} pages")
        
        # Filter valid pages
        valid_schemas = filter_valid_pages(page_schemas)
        valid_page_numbers = [schema.page_number for schema in valid_schemas]
        
        print(f"Found {len(valid_page_numbers)} valid pages with page indicators")
        
        # Save page schemas if requested
        if output_json:
            save_page_schemas(page_schemas, output_json)
        
        # Create filtered PDF
        create_output_pdf(pdf_path, valid_page_numbers, output_pdf)
        
        # Print summary
        print("\nPage Summary:")
        for schema in page_schemas:
            status = "KEPT" if schema.is_valid_page else "REMOVED"
            indicator = schema.page_indicator_text or "None"
            print(f"Page {schema.page_number}: {status} - Indicator: {indicator} (confidence: {schema.confidence:.2f})")
        
        return valid_page_numbers
        
    finally:
        await ocr_client.close()


def sync_main():
    """Synchronous wrapper for command-line usage"""
    parser = argparse.ArgumentParser(
        description="Filter PDF pages based on 'page X of Y' indicators using Mistral OCR"
    )
    parser.add_argument("--pdf", required=True, help="Input PDF file path")
    parser.add_argument("--output", required=True, help="Output filtered PDF file path")
    parser.add_argument("--api-key", help="Mistral AI API key (defaults to .mistral_api_key file)")
    parser.add_argument("--json-output", help="Path to save page schemas JSON")
    parser.add_argument("--workers", type=int, default=2, help="Number of parallel workers")
    parser.add_argument("--dpi", type=int, default=200, help="DPI for PDF to image conversion")
    
    args = parser.parse_args()
    
    # Read API key from file if not provided
    api_key = args.api_key
    if not api_key:
        api_key_file = "/workspace/joshhartman74-droid__suppository/.mistral_api_key"
        if os.path.exists(api_key_file):
            with open(api_key_file, 'r') as f:
                api_key = f.read().strip()
        else:
            raise ValueError("API key not provided and .mistral_api_key file not found")
    
    # Run async main function
    asyncio.run(main(
        pdf_path=args.pdf,
        output_pdf=args.output,
        api_key=api_key,
        output_json=args.json_output,
        max_workers=args.workers,
        dpi=args.dpi
    ))


if __name__ == "__main__":
    sync_main()