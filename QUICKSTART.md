# Quick Start Guide

## Getting Your Books Ready

Since you have books as image folders, here's how to get started:

### Option 1: Copy Your Existing Book Scans

If you already have folders of scanned book images:

1. Copy each book folder into the `books/` directory
2. Create a `metadata.json` file in each folder (see example below)
3. Make sure images are named in sequential order

Example:
```bash
# If you have a book at ~/Documents/MyScans/BookName/
cp -r ~/Documents/MyScans/BookName books/my-book-name
cd books/my-book-name
# Create metadata.json (see below)
```

### Option 2: Converting PDFs to Images

If you have PDFs that you want to convert to images:

**Using ImageMagick:**
```bash
# Install ImageMagick if needed
# Ubuntu/Debian: sudo apt-get install imagemagick
# macOS: brew install imagemagick

# Convert PDF to images
mkdir books/my-book
cd books/my-book
convert -density 300 ~/path/to/your/book.pdf -quality 90 page-%03d.jpg
```

**Using pdftoppm (faster):**
```bash
# Install poppler-utils if needed
# Ubuntu/Debian: sudo apt-get install poppler-utils
# macOS: brew install poppler

# Convert PDF to images
mkdir books/my-book
pdftoppm -jpeg -r 300 ~/path/to/your/book.pdf books/my-book/page
# This creates page-1.jpg, page-2.jpg, etc.
```

### Creating Metadata

After adding images, create a `metadata.json` file in the book folder:

```json
{
  "title": "Your Book Title",
  "author": "Author Name",
  "year": "2023",
  "description": "Brief description of the book",
  "cover": "page-001.jpg",
  "tags": ["genre", "topic"]
}
```

**Minimal version (just title):**
```json
{
  "title": "Your Book Title"
}
```

## Running the App

1. Install dependencies (first time only):
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python app.py
```

3. Open your browser to:
```
http://localhost:5000
```

## Tips for Best Results

1. **Image naming**: Use leading zeros for proper sorting
   - Good: `page-001.jpg`, `page-002.jpg`, `page-010.jpg`
   - Bad: `page-1.jpg`, `page-2.jpg`, `page-10.jpg` (will sort incorrectly)

2. **Image quality**: 300 DPI is recommended for good readability
   - Higher DPI = better quality but larger files
   - Lower DPI = smaller files but may be hard to read

3. **Image format**: JPG is recommended for photographs/scans
   - JPG: Better for scanned pages (smaller file size)
   - PNG: Better for diagrams/text (lossless but larger)

4. **Organization**: Use descriptive folder names
   - Good: `pride-and-prejudice`, `python-programming-guide`
   - Bad: `book1`, `scan-20241210`

## Troubleshooting

**No books showing up?**
- Check that books are in the `books/` directory
- Ensure image files are JPG or PNG format
- Check that filenames don't have special characters

**Pages in wrong order?**
- Use leading zeros in filenames (001.jpg not 1.jpg)
- Ensure all files have consistent naming

**Can't see cover images?**
- Check that the `cover` field in metadata.json matches an actual image file
- If no cover specified, the first image (alphabetically) is used

**Images too large/slow to load?**
- Consider resizing images to max 2000px width
- Use JPG format with 85-90 quality for good balance
