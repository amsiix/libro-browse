"""Helpers that generate tiny synthetic books for tests, so nothing depends
on the user's real (gitignored, personal) books/ folder."""

import json
from pathlib import Path

from reportlab.pdfgen import canvas
from PIL import Image


def build_pdf_book(books_dir, book_id, pages_text, metadata_overrides=None):
    """
    Create a books/<book_id>/ folder containing a small real PDF (one page
    per string in pages_text, each with that text drawn on it) and a
    matching metadata.json declaring it as a native-pdf book.
    Returns the book_dir Path.
    """
    book_dir = Path(books_dir) / book_id
    book_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = book_dir / 'book.pdf'
    c = canvas.Canvas(str(pdf_path))
    for text in pages_text:
        c.drawString(72, 700, text)
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
