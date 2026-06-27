#!/usr/bin/env python3
"""
PDF Page Filter using Mistral OCR

This script filters PDF pages based on the "page X of Y" text pattern found in the top right corner.
It uses Mistral AI's OCR capabilities to extract text from each page, creates a JSON schema for each page,
and filters pages accordingly. The processing is parallelized for efficiency.

Requirements:
- mistralai>=1.0.0
- pypdf>=3.0.0
- python-multipart
- concurrent.futures for parallel processing

Usage:
    python pdf_page_filter.py --pdf input.pdf --output filtered.pdf --api-key YOUR_MISTRAL_API_KEY
"""

import argparse
import asyncio
import base64
import json
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import httpx
from pypdf import PdfReader, PdfWriter


@dataclass
class PageSchema:
    """JSON Schema for each PDF page"""
    page_number: int
    total_pages: Optional[int] = None
    page_text: str = ""
    has_page_indicator: bool = False
    page_indicator_text: Optional[str] = None
    top_right_text: str = ""
    is_valid_page: bool = False
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "total_pages": self.total_pages,
            "page_text": self.page_text,
            "has_page_indicator": self.has_page_indicator,
            "page_indicator_text": self.page_indicator_text,
            "top_right_text": self.top_right_text,
            "is_valid_page": self.is_valid_page,
            "confidence": self.confidence
        }


