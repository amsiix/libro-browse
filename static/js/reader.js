// Book reader functionality

let bookData = null;
let currentPage = 0;
let zoomLevel = 1.0;

document.addEventListener('DOMContentLoaded', () => {
    const bookId = document.getElementById('reader').dataset.bookId;
    loadBook(bookId);

    // Set up controls
    document.getElementById('prevBtn').addEventListener('click', prevPage);
    document.getElementById('nextBtn').addEventListener('click', nextPage);
    document.getElementById('pageInput').addEventListener('change', goToPage);
    document.getElementById('zoomInBtn').addEventListener('click', zoomIn);
    document.getElementById('zoomOutBtn').addEventListener('click', zoomOut);
    document.getElementById('resetZoomBtn').addEventListener('click', resetZoom);

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);
});

async function loadBook(bookId) {
    const pageDisplay = document.getElementById('pageDisplay');
    pageDisplay.innerHTML = '<div class="loading">Loading book...</div>';

    try {
        const response = await fetch(`/api/books/${bookId}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load book');
        }

        bookData = data.book;

        // Update title
        document.getElementById('bookTitle').textContent = bookData.title;
        document.getElementById('totalPages').textContent = bookData.pageCount;

        // Restore the page image element
        pageDisplay.innerHTML = '<img id="pageImage" class="page-image" alt="Book page">';

        // Load first page
        displayPage(0);
    } catch (error) {
        pageDisplay.innerHTML = `
            <div class="error">
                Error loading book: ${error.message}
            </div>
        `;
    }
}

function displayPage(pageNum) {
    if (!bookData || pageNum < 0 || pageNum >= bookData.pageCount) {
        return;
    }

    currentPage = pageNum;

    const pageUrl = `/api/books/${bookData.id}/page/${pageNum}`;
    const pageImg = document.getElementById('pageImage');

    pageImg.src = pageUrl;
    pageImg.style.transform = `scale(${zoomLevel})`;

    // Update controls
    document.getElementById('pageInput').value = pageNum + 1;
    document.getElementById('prevBtn').disabled = pageNum === 0;
    document.getElementById('nextBtn').disabled = pageNum === bookData.pageCount - 1;
}

function nextPage() {
    if (currentPage < bookData.pageCount - 1) {
        displayPage(currentPage + 1);
    }
}

function prevPage() {
    if (currentPage > 0) {
        displayPage(currentPage - 1);
    }
}

function goToPage() {
    const input = document.getElementById('pageInput');
    const pageNum = parseInt(input.value) - 1;

    if (!isNaN(pageNum) && pageNum >= 0 && pageNum < bookData.pageCount) {
        displayPage(pageNum);
    } else {
        // Reset to current page if invalid
        input.value = currentPage + 1;
    }
}

function zoomIn() {
    zoomLevel = Math.min(zoomLevel + 0.25, 3.0);
    updateZoom();
}

function zoomOut() {
    zoomLevel = Math.max(zoomLevel - 0.25, 0.5);
    updateZoom();
}

function resetZoom() {
    zoomLevel = 1.0;
    updateZoom();
}

function updateZoom() {
    const pageImg = document.getElementById('pageImage');
    pageImg.style.transform = `scale(${zoomLevel})`;
    document.getElementById('zoomLevel').textContent = `${Math.round(zoomLevel * 100)}%`;
}

function handleKeyboard(e) {
    // Ignore if typing in input field
    if (e.target.tagName === 'INPUT') {
        return;
    }

    switch(e.key) {
        case 'ArrowLeft':
        case 'PageUp':
            prevPage();
            e.preventDefault();
            break;
        case 'ArrowRight':
        case 'PageDown':
        case ' ':
            nextPage();
            e.preventDefault();
            break;
        case 'Home':
            displayPage(0);
            e.preventDefault();
            break;
        case 'End':
            displayPage(bookData.pageCount - 1);
            e.preventDefault();
            break;
        case '+':
        case '=':
            zoomIn();
            e.preventDefault();
            break;
        case '-':
        case '_':
            zoomOut();
            e.preventDefault();
            break;
        case '0':
            resetZoom();
            e.preventDefault();
            break;
    }
}
