# PDF Highlighting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a reader select text in a native-PDF book and save it as a citation-formatted markdown file (with duplicate/overlap protection), and stand up this repo's first test suite along the way.

**Architecture:** A new `POST /api/books/<book_id>/highlights` Flask endpoint builds a citation from `metadata.json`, checks the selection's character range against a per-book `.index.json` for overlaps, and writes one markdown file per highlight. The reader's PDF.js text layer gains a status-bar UI (button + `H` shortcut) that computes the selection's range and calls the endpoint. Tests are a pytest pyramid: unit (`book_utils.py` logic), integration (Flask `test_client()`), and end-to-end (`pytest-playwright` driving a real server against synthetic fixture books).

**Tech Stack:** Python 3 / Flask (existing), vanilla JS + PDF.js (existing), pytest + pytest-playwright + reportlab (new, dev-only).

## Global Constraints

- Citation format: `<author(s)> (<year>). _<title>_. <pdf filename>. p. <page>.` — authors joined with `", "`, year falls back to `n.d.`, title falls back to `Untitled`.
- `author` in `metadata.json` may be a single string (existing books, unchanged) or a list of `"First Last"` strings (new) — always normalize through `get_authors()`.
- Highlighting only applies to books where `is_pdf_book()` is true AND `render_mode == 'native-pdf'`. Image-mode books never show the highlight UI.
- One file per highlight at `books/<book_id>/highlights/<page>-<slug>.md`; never overwrite — filename collisions get a numeric suffix.
- Overlap/duplicate detection is range-based (character offsets within a page's extracted text), tracked in `books/<book_id>/highlights/.index.json`, and scoped per-page only.
- `books/` stays gitignored and personal — nothing in this plan writes test fixtures there; all fixtures live under `tmp_path` in disposable test directories.
- No Node tooling — tests are 100% Python (`pytest` + `pytest-playwright`).
- Unit/integration tests follow strict TDD (failing test → implement → passing test). End-to-end tests are written and verified *after* the frontend+backend behavior they cover exists — driving a browser against nothing yet built isn't meaningful red-green, so those tasks are framed as acceptance/regression tests instead, not literal TDD.

---

## File Structure

```
requirements-dev.txt              # new: pytest, pytest-playwright, reportlab
pytest.ini                        # new: testpaths, markers
conftest.py                       # new: repo-root, shared fixtures (books dir, Flask client, live server)
tests/
  fixtures/
    build_books.py                # new: synthetic PDF/image book generators
  unit/
    test_book_utils.py            # new
  integration/
    test_api_books.py             # new: existing routes
    test_highlights_api.py        # new: highlights endpoint
  e2e/
    test_reader_e2e.py            # new: pytest-playwright acceptance/regression tests

book_utils.py                     # modify: + get_authors, build_citation, slugify_quote,
                                   #   load_highlight_index, save_highlight_index,
                                   #   ranges_overlap, find_overlapping_entry,
                                   #   resolve_highlight_filename
app.py                            # modify: env vars, author-field normalization,
                                   #   new /highlights route
add_book.py                       # modify: multi-author prompt
templates/reader.html             # modify: highlight status bar markup, shortcuts list
static/css/reader.css             # modify: highlight status bar styles
static/js/reader.js               # modify: selection/range tracking, save handler
```

---

## Task 1: Test infrastructure

**Files:**
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `conftest.py`
- Create: `tests/fixtures/build_books.py`
- Test: `tests/unit/test_smoke.py`

**Interfaces:**
- Produces: `build_pdf_book(books_dir, book_id, pages_text, metadata_overrides=None) -> Path`, `build_image_book(books_dir, book_id, num_pages=2, metadata_overrides=None) -> Path`, and pytest fixtures `fixture_books_dir` and `app_client`, used by every later test task.

- [ ] **Step 1: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.3
pytest-playwright==0.5.2
reportlab==4.2.5
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
markers =
    e2e: end-to-end browser tests (slower, require `playwright install chromium`)
```

- [ ] **Step 3: Install dev dependencies and Playwright's browser**

Run: `pip install -r requirements-dev.txt && playwright install chromium`

- [ ] **Step 4: Write `tests/fixtures/build_books.py`**

```python
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
```

- [ ] **Step 5: Write `conftest.py` at the repo root**

pytest always inserts a conftest.py's own directory onto `sys.path`, which is what makes `import app` / `import book_utils` resolve from test files anywhere under `tests/` — that's why this file lives at the repo root, not inside `tests/`.

```python
import pytest

from tests.fixtures.build_books import build_pdf_book, build_image_book


@pytest.fixture
def fixture_books_dir(tmp_path):
    """A disposable books/ directory with one PDF book and one image book."""
    books_dir = tmp_path / 'books'
    books_dir.mkdir()
    build_pdf_book(
        books_dir, 'test-pdf-book',
        pages_text=['Page one text for testing.', 'Page two has different text.']
    )
    build_image_book(books_dir, 'test-image-book', num_pages=2)
    return books_dir


@pytest.fixture
def app_client(fixture_books_dir, monkeypatch):
    """Flask test_client() pointed at fixture_books_dir via monkeypatch —
    no app refactor needed, since BOOKS_DIR is a plain module global
    resolved fresh on every function call."""
    import app as app_module
    monkeypatch.setattr(app_module, 'BOOKS_DIR', fixture_books_dir)
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        yield client
```

- [ ] **Step 6: Write a smoke test**

```python
def test_fixture_books_dir_has_two_books(fixture_books_dir):
    assert (fixture_books_dir / 'test-pdf-book' / 'book.pdf').exists()
    assert (fixture_books_dir / 'test-pdf-book' / 'metadata.json').exists()
    assert (fixture_books_dir / 'test-image-book' / '001.jpg').exists()


def test_app_client_lists_fixture_books(app_client):
    response = app_client.get('/api/books')
    data = response.get_json()
    assert data['success'] is True
    ids = {b['id'] for b in data['books']}
    assert ids == {'test-pdf-book', 'test-image-book'}
```

- [ ] **Step 7: Run the smoke tests**

Run: `pytest tests/unit/test_smoke.py -v`
Expected: both tests PASS (this exercises the real `get_all_books()` against fixture data, so it also validates Task 1's infra end-to-end).

- [ ] **Step 8: Commit**

```bash
git add requirements-dev.txt pytest.ini conftest.py tests/fixtures/build_books.py tests/unit/test_smoke.py
git commit -m "test: add pytest infrastructure with synthetic book fixtures"
```

---

## Task 2: Unit tests for existing `book_utils.py` functions

Backfills coverage for code that already shipped this session but has no tests yet: `is_pdf_book`, `get_pdf_page_count`, `compute_pdf_fingerprint`, `check_book`, `check_all_books`. No production code changes in this task.

**Files:**
- Test: `tests/unit/test_book_utils.py`

**Interfaces:**
- Consumes: `book_utils.is_pdf_book(book_dir)`, `book_utils.get_pdf_page_count(pdf_path)`, `book_utils.compute_pdf_fingerprint(pdf_path)`, `book_utils.check_book(book_dir, backfill_fingerprint=False)`, `book_utils.check_all_books(books_dir, backfill_fingerprint=False)`; `tests.fixtures.build_books.build_pdf_book`, `build_image_book`.

- [ ] **Step 1: Write the tests**

```python
import json

import book_utils
from tests.fixtures.build_books import build_pdf_book, build_image_book


def test_is_pdf_book_true_for_pdf_metadata(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one'])
    is_pdf, pdf_file = book_utils.is_pdf_book(book_dir)
    assert is_pdf is True
    assert pdf_file == 'book.pdf'


def test_is_pdf_book_false_for_image_metadata(tmp_path):
    book_dir = build_image_book(tmp_path, 'b1')
    is_pdf, pdf_file = book_utils.is_pdf_book(book_dir)
    assert is_pdf is False
    assert pdf_file is None


def test_is_pdf_book_false_when_metadata_missing(tmp_path):
    book_dir = tmp_path / 'no-metadata'
    book_dir.mkdir()
    is_pdf, pdf_file = book_utils.is_pdf_book(book_dir)
    assert is_pdf is False
    assert pdf_file is None


def test_get_pdf_page_count_reads_actual_pdf(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one', 'two', 'three'])
    count = book_utils.get_pdf_page_count(book_dir / 'book.pdf')
    assert count == 3


def test_get_pdf_page_count_none_for_missing_file(tmp_path):
    assert book_utils.get_pdf_page_count(tmp_path / 'nope.pdf') is None


def test_compute_pdf_fingerprint_changes_when_file_changes(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one'])
    pdf_path = book_dir / 'book.pdf'
    fp1 = book_utils.compute_pdf_fingerprint(pdf_path)
    assert fp1['size'] == pdf_path.stat().st_size

    other_dir = build_pdf_book(tmp_path, 'b2', pages_text=['completely different text'])
    fp2 = book_utils.compute_pdf_fingerprint(other_dir / 'book.pdf')
    assert fp2['sha256'] != fp1['sha256']


def test_check_book_flags_page_count_mismatch(tmp_path):
    book_dir = build_pdf_book(
        tmp_path, 'b1', pages_text=['one', 'two'],
        metadata_overrides={'page_count': 999}
    )
    warnings = book_utils.check_book(book_dir)
    assert any('page_count' in w for w in warnings)


def test_check_book_no_warnings_for_correct_pdf_book(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one', 'two'])
    warnings = book_utils.check_book(book_dir)
    assert warnings == []


def test_check_book_flags_missing_pdf_file(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one'])
    (book_dir / 'book.pdf').unlink()
    warnings = book_utils.check_book(book_dir)
    assert any('does not exist' in w for w in warnings)


def test_check_book_flags_fingerprint_drift(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one'])
    warnings = book_utils.check_book(book_dir, backfill_fingerprint=True)
    assert warnings == []

    # Swap in a different PDF without updating metadata.json
    other = build_pdf_book(tmp_path, 'b2', pages_text=['a totally different book'])
    (book_dir / 'book.pdf').write_bytes((other / 'book.pdf').read_bytes())

    warnings = book_utils.check_book(book_dir)
    assert any('changed since its fingerprint' in w for w in warnings)


def test_check_book_flags_missing_cover_for_image_book(tmp_path):
    book_dir = build_image_book(tmp_path, 'b1', metadata_overrides={'cover': 'missing.jpg'})
    warnings = book_utils.check_book(book_dir)
    assert any('missing.jpg' in w for w in warnings)


def test_check_all_books_only_returns_books_with_issues(tmp_path):
    build_pdf_book(tmp_path, 'good', pages_text=['one'])
    build_pdf_book(tmp_path, 'bad', pages_text=['one', 'two'], metadata_overrides={'page_count': 5})

    issues = book_utils.check_all_books(tmp_path)
    assert set(issues.keys()) == {'bad'}
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/unit/test_book_utils.py -v`
Expected: all PASS (this is backfilled coverage for already-shipped code, so no implementation step follows).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_book_utils.py
git commit -m "test: backfill unit coverage for existing book_utils functions"
```

---

## Task 3: `book_utils.get_authors()`

**Files:**
- Modify: `book_utils.py` (append after `check_all_books`)
- Test: `tests/unit/test_book_utils.py` (append)

**Interfaces:**
- Produces: `get_authors(metadata: dict) -> list[str]`, used by Task 4 (`build_citation`) and Task 8 (`app.py` author-field normalization).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_book_utils.py`:

```python
def test_get_authors_single_string():
    assert book_utils.get_authors({'author': 'Seneca'}) == ['Seneca']


def test_get_authors_list_of_strings():
    metadata = {'author': ['Wolfgang Karl Härdle', 'Léopold Simar']}
    assert book_utils.get_authors(metadata) == ['Wolfgang Karl Härdle', 'Léopold Simar']


def test_get_authors_strips_whitespace_and_drops_empties():
    metadata = {'author': [' Ada Lovelace ', '', '  ']}
    assert book_utils.get_authors(metadata) == ['Ada Lovelace']


def test_get_authors_defaults_to_unknown_when_missing():
    assert book_utils.get_authors({}) == ['Unknown']


def test_get_authors_defaults_to_unknown_when_blank_string():
    assert book_utils.get_authors({'author': '   '}) == ['Unknown']
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_book_utils.py -k get_authors -v`
Expected: FAIL with `AttributeError: module 'book_utils' has no attribute 'get_authors'`

- [ ] **Step 3: Implement `get_authors()`**

Append to `book_utils.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_book_utils.py -k get_authors -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add book_utils.py tests/unit/test_book_utils.py
git commit -m "feat: add get_authors() for single- and multi-author metadata"
```

---

## Task 4: `book_utils.build_citation()`

**Files:**
- Modify: `book_utils.py` (append)
- Test: `tests/unit/test_book_utils.py` (append)

**Interfaces:**
- Consumes: `get_authors(metadata)` from Task 3.
- Produces: `build_citation(metadata: dict, pdf_filename: str, page: int) -> str`, used by Task 9 (`/highlights` endpoint).

- [ ] **Step 1: Write the failing tests**

```python
def test_build_citation_single_author():
    metadata = {'title': 'The Theory of Probability', 'author': 'B. V. Gnedenko', 'year': '1978'}
    citation = book_utils.build_citation(metadata, 'Gnedenko-Theory of Probability.pdf', 42)
    assert citation == (
        'B. V. Gnedenko (1978). _The Theory of Probability_. '
        'Gnedenko-Theory of Probability.pdf. p. 42.'
    )


def test_build_citation_multi_author_comma_separated():
    metadata = {
        'title': 'Applied Multivariate Statistical Analysis',
        'author': ['Wolfgang Karl Härdle', 'Léopold Simar'],
        'year': '2003',
    }
    citation = book_utils.build_citation(metadata, 'stats.pdf', 5)
    assert citation.startswith('Wolfgang Karl Härdle, Léopold Simar (2003).')


def test_build_citation_falls_back_when_year_missing():
    metadata = {'title': 'Untitled Work', 'author': 'Someone'}
    citation = book_utils.build_citation(metadata, 'book.pdf', 1)
    assert '(n.d.)' in citation


def test_build_citation_falls_back_when_title_missing():
    metadata = {'author': 'Someone', 'year': '2020'}
    citation = book_utils.build_citation(metadata, 'book.pdf', 1)
    assert '_Untitled_' in citation
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_book_utils.py -k build_citation -v`
Expected: FAIL with `AttributeError: module 'book_utils' has no attribute 'build_citation'`

- [ ] **Step 3: Implement `build_citation()`**

Append to `book_utils.py`:

```python
def build_citation(metadata, pdf_filename, page):
    """
    Build a citation string: "<authors> (<year>). _<title>_. <pdf filename>. p. <page>."
    """
    authors = ', '.join(get_authors(metadata))
    year = metadata.get('year') or 'n.d.'
    title = metadata.get('title') or 'Untitled'
    return f"{authors} ({year}). _{title}_. {pdf_filename}. p. {page}."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_book_utils.py -k build_citation -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add book_utils.py tests/unit/test_book_utils.py
git commit -m "feat: add build_citation() for highlight markdown files"
```

---

## Task 5: `book_utils.slugify_quote()`

**Files:**
- Modify: `book_utils.py` (append; add `import re` to the top imports)
- Test: `tests/unit/test_book_utils.py` (append)

**Interfaces:**
- Produces: `slugify_quote(quote: str, max_words: int = 6, max_len: int = 50) -> str`, used by Task 9.

- [ ] **Step 1: Write the failing tests**

```python
def test_slugify_quote_basic():
    assert book_utils.slugify_quote('Doubt is not a pleasant condition, but certainty is absurd.') \
        == 'doubt-is-not-a-pleasant-condition'


def test_slugify_quote_truncates_to_max_len():
    quote = 'a very long quote ' * 10
    slug = book_utils.slugify_quote(quote)
    assert len(slug) <= 50
    assert not slug.endswith('-')


def test_slugify_quote_strips_punctuation():
    assert book_utils.slugify_quote("It's--strange, isn't it?") == 'its-strange-isnt-it'


def test_slugify_quote_falls_back_when_empty_after_stripping():
    assert book_utils.slugify_quote('...???!!!') == 'highlight'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_book_utils.py -k slugify_quote -v`
Expected: FAIL with `AttributeError: module 'book_utils' has no attribute 'slugify_quote'`

- [ ] **Step 3: Implement `slugify_quote()`**

Add `import re` near the top of `book_utils.py` (alongside the existing `import hashlib` / `import json`), then append:

```python
def slugify_quote(quote, max_words=6, max_len=50):
    """
    Turn the first few words of a quote into a filename-safe slug.
    Falls back to "highlight" if nothing alphanumeric survives.
    """
    normalized = re.sub(r"[^\w\s]", "", quote.lower())
    words = normalized.split()[:max_words]
    slug = '-'.join(words)[:max_len].rstrip('-')
    return slug or 'highlight'
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_book_utils.py -k slugify_quote -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add book_utils.py tests/unit/test_book_utils.py
git commit -m "feat: add slugify_quote() for highlight filenames"
```

---

## Task 6: Highlight index + overlap detection

**Files:**
- Modify: `book_utils.py` (append)
- Test: `tests/unit/test_book_utils.py` (append)

**Interfaces:**
- Produces:
  - `load_highlight_index(highlights_dir: Path) -> list[dict]`
  - `save_highlight_index(highlights_dir: Path, index: list[dict]) -> None`
  - `ranges_overlap(s1: int, e1: int, s2: int, e2: int) -> bool`
  - `find_overlapping_entry(index: list[dict], page: int, range_start: int, range_end: int) -> dict | None`
  - `resolve_highlight_filename(highlights_dir: Path, page: int, slug: str) -> str`
  - Index entry shape: `{"file": str, "page": int, "rangeStart": int, "rangeEnd": int}`
  - Used by Task 9 (`/highlights` endpoint).

- [ ] **Step 1: Write the failing tests**

```python
def test_load_highlight_index_empty_when_missing(tmp_path):
    assert book_utils.load_highlight_index(tmp_path) == []


def test_save_and_load_highlight_index_roundtrip(tmp_path):
    index = [{'file': '1-foo.md', 'page': 1, 'rangeStart': 0, 'rangeEnd': 10}]
    book_utils.save_highlight_index(tmp_path, index)
    assert book_utils.load_highlight_index(tmp_path) == index


def test_ranges_overlap_true_for_exact_duplicate():
    assert book_utils.ranges_overlap(5, 15, 5, 15) is True


def test_ranges_overlap_true_for_partial_overlap():
    assert book_utils.ranges_overlap(5, 15, 10, 20) is True


def test_ranges_overlap_false_for_adjacent_ranges():
    assert book_utils.ranges_overlap(5, 15, 15, 25) is False


def test_ranges_overlap_false_for_disjoint_ranges():
    assert book_utils.ranges_overlap(5, 10, 20, 30) is False


def test_find_overlapping_entry_matches_same_page(tmp_path):
    index = [{'file': '1-foo.md', 'page': 1, 'rangeStart': 5, 'rangeEnd': 15}]
    conflict = book_utils.find_overlapping_entry(index, page=1, range_start=10, range_end=20)
    assert conflict == index[0]


def test_find_overlapping_entry_ignores_other_pages(tmp_path):
    index = [{'file': '1-foo.md', 'page': 1, 'rangeStart': 5, 'rangeEnd': 15}]
    conflict = book_utils.find_overlapping_entry(index, page=2, range_start=5, range_end=15)
    assert conflict is None


def test_find_overlapping_entry_none_when_no_overlap(tmp_path):
    index = [{'file': '1-foo.md', 'page': 1, 'rangeStart': 5, 'rangeEnd': 15}]
    conflict = book_utils.find_overlapping_entry(index, page=1, range_start=20, range_end=30)
    assert conflict is None


def test_resolve_highlight_filename_no_collision(tmp_path):
    assert book_utils.resolve_highlight_filename(tmp_path, 42, 'doubt-is-not') == '42-doubt-is-not.md'


def test_resolve_highlight_filename_disambiguates_collision(tmp_path):
    (tmp_path / '42-doubt-is-not.md').write_text('existing')
    assert book_utils.resolve_highlight_filename(tmp_path, 42, 'doubt-is-not') == '42-doubt-is-not-2.md'

    (tmp_path / '42-doubt-is-not-2.md').write_text('existing')
    assert book_utils.resolve_highlight_filename(tmp_path, 42, 'doubt-is-not') == '42-doubt-is-not-3.md'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_book_utils.py -k "highlight_index or ranges_overlap or overlapping_entry or resolve_highlight_filename" -v`
Expected: FAIL with `AttributeError` for each missing function.

- [ ] **Step 3: Implement the index/overlap helpers**

Append to `book_utils.py`:

```python
def load_highlight_index(highlights_dir):
    """Read books/<id>/highlights/.index.json. Returns [] if missing/invalid."""
    index_file = Path(highlights_dir) / '.index.json'
    if not index_file.exists():
        return []
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


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
```

Add `from pathlib import Path` to `book_utils.py`'s imports (it isn't imported there yet — only used via the `book_dir`/`pdf_path` parameters passed in from callers so far).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_book_utils.py -k "highlight_index or ranges_overlap or overlapping_entry or resolve_highlight_filename" -v`
Expected: all PASS

- [ ] **Step 5: Run the full unit suite**

Run: `pytest tests/unit/ -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add book_utils.py tests/unit/test_book_utils.py
git commit -m "feat: add highlight index storage and overlap detection"
```

---

## Task 7: `app.py` testability env vars (`LIBRO_BOOKS_DIR`, `LIBRO_PORT`, `LIBRO_DEBUG`)

**Files:**
- Modify: `app.py:23` (BOOKS_DIR), `app.py:417-423` (`__main__` block)
- Test: `tests/integration/test_api_books.py` (new file)

**Interfaces:**
- Produces: `app.BOOKS_DIR` overridable via `LIBRO_BOOKS_DIR` env var at import time; `python app.py` honors `LIBRO_PORT` (default `5000`) and `LIBRO_DEBUG` (default on, `0` disables). Used by Task 13's `live_server` fixture to run a real, isolated server for e2e tests.

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_api_books.py`:

```python
import importlib
import os


def test_books_dir_honors_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv('LIBRO_BOOKS_DIR', str(tmp_path))
    import app as app_module
    importlib.reload(app_module)
    try:
        assert app_module.BOOKS_DIR == tmp_path
    finally:
        monkeypatch.delenv('LIBRO_BOOKS_DIR', raising=False)
        importlib.reload(app_module)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_api_books.py -v`
Expected: FAIL — `app_module.BOOKS_DIR` resolves to the hardcoded `books/` path, not `tmp_path`.

- [ ] **Step 3: Implement the env var support**

In `app.py`, replace line 23:

```python
BOOKS_DIR = Path(__file__).parent / 'books'
```

with:

```python
BOOKS_DIR = Path(os.environ.get('LIBRO_BOOKS_DIR', Path(__file__).parent / 'books'))
```

Replace the `if __name__ == '__main__':` block at the bottom of `app.py`:

```python
if __name__ == '__main__':
    DEBUG = True
    # The Werkzeug reloader re-execs this file in a child process when DEBUG
    # is on; only run the check there so it doesn't print/backfill twice.
    if not DEBUG or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print_metadata_warnings()
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)
```

with:

```python
if __name__ == '__main__':
    DEBUG = os.environ.get('LIBRO_DEBUG', '1') != '0'
    PORT = int(os.environ.get('LIBRO_PORT', '5000'))
    # The Werkzeug reloader re-execs this file in a child process when DEBUG
    # is on; only run the check there so it doesn't print/backfill twice.
    if not DEBUG or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print_metadata_warnings()
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_api_books.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/integration/test_api_books.py
git commit -m "feat: make BOOKS_DIR/port/debug overridable via env vars for testing"
```

---

## Task 8: Integration tests for existing routes + author-field normalization

**Files:**
- Modify: `app.py:87-96` (PDF branch of `get_all_books()`), `app.py:120-129` (image branch), `app.py:246` (`api_book_detail`)
- Test: `tests/integration/test_api_books.py` (append)

**Interfaces:**
- Consumes: `book_utils.get_authors(metadata)` from Task 3.
- Produces: `get_all_books()` and `api_book_detail()`'s `author` field is now always a single, comma-joined display string regardless of whether `metadata.json` stores a string or a list.

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_api_books.py`:

```python
from tests.fixtures.build_books import build_pdf_book, build_image_book


def test_api_books_lists_fixture_books(app_client):
    response = app_client.get('/api/books')
    data = response.get_json()
    assert data['success'] is True
    ids = {b['id'] for b in data['books']}
    assert {'test-pdf-book', 'test-image-book'} == ids


def test_api_books_multi_author_joined_with_comma(fixture_books_dir, monkeypatch):
    build_pdf_book(
        fixture_books_dir, 'multi-author-book', pages_text=['one'],
        metadata_overrides={'author': ['Wolfgang Karl Härdle', 'Léopold Simar']}
    )
    import app as app_module
    monkeypatch.setattr(app_module, 'BOOKS_DIR', fixture_books_dir)
    with app_module.app.test_client() as client:
        data = client.get('/api/books').get_json()
    book = next(b for b in data['books'] if b['id'] == 'multi-author-book')
    assert book['author'] == 'Wolfgang Karl Härdle, Léopold Simar'


def test_api_book_detail_returns_pdf_book(app_client):
    response = app_client.get('/api/books/test-pdf-book')
    data = response.get_json()
    assert data['success'] is True
    assert data['book']['type'] == 'pdf'
    assert data['book']['renderMode'] == 'native-pdf'
    assert data['book']['pageCount'] == 2


def test_api_book_detail_404_for_missing_book(app_client):
    response = app_client.get('/api/books/does-not-exist')
    assert response.status_code == 404


def test_api_book_page_serves_rendered_pdf_page(app_client):
    response = app_client.get('/api/books/test-pdf-book/page/0')
    assert response.status_code == 200
    assert response.mimetype == 'image/jpeg'


def test_api_book_cover_serves_image(app_client):
    response = app_client.get('/api/books/test-image-book/cover')
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify the multi-author one fails**

Run: `pytest tests/integration/test_api_books.py -k multi_author -v`
Expected: FAIL — `book['author']` is currently `['Wolfgang Karl Härdle', 'Léopold Simar']` (a raw list), not the joined string.

- [ ] **Step 3: Wire `get_authors()` into `app.py`**

Add the import at the top of `app.py` (line 8):

```python
from book_utils import is_pdf_book, get_pdf_page_count, check_all_books, get_authors
```

In `get_all_books()`'s PDF branch, replace:

```python
                book_info = {
                    'id': book_dir.name,
                    'title': metadata.get('title', book_dir.name),
                    'author': metadata.get('author', 'Unknown'),
```

with:

```python
                book_info = {
                    'id': book_dir.name,
                    'title': metadata.get('title', book_dir.name),
                    'author': ', '.join(get_authors(metadata)),
```

In `get_all_books()`'s image branch, replace:

```python
                book_info = {
                    'id': book_dir.name,
                    'title': metadata.get('title', book_dir.name),
                    'author': metadata.get('author', 'Unknown'),
```

with the same `', '.join(get_authors(metadata))` line.

In `api_book_detail()`, replace:

```python
            'author': metadata.get('author', 'Unknown'),
```

with:

```python
            'author': ', '.join(get_authors(metadata)),
```

- [ ] **Step 4: Run all tests in this task to verify they pass**

Run: `pytest tests/integration/test_api_books.py -v`
Expected: all PASS

- [ ] **Step 5: Run the full test suite so far**

Run: `pytest tests/unit tests/integration -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app.py tests/integration/test_api_books.py
git commit -m "feat: normalize author display through get_authors() in API responses"
```

---

## Task 9: `POST /api/books/<book_id>/highlights` endpoint

**Files:**
- Modify: `app.py` (add route before `if __name__ == '__main__':`, update the import line from Task 8)
- Test: `tests/integration/test_highlights_api.py` (new file)

**Interfaces:**
- Consumes: `is_pdf_book`, `build_citation`, `slugify_quote`, `resolve_highlight_filename`, `load_highlight_index`, `save_highlight_index`, `find_overlapping_entry` — all from `book_utils`.
- Produces: `POST /api/books/<book_id>/highlights` accepting `{"page": int, "quote": str, "rangeStart": int, "rangeEnd": int}`, returning `{"success": true, "path": "highlights/<file>"}` on `200`, or `{"success": false, "error": str}` on `400`/`404`/`409`. Consumed by the frontend in Task 12.

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_highlights_api.py`:

```python
def test_save_highlight_creates_file_with_citation(app_client, fixture_books_dir):
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'Page one text for testing.',
        'rangeStart': 0, 'rangeEnd': 26,
    })
    data = response.get_json()
    assert response.status_code == 200
    assert data['success'] is True
    assert data['path'].startswith('highlights/1-')

    saved = fixture_books_dir / 'test-pdf-book' / data['path']
    content = saved.read_text()
    assert content.startswith('> Page one text for testing.')
    assert 'Test Author (2020). _Test Book_. book.pdf. p. 1.' in content


def test_save_highlight_writes_index_entry(app_client, fixture_books_dir):
    app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'Page one text for testing.',
        'rangeStart': 0, 'rangeEnd': 26,
    })
    import json as jsonlib
    index_path = fixture_books_dir / 'test-pdf-book' / 'highlights' / '.index.json'
    index = jsonlib.loads(index_path.read_text())
    assert len(index) == 1
    assert index[0]['page'] == 1
    assert index[0]['rangeStart'] == 0
    assert index[0]['rangeEnd'] == 26


def test_save_highlight_404_for_missing_book(app_client):
    response = app_client.post('/api/books/does-not-exist/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 4,
    })
    assert response.status_code == 404


def test_save_highlight_400_for_image_book(app_client):
    response = app_client.post('/api/books/test-image-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 4,
    })
    assert response.status_code == 400


def test_save_highlight_400_for_empty_quote(app_client):
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': '   ', 'rangeStart': 0, 'rangeEnd': 4,
    })
    assert response.status_code == 400


def test_save_highlight_400_for_invalid_range(app_client):
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 10, 'rangeEnd': 5,
    })
    assert response.status_code == 400


def test_save_highlight_409_for_exact_duplicate(app_client):
    payload = {'page': 1, 'quote': 'Page one text for testing.', 'rangeStart': 0, 'rangeEnd': 26}
    first = app_client.post('/api/books/test-pdf-book/highlights', json=payload)
    assert first.status_code == 200

    second = app_client.post('/api/books/test-pdf-book/highlights', json=payload)
    assert second.status_code == 409


def test_save_highlight_409_for_partial_overlap(app_client):
    app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'Page one text', 'rangeStart': 0, 'rangeEnd': 13,
    })
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text for testing', 'rangeStart': 8, 'rangeEnd': 26,
    })
    assert response.status_code == 409


def test_save_highlight_allows_same_text_different_position(app_client, fixture_books_dir):
    app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 4,
    })
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 50, 'rangeEnd': 54,
    })
    assert response.status_code == 200
    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 2


def test_save_highlight_allows_overlapping_ranges_on_different_pages(app_client, fixture_books_dir):
    app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 10,
    })
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 2, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 10,
    })
    assert response.status_code == 200
    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 2


def test_save_highlight_filename_collision_disambiguated(app_client, fixture_books_dir):
    payload_a = {'page': 1, 'quote': 'repeat', 'rangeStart': 0, 'rangeEnd': 6}
    payload_b = {'page': 1, 'quote': 'repeat', 'rangeStart': 20, 'rangeEnd': 26}

    resp_a = app_client.post('/api/books/test-pdf-book/highlights', json=payload_a)
    resp_b = app_client.post('/api/books/test-pdf-book/highlights', json=payload_b)

    assert resp_a.get_json()['path'] != resp_b.get_json()['path']
    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_highlights_api.py -v`
Expected: FAIL — `404 NOT FOUND` for all requests, since the route doesn't exist yet.

- [ ] **Step 3: Implement the endpoint**

Update the import line at the top of `app.py` (from Task 8) to:

```python
from book_utils import (
    is_pdf_book, get_pdf_page_count, check_all_books, get_authors,
    build_citation, slugify_quote, resolve_highlight_filename,
    load_highlight_index, save_highlight_index, find_overlapping_entry,
)
```

Add this route in `app.py`, immediately before `def print_metadata_warnings():`:

```python
@app.route('/api/books/<book_id>/highlights', methods=['POST'])
def api_book_highlight(book_id):
    """API endpoint to save a text selection as a citation-formatted
    markdown highlight. Only supported for native-PDF books."""
    try:
        book_dir = BOOKS_DIR / book_id

        if not book_dir.exists():
            return jsonify({'success': False, 'error': 'Book not found'}), 404

        is_pdf, pdf_filename = is_pdf_book(book_dir)
        metadata_file = book_dir / 'metadata.json'
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        render_mode = metadata.get('render_mode', metadata.get('render-mode', 'images'))

        if not is_pdf or render_mode != 'native-pdf':
            return jsonify({
                'success': False,
                'error': 'Highlights are only supported for native-PDF books'
            }), 400

        data = request.get_json(silent=True) or {}
        quote = (data.get('quote') or '').strip()
        page = data.get('page')
        range_start = data.get('rangeStart')
        range_end = data.get('rangeEnd')

        if not quote:
            return jsonify({'success': False, 'error': 'quote is required'}), 400
        if not isinstance(page, int) or page < 1:
            return jsonify({'success': False, 'error': 'page must be a positive integer'}), 400
        if (not isinstance(range_start, int) or not isinstance(range_end, int)
                or range_end <= range_start):
            return jsonify({
                'success': False,
                'error': 'rangeStart/rangeEnd are required and must form a valid range'
            }), 400

        highlights_dir = book_dir / 'highlights'
        highlights_dir.mkdir(exist_ok=True)

        index = load_highlight_index(highlights_dir)
        conflict = find_overlapping_entry(index, page, range_start, range_end)
        if conflict:
            return jsonify({
                'success': False,
                'error': f"Overlaps an existing highlight ({conflict['file']})"
            }), 409

        citation = build_citation(metadata, pdf_filename, page)
        slug = slugify_quote(quote)
        filename = resolve_highlight_filename(highlights_dir, page, slug)

        content = f"> {quote}\n\n{citation}\n"
        with open(highlights_dir / filename, 'w', encoding='utf-8') as f:
            f.write(content)

        index.append({'file': filename, 'page': page, 'rangeStart': range_start, 'rangeEnd': range_end})
        save_highlight_index(highlights_dir, index)

        return jsonify({'success': True, 'path': f'highlights/{filename}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_highlights_api.py -v`
Expected: all PASS

- [ ] **Step 5: Run the full test suite so far**

Run: `pytest tests/unit tests/integration -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add app.py tests/integration/test_highlights_api.py
git commit -m "feat: add POST /api/books/<id>/highlights endpoint"
```

---

## Task 10: `add_book.py` multi-author prompt

**Files:**
- Modify: `add_book.py:152-158` (PDF path author prompt), `add_book.py:243` (image path author prompt)

**Interfaces:**
- Consumes: nothing new.
- Produces: `metadata['author']` is a list when more than one name is entered, a single string when only one is — matches the shape `get_authors()` (Task 3) already handles.

No automated test for this one — it's an interactive CLI prompt with no meaningful unit-testable surface beyond string splitting, which is simple enough to verify by reading the diff. (If you want to double check the splitting logic in isolation, `', '.join(name.strip() for name in 'A, B'.split(',') if name.strip())` behavior is exercised indirectly by Task 3's `get_authors()` tests already, since that's what consumes this data.)

- [ ] **Step 1: Update the PDF-book author prompt**

In `add_book.py`, replace:

```python
            default_author = pdf_metadata.get('author') or 'Unknown'
            author_prompt = f"Author [{default_author}]: "
            author = input(author_prompt).strip()
            if not author:
                author = default_author
```

with:

```python
            default_author = pdf_metadata.get('author') or 'Unknown'
            author_prompt = f"Author(s), comma-separated if multiple [{default_author}]: "
            author_input = input(author_prompt).strip()
            if not author_input:
                author_input = default_author
            author_names = [name.strip() for name in author_input.split(',') if name.strip()]
            author = author_names[0] if len(author_names) == 1 else author_names
```

- [ ] **Step 2: Update the image-book author prompt**

Replace:

```python
        author = input("Author (optional): ").strip()
```

with:

```python
        author_input = input("Author(s), comma-separated if multiple (optional): ").strip()
        author_names = [name.strip() for name in author_input.split(',') if name.strip()]
        author = author_names[0] if len(author_names) == 1 else (author_names or None)
```

And a few lines later, replace:

```python
        if author:
            metadata["author"] = author
```

with the same condition (it still works unchanged, since `author` is now either a non-empty string, a non-empty list, or `None`/falsy) — no edit needed there, just confirm it still reads `if author:`.

- [ ] **Step 3: Manually verify**

Run: `python add_book.py --verify` (should still run cleanly against your real `books/` folder — this task doesn't touch verification logic, just the interactive add prompts).

- [ ] **Step 4: Commit**

```bash
git add add_book.py
git commit -m "feat: accept comma-separated multi-author input in add_book.py"
```

---

## Task 11: Highlight status bar — markup, styles, and selection-range tracking

**Files:**
- Modify: `templates/reader.html` (add highlight bar markup, document the `H` shortcut)
- Modify: `static/css/reader.css` (append highlight bar styles)
- Modify: `static/js/reader.js` (capture page text content, compute selection ranges, show/hide the bar)

**Interfaces:**
- Consumes: `renderMode`, `currentPage`, `bookData` (existing module state in `reader.js`).
- Produces: module-level `activeSelection` (`{quote, rangeStart, rangeEnd} | null`) and `currentPageTextContent` (PDF.js `TextContent` for the page currently on screen), both consumed by Task 12's save handler. DOM elements `#highlightBar`, `#highlightPreview`, `#saveHighlightBtn`.

No unit test for this task — it's DOM/PDF.js wiring with no meaningful surface outside a real browser. Verified together with Task 12 in Task 14's end-to-end test, since a highlight can't be *saved* (and thus can't be asserted against) until the save handler exists. This task's own correctness (the bar appearing with the right preview text) is folded into that same e2e test rather than tested twice.

- [ ] **Step 1: Add the highlight bar markup to `templates/reader.html`**

Insert after the closing `</div>` of `<div id="reader" ...>` (i.e. right after the `.controls` div closes, before `<div class="shortcuts-help">`):

```html
    <div id="highlightBar" class="highlight-bar" style="display: none;">
        <span id="highlightPreview" class="highlight-preview"></span>
        <button id="saveHighlightBtn" class="highlight-save-btn">Save Highlight (H)</button>
    </div>
```

Also add a line to the existing shortcuts list (inside `<ul>` in `.shortcuts-help`), after the `0` reset-zoom entry:

```html
            <li><kbd>H</kbd> Save highlighted text</li>
```

- [ ] **Step 2: Add highlight bar styles to `static/css/reader.css`**

Append:

```css
/* Highlight status bar */
.highlight-bar {
    background-color: #2c2c2c;
    padding: 0.6rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    border-top: 1px solid #444;
}

.highlight-bar.error {
    background-color: #4a1f1f;
}

.highlight-preview {
    color: #ccc;
    font-size: 0.85rem;
    font-style: italic;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
}

.highlight-save-btn {
    padding: 0.4rem 0.9rem;
    background-color: #2ecc71;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85rem;
    white-space: nowrap;
}

.highlight-save-btn:hover {
    background-color: #27ae60;
}
```

- [ ] **Step 3: Capture page text content in `displayPdfPage()`**

In `static/js/reader.js`, add a new module-level variable near the top, alongside the other PDF.js state (after `let renderMode = 'images';`):

```javascript
let currentPageTextContent = null;
let activeSelection = null;
```

In `displayPdfPage()`, right after the line `const textContent = await page.getTextContent();`, add:

```javascript
            currentPageTextContent = textContent;
```

- [ ] **Step 4: Add selection-range computation helpers**

Append to `static/js/reader.js`:

```javascript
function getPageFullText() {
    if (!currentPageTextContent) return '';
    return currentPageTextContent.items
        .map(item => item.str + (item.hasEOL ? ' ' : ''))
        .join('');
}

function getSpanOffset(spans, targetSpan) {
    let offset = 0;
    for (let i = 0; i < spans.length; i++) {
        if (spans[i] === targetSpan) return offset;
        const item = currentPageTextContent.items[i];
        offset += item.str.length + (item.hasEOL ? 1 : 0);
    }
    return offset;
}

function findSpanForNode(node, textLayer) {
    let el = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    while (el && el.parentElement !== textLayer) {
        el = el.parentElement;
    }
    return el;
}

function getSelectionRange(textLayer) {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null;

    const range = selection.getRangeAt(0);
    if (!textLayer.contains(range.commonAncestorContainer)) return null;

    const spans = Array.from(textLayer.querySelectorAll('span'));
    const startSpan = findSpanForNode(range.startContainer, textLayer);
    const endSpan = findSpanForNode(range.endContainer, textLayer);
    if (!startSpan || !endSpan) return null;

    const startSpanOffset = getSpanOffset(spans, startSpan);
    const endSpanOffset = getSpanOffset(spans, endSpan);

    let rangeStart = startSpanOffset + range.startOffset;
    let rangeEnd = endSpanOffset + range.endOffset;

    if (rangeEnd < rangeStart) {
        [rangeStart, rangeEnd] = [rangeEnd, rangeStart];
    }

    const quote = selection.toString().replace(/\s+/g, ' ').trim();
    if (!quote || rangeEnd <= rangeStart) return null;

    return { quote, rangeStart, rangeEnd };
}
```

- [ ] **Step 5: Wire the `selectionchange` listener**

Inside the `document.addEventListener('DOMContentLoaded', () => { ... })` block in `static/js/reader.js`, add (after the existing `wheel` listener block, before the closing `});`):

```javascript
    document.addEventListener('selectionchange', () => {
        if (renderMode !== 'native-pdf') return;
        const textLayer = document.getElementById('textLayer');
        const highlightBar = document.getElementById('highlightBar');
        if (!textLayer || !highlightBar) return;

        activeSelection = getSelectionRange(textLayer);

        if (activeSelection) {
            document.getElementById('highlightPreview').textContent = activeSelection.quote;
            highlightBar.classList.remove('error');
            highlightBar.style.display = 'flex';
        } else {
            highlightBar.style.display = 'none';
        }
    });
```

- [ ] **Step 6: Clear stale selections on page change**

In `displayPage()`, right after the `currentPage = pageNum;` line, add:

```javascript
    activeSelection = null;
    const highlightBar = document.getElementById('highlightBar');
    if (highlightBar) highlightBar.style.display = 'none';
```

- [ ] **Step 7: Commit**

```bash
git add templates/reader.html static/css/reader.css static/js/reader.js
git commit -m "feat: add highlight status bar and text-selection range tracking"
```

---

## Task 12: Wire the save handler (button + `H` shortcut)

**Files:**
- Modify: `static/js/reader.js`

**Interfaces:**
- Consumes: `activeSelection`, `bookData`, `currentPage` (existing/Task 11 state); `POST /api/books/<id>/highlights` (Task 9).
- Produces: `saveHighlight()`, called from a click listener and from `handleKeyboard()`.

- [ ] **Step 1: Implement `saveHighlight()`**

Append to `static/js/reader.js`:

```javascript
async function saveHighlight() {
    if (!activeSelection || !bookData) return;

    const highlightBar = document.getElementById('highlightBar');
    const preview = document.getElementById('highlightPreview');

    try {
        const response = await fetch(`/api/books/${bookData.id}/highlights`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                page: currentPage + 1,
                quote: activeSelection.quote,
                rangeStart: activeSelection.rangeStart,
                rangeEnd: activeSelection.rangeEnd
            })
        });
        const data = await response.json();

        if (data.success) {
            preview.textContent = `Saved to ${data.path}`;
            highlightBar.classList.remove('error');
            window.getSelection().removeAllRanges();
            activeSelection = null;
            setTimeout(() => { highlightBar.style.display = 'none'; }, 3000);
        } else {
            preview.textContent = data.error || 'Failed to save highlight';
            highlightBar.classList.add('error');
        }
    } catch (error) {
        preview.textContent = 'Failed to save highlight';
        highlightBar.classList.add('error');
    }
}
```

- [ ] **Step 2: Wire the button click**

In the `document.addEventListener('DOMContentLoaded', ...)` block, alongside the other `addEventListener('click', ...)` calls (e.g. right after `document.getElementById('resetZoomBtn').addEventListener('click', resetZoom);`), add:

```javascript
    document.getElementById('saveHighlightBtn').addEventListener('click', saveHighlight);
```

- [ ] **Step 3: Wire the `H` keyboard shortcut**

In `handleKeyboard()`, add this check near the top of the function, right after the "Ignore if typing in input field" guard and before the `pageDisplay`/`panAmount` declarations:

```javascript
    if ((e.key === 'h' || e.key === 'H') && activeSelection) {
        saveHighlight();
        e.preventDefault();
        return;
    }
```

- [ ] **Step 4: Commit**

```bash
git add static/js/reader.js
git commit -m "feat: wire highlight save button and H keyboard shortcut"
```

---

## Task 13: End-to-end test infrastructure (`live_server` fixture)

**Files:**
- Modify: `conftest.py` (append `live_server` fixture)

**Interfaces:**
- Consumes: `fixture_books_dir` (Task 1), `LIBRO_BOOKS_DIR`/`LIBRO_PORT`/`LIBRO_DEBUG` env vars (Task 7).
- Produces: `live_server(fixture_books_dir) -> str` (base URL of a running, isolated `python app.py` process), consumed by Tasks 14 and 15. The `page`/`browser`/`context` fixtures come from the `pytest-playwright` plugin automatically (installed in Task 1) — no need to define them.

- [ ] **Step 1: Append the fixture to `conftest.py`**

Add these imports at the top of `conftest.py` (alongside the existing `import pytest`):

```python
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
```

Append the fixture:

```python
@pytest.fixture
def live_server(fixture_books_dir):
    """Launches a real `python app.py` subprocess pointed at fixture_books_dir
    on a free local port, for tests that need actual PDF.js rendering in a
    real browser. Never touches the user's real books/ folder."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    env = os.environ.copy()
    env['LIBRO_BOOKS_DIR'] = str(fixture_books_dir)
    env['LIBRO_PORT'] = str(port)
    env['LIBRO_DEBUG'] = '0'

    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / 'app.py')],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    base_url = f'http://127.0.0.1:{port}'
    deadline = time.time() + 15
    started = False
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                started = True
                break
        except OSError:
            time.sleep(0.2)

    if not started:
        proc.terminate()
        raise RuntimeError('Server did not start in time')

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
```

- [ ] **Step 2: Write a smoke test for the fixture**

Create `tests/e2e/test_reader_e2e.py`:

```python
import pytest

pytestmark = pytest.mark.e2e


def test_live_server_serves_library_page(live_server, page):
    page.goto(live_server)
    page.wait_for_selector('text=Libro Browse')
```

- [ ] **Step 3: Run the smoke test**

Run: `pytest tests/e2e/test_reader_e2e.py -v`
Expected: PASS (confirms the subprocess launches, serves fixture books, and Playwright can drive it).

- [ ] **Step 4: Commit**

```bash
git add conftest.py tests/e2e/test_reader_e2e.py
git commit -m "test: add live_server fixture for end-to-end browser tests"
```

---

## Task 14: End-to-end regression tests

Acceptance/regression tests for the two bugs found and fixed earlier this session — written now (not test-first) since they characterize already-shipped behavior; see Global Constraints for why e2e tasks skip the fail-first step.

**Files:**
- Modify: `tests/e2e/test_reader_e2e.py` (append)

**Interfaces:**
- Consumes: `live_server`, `page` (Playwright fixtures), `fixture_books_dir`.

- [ ] **Step 1: Write the regression tests**

Append to `tests/e2e/test_reader_e2e.py`:

```python
import json
import time


def test_next_page_before_load_does_not_throw(live_server, page):
    """Regression test: nextPage()/goToPage()/End used to throw
    "Cannot read properties of null (reading 'pageCount')" if fired
    before bookData finished loading. Delay the book-data fetch to
    reliably hit that window."""
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))

    def delay_route(route):
        time.sleep(2)
        route.continue_()

    page.route('**/api/books/test-pdf-book', delay_route)
    page.goto(f'{live_server}/reader/test-pdf-book')

    page.keyboard.press('ArrowRight')
    page.keyboard.press('End')
    page.wait_for_timeout(500)

    assert errors == []

    page.unroute('**/api/books/test-pdf-book', delay_route)
    page.wait_for_function(
        "document.getElementById('bookTitle').textContent !== 'Loading...'",
        timeout=10000
    )


def test_page_count_reflects_actual_pdf_not_stale_metadata(live_server, page, fixture_books_dir):
    """Regression test: page count must come from the real PDF (2 pages),
    not a stale metadata.json value."""
    metadata_path = fixture_books_dir / 'test-pdf-book' / 'metadata.json'
    metadata = json.loads(metadata_path.read_text())
    metadata['page_count'] = 999
    metadata_path.write_text(json.dumps(metadata))

    page.goto(f'{live_server}/reader/test-pdf-book')
    page.wait_for_function(
        "document.getElementById('bookTitle').textContent !== 'Loading...'",
        timeout=10000
    )
    total_pages = page.eval_on_selector('#totalPages', 'el => el.textContent')
    assert total_pages == '2'
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/e2e/test_reader_e2e.py -k "next_page_before_load or page_count_reflects" -v`
Expected: both PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_reader_e2e.py
git commit -m "test: add e2e regression tests for null-guard and page-count fixes"
```

---

## Task 15: End-to-end highlight flow tests

**Files:**
- Modify: `tests/e2e/test_reader_e2e.py` (append)

**Interfaces:**
- Consumes: `live_server`, `page`, `fixture_books_dir`.

- [ ] **Step 1: Write the tests**

Append to `tests/e2e/test_reader_e2e.py`:

```python
SELECT_FIRST_SPAN_JS = """
() => {
    const span = document.querySelector('#textLayer span');
    const range = document.createRange();
    range.selectNodeContents(span);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    document.dispatchEvent(new Event('selectionchange'));
}
"""


def test_save_highlight_via_button(live_server, page, fixture_books_dir):
    page.goto(f'{live_server}/reader/test-pdf-book')
    page.wait_for_selector('#textLayer span')

    page.evaluate(SELECT_FIRST_SPAN_JS)
    page.wait_for_selector('#highlightBar[style*="flex"]', timeout=5000)
    page.click('#saveHighlightBtn')

    page.wait_for_function(
        "document.getElementById('highlightPreview').textContent.includes('Saved to')",
        timeout=5000
    )

    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    saved_files = list(highlights_dir.glob('*.md'))
    assert len(saved_files) == 1
    content = saved_files[0].read_text()
    assert content.startswith('> ')
    assert 'Test Author' in content
    assert 'p. 1.' in content


def test_keyboard_shortcut_saves_highlight(live_server, page, fixture_books_dir):
    page.goto(f'{live_server}/reader/test-pdf-book')
    page.wait_for_selector('#textLayer span')

    page.evaluate(SELECT_FIRST_SPAN_JS)
    page.wait_for_selector('#highlightBar[style*="flex"]', timeout=5000)
    page.keyboard.press('h')

    page.wait_for_function(
        "document.getElementById('highlightPreview').textContent.includes('Saved to')",
        timeout=5000
    )

    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 1


def test_image_book_has_no_highlight_affordance(live_server, page):
    page.goto(f'{live_server}/reader/test-image-book')
    page.wait_for_function(
        "document.getElementById('bookTitle').textContent !== 'Loading...'",
        timeout=10000
    )
    highlight_bar = page.query_selector('#highlightBar')
    is_visible = highlight_bar is not None and page.evaluate(
        "el => window.getComputedStyle(el).display !== 'none'", highlight_bar
    )
    assert not is_visible


def test_overlapping_highlight_rejected_in_ui(live_server, page, fixture_books_dir):
    page.goto(f'{live_server}/reader/test-pdf-book')
    page.wait_for_selector('#textLayer span')

    page.evaluate(SELECT_FIRST_SPAN_JS)
    page.wait_for_selector('#highlightBar[style*="flex"]', timeout=5000)
    page.click('#saveHighlightBtn')
    page.wait_for_function(
        "document.getElementById('highlightPreview').textContent.includes('Saved to')",
        timeout=5000
    )

    page.evaluate(SELECT_FIRST_SPAN_JS)
    page.wait_for_selector('#highlightBar[style*="flex"]', timeout=5000)
    page.click('#saveHighlightBtn')
    page.wait_for_selector('#highlightBar.error', timeout=5000)

    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 1
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/e2e/test_reader_e2e.py -v`
Expected: all PASS.

- [ ] **Step 3: Run the entire test suite**

Run: `pytest -v`
Expected: all PASS (unit + integration + e2e).

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_reader_e2e.py
git commit -m "test: add e2e coverage for the highlight save flow"
```

---

## Manual verification (after all tasks)

Automated tests cover the logic; this confirms it feels right in the real app against your real library:

1. `python app.py`, open a real native-PDF book (e.g. `libro3`).
2. Drag-select a sentence — confirm the status bar shows a preview and a "Save Highlight (H)" button.
3. Click it — confirm the bar shows "Saved to highlights/..." and check that file's content and citation.
4. Select different text, press `H` — confirm it saves too.
5. Re-select the exact same text and try to save again — confirm it's rejected with an inline error.
6. Open an image-scanned book (e.g. `libro2`) — confirm no highlight bar ever appears.
7. `python add_book.py --verify` — confirm it still runs cleanly against your real library.
