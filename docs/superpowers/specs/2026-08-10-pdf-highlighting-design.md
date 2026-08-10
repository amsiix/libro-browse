# PDF Highlighting — Design

## Purpose

Let the reader select text in a native-PDF book and save it as a
citation-formatted markdown file, so quotes captured while reading can be
reused elsewhere (notes, writing, research) without retyping the citation
by hand.

Reading-position persistence is already implemented (browser-only
localStorage, resumes at the last page on reopen) and is considered
sufficient — no changes are in scope here.

## Scope

- **In scope**: highlighting for native-PDF books only (`renderMode ===
  'native-pdf'`), which already have a real, selectable PDF.js text layer.
- **Out of scope, deliberately**:
  - Image-scanned books (`libro1`, `libro2`, `libro5`'s raw page images)
    have no extractable text, so highlighting isn't available for them in
    this iteration. A follow-up idea — OCR'ing image-page books into
    searchable PDFs via `ocrmypdf` — was discussed and explicitly deferred
    to a later spec. Once a book is OCR'd into a native-PDF, it picks up
    highlighting for free through this same code path.
  - An in-app "browse my highlights" view. Saved highlights are just
    markdown files on disk — read/manage them however you like. Revisit if
    that ever becomes a real need (YAGNI).

## User flow

1. User drag-selects text inside the PDF's text layer in the reader.
2. A status-bar region at the bottom of the reader (same visual slot/style
   as the existing `Cache: -` indicator) shows a truncated preview of the
   selection and a **"Save Highlight (H)"** button.
3. User clicks the button, or presses **H** while a selection is active.
4. The client reads `window.getSelection().toString()` (trimmed,
   whitespace-collapsed) and POSTs `{ page, quote }` to
   `/api/books/<book_id>/highlights`, where `page` is the 1-indexed page
   number currently displayed.
5. The server builds the citation from `metadata.json`, generates a
   filename, writes the markdown file, and returns its path.
6. The status bar flashes a confirmation (e.g. "Saved to
   highlights/42-doubt-is-not-a-pleasant.md") for a few seconds, then
   reverts to neutral. On failure, it shows an inline error instead.

Selecting text in an image-mode book shows no highlight affordance at
all — the status bar stays in its normal (non-highlight) state.

## Citation format

```
<author> (<year>). _<title>_. <pdf filename>. p. <page>.
```

Example:

```
B. V. GNEDENKO (1978). _The Theory of Probability_. Gnedenko-Theory of Probability.pdf. p. 42.
```

- `author`, `year`, `title` come straight from `metadata.json`, with the
  same fallbacks `app.py` already uses elsewhere (e.g. `author` defaults
  to `"Unknown"`). No new required metadata fields — this only reads
  fields that already exist for every PDF book.
- `<pdf filename>` is the PDF's actual filename (`pdf_file` in
  `metadata.json`, already required for every PDF book) — used in place
  of "Place: Publisher", which isn't tracked anywhere in this app and
  isn't worth adding just for this.
- Multi-author books: `author` stays a single string field as it is
  today; if a book has multiple authors, the string is just formatted
  however the user likes when editing `metadata.json` (e.g. `"Härdle, W.
  and Simar, L."`). No schema change.

## Saved file format

One file per highlight: a markdown blockquote of the selected text, a
blank line, then the citation.

```markdown
> Doubt is not a pleasant condition, but certainty is absurd.

GNEDENKO, B. V. (1978). _The Theory of Probability_. Gnedenko-Theory of Probability.pdf. p. 42.
```

## File location & naming

```
books/<book_id>/highlights/<page>-<slug>.md
```

- `<slug>` is generated from the first few words of the quote:
  lowercased, punctuation stripped, words joined with hyphens, truncated
  to a reasonable length (~50 chars).
- If the resulting filename already exists (e.g. two highlights that slug
  to the same text on the same page), a numeric suffix is appended
  (`-2`, `-3`, ...) — never overwrites an existing highlight.
- Nested inside the book's own folder in `books/`, alongside its PDF and
  `metadata.json`, consistent with everything else being organized
  per-book. `books/` stays gitignored and personal, same as today.

## Backend changes

### New endpoint: `POST /api/books/<book_id>/highlights`

Request body: `{ "page": <int>, "quote": <string> }` (page is 1-indexed,
matching what the reader UI displays).

Behavior:
1. 404 if the book doesn't exist or isn't a native-PDF book.
2. 400 if `quote` is empty/whitespace-only after trimming.
3. Load `metadata.json`, build the citation string.
4. Slugify the quote, resolve any filename collision.
5. Ensure `books/<book_id>/highlights/` exists, write the `.md` file.
6. Return `{ success: true, path: "highlights/<page>-<slug>.md" }` (or a
   4xx/5xx JSON error).

### `LIBRO_BOOKS_DIR` environment variable

`app.py`'s `BOOKS_DIR` becomes overridable via an environment variable
(defaulting to today's hardcoded `books/` path when unset). This is a
one-line change whose only purpose is letting end-to-end tests point a
real running server at disposable fixture books, without ever touching
the user's real library. No other behavior changes.

## Frontend changes (`reader.js`, `reader.html`, `reader.css`)

- Add a highlight-status element to the bottom bar, styled/positioned
  like the existing cache-status indicator.
- Listen for `selectionchange` (or `mouseup`) scoped to `#textLayer`;
  update the status element based on whether there's a live, non-empty
  selection inside it.
- Wire the "Save Highlight" button and the `H` keydown handler (only
  active when a selection exists, so it doesn't collide with typing
  elsewhere) to POST to the new endpoint and update the status element
  with the result.
- Gate all of the above on `renderMode === 'native-pdf'` — image-mode
  books never show or wire up the highlight status element.

## Error handling

- Empty/whitespace-only selection → status bar never shows the Save
  button.
- Selection outside `#textLayer` (e.g. UI chrome) → ignored.
- Server can't write the file (disk error, etc.) → JSON error response;
  status bar shows an inline error instead of failing silently.
- Filename collisions → auto-disambiguated, never overwritten.

## Testing

No test suite exists in this repo today. This adds one, structured as a
pyramid, entirely in Python (`pytest` + Microsoft's official
`pytest-playwright`) — this repo has zero Node tooling, so staying in one
language/one test runner instead of bolting on a second ecosystem.

```
tests/
  conftest.py                 # shared fixtures (see below)
  fixtures/
    build_books.py            # helpers that generate tiny synthetic books
  unit/
    test_book_utils.py        # is_pdf_book, get_pdf_page_count,
                               # compute_pdf_fingerprint, check_book,
                               # check_all_books
  integration/
    test_api_books.py         # existing routes via Flask test_client()
    test_highlights_api.py    # new highlights endpoint: citation format,
                               # slug/collision handling, missing-field
                               # fallbacks, 400/404s
  e2e/
    test_reader_e2e.py        # pytest-playwright against a real running
                               # server pointed at fixture books
```

- **Unit tests**: `book_utils.py`'s pure logic. Fast, no server.
- **Integration tests**: Flask's `test_client()` against real routes,
  including the new highlights endpoint. `BOOKS_DIR` is pointed at a
  disposable `tmp_path` fixture via `pytest`'s `monkeypatch` — no app
  refactor needed, since `BOOKS_DIR` is a plain module global resolved
  fresh on every function call, so monkeypatching the module attribute
  before a request is enough.
- **E2E tests**: `pytest-playwright` drives a real headless browser
  against a real `python app.py` process, launched with
  `LIBRO_BOOKS_DIR` pointed at fixture books — the only layer that can
  exercise actual PDF.js rendering, text selection, and keyboard
  shortcuts.
- **Fixture books**, generated at test time (nothing depends on the
  user's real `books/` folder, which stays gitignored):
  - A small multi-page PDF with real selectable text, built with
    `reportlab` (new test-only dependency) — used for the PDF/highlight
    path.
  - A couple of tiny generated images (via Pillow, already a project
    dependency) — used for the image-book path.
  - A "broken" fixture book (declared `page_count` deliberately wrong)
    — used to test `check_book`/`check_all_books` catching drift.
- **Named regression tests** for bugs already found and fixed this
  session, so they can't silently reappear:
  - `nextPage()`/`goToPage()`/the `End` key firing before `bookData` has
    loaded must not throw (the null-guard fix).
  - A PDF book's page count shown to the user must come from the actual
    PDF file, not a stale `metadata.json` value (the book-`10`
    mismatch).

### Dependencies

- `reportlab` — added to a new `requirements-dev.txt`, test-only.
- `pytest`, `pytest-playwright` — same, `requirements-dev.txt`.
- Playwright's browser binaries installed separately (`playwright install
  chromium`), documented alongside the test instructions, not part of
  the app's runtime requirements.

## Non-goals (this iteration)

- OCR'ing image-scanned books into searchable PDFs (explicitly deferred
  as a follow-up spec).
- An in-app view for browsing/managing saved highlights.
- New required metadata fields (place published, publisher) — dropped in
  favor of reusing the PDF filename, which already exists for every PDF
  book.
- CI/GitHub Actions wiring for the new test suite — out of scope unless
  requested separately.
