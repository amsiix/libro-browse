from flask import Flask, render_template, jsonify, send_file, request
import os
import json
from pathlib import Path
import mimetypes
import threading

try:
    from pdf2image import convert_from_path
    pdf2image_available = True
except ImportError:
    pdf2image_available = False

app = Flask(__name__)

# Thread-safe rendering locks
render_locks = {}
render_locks_lock = threading.Lock()

# Configuration
BOOKS_DIR = Path(__file__).parent / 'books'
BOOKS_DIR.mkdir(exist_ok=True)

def is_pdf_book(book_dir):
    """
    Check if book is PDF by reading metadata.
    Returns: (bool, pdf_filename)
    """
    metadata_file = book_dir / 'metadata.json'
    if not metadata_file.exists():
        return False, None

    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        if metadata.get('type') == 'pdf':
            return True, metadata.get('pdf_file', 'book.pdf')
    except:
        pass

    return False, None

def render_pdf_page(pdf_path, page_num, output_path, dpi=150):
    """
    Render PDF page to JPEG.
    Returns True on success.
    """
    if not pdf2image_available:
        print("Error: pdf2image not installed")
        return False

    try:
        # pdf2image uses 1-indexed pages
        page_index = page_num + 1

        # Convert single page to image
        images = convert_from_path(
            str(pdf_path),
            first_page=page_index,
            last_page=page_index,
            dpi=dpi
        )

        if not images:
            return False

        # Save as JPEG
        output_path.parent.mkdir(parents=True, exist_ok=True)
        images[0].save(str(output_path), "JPEG", quality=90)

        return True

    except Exception as e:
        print(f"Error rendering page {page_num}: {e}")
        return False

def get_all_books():
    """Scan the books directory and return all books with metadata"""
    books = []

    if not BOOKS_DIR.exists():
        return books

    for book_dir in BOOKS_DIR.iterdir():
        if book_dir.is_dir():
            metadata_file = book_dir / 'metadata.json'

            # Check if PDF book
            is_pdf, pdf_file = is_pdf_book(book_dir)

            if is_pdf:
                # Load metadata (required for PDF books)
                if not metadata_file.exists():
                    continue
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    continue

                book_info = {
                    'id': book_dir.name,
                    'title': metadata.get('title', book_dir.name),
                    'author': metadata.get('author', 'Unknown'),
                    'year': metadata.get('year', ''),
                    'description': metadata.get('description', ''),
                    'tags': metadata.get('tags', []),
                    'cover': metadata.get('cover', 'page-001.jpg'),
                    'pageCount': metadata.get('page_count', 0)
                }
                books.append(book_info)
            else:
                # Existing image book logic
                # Get list of image files
                image_files = sorted([
                    f.name for f in book_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']
                ])

                if not image_files:
                    continue

                # Load metadata if exists, otherwise use defaults
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except:
                        metadata = {}
                else:
                    metadata = {}

                # Build book info
                book_info = {
                    'id': book_dir.name,
                    'title': metadata.get('title', book_dir.name),
                    'author': metadata.get('author', 'Unknown'),
                    'year': metadata.get('year', ''),
                    'description': metadata.get('description', ''),
                    'tags': metadata.get('tags', []),
                    'cover': metadata.get('cover', image_files[0]),
                    'pageCount': len(image_files)
                }

                books.append(book_info)

    return books

def get_book_pages(book_id):
    """
    Get all pages for a specific book.
    For PDF books, returns expected page filenames.
    For image books, returns actual image files.
    """
    book_dir = BOOKS_DIR / book_id

    if not book_dir.exists() or not book_dir.is_dir():
        return None

    # Check if PDF book
    is_pdf, pdf_file = is_pdf_book(book_dir)

    if is_pdf:
        # Read page count from metadata
        metadata_file = book_dir / 'metadata.json'
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            page_count = metadata.get('page_count', 0)
            # Return expected page filenames (may not exist yet)
            return [f"page-{i+1:03d}.jpg" for i in range(page_count)]
        except:
            return []
    else:
        # Existing image book logic
        image_files = sorted([
            f.name for f in book_dir.iterdir()
            if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']
        ])
        return image_files

@app.route('/')
def index():
    """Serve the main browsing page"""
    return render_template('index.html')

@app.route('/reader/<book_id>')
def reader(book_id):
    """Serve the book reader page"""
    return render_template('reader.html', book_id=book_id)

