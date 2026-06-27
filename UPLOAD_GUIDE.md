# 📁 PDF Upload Guide

## Where to Upload Your PDF

Your workspace is located at:
```
/workspace/joshhartman74-droid__suppository/
```

**Upload your PDF to this specific folder:**
```
/workspace/joshhartman74-droid__suppository/pdf_uploads/
```

## 🎯 Current Directory Structure

```
/workspace/joshhartman74-droid__suppository/
├── pdf_uploads/                  ← **PUT YOUR PDF HERE**
│   ├── test_pdf.pdf             (test file we created)
│   ├── test_pdf_mixed.pdf        (test file we created)
│   ├── filtered_test.pdf         (result of our test)
│   └── test_schemas.json         (JSON output from test)
│
├── pdf_filter_mistral.py        (main processing script)
├── run_pdf_filter.py            (easy runner script)
├── upload_pdf.sh                (upload helper script)
├── .mistral_api_key             (your API key - secure)
├── README.md                    (documentation)
└── [other script files...]
```

## 🖥️ Upload Methods

### Method 1: Web Interface (Recommended)
1. **Find the file upload area** in your interface
2. **Navigate to**: `/workspace/joshhartman74-droid__suppository/pdf_uploads/`
3. **Drag and drop** your PDF file into this folder
4. **Or click "Upload"** and select your file

### Method 2: Command Line
If you have terminal access, run:
```bash
# Copy your PDF to the uploads directory
cp /path/to/your/large_file.pdf /workspace/joshhartman74-droid__suppository/pdf_uploads/

# Verify it's there
ls -lh /workspace/joshhartman74-droid__suppository/pdf_uploads/
```

### Method 3: Using the Upload Script
```bash
cd /workspace/joshhartman74-droid__suppository
./upload_pdf.sh
```

## ✅ After Uploading

Once your PDF is in the `pdf_uploads/` folder, run:

```bash
cd /workspace/joshhartman74-droid__suppository
python pdf_filter_mistral.py \
    --pdf pdf_uploads/your_file.pdf \
    --output pdf_uploads/filtered_your_file.pdf \
    --json-output pdf_uploads/your_file_schemas.json \
    --workers 1 \
    --dpi 150
```

## 📋 Quick Check

To see if your file uploaded successfully:
```bash
ls -lh /workspace/joshhartman74-droid__suppository/pdf_uploads/
```

## 🎯 Example

If your PDF is named `my_document.pdf`, after uploading it should look like:

```
/workspace/joshhartman74-droid__suppository/pdf_uploads/
├── my_document.pdf              ← Your uploaded file
├── test_pdf.pdf
├── filtered_test.pdf
└── test_schemas.json
```

Then run:
```bash
python pdf_filter_mistral.py \
    --pdf pdf_uploads/my_document.pdf \
    --output pdf_uploads/filtered_my_document.pdf \
    --json-output pdf_uploads/my_document_schemas.json
```

## 💡 Tips

- **File size**: Your 300MB PDF is fine - we have the space
- **Processing time**: Will take a few minutes depending on the number of pages
- **API usage**: Your Mistral API key is working and ready
- **Results**: You'll get both a filtered PDF and a JSON file with all page details

## 🚀 Ready to Go!

The system is fully set up and tested. Just upload your PDF to the `pdf_uploads/` folder and run the processing command!