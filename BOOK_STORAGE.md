# Book Storage Structure

## How to organize your books

Place your scanned books in the `books/` directory. Each book should be in its own folder with the following structure:

```
books/
├── my-first-book/
│   ├── metadata.json
│   ├── 001.jpg
│   ├── 002.jpg
│   ├── 003.jpg
│   └── ...
├── another-book/
│   ├── metadata.json
│   ├── page001.png
│   ├── page002.png
│   └── ...
```

## Metadata file format

Each book folder should contain a `metadata.json` file with the following structure:

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
- `title`: The book's title
- `cover`: The filename of the cover image (usually the first page)

**Optional fields:**
- `author`: Book author
- `year`: Publication year
- `description`: Book description
- `tags`: Array of tags for categorization

## Image files

- Supported formats: JPG, JPEG, PNG
- Name files in alphabetical/numerical order (they will be displayed in sorted order)
- Recommended naming: `001.jpg`, `002.jpg`, etc. or `page001.jpg`, `page002.jpg`, etc.
