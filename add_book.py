#!/usr/bin/env python3
"""
Helper script to add a new book to Libro Browse
"""

import os
import json
import sys
from pathlib import Path
import shutil

try:
    from pypdf import PdfReader
    pypdf_available = True
except ImportError:
    pypdf_available = False

def detect_pdf(source_path):
    """
    Check if folder contains a PDF file.
    Returns: (bool, Path or None)
    """
    pdf_files = list(source_path.glob('*.pdf')) + list(source_path.glob('*.PDF'))

    if len(pdf_files) == 0:
        return False, None
    elif len(pdf_files) == 1:
        return True, pdf_files[0]
    else:
        # Multiple PDFs found - prompt user to choose
        print("Multiple PDF files found:")
        for i, pdf in enumerate(pdf_files):
            print(f"  {i+1}. {pdf.name}")
        try:
            choice = int(input("Select PDF to import (number): ")) - 1
            if 0 <= choice < len(pdf_files):
                return True, pdf_files[choice]
            else:
                print("Invalid selection")
                return False, None
        except (ValueError, IndexError):
            print("Invalid selection")
            return False, None

def extract_pdf_metadata(pdf_path):
    """
    Extract metadata from PDF using pypdf.
    Returns: dict with title, author, page_count, pdf_metadata
    """
    if not pypdf_available:
        print("Warning: pypdf not installed. Cannot extract PDF metadata.")
        return {'title': '', 'author': '', 'page_count': 0, 'pdf_metadata': {}}

    try:
        reader = PdfReader(str(pdf_path))
        metadata = reader.metadata or {}

        # pypdf metadata keys start with '/'
        result = {
            'title': (metadata.get('/Title') or metadata.get('title') or '').strip(),
            'author': (metadata.get('/Author') or metadata.get('author') or '').strip(),
            'page_count': len(reader.pages),
            'pdf_metadata': {
                'creator': (metadata.get('/Creator') or metadata.get('creator') or '').strip(),
                'creation_date': (metadata.get('/CreationDate') or metadata.get('creation_date') or '').strip(),
            }
        }

        return result

    except Exception as e:
        print(f"Warning: Could not extract PDF metadata: {e}")
        return {'title': '', 'author': '', 'page_count': 0, 'pdf_metadata': {}}

