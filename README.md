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
- `author`: Author name
- `year`: Publication year
- `description`: Book description
- `tags`: Array of tags for categorization and searching

## Reader Keyboard Shortcuts

- `←` / `→` - Previous/Next page
- `Space` / `PageUp` / `PageDown` - Navigate pages
- `Home` / `End` - Jump to first/last page
- `+` / `-` - Zoom in/out
- `0` - Reset zoom

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
