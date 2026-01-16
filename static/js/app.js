// Main app for browsing books

let allBooks = [];

// Load all books on page load
document.addEventListener('DOMContentLoaded', () => {
    loadBooks();

    // Set up search
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
});

async function loadBooks(query = '') {
    const booksGrid = document.getElementById('booksGrid');
    const statsEl = document.getElementById('stats');

    // Show loading
    booksGrid.innerHTML = '<div class="loading">Loading books...</div>';

    try {
        const url = query ? `/api/books?q=${encodeURIComponent(query)}` : '/api/books';
        const response = await fetch(url);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load books');
        }

        allBooks = data.books;

        // Update stats
        statsEl.textContent = `Showing ${data.count} book${data.count !== 1 ? 's' : ''}`;

        // Display books
        if (data.books.length === 0) {
            booksGrid.innerHTML = `
                <div class="empty-state">
                    <h2>No books found</h2>
                    ${query ? '<p>Try a different search term</p>' : ''}
                    <p>Add your scanned books to the <code>books/</code> directory</p>
                    <p>See <code>BOOK_STORAGE.md</code> for instructions</p>
                </div>
            `;
        } else {
            booksGrid.innerHTML = '';
            data.books.forEach(book => {
                const bookCard = createBookCard(book);
                booksGrid.appendChild(bookCard);
            });
        }
    } catch (error) {
        booksGrid.innerHTML = `
            <div class="error">
                Error loading books: ${error.message}
            </div>
        `;
    }
}

function createBookCard(book) {
    const card = document.createElement('div');
    card.className = 'book-card';
    card.onclick = () => openBook(book.id);

    const coverUrl = `/api/books/${book.id}/cover`;

    let tagsHTML = '';
    if (book.tags && book.tags.length > 0) {
        tagsHTML = `
            <div class="book-tags">
                ${book.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
        `;
    }

    card.innerHTML = `
        <img src="${coverUrl}" alt="${book.title}" class="book-cover" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22280%22><rect width=%22200%22 height=%22280%22 fill=%22%23bdc3c7%22/><text x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22 fill=%22%23fff%22 font-size=%2216%22>No Cover</text></svg>'">
        <div class="book-info">
            <div class="book-title">${book.title}</div>
            <div class="book-author">${book.author}</div>
            ${book.year ? `<div class="book-year">${book.year}</div>` : ''}
            <div class="book-pages">${book.pageCount} pages</div>
            ${tagsHTML}
        </div>
    `;

    return card;
}

function openBook(bookId) {
    window.location.href = `/reader/${bookId}`;
}

function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const query = searchInput.value.trim();
    loadBooks(query);
}
