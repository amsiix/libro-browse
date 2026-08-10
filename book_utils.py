"""
Shared helpers for working with book folders — used by both app.py (serving)
and add_book.py (importing/verifying), so page counts and metadata checks
stay consistent between the two.
"""

import hashlib
import json
import re
from pathlib import Path

try:
    from pypdf import PdfReader
    pypdf_available = True
except ImportError:
    pypdf_available = False


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
    except Exception:
        pass

    return False, None


_page_count_cache = {}  # str(path) -> (mtime, count)

def get_pdf_page_count(pdf_path):
    """
    Authoritative page count read straight from the PDF file itself
    (never from metadata.json, which can drift). Cached by mtime so
    repeated requests don't re-parse the file.
    """
    if not pypdf_available or not pdf_path.exists():
        return None
    try:
        mtime = pdf_path.stat().st_mtime
        cached = _page_count_cache.get(str(pdf_path))
        if cached and cached[0] == mtime:
            return cached[1]
        count = len(PdfReader(str(pdf_path)).pages)
        _page_count_cache[str(pdf_path)] = (mtime, count)
        return count
    except Exception:
        return None


def compute_pdf_fingerprint(pdf_path, chunk_size=1024 * 1024):
    """
    sha256 + size fingerprint of a PDF's bytes, so a later swap of the
    underlying file (without updating metadata.json) can be detected.
    """
    if not pdf_path.exists():
        return None
    hasher = hashlib.sha256()
    size = 0
    with open(pdf_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hasher.update(chunk)
            size += len(chunk)
    return {'sha256': hasher.hexdigest(), 'size': size}


def check_book(book_dir, backfill_fingerprint=False):
    """
    Cross-check a book's metadata.json against its actual files.
    Returns a list of human-readable warning strings (empty if all good).

    If backfill_fingerprint is True and a PDF book has no recorded
    pdf_fingerprint yet, one is computed and written now so future
    swaps of the file can be caught.
    """
    warnings = []
    metadata_file = book_dir / 'metadata.json'
    if not metadata_file.exists():
        return warnings  # nothing to check against

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        return [f"metadata.json is not valid JSON: {e}"]

    is_pdf, pdf_file = is_pdf_book(book_dir)

    if is_pdf:
        pdf_path = book_dir / pdf_file
        if not pdf_path.exists():
            warnings.append(f"metadata references pdf_file '{pdf_file}' but it does not exist")
            return warnings

        actual_count = get_pdf_page_count(pdf_path)
        declared_count = metadata.get('page_count')
        if actual_count is not None and declared_count and actual_count != declared_count:
            warnings.append(
                f"declared page_count ({declared_count}) does not match the PDF's actual "
                f"page count ({actual_count}) -- metadata.json may be stale or point at the wrong file"
            )

        fingerprint = compute_pdf_fingerprint(pdf_path)
        recorded = metadata.get('pdf_fingerprint')
        if recorded and fingerprint and recorded.get('sha256') != fingerprint['sha256']:
            warnings.append(
                "the PDF file's contents changed since its fingerprint was recorded in "
                "metadata.json -- title/author/page_count may now be stale"
            )
        elif not recorded and fingerprint and backfill_fingerprint:
            metadata['pdf_fingerprint'] = fingerprint
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
    else:
        image_files = [
            f for f in book_dir.iterdir()
            if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']
        ]
        if not image_files:
            warnings.append("no page images found in this folder")
        cover = metadata.get('cover')
        if cover and not (book_dir / cover).exists():
            warnings.append(f"metadata cover '{cover}' does not exist in this folder")

    return warnings


def check_all_books(books_dir, backfill_fingerprint=False):
    """
    Run check_book() over every folder in books_dir.
    Returns {book_id: [warnings]} for books that have issues.
    """
    results = {}
    if not books_dir.exists():
        return results
    for book_dir in sorted(books_dir.iterdir()):
        if book_dir.is_dir():
            warnings = check_book(book_dir, backfill_fingerprint=backfill_fingerprint)
            if warnings:
                results[book_dir.name] = warnings
    return results


def get_authors(metadata):
    """
    Normalize metadata['author'] into a list of author name strings.
    Accepts either a single string (existing books) or a list of
    "First Last" strings (new). Always returns a non-empty list.
    """
    author = metadata.get('author')

    if isinstance(author, list):
        names = [str(a).strip() for a in author if str(a).strip()]
        return names or ['Unknown']

    if isinstance(author, str) and author.strip():
        return [author.strip()]

    return ['Unknown']


def build_citation(metadata, pdf_filename, page):
    """
    Build a citation string: "<authors> (<year>). _<title>_. <pdf filename>. p. <page>."
    """
    authors = ', '.join(get_authors(metadata))
    year = metadata.get('year') or 'n.d.'
    title = metadata.get('title') or 'Untitled'
    return f"{authors} ({year}). _{title}_. {pdf_filename}. p. {page}."


def slugify_quote(quote, max_words=6, max_len=50):
    """
    Turn the first few words of a quote into a filename-safe slug.
    Falls back to "highlight" if nothing alphanumeric survives.
    """
    # Remove apostrophes first -- both straight ASCII (') and the Unicode
    # curly quotes (’ right single quote, ‘ left single quote)
    # that real PDF text extraction very commonly produces, so e.g.
    # "isn’t" slugs the same as "isn't" instead of splitting into
    # "isn" + "t".
    normalized = re.sub(r"['‘’]", "", quote.lower())
    normalized = re.sub(r"[^\w\s]", " ", normalized)  # Replace other punctuation with spaces
    words = normalized.split()[:max_words]
    slug = '-'.join(words)[:max_len].rstrip('-')
    return slug or 'highlight'


class HighlightIndexError(Exception):
    """Raised by load_highlight_index() when .index.json exists but can't
    be parsed as a JSON list -- deliberately distinct from "missing",
    which is the normal, safe-to-start-fresh case and returns [] instead.
    Callers must NOT treat this the same as "missing" (e.g. by catching
    it and writing a fresh index): a corrupt-but-present index still
    reflects real highlights whose .md files are on disk, and silently
    replacing it with a fresh index would permanently discard their
    range data, leaving those files unprotected against future overlaps."""


def load_highlight_index(highlights_dir):
    """Read books/<id>/highlights/.index.json.

    Returns [] if the file does not exist (nothing recorded yet). Raises
    HighlightIndexError if the file exists but is not valid JSON or does
    not contain a JSON list, so a corrupt index surfaces as an error
    instead of being silently discarded and overwritten by the next
    highlight save.
    """
    index_file = Path(highlights_dir) / '.index.json'
    if not index_file.exists():
        return []
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        raise HighlightIndexError(
            f"{index_file} exists but is not valid JSON: {e}"
        ) from e
    if not isinstance(data, list):
        raise HighlightIndexError(
            f"{index_file} exists but does not contain a JSON list "
            f"(got {type(data).__name__})"
        )
    return data


def save_highlight_index(highlights_dir, index):
    """Write books/<id>/highlights/.index.json."""
    index_file = Path(highlights_dir) / '.index.json'
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)


def ranges_overlap(s1, e1, s2, e2):
    """Half-open interval overlap check; exact duplicates are the trivial case."""
    return s1 < e2 and s2 < e1


def find_overlapping_entry(index, page, range_start, range_end):
    """Return the first index entry on the same page whose range overlaps
    [range_start, range_end), or None."""
    for entry in index:
        if entry.get('page') != page:
            continue
        if ranges_overlap(range_start, range_end, entry['rangeStart'], entry['rangeEnd']):
            return entry
    return None


def resolve_highlight_filename(highlights_dir, page, slug):
    """Return "<page>-<slug>.md", disambiguated with a numeric suffix if
    a file with that name already exists. Never overwrites."""
    highlights_dir = Path(highlights_dir)
    base = f"{page}-{slug}"
    candidate = f"{base}.md"
    suffix = 2
    while (highlights_dir / candidate).exists():
        candidate = f"{base}-{suffix}.md"
        suffix += 1
    return candidate