@app.route('/api/books')
def api_books():
    """API endpoint to get all books"""
    try:
        books = get_all_books()

        # Filter by search query if provided
        query = request.args.get('q', '').lower()
        if query:
            books = [
                book for book in books
                if query in book['title'].lower()
                or query in book['author'].lower()
                or query in book.get('description', '').lower()
                or any(query in tag.lower() for tag in book.get('tags', []))
            ]

        return jsonify({
            'success': True,
            'books': books,
            'count': len(books)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/books/<book_id>')
def api_book_detail(book_id):
    """API endpoint to get details for a specific book"""
    try:
        book_dir = BOOKS_DIR / book_id

        if not book_dir.exists():
            return jsonify({
                'success': False,
                'error': 'Book not found'
            }), 404

        # Get metadata
        metadata_file = book_dir / 'metadata.json'
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {}

        # Get pages
        pages = get_book_pages(book_id)

        if pages is None:
            return jsonify({
                'success': False,
                'error': 'Book not found'
            }), 404

        book_info = {
            'id': book_id,
            'title': metadata.get('title', book_id),
            'author': metadata.get('author', 'Unknown'),
            'year': metadata.get('year', ''),
            'description': metadata.get('description', ''),
            'tags': metadata.get('tags', []),
            'pages': pages,
            'pageCount': len(pages)
        }

        return jsonify({
            'success': True,
            'book': book_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/books/<book_id>/page/<int:page_num>')
def api_book_page(book_id, page_num):
    """API endpoint to get a specific page image. Renders PDF pages on-demand if not cached."""
    try:
        book_dir = BOOKS_DIR / book_id

        if not book_dir.exists():
            return jsonify({'success': False, 'error': 'Book not found'}), 404

        pages = get_book_pages(book_id)

        if pages is None or page_num < 0 or page_num >= len(pages):
            return jsonify({
                'success': False,
                'error': 'Page not found'
            }), 404

        page_file = book_dir / pages[page_num]

        # Check if PDF book
        is_pdf, pdf_filename = is_pdf_book(book_dir)

        if is_pdf:
            # Render if not cached
            if not page_file.exists():
                pdf_path = book_dir / pdf_filename

                if not pdf_path.exists():
                    return jsonify({'success': False, 'error': 'PDF file not found'}), 404

                # Thread-safe rendering
                lock_key = f"{book_id}:{page_num}"

                with render_locks_lock:
                    if lock_key not in render_locks:
                        render_locks[lock_key] = threading.Lock()
                    page_lock = render_locks[lock_key]

                with page_lock:
                    # Double-check after acquiring lock
                    if not page_file.exists():
                        success = render_pdf_page(pdf_path, page_num, page_file, dpi=150)
                        if not success:
                            return jsonify({
                                'success': False,
                                'error': 'Failed to render PDF page'
                            }), 500

                # Cleanup lock
                with render_locks_lock:
                    if lock_key in render_locks:
                        del render_locks[lock_key]

        # Serve file (works for both types)
        if not page_file.exists():
            return jsonify({
                'success': False,
                'error': 'Page file not found'
            }), 404

        return send_file(page_file, mimetype=mimetypes.guess_type(page_file)[0])
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/books/<book_id>/cover')
def api_book_cover(book_id):
    """API endpoint to get book cover image. Renders PDF page 1 on-demand if needed."""
    try:
        book_dir = BOOKS_DIR / book_id
        metadata_file = book_dir / 'metadata.json'

        is_pdf, pdf_filename = is_pdf_book(book_dir)

        # Determine cover file
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                cover_name = metadata.get('cover', 'page-001.jpg' if is_pdf else None)
        else:
            pages = get_book_pages(book_id)
            cover_name = pages[0] if pages else None

        if not cover_name:
            return jsonify({
                'success': False,
                'error': 'Cover not found'
            }), 404

        cover_file = book_dir / cover_name

        # Render PDF cover if needed
        if is_pdf and not cover_file.exists():
            pdf_path = book_dir / pdf_filename
            if pdf_path.exists():
                render_pdf_page(pdf_path, 0, cover_file, dpi=150)

        if not cover_file.exists():
            return jsonify({
                'success': False,
                'error': 'Cover file not found'
            }), 404

        return send_file(cover_file, mimetype=mimetypes.guess_type(cover_file)[0])
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
