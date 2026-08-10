"""Helpers that generate tiny synthetic books for tests, so nothing depends
on the user's real (gitignored, personal) books/ folder."""

import json
from pathlib import Path

from reportlab.pdfgen import canvas
from PIL import Image


def build_pdf_book(books_dir, book_id, pages_text, metadata_overrides=None):
    """
    Create a books/<book_id>/ folder containing a small real PDF (one page
    per entry in pages_text) and a matching metadata.json declaring it as
    a native-pdf book. Returns the book_dir Path.

    Each entry in pages_text is normally a single string, drawn with one
    c.drawString() call -- which is what makes PDF.js produce exactly one
    text item/DOM span for that page. To exercise the multi-item offset
    math (buildSpanOffsets/getSelectionRange in reader.js), an entry may
    instead be a list/tuple of strings: each is drawn with its own
    drawString() call on its own line (PDF.js merges same-line, abutting
    drawString() calls back into a single text item, so separate lines
    are what reliably produce separate text items/spans -- one per
    segment). Segments are joined with a single space when extracted
    (PDF.js sets hasEOL on the line-ending item, and both reader.js's
    getPageFullText() and this module's expected-text helper below treat
    hasEOL as "insert one space"), so write segment text without your own
    trailing/leading spaces (e.g. ["Hello", "World this is a test."]).
    """
    book_dir = Path(books_dir) / book_id
    book_dir.mkdir(parents=True, exist_ok=True)

    font_name = 'Helvetica'
    font_size = 12
    line_height = 16

    pdf_path = book_dir / 'book.pdf'
    c = canvas.Canvas(str(pdf_path))
    c.setFont(font_name, font_size)
    for page_text in pages_text:
        segments = page_text if isinstance(page_text, (list, tuple)) else [page_text]
        x = 72
        y = 700
        for segment in segments:
            c.drawString(x, y, segment)
            y -= line_height
        c.showPage()
    c.save()

    metadata = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': '2020',
        'type': 'pdf',
        'pdf_file': 'book.pdf',
        'render_mode': 'native-pdf',
        'page_count': len(pages_text),
    }
    if metadata_overrides:
        metadata.update(metadata_overrides)

    with open(book_dir / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f)

    return book_dir


def build_image_book(books_dir, book_id, num_pages=2, metadata_overrides=None):
    """
    Create a books/<book_id>/ folder containing num_pages tiny generated
    JPEGs and a matching metadata.json (no 'type' key, so it's treated as
    an image book).
    Returns the book_dir Path.
    """
    book_dir = Path(books_dir) / book_id
    book_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, num_pages + 1):
        img = Image.new('RGB', (20, 20), color=(i * 10 % 255, 0, 0))
        img.save(book_dir / f'{i:03d}.jpg', 'JPEG')

    metadata = {
        'title': 'Test Image Book',
        'author': 'Test Author',
        'year': '2020',
        'cover': '001.jpg',
    }
    if metadata_overrides:
        metadata.update(metadata_overrides)

    with open(book_dir / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f)

    return book_dir