def create_book_from_folder(source_folder, book_id=None, metadata=None):
    """
    Copy a folder of images into the books directory and create metadata

    Args:
        source_folder: Path to folder containing book images
        book_id: ID/folder name for the book (defaults to source folder name)
        metadata: Dictionary of metadata (will prompt if not provided)
    """
    source_path = Path(source_folder)

    if not source_path.exists():
        print(f"Error: Source folder '{source_folder}' does not exist")
        return False

    if not source_path.is_dir():
        print(f"Error: '{source_folder}' is not a directory")
        return False

    # Check for PDF files first
    has_pdf, pdf_file = detect_pdf(source_path)

    if has_pdf:
        # PDF import path
        if not pypdf_available:
            print("Error: pypdf is not installed. Install it with: pip install pypdf")
            return False

        pdf_metadata = extract_pdf_metadata(pdf_file)

        if pdf_metadata['page_count'] == 0:
            print("Error: PDF appears to be empty or corrupted")
            return False

        print(f"Found PDF: {pdf_file.name}")
        print(f"  Pages: {pdf_metadata['page_count']}")
        if pdf_metadata.get('title'):
            print(f"  Extracted title: {pdf_metadata['title']}")
        if pdf_metadata.get('author'):
            print(f"  Extracted author: {pdf_metadata['author']}")

        # Determine book ID
        if not book_id:
            book_id = source_path.name.lower().replace(' ', '-')

        # Sanitize book ID
        book_id = ''.join(c for c in book_id if c.isalnum() or c in '-_')

        # Create destination
        books_dir = Path(__file__).parent / 'books'
        books_dir.mkdir(exist_ok=True)
        dest_path = books_dir / book_id

        if dest_path.exists():
            response = input(f"Book '{book_id}' already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled")
                return False
            shutil.rmtree(dest_path)

        # Create book folder
        dest_path.mkdir(exist_ok=True)

        # Copy PDF with standardized name
        print(f"Copying PDF to books/{book_id}/...")
        shutil.copy2(pdf_file, dest_path / 'book.pdf')

        # Prompt for metadata with extracted values as defaults
        if not metadata:
            print("\nEnter book metadata (press Enter to use extracted/default values):")

            default_title = pdf_metadata.get('title') or pdf_file.stem
            title_prompt = f"Title [{default_title}]: "
            title = input(title_prompt).strip()
            if not title:
                title = default_title

            default_author = pdf_metadata.get('author') or 'Unknown'
            author_prompt = f"Author [{default_author}]: "
            author = input(author_prompt).strip()
            if not author:
                author = default_author

            year = input("Year (optional): ").strip()
            description = input("Description (optional): ").strip()
            tags = input("Tags (comma-separated, optional): ").strip()

            metadata = {
                'type': 'pdf',
                'pdf_file': 'book.pdf',
                'title': title,
                'author': author,
                'page_count': pdf_metadata['page_count'],
                'cover': 'page-001.jpg',
                'pdf_metadata': pdf_metadata.get('pdf_metadata', {})
            }

            if year:
                metadata['year'] = year
            if description:
                metadata['description'] = description
            if tags:
                metadata['tags'] = [tag.strip() for tag in tags.split(',')]

        # Write metadata
        metadata_file = dest_path / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"\n✓ PDF book '{book_id}' added successfully!")
        print(f"  Location: books/{book_id}/")
        print(f"  Pages: {pdf_metadata['page_count']}")
        print(f"  Title: {metadata.get('title', 'N/A')}")
        print(f"  Pages will be rendered on-demand when viewing")

        return True

    # If no PDF, continue with image import path
    # Count image files
    image_files = list(source_path.glob('*.jpg')) + list(source_path.glob('*.jpeg')) + \
                  list(source_path.glob('*.png')) + list(source_path.glob('*.JPG')) + \
                  list(source_path.glob('*.PNG'))

    if not image_files:
        print(f"Error: No PDF or image files (jpg, jpeg, png) found in '{source_folder}'")
        return False

    print(f"Found {len(image_files)} images")

    # Determine book ID
    if not book_id:
        book_id = source_path.name.lower().replace(' ', '-')

    # Sanitize book ID
    book_id = ''.join(c for c in book_id if c.isalnum() or c in '-_')

    # Create destination
    books_dir = Path(__file__).parent / 'books'
    books_dir.mkdir(exist_ok=True)
    dest_path = books_dir / book_id

    if dest_path.exists():
        response = input(f"Book '{book_id}' already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled")
            return False
        shutil.rmtree(dest_path)

    # Copy folder
    print(f"Copying images to books/{book_id}/...")
    shutil.copytree(source_path, dest_path)

    # Create metadata
    if not metadata:
        print("\nEnter book metadata (press Enter to skip optional fields):")
        title = input("Title (required): ").strip()
        if not title:
            title = book_id.replace('-', ' ').title()
            print(f"Using default title: {title}")

        author = input("Author (optional): ").strip()
        year = input("Year (optional): ").strip()
        description = input("Description (optional): ").strip()
        tags = input("Tags (comma-separated, optional): ").strip()

        # Find first image for cover
        sorted_images = sorted([f.name for f in image_files])
        cover = sorted_images[0] if sorted_images else ""
        print(f"Using '{cover}' as cover image")

        metadata = {
            "title": title,
            "cover": cover
        }

        if author:
            metadata["author"] = author
        if year:
            metadata["year"] = year
        if description:
            metadata["description"] = description
        if tags:
            metadata["tags"] = [tag.strip() for tag in tags.split(',')]

    # Write metadata
    metadata_file = dest_path / 'metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Book '{book_id}' added successfully!")
    print(f"  Location: books/{book_id}/")
    print(f"  Pages: {len(image_files)}")
    print(f"  Title: {metadata.get('title', 'N/A')}")

    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python add_book.py <folder_path> [book_id]")
        print("\nExample:")
        print("  python add_book.py ~/Documents/MyScans/BookName")
        print("  python add_book.py ~/Documents/MyScans/BookName custom-book-id")
        sys.exit(1)

    source_folder = sys.argv[1]
    book_id = sys.argv[2] if len(sys.argv) > 2 else None

    create_book_from_folder(source_folder, book_id)

if __name__ == '__main__':
    main()
