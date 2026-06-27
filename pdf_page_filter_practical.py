#!/usr/bin/env python3
"""
Practical PDF Page Filter using OCR

This script filters PDF pages based on the "page X of Y" text pattern found in the top right corner.
It supports multiple OCR backends:
1. Mistral AI API (requires API key)
2. Local Tesseract OCR (requires installation)
3. EasyOCR (requires installation)

The processing is parallelized for efficiency.

Installation:
    pip install -r requirements.txt
    
    # For Tesseract OCR:
    # On Ubuntu: sudo apt install tesseract-ocr
    # On Mac: brew install tesseract
    # On Windows: download installer from https://github.com/UB-Mannheim/tesseract/wiki
    
    # For EasyOCR:
    pip install easyocr

Usage:
    # Using Mistral AI API
    python pdf_page_filter_practical.py --pdf input.pdf --output filtered.pdf --api-key YOUR_KEY --backend mistral
    
    # Using local Tesseract OCR
    python pdf_page_filter_practical.py --pdf input.pdf --output filtered.pdf --backend tesseract
    
    # Using EasyOCR
    python pdf_page_filter_practical.py --pdf input.pdf --output filtered.pdf --backend easyocr
"""

import argparse
import asyncio
import base64
import json
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Literal
from enum import Enum
import httpx
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_path
import numpy as np


class OCRBackend(Enum):
    MISTRAL = "mistral"
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"


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
    processing_time: float = 0.0
    backend_used: str = ""
    
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
            "processing_time": round(self.processing_time, 3),
            "backend_used": self.backend_used
        }


# Type alias for OCR function
OCRFunction = callable[[bytes], Tuple[str, float]]


class OCRClient:
    """Base OCR Client"""
    
    def __init__(self, backend: OCRBackend, api_key: Optional[str] = None, **kwargs):
        self.backend = backend
        self.api_key = api_key
        self.kwargs = kwargs
        
    async def extract_text(self, image_data: bytes) -> Tuple[str, float]:
        """Extract text from image data"""
        raise NotImplementedError


class MistralOCRClient(OCRClient):
    """Mistral AI OCR Client"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.mistral.ai/v1"):
        super().__init__(OCRBackend.MISTRAL, api_key)
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def close(self):
        await self.client.aclose()
        
    async def extract_text(self, image_data: bytes) -> Tuple[str, float]:
        """Extract text using Mistral AI API"""
        url = f"{self.base_url}/images"
        
        # Encode image as base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        payload = {
            "image": image_base64,
            "prompt": "Extract all text from this image, especially any page numbers or indicators like 'page X of Y' in the top right corner. Return only the extracted text."
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, dict):
                if 'output' in result:
                    text = result['output']
                elif 'text' in result:
                    text = result['text']
                elif 'choices' in result and len(result['choices']) > 0:
                    text = result['choices'][0].get('text', '')
                else:
                    text = str(result)
            elif isinstance(result, list) and len(result) > 0:
                text = result[0].get('text', str(result))
            else:
                text = str(result)
            
            # Estimate confidence (Mistral typically has high confidence)
            confidence = 0.95 if text else 0.0
            return text, confidence
            
        except Exception as e:
            print(f"Mistral OCR Error: {e}")
            return "", 0.0


class TesseractOCRClient(OCRClient):
    """Tesseract OCR Client"""
    
    def __init__(self, **kwargs):
        super().__init__(OCRBackend.TESSERACT, **kwargs)
        try:
            import pytesseract
            self.pytesseract = pytesseract
        except ImportError:
            raise ImportError("pytesseract is required for Tesseract OCR. Install with: pip install pytesseract")
        
    async def extract_text(self, image_data: bytes) -> Tuple[str, float]:
        """Extract text using Tesseract OCR"""
        try:
            from PIL import Image
            import io
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Use Tesseract to extract text
            text = self.pytesseract.image_to_string(image)
            
            # Estimate confidence based on text length and quality
            confidence = self._estimate_confidence(text)
            return text, confidence
            
        except Exception as e:
            print(f"Tesseract OCR Error: {e}")
            return "", 0.0
        
    def _estimate_confidence(self, text: str) -> float:
        """Estimate confidence for Tesseract OCR"""
        if not text:
            return 0.0
        
        # Simple heuristic: longer text with page indicators = higher confidence
        has_page_indicator = bool(re.search(r'page\s+\d+\s+of\s+\d+', text, re.IGNORECASE))
        length_factor = min(1.0, len(text) / 500)  # Normalize by typical page text length
        
        if has_page_indicator:
            return min(0.95, 0.7 + length_factor * 0.25)
        else:
            return min(0.85, 0.5 + length_factor * 0.35)


class EasyOCRClient(OCRClient):
    """EasyOCR Client"""
    
    def __init__(self, **kwargs):
        super().__init__(OCRBackend.EASYOCR, **kwargs)
        try:
            import easyocr
            self.reader = easyocr.Reader(['en'])
        except ImportError:
            raise ImportError("easyocr is required. Install with: pip install easyocr")
        
    async def extract_text(self, image_data: bytes) -> Tuple[str, float]:
        """Extract text using EasyOCR"""
        try:
            from PIL import Image
            import io
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Use EasyOCR to extract text
            results = self.reader.readtext(np.array(image))
            text = ' '.join([result[1] for result in results])
            
            # Estimate confidence
            confidence = self._estimate_confidence(results)
            return text, confidence
            
        except Exception as e:
            print(f"EasyOCR Error: {e}")
            return "", 0.0
        
    def _estimate_confidence(self, results: List) -> float:
        """Estimate confidence for EasyOCR"""
        if not results:
            return 0.0
        
        # Use average confidence from EasyOCR results
        confidences = [result[2] for result in results if len(result) > 2]
        if confidences:
            return sum(confidences) / len(confidences)
        return 0.7  # Default confidence


class PDFPageProcessor:
    """Process PDF pages and extract page information"""
    
    def __init__(self, ocr_client: OCRClient):
        self.ocr_client = ocr_client
        # Pattern to match various page indicator formats
        self.page_indicator_pattern = re.compile(
            r'(?:page|p|pg)\s*[\-:]?\s*(\d+)\s*(?:of|/|\-|to)\s*(\d+)'
            r'|(\d+)\s*(?:of|/|\-|to)\s*(\d+)'
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
        import time
        start_time = time.time()
        
        try:
            # Extract text using OCR
            text, confidence = await self.ocr_client.extract_text(page_image)
            
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
                processing_time=processing_time,
                backend_used=self.ocr_client.backend.value
            )
            
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            return PageSchema(
                page_number=page_num,
                total_pages=total_pages,
                is_valid_page=False,
                backend_used=self.ocr_client.backend.value
            )
    
    def _extract_top_right_text(self, text: str) -> str:
        """
        Extract text likely to be in the top right corner
        This is a heuristic approach since we don't have spatial information from basic OCR
        """
        if not text:
            return ""
        
        lines = text.split('\n')
        
        # Look for short lines that might be page indicators
        # Page indicators are typically short and at the top
        short_lines = []
        for line in lines[:5]:  # Check first 5 lines
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
    
    def __init__(self, dpi: int = 300):
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
                fmt='png'
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
    ocr_client: OCRClient,
    max_workers: int = 4
) -> List[PageSchema]:
    """
    Process all pages of a PDF in parallel
    
    Args:
        pdf_path: Path to the PDF file
        ocr_client: OCR client instance
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
    
    # Use ThreadPoolExecutor for CPU-bound image rendering
    # and asyncio for I/O-bound OCR API calls
    def process_single_page(page_num: int) -> PageSchema:
        """Process a single page (synchronous wrapper)"""
        page_image = renderer.render_page(pdf_path, page_num)
        if not page_image:
            return PageSchema(
                page_number=page_num,
                total_pages=total_pages,
                is_valid_page=False,
                backend_used=ocr_client.backend.value
            )
        
        # Run async function in a new event loop
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                processor.process_page(page_image, page_num, total_pages)
            )
        finally:
            loop.close()
    
    # Process pages in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_page, page_num): page_num 
            for page_num in range(1, total_pages + 1)
        }
        
        for future in as_completed(futures):
            page_num = futures[future]
            try:
                schema = future.result()
                page_schemas.append(schema)
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
                page_schemas.append(PageSchema(
                    page_number=page_num,
                    total_pages=total_pages,
                    is_valid_page=False,
                    backend_used=ocr_client.backend.value
                ))
    
    # Sort by page number
    page_schemas.sort(key=lambda x: x.page_number)
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


