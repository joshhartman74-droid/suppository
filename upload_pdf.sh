#!/bin/bash

# PDF Upload Script
# This script helps you upload your PDF to the correct location

echo "PDF Page Filter - Upload Helper"
echo "================================"
echo ""

# Check if PDF is already uploaded
if [ -f "/workspace/joshhartman74-droid__suppository/pdf_uploads/*.pdf" ]; then
    echo "PDF files found in uploads directory:"
    ls -lh /workspace/joshhartman74-droid__suppository/pdf_uploads/*.pdf
    echo ""
fi

# Show current directory
UPLOAD_DIR="/workspace/joshhartman74-droid__suppository/pdf_uploads"
echo "Upload your PDF to: $UPLOAD_DIR"
echo ""

# Show available space
echo "Available disk space:"
df -h /workspace

# Show instructions
echo ""
echo "Upload Instructions:"
echo "1. Drag and drop your PDF file to: $UPLOAD_DIR"
echo "2. Or use: cp /path/to/your/file.pdf $UPLOAD_DIR/"
echo "3. Then run: python pdf_page_filter_practical.py --pdf $UPLOAD_DIR/your_file.pdf --output filtered.pdf --backend mistral --api-key \"\$(cat .mistral_api_key)\""
echo ""

# List all PDF files in the repository
echo "All PDF files in the repository:"
find /workspace/joshhartman74-droid__suppository -name "*.pdf" -type f 2>/dev/null | while read file; do
    echo "  - $file (\$(du -h \"$file\" | cut -f1))"
done

if [ ! -f "/workspace/joshhartman74-droid__suppository/pdf_uploads/*.pdf" ]; then
    echo ""
    echo "No PDF files found yet. Please upload your PDF to get started."
fi