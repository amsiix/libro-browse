// Book reader functionality

let bookData = null;
let currentPage = 0;
let zoomLevel = 1.0;

// Panning state
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let scrollStartX = 0;
let scrollStartY = 0;

// Scroll navigation debounce
let lastScrollPageChange = 0;
const scrollDebounceMs = 250;

// Base image dimensions (fitted size at 100% zoom)
let baseImageWidth = 0;
let baseImageHeight = 0;

// Reading position persistence
function saveReadingPosition(bookId, pageNum) {
    localStorage.setItem(`libro-browse-page-${bookId}`, pageNum);
}

function getReadingPosition(bookId) {
    const saved = localStorage.getItem(`libro-browse-page-${bookId}`);
    return saved !== null ? parseInt(saved, 10) : null;
}

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

    // Drag to pan when zoomed
    const pageDisplay = document.getElementById('pageDisplay');

    pageDisplay.addEventListener('mousedown', (e) => {
        if (zoomLevel > 1.0) {
            isDragging = true;
            dragStartX = e.clientX;
            dragStartY = e.clientY;
            scrollStartX = pageDisplay.scrollLeft;
            scrollStartY = pageDisplay.scrollTop;
            pageDisplay.classList.add('dragging');
            e.preventDefault();
        }
    });

    pageDisplay.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const deltaX = e.clientX - dragStartX;
        const deltaY = e.clientY - dragStartY;
        pageDisplay.scrollLeft = scrollStartX - deltaX;
        pageDisplay.scrollTop = scrollStartY - deltaY;
    });

    pageDisplay.addEventListener('mouseup', () => {
        isDragging = false;
        pageDisplay.classList.remove('dragging');
    });

    pageDisplay.addEventListener('mouseleave', () => {
        isDragging = false;
        pageDisplay.classList.remove('dragging');
    });

    // Mouse wheel navigation at normal zoom
    pageDisplay.addEventListener('wheel', (e) => {
        // When zoomed, let browser handle scrolling within the page
        if (zoomLevel > 1.0) {
            return;
        }

        // At normal zoom, change pages with debounce
        e.preventDefault();
        const now = Date.now();
        if (now - lastScrollPageChange < scrollDebounceMs) {
            return;
        }

        if (e.deltaY > 0) {
            nextPage();
        } else if (e.deltaY < 0) {
            prevPage();
        }
        lastScrollPageChange = now;
    }, { passive: false });
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

        // Load saved page or first page
        const savedPage = getReadingPosition(bookId);
        const startPage = (savedPage !== null && savedPage >= 0 && savedPage < bookData.pageCount) ? savedPage : 0;
        displayPage(startPage);
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
    saveReadingPosition(bookData.id, pageNum);

    const pageUrl = `/api/books/${bookData.id}/page/${pageNum}`;
    const pageImg = document.getElementById('pageImage');
    const pageDisplay = document.getElementById('pageDisplay');

    // Reset to base state before loading new image
    pageImg.style.width = '';
    pageImg.style.height = '';
    pageImg.style.transform = '';

    pageImg.onload = () => {
        // Capture the fitted dimensions as base size
        baseImageWidth = pageImg.offsetWidth;
        baseImageHeight = pageImg.offsetHeight;
        // Apply current zoom level
        applyZoom();
    };

    pageImg.src = pageUrl;

    // Reset scroll position when changing pages
    pageDisplay.scrollLeft = 0;
    pageDisplay.scrollTop = 0;

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

function applyZoom() {
    const pageImg = document.getElementById('pageImage');
    const pageDisplay = document.getElementById('pageDisplay');

    if (baseImageWidth === 0 || baseImageHeight === 0) {
        return; // Image not loaded yet
    }

    if (zoomLevel === 1.0) {
        // At 100%, use CSS constraints (clear explicit dimensions)
        pageImg.style.width = '';
        pageImg.style.height = '';
        pageDisplay.classList.remove('zoomed');
        pageDisplay.scrollLeft = 0;
        pageDisplay.scrollTop = 0;
    } else {
        // At other zoom levels, set explicit pixel dimensions
        pageImg.style.width = (baseImageWidth * zoomLevel) + 'px';
        pageImg.style.height = (baseImageHeight * zoomLevel) + 'px';
        pageDisplay.classList.add('zoomed');
        // Center scroll position after zoom change
        requestAnimationFrame(() => {
            const scrollMaxX = pageDisplay.scrollWidth - pageDisplay.clientWidth;
            const scrollMaxY = pageDisplay.scrollHeight - pageDisplay.clientHeight;
            pageDisplay.scrollLeft = scrollMaxX / 2;
            pageDisplay.scrollTop = scrollMaxY / 2;
        });
    }
}

function updateZoom() {
    document.getElementById('zoomLevel').textContent = `${Math.round(zoomLevel * 100)}%`;
    applyZoom();
}

function handleKeyboard(e) {
    // Ignore if typing in input field
    if (e.target.tagName === 'INPUT') {
        return;
    }

    const pageDisplay = document.getElementById('pageDisplay');
    const panAmount = 100;

    // When zoomed, arrow keys pan instead of navigating pages
    if (zoomLevel > 1.0) {
        switch(e.key) {
            case 'ArrowLeft':
                pageDisplay.scrollLeft -= panAmount;
                e.preventDefault();
                return;
            case 'ArrowRight':
                pageDisplay.scrollLeft += panAmount;
                e.preventDefault();
                return;
            case 'ArrowUp':
                pageDisplay.scrollTop -= panAmount;
                e.preventDefault();
                return;
            case 'ArrowDown':
                pageDisplay.scrollTop += panAmount;
                e.preventDefault();
                return;
        }
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
