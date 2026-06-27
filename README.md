# PDF Page Filter with Mistral OCR

A Python tool to filter PDF pages based on "page X of Y" indicators in the top right corner using OCR technology. This solution supports multiple OCR backends including Mistral AI API, Tesseract, and EasyOCR, with parallel processing for efficiency.

## Features

- **Multiple OCR Backends**: Choose between Mistral AI API, Tesseract (local), or EasyOCR
- **Parallel Processing**: Process multiple pages simultaneously for improved performance
- **JSON Schema Output**: Generate structured JSON output for each page with metadata
- **Flexible Page Detection**: Detect various page indicator formats ("page 1 of 5", "1/5", etc.)
- **Confidence Scoring**: Each page gets a confidence score based on OCR quality
- **Comprehensive Logging**: Detailed output about processing status and results

## Installation

### Prerequisites

```bash
# Clone the repository
git clone https://github.com/joshhartman74-droid/suppository.git
cd suppository

# Install Python dependencies
pip install -r requirements.txt
```

### Additional Requirements by Backend

#### Tesseract OCR (Recommended for local use)
```bash
# On Ubuntu/Debian
sudo apt install tesseract-ocr

# On macOS
brew install tesseract

# On Windows
download from https://github.com/UB-Mannheim/tesseract/wiki
```

#### EasyOCR
```bash
pip install easyocr
```

#### Mistral AI API
- Sign up at https://mistral.ai/ to get an API key
- No additional installation needed beyond the requirements

## Usage

### Command Line Interface

```bash
# Using Tesseract OCR (local, no API key needed)
python pdf_page_filter_practical.py --pdf input.pdf --output filtered.pdf --backend tesseract

# Using Mistral AI API
python pdf_page_filter_practical.py --pdf input.pdf --output filtered.pdf --backend mistral --api-key YOUR_API_KEY

# Using EasyOCR
python pdf_page_filter_practical.py --pdf input.pdf --output filtered.pdf --backend easyocr

# With additional options
python pdf_page_filter_practical.py \
    --pdf input.pdf \
    --output filtered.pdf \
    --backend tesseract \
    --json-output page_schemas.json \
    --workers 8 \
    --dpi 200
```

### Python API

```python
import asyncio
from pdf_page_filter_practical import main_async

async def process_pdf():
    await main_async(
        pdf_path="input.pdf",
        output_pdf="filtered.pdf",
        backend="tesseract",  # or "mistral" or "easyocr"
        api_key="your_api_key",  # required for Mistral
        output_json="page_schemas.json",
        max_workers=4,
        dpi=300
    )

asyncio.run(process_pdf())
```

### Example Usage

Run the example script to see how it works:

```bash
python example_usage.py
```

This will guide you through creating a sample PDF and testing different OCR backends.

## JSON Schema Output

The tool generates a JSON schema for each page with the following structure:

```json
{
  "page_number": 1,
  "total_pages": 10,
  "page_text": "Extracted text from the page...",
  "has_page_indicator": true,
  "page_indicator_text": "page 1 of 10",
  "top_right_text": "page 1 of 10",
  "is_valid_page": true,
  "confidence": 0.95,
  "processing_time": 1.234,
  "backend_used": "tesseract"
}
```

## How It Works

1. **PDF Rendering**: Each page is converted to an image using `pdf2image`
2. **OCR Processing**: Text is extracted from each page image using the selected OCR backend
3. **Pattern Matching**: The tool searches for page indicator patterns like "page X of Y" in the extracted text
4. **Top-Right Detection**: Uses heuristics to identify text likely in the top-right corner
5. **Page Validation**: Pages with valid page indicators matching their position are kept
6. **Parallel Processing**: Multiple pages are processed simultaneously for efficiency
7. **PDF Creation**: A new PDF is created containing only the valid pages

## Page Indicator Patterns

The tool recognizes various page indicator formats:

- `page 1 of 10`
- `page 1/10`
- `1 of 10`
- `1/10`
- `page 1 - 10`
- Case insensitive (e.g., `Page 1 Of 10`)

## Performance Considerations

- **DPI Setting**: Higher DPI (300+) gives better OCR accuracy but slower processing
- **Parallel Workers**: More workers = faster processing but higher memory usage
- **Backend Choice**: 
  - Mistral AI: High accuracy, requires API key, internet connection
  - Tesseract: Good accuracy, local, requires installation
  - EasyOCR: Good accuracy, local, easier to install than Tesseract

## Error Handling

The tool handles various error conditions:
- Missing PDF files
- Invalid API keys (for Mistral)
- OCR processing failures
- Page rendering issues

Failed pages are marked as invalid and excluded from the output.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues or questions:
- Open an issue on GitHub
- Ensure you have the required dependencies installed
- Check that your PDF is not password-protected
- For Mistral backend, verify your API key is valid

## API Key Requirements

If you need a Mistral AI API key:
1. Go to https://mistral.ai/
2. Sign up for an account
3. Navigate to your account settings
4. Generate an API key
5. Use it with the `--api-key` parameter

**Note**: The Mistral AI API may have usage limits and costs. Check their pricing page for details.

## Alternative Approach

If you prefer not to use OCR, and your PDF has selectable text, you could use a simpler approach with just text extraction. However, this solution uses OCR to handle scanned PDFs and images where text extraction alone wouldn't work.