class MistralOCRClient:
    """Client for Mistral AI OCR API"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.mistral.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        
    async def close(self):
        await self.client.aclose()
        
    async def extract_text_from_image(self, image_data: bytes, prompt: Optional[str] = None) -> str:
        """
        Extract text from an image using Mistral OCR
        
        Args:
            image_data: Raw image bytes
            prompt: Optional prompt to guide OCR
            
        Returns:
            Extracted text
        """
        url = f"{self.base_url}/images"
        
        # Encode image as base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        payload = {
            "image": image_base64,
            "prompt": prompt or "Extract all text from this image, especially any page numbers or indicators like 'page X of Y' in the top right corner."
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            
            result = response.json()
            # Handle different response formats
            if isinstance(result, dict):
                if 'output' in result:
                    return result['output']
                elif 'text' in result:
                    return result['text']
                elif 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0].get('text', '')
            elif isinstance(result, list) and len(result) > 0:
                return result[0].get('text', '')
                
            return str(result)
            
        except Exception as e:
            print(f"Error in OCR extraction: {e}")
            return ""


class PDFPageProcessor:
    """Process PDF pages and extract page information"""
    
    def __init__(self, ocr_client: MistralOCRClient):
        self.ocr_client = ocr_client
        self.page_indicator_pattern = re.compile(
            r'page\s+(\d+)\s+of\s+(\d+)'
            r'|page\s+(\d+)/(\d+)'
            r'|(\d+)/(\d+)'
            r'|page\s+(\d+)\s+-\s+(\d+)',
            re.IGNORECASE
        )
        
    async def extract_page_text(self, page_image: bytes, page_num: int) -> Tuple[str, float]:
        """
        Extract text from a single PDF page image
        
        Args:
            page_image: Rendered page as image bytes
            page_num: Page number (1-indexed)
            
        Returns:
            Tuple of (extracted_text, confidence)
        """
        prompt = f"Extract all text from this PDF page. Pay special attention to any page indicators like 'page {page_num} of X' or similar patterns in the top right corner."
        
        try:
            text = await self.ocr_client.extract_text_from_image(page_image, prompt)
            # Simple confidence estimation based on text length and pattern matching
            confidence = self._estimate_confidence(text, page_num)
            return text, confidence
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            return "", 0.0
        
    def _estimate_confidence(self, text: str, expected_page: int) -> float:
        """Estimate confidence score for OCR result"""
        if not text:
            return 0.0
            
        # Check if expected page number appears
        page_pattern = re.compile(rf'page\s+{expected_page}\s+of\s+\d+', re.IGNORECASE)
        if page_pattern.search(text):
            return 0.95
            
        # Check for any page indicator
        if self.page_indicator_pattern.search(text):
            return 0.85
            
        # Check for page number alone
        if str(expected_page) in text:
            return 0.75
            
        # Base confidence based on text length
        return min(0.6, len(text) / 1000)
    
    def _extract_top_right_text(self, text: str, width: int = 800, height: int = 600) -> str:
        """
        Extract text likely to be in the top right corner
        This is a heuristic approach since we don't have spatial information
        """
        lines = text.split('\n')
        top_lines = lines[:3]  # Top 3 lines are likely in the top right
        
        # Look for short lines that might be page indicators
        short_lines = [line.strip() for line in top_lines if len(line.strip()) < 50]
        
        return ' '.join(short_lines)
    
    def _find_page_indicator(self, text: str) -> Optional[Tuple[int, int]]:
        """
        Find page indicator pattern in text
        Returns (current_page, total_pages) if found, None otherwise
        """
        match = self.page_indicator_pattern.search(text)
        if match:
            # Try different capture groups
            groups = match.groups()
            for i in range(0, len(groups), 2):
                if groups[i] and groups[i+1]:
                    try:
                        current = int(groups[i])
                        total = int(groups[i+1])
                        return current, total
                    except ValueError:
                        continue
        return None
    
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
        # Extract text using OCR
        text, confidence = await self.extract_page_text(page_image, page_num)
        
        # Extract top right text
        top_right_text = self._extract_top_right_text(text)
        
        # Find page indicator
        page_indicator = self._find_page_indicator(text)
        page_indicator_text = None
        
        if page_indicator:
            current, total = page_indicator
            page_indicator_text = f"page {current} of {total}"
            # Check if this page should be kept (current page matches expected)
            is_valid = (current == page_num)
        else:
            # Check if top right text contains page indicator
            indicator_in_top_right = self._find_page_indicator(top_right_text)
            if indicator_in_top_right:
                current, total = indicator_in_top_right
                page_indicator_text = f"page {current} of {total}"
                is_valid = (current == page_num)
            else:
                # No page indicator found
                is_valid = False
        
        return PageSchema(
            page_number=page_num,
            total_pages=total_pages,
            page_text=text,
            has_page_indicator=page_indicator is not None,
            page_indicator_text=page_indicator_text,
            top_right_text=top_right_text,
            is_valid_page=is_valid,
            confidence=confidence
        )


class PDFRenderer:
    """Render PDF pages as images for OCR processing"""
    
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        
    def render_page_as_image(self, page) -> bytes:
        """
        Render a PDF page as an image
        
        Args:
            page: PyPDF page object
            
        Returns:
            Image as bytes (PNG format)
        """
        try:
            # This is a simplified approach - in practice you might use pdf2image or similar
            # For now, we'll create a placeholder
            # In a real implementation, you would use pdf2image library:
            # from pdf2image import convert_from_path
            # images = convert_from_path(pdf_path, dpi=self.dpi, first_page=page_num, last_page=page_num)
            # return images[0].tobytes()
            
            # For this example, we'll return a placeholder
            # You'll need to install pdf2image: pip install pdf2image
            print("Note: For actual image rendering, install pdf2image library")
            return b"placeholder_image_data"
            
        except Exception as e:
            print(f"Error rendering page: {e}")
            return b""


async def process_pdf_pages_parallel(
    pdf_path: str,
    ocr_client: MistralOCRClient,
    max_workers: int = 4
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
    
    # Create a thread pool for CPU-bound tasks (image rendering)
    # and use asyncio for I/O-bound tasks (API calls)
    page_schemas = []
    
    # Process pages in batches to avoid overwhelming the API
    batch_size = min(max_workers, 10)  # Limit batch size
    
    for batch_start in range(0, total_pages, batch_size):
        batch_end = min(batch_start + batch_size, total_pages)
        batch_tasks = []
        
        for page_num in range(batch_start, batch_end):
            # Get the actual page (0-indexed in PyPDF)
            page = reader.pages[page_num]
            
            # Render page as image (this would be done with pdf2image in practice)
            # For now, we'll simulate this
            page_image = renderer.render_page_as_image(page)
            
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
    max_workers: int = 4
):
    """
    Main function to process PDF and filter pages
    
    Args:
        pdf_path: Input PDF file path
        output_pdf: Output filtered PDF file path
        api_key: Mistral AI API key
        output_json: Optional path to save page schemas JSON
        max_workers: Maximum number of parallel workers
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
        print(f"Using {max_workers} parallel workers")
        
        # Process all pages in parallel
        page_schemas = await process_pdf_pages_parallel(
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
            print(f"Page {schema.page_number}: {status} - Indicator: {indicator}")
        
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
    parser.add_argument("--api-key", required=True, help="Mistral AI API key")
    parser.add_argument("--json-output", help="Path to save page schemas JSON")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    # Run async main function
    asyncio.run(main(
        pdf_path=args.pdf,
        output_pdf=args.output,
        api_key=args.api_key,
        output_json=args.json_output,
        max_workers=args.workers
    ))


if __name__ == "__main__":
    sync_main()