async def main_async(
    pdf_path: str,
    output_pdf: str,
    api_key: Optional[str] = None,
    backend: str = "tesseract",
    output_json: Optional[str] = None,
    max_workers: int = 4,
    dpi: int = 300
):
    """
    Main async function to process PDF and filter pages
    """
    # Validate inputs
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Initialize OCR client based on backend
    backend_enum = OCRBackend(backend.lower())
    
    if backend_enum == OCRBackend.MISTRAL:
        if not api_key:
            raise ValueError("Mistral AI API key is required for Mistral backend")
        ocr_client = MistralOCRClient(api_key)
    elif backend_enum == OCRBackend.TESSERACT:
        ocr_client = TesseractOCRClient()
    elif backend_enum == OCRBackend.EASYOCR:
        ocr_client = EasyOCRClient()
    else:
        raise ValueError(f"Unsupported backend: {backend}")
    
    try:
        print(f"Processing PDF: {pdf_path}")
        print(f"Using backend: {backend}")
        print(f"Using {max_workers} parallel workers")
        print(f"DPI: {dpi}")
        
        # Process all pages in parallel
        page_schemas = await asyncio.to_thread(
            process_pdf_parallel, pdf_path, ocr_client, max_workers
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
        if hasattr(ocr_client, 'close'):
            await ocr_client.close()


def sync_main():
    """Synchronous wrapper for command-line usage"""
    parser = argparse.ArgumentParser(
        description="Filter PDF pages based on 'page X of Y' indicators using OCR"
    )
    parser.add_argument("--pdf", required=True, help="Input PDF file path")
    parser.add_argument("--output", required=True, help="Output filtered PDF file path")
    parser.add_argument("--backend", choices=["mistral", "tesseract", "easyocr"], 
                        default="tesseract", help="OCR backend to use")
    parser.add_argument("--api-key", help="Mistral AI API key (required for Mistral backend)")
    parser.add_argument("--json-output", help="Path to save page schemas JSON")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF to image conversion")
    
    args = parser.parse_args()
    
    # Run async main function
    asyncio.run(main_async(
        pdf_path=args.pdf,
        output_pdf=args.output,
        api_key=args.api_key,
        backend=args.backend,
        output_json=args.json_output,
        max_workers=args.workers,
        dpi=args.dpi
    ))


if __name__ == "__main__":
    sync_main()