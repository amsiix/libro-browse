# Libro Browse

A local web application for browsing and reading your scanned books. Built with Flask and vanilla JavaScript, completely offline-capable.

## Features

- 📚 Browse your local book collection with cover thumbnails
- 🔍 Search books by title, author, description, or tags
- 📖 Read books with a clean, keyboard-navigable reader
- 🔎 Zoom in/out on pages
- ⌨️ Full keyboard shortcuts support
- 🏷️ Organize books with metadata and tags
- 💾 100% local - no internet required after setup

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Organize Your Books

Place your scanned books in the `books/` directory. Each book should be in its own folder containing:

- Image files (JPG, PNG) for each page
- A `metadata.json` file (optional but recommended)

Example structure:
```
books/
├── my-first-book/
│   ├── metadata.json
│   ├── 001.jpg
│   ├── 002.jpg
│   └── 003.jpg
└── another-book/
    ├── metadata.json
    └── page001.png
```

See `BOOK_STORAGE.md` for detailed instructions on organizing your books.

### 3. Run the Application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

## Creating Book Metadata

Each book folder can include a `metadata.json` file:

```json
{
  "title": "My Book Title",
  "author": "Author Name",
  "year": "2024",
  "description": "A brief description of the book",
  "cover": "001.jpg",
  "tags": ["fiction", "adventure"]
}
```

**Required fields:**
- `title`: Book title (defaults to folder name if not provided)
- `cover`: Cover image filename (defaults to first image if not provided)

**Optional fields:**
- `author`: Author name. Either a single string (`"Author Name"`) or, for
  books with multiple authors, a list of `"First Last"` strings (e.g.
  `["Wolfgang Karl Härdle", "Léopold Simar"]`) -- both forms are accepted
  everywhere `author` is read, including highlight citations.
- `year`: Publication year
- `description`: Book description
- `tags`: Array of tags for categorization and searching

## Reader Keyboard Shortcuts

- `←` / `→` - Previous/Next page
- `Space` / `PageUp` / `PageDown` - Navigate pages
- `Home` / `End` - Jump to first/last page
- `+` / `-` - Zoom in/out
- `0` - Reset zoom
- `H` - Save the current text selection as a highlight (native-PDF books only)

## Highlighting Text (native-PDF books)

Books rendered in native-PDF mode (`render_mode: "native-pdf"` in
`metadata.json`) support saving text selections as citation-formatted
highlights:

1. Drag-select a passage of text in the reader.
2. A status bar appears at the bottom of the screen showing a preview of
   the selection and a **Save Highlight (H)** button. Click the button,
   or press `H`, to save it.
3. The bar confirms with the saved file's path, or shows an inline error
   if the selection overlaps a highlight you've already saved on that
   page.

Each highlight is written as its own markdown file at
`books/<book_id>/highlights/<page>-<slug>.md`, containing a blockquote of
the selected text followed by a citation built from the book's
`metadata.json` (author(s), year, title, PDF filename, and page number).
A per-book `books/<book_id>/highlights/.index.json` tracks the character
range of every saved highlight so overlapping/duplicate selections on the
same page are rejected rather than silently creating redundant files.

Highlighting is only available for native-PDF books -- image-scanned
books have no extractable text layer to select from, so the highlight
status bar never appears for them.

## Running the tests

```bash
pip install -r requirements-dev.txt
playwright install chromium
pytest
```

This runs the full pytest suite (unit, integration, and end-to-end
browser tests via Playwright). All fixture books used by the tests are
synthetic and generated under a temporary directory -- nothing touches
your real `books/` folder.

## Technologies Used

- **Backend**: Python Flask
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Design**: Clean, responsive interface inspired by modern book readers

## License

MIT License - feel free to use and modify for your personal use.

## Tips

- Name your page images with leading zeros (001.jpg, 002.jpg) for proper sorting
- Use high-quality scans for the best reading experience
- The cover image can be any page - just specify it in metadata.json
- Use tags to organize books by genre, topic, or any other category
- The search function searches across all metadata fields
