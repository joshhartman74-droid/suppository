# 📤 GitHub Upload Guide for Your PDF

## 🎯 Your Repository

**Repository Name**: `joshhartman74-droid/suppository`  
**GitHub URL**: https://github.com/joshhartman74-droid/suppository

## 📁 Where to Upload Your PDF

I've created a special folder in your GitHub repository for your PDF uploads:

**Upload Path**: `pdf_uploads/`

**Full GitHub Path**: `https://github.com/joshhartman74-droid/suppository/tree/main/pdf_uploads`

## 🖥️ How to Upload via GitHub Web Interface

### Method 1: Direct Upload via GitHub Website (Easiest)

1. **Go to your repository**:
   - Visit: https://github.com/joshhartman74-droid/suppository

2. **Navigate to the pdf_uploads folder**:
   - Click on the `pdf_uploads` folder

3. **Upload your PDF**:
   - Click the green **"Add file"** button
   - Select **"Upload files"**
   - Drag and drop your PDF file, or click **"choose your files"**
   - Click **"Commit changes"**

### Method 2: GitHub Desktop (If you have it installed)

1. **Clone your repository** in GitHub Desktop
2. **Navigate to the pdf_uploads folder** in your local clone
3. **Copy your PDF** into the pdf_uploads folder
4. **Commit and push** the changes

### Method 3: Command Line (If you have Git installed)

```bash
# Clone your repository
git clone https://github.com/joshhartman74-droid/suppository.git
cd suppository

# Copy your PDF to the uploads folder
cp /path/to/your/file.pdf pdf_uploads/

# Commit and push
git add pdf_uploads/your_file.pdf
git commit -m "Add my PDF for processing"
git push origin main
```

## ✅ After Uploading via GitHub

Once you've uploaded your PDF to the `pdf_uploads/` folder on GitHub:

1. **The file will automatically sync** to the workspace (may take a few seconds)
2. **Run the processing script**:

```bash
cd /workspace/joshhartman74-droid__suppository
python pdf_filter_mistral.py \
    --pdf pdf_uploads/your_file.pdf \
    --output pdf_uploads/filtered_your_file.pdf \
    --json-output pdf_uploads/your_file_schemas.json \
    --workers 1 \
    --dpi 150
```

## 📋 Current Files in pdf_uploads/

You should see these files already in the folder:
- `test_pdf.pdf` - Test file we created
- `test_pdf_mixed.pdf` - Another test file
- `filtered_test.pdf` - Result of our test processing
- `test_schemas.json` - JSON output from test
- `UPLOAD_HERE.txt` - Instructions

**Your PDF will appear alongside these files once uploaded.**

## 💡 Tips for GitHub Upload

- **File size limit**: GitHub allows files up to 100MB in the web interface
- **Your file is 300MB**: This exceeds GitHub's web upload limit
- **Solution**: Use Git LFS or split your file

### For Files > 100MB (Your 300MB PDF)

Since your PDF is 300MB, you have two options:

#### Option A: Use Git LFS (Recommended)

1. **Install Git LFS**: https://git-lfs.com/
2. **Enable LFS in your repo**:
   ```bash
   git lfs install
   git lfs track "*.pdf"
   git add .gitattributes
   git commit -m "Add Git LFS tracking"
   git push origin main
   ```
3. **Upload your PDF**:
   ```bash
   git add pdf_uploads/your_large_file.pdf
   git commit -m "Add large PDF"
   git push origin main
   ```

#### Option B: Split Your PDF

Use a PDF splitter tool to create smaller files (<100MB each), then upload them separately.

#### Option C: Share via URL Instead

Since GitHub has file size limits, you might prefer to:
1. **Upload to Google Drive/Dropbox**
2. **Share the link with me**
3. **I'll download it to the workspace**

## 🎯 Quick Summary

**Easiest method**: Upload via GitHub website to `pdf_uploads/` folder  
**For 300MB file**: Use Git LFS or share a URL  
**After upload**: Run the processing script  

**Your repository is ready and waiting for your PDF!** 🚀

## 🔗 Direct Links

- **Repository**: https://github.com/joshhartman74-droid/suppository
- **pdf_uploads folder**: https://github.com/joshhartman74-droid/suppository/tree/main/pdf_uploads
- **Raw folder**: https://github.com/joshhartman74-droid/suppository/trunk/pdf_uploads

Need help with any of these methods? Just let me know which one you'd like to use!