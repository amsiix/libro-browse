// Book reader functionality

let bookData = null;
let currentPage = 0;
let zoomLevel = 1.0;

// PDF.js state
let pdfDoc = null;
let renderMode = 'images'; // 'images' or 'native-pdf'

// Panning state
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let scrollStartX = 0;
let scrollStartY = 0;
let isPanMode = false;

// Scroll navigation debounce
let lastScrollPageChange = 0;
const scrollDebounceMs = 250;

// Base image dimensions (fitted size at 100% zoom)
// These are captured once and reused for consistent zoom across pages
let baseImageWidth = 0;
let baseImageHeight = 0;
let baseDimensionsCaptured = false;

// Preload cache and settings
const preloadCache = new Map();
const PRELOAD_AHEAD = 3; // Number of pages to preload ahead/behind

// Reading position persistence (browser-only)
const READING_POSITIONS_KEY = 'libro-browse-reading-positions-v1';
let readingPositionsMemory = {};

function loadReadingPositions() {
    try {
        const raw = localStorage.getItem(READING_POSITIONS_KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (error) {
        return { ...readingPositionsMemory };
    }
}

function persistReadingPositions(positions) {
    try {
        localStorage.setItem(READING_POSITIONS_KEY, JSON.stringify(positions));
        readingPositionsMemory = { ...positions };
    } catch (error) {
        readingPositionsMemory = { ...positions };
    }
}

function saveReadingPosition(bookId, pageNum) {
    const positions = loadReadingPositions();
    positions[bookId] = {
        page: pageNum,
        updatedAt: Date.now()
    };
    persistReadingPositions(positions);
}

function getReadingPosition(bookId) {
    const positions = loadReadingPositions();
    if (positions[bookId] && Number.isInteger(positions[bookId].page)) {
        return positions[bookId].page;
    }

    // Migrate legacy per-book keys if they exist
    try {
        const legacy = localStorage.getItem(`libro-browse-page-${bookId}`);
        if (legacy !== null) {
            const pageNum = parseInt(legacy, 10);
            if (!Number.isNaN(pageNum)) {
                saveReadingPosition(bookId, pageNum);
                localStorage.removeItem(`libro-browse-page-${bookId}`);
                return pageNum;
            }
        }
    } catch (error) {
        return null;
    }

    return null;
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
        const panAllowed = zoomLevel > 1.0 && (isPanMode || e.button === 1 || e.button === 2);
        if (panAllowed) {
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

    // Prevent context menu while panning with right-click
    pageDisplay.addEventListener('contextmenu', (e) => {
        if (isDragging || isPanMode) {
            e.preventDefault();
        }
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
        renderMode = bookData.renderMode || 'images';

        // Update title
        document.getElementById('bookTitle').textContent = bookData.title;
        document.getElementById('totalPages').textContent = bookData.pageCount;

        // Set up page display based on render mode
        if (renderMode === 'native-pdf') {
            // Load PDF document - wrap canvas and text layer in a container for proper positioning
            // Note: PDF.js expects class "textLayer" (no hyphen) for its official CSS
            pageDisplay.innerHTML = '<div id="loadingSpinner" class="loading-spinner"></div><div id="pdfContainer" class="pdf-container"><canvas id="pdfCanvas"></canvas><div id="textLayer" class="textLayer"></div></div>';

            const pdfUrl = `/api/books/${bookId}/pdf`;
            pdfDoc = await pdfjsLib.getDocument(pdfUrl).promise;

            // Update page count from actual PDF
            bookData.pageCount = pdfDoc.numPages;
            document.getElementById('totalPages').textContent = bookData.pageCount;
        } else {
            // Image mode - restore the page image element and add loading spinner
            pageDisplay.innerHTML = '<div id="loadingSpinner" class="loading-spinner" style="display: none;"></div><img id="pageImage" class="page-image" alt="Book page">';
        }

        // Add cache status indicator
        if (!document.getElementById('cacheStatus')) {
            const cacheStatus = document.createElement('div');
            cacheStatus.id = 'cacheStatus';
            cacheStatus.className = 'cache-status';
            cacheStatus.innerHTML = '<span class="status-text">Cache: </span><span id="cacheStatusText">-</span>';
            document.body.appendChild(cacheStatus);
        }

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

// direction: 'forward' (show top), 'backward' (show bottom), or null (default to top)
function displayPage(pageNum, direction = null) {
    if (!bookData || pageNum < 0 || pageNum >= bookData.pageCount) {
        return;
    }

    currentPage = pageNum;
    saveReadingPosition(bookData.id, pageNum);

    if (renderMode === 'native-pdf') {
        displayPdfPage(pageNum, direction);
    } else {
        displayImagePage(pageNum, direction);
    }

    // Update controls
    document.getElementById('pageInput').value = pageNum + 1;
    document.getElementById('prevBtn').disabled = pageNum === 0;
    document.getElementById('nextBtn').disabled = pageNum === bookData.pageCount - 1;
}

async function displayPdfPage(pageNum, direction = null) {
    const canvas = document.getElementById('pdfCanvas');
    const pdfContainer = document.getElementById('pdfContainer');
    const pageDisplay = document.getElementById('pageDisplay');
    const spinner = document.getElementById('loadingSpinner');
    const textLayer = document.getElementById('textLayer');

    if (!pdfDoc || !canvas) return;

    spinner.style.display = 'block';

    try {
        // PDF.js uses 1-indexed pages
        const page = await pdfDoc.getPage(pageNum + 1);

        // Calculate scale to fit container (similar to max-width: 90%, max-height: 90%)
        const containerWidth = pageDisplay.clientWidth * 0.9;
        const containerHeight = pageDisplay.clientHeight * 0.9;

        const viewport = page.getViewport({ scale: 1 });
        const scaleX = containerWidth / viewport.width;
        const scaleY = containerHeight / viewport.height;
        const baseScale = Math.min(scaleX, scaleY);

        // Apply zoom level
        const scale = baseScale * zoomLevel;
        const scaledViewport = page.getViewport({ scale });

        // Set container dimensions
        if (pdfContainer) {
            pdfContainer.style.width = scaledViewport.width + 'px';
            pdfContainer.style.height = scaledViewport.height + 'px';
        }

        // Set canvas dimensions
        canvas.width = scaledViewport.width;
        canvas.height = scaledViewport.height;
        canvas.style.width = scaledViewport.width + 'px';
        canvas.style.height = scaledViewport.height + 'px';

        // Capture base dimensions (at zoom 1.0)
        if (!baseDimensionsCaptured) {
            const baseViewport = page.getViewport({ scale: baseScale });
            baseImageWidth = baseViewport.width;
            baseImageHeight = baseViewport.height;
            baseDimensionsCaptured = true;
        }

        // Render PDF page to canvas
        const ctx = canvas.getContext('2d');
        await page.render({
            canvasContext: ctx,
            viewport: scaledViewport
        }).promise;

        // Render text layer for selection
        if (textLayer) {
            textLayer.innerHTML = '';

            // Use the same scaled viewport as the canvas for proper alignment
            textLayer.style.width = scaledViewport.width + 'px';
            textLayer.style.height = scaledViewport.height + 'px';
            textLayer.style.transform = '';
            textLayer.style.transformOrigin = '';

            const textContent = await page.getTextContent();

            // PDF.js 3.x API - render at the same scale as canvas
            const textLayerRender = pdfjsLib.renderTextLayer({
                textContentSource: textContent,
                container: textLayer,
                viewport: scaledViewport
            });
            await textLayerRender.promise;
        }

        spinner.style.display = 'none';

        // Handle zoomed state
        if (zoomLevel > 1.0) {
            pageDisplay.classList.add('zoomed');
        } else {
            pageDisplay.classList.remove('zoomed');
        }

        // Set scroll position based on navigation direction
        requestAnimationFrame(() => {
            pageDisplay.scrollLeft = 0;
            if (direction === 'backward' && zoomLevel > 1.0) {
                pageDisplay.scrollTop = pageDisplay.scrollHeight - pageDisplay.clientHeight;
            } else {
                pageDisplay.scrollTop = 0;
            }
        });

    } catch (error) {
        spinner.style.display = 'none';
        console.error('Error rendering PDF page:', error);
    }
}

function displayImagePage(pageNum, direction = null) {
    const pageUrl = `/api/books/${bookData.id}/page/${pageNum}`;
    const pageImg = document.getElementById('pageImage');
    const pageDisplay = document.getElementById('pageDisplay');
    const spinner = document.getElementById('loadingSpinner');

    // Reset to base state before loading new image
    pageImg.style.width = '';
    pageImg.style.height = '';
    pageImg.style.transform = '';

    // Check if page is already preloaded
    const cached = preloadCache.get(pageNum);
    const isCached = cached && cached.complete;

    // Show loading spinner only for non-cached images
    if (!isCached) {
        spinner.style.display = 'block';
        pageImg.classList.add('loading');
    }

    pageImg.onload = () => {
        // Hide loading spinner
        spinner.style.display = 'none';
        pageImg.classList.remove('loading');
        // Capture the fitted dimensions as base size (only once, for consistency)
        if (!baseDimensionsCaptured) {
            baseImageWidth = pageImg.offsetWidth;
            baseImageHeight = pageImg.offsetHeight;
            baseDimensionsCaptured = true;
        }
        // Apply current zoom level
        applyZoom();
        // Set scroll position based on navigation direction (after zoom applied)
        requestAnimationFrame(() => {
            pageDisplay.scrollLeft = 0;
            if (direction === 'backward' && zoomLevel > 1.0) {
                // Going backward: show bottom of page
                pageDisplay.scrollTop = pageDisplay.scrollHeight - pageDisplay.clientHeight;
            } else {
                // Going forward or default: show top of page
                pageDisplay.scrollTop = 0;
            }
        });
        // Preload adjacent pages
        preloadPages(pageNum);
    };

    pageImg.onerror = () => {
        spinner.style.display = 'none';
        pageImg.classList.remove('loading');
    };

    // Set src - onload will fire even for cached images
    pageImg.src = isCached ? cached.src : pageUrl;
}

function preloadPages(currentPageNum) {
    // Only preload for image mode
    if (!bookData || renderMode === 'native-pdf') return;

    // Preload pages ahead and behind
    for (let offset = 1; offset <= PRELOAD_AHEAD; offset++) {
        // Preload next pages
        const nextPage = currentPageNum + offset;
        if (nextPage < bookData.pageCount && !preloadCache.has(nextPage)) {
            preloadPage(nextPage);
        }

        // Preload previous pages
        const prevPage = currentPageNum - offset;
        if (prevPage >= 0 && !preloadCache.has(prevPage)) {
            preloadPage(prevPage);
        }
    }

    // Clean up old cached pages (keep only nearby pages)
    const minKeep = Math.max(0, currentPageNum - PRELOAD_AHEAD - 1);
    const maxKeep = Math.min(bookData.pageCount - 1, currentPageNum + PRELOAD_AHEAD + 1);
    for (const pageNum of preloadCache.keys()) {
        if (pageNum < minKeep || pageNum > maxKeep) {
            preloadCache.delete(pageNum);
        }
    }

    updateCacheStatus();
}

function preloadPage(pageNum) {
    const img = new Image();
    img.onload = () => updateCacheStatus();
    img.onerror = () => updateCacheStatus();
    img.src = `/api/books/${bookData.id}/page/${pageNum}`;
    preloadCache.set(pageNum, img);
}

function updateCacheStatus() {
    const statusText = document.getElementById('cacheStatusText');
    if (!statusText) return;

    // For PDF mode, show different status
    if (renderMode === 'native-pdf') {
        statusText.textContent = 'PDF';
        statusText.className = 'status-ready';
        return;
    }

    let loaded = 0;
    let total = preloadCache.size;

    for (const img of preloadCache.values()) {
        if (img.complete && img.naturalWidth > 0) {
            loaded++;
        }
    }

    if (total === 0) {
        statusText.textContent = '-';
        statusText.className = '';
    } else if (loaded === total) {
        statusText.textContent = `${loaded}/${total} ready`;
        statusText.className = 'status-ready';
    } else {
        statusText.textContent = `${loaded}/${total} loading...`;
        statusText.className = 'status-loading';
    }
}

function nextPage() {
    if (currentPage < bookData.pageCount - 1) {
        displayPage(currentPage + 1, 'forward');
    }
}

function prevPage() {
    if (currentPage > 0) {
        displayPage(currentPage - 1, 'backward');
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
    // Update zoom level display
    document.getElementById('zoomLevel').textContent = '100%';
    // Reset base dimensions flag so they get recaptured for current page
    baseDimensionsCaptured = false;
    // Re-display current page to capture fresh base dimensions
    displayPage(currentPage);
}

function applyZoom() {
    // For PDF mode, re-render the page at new zoom
    if (renderMode === 'native-pdf') {
        displayPdfPage(currentPage);
        return;
    }

    // Image mode zoom
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

    if (e.key === ' ' && !isPanMode) {
        isPanMode = true;
        pageDisplay.classList.add('pan-mode');
        e.preventDefault();
        return;
    }
    if (e.key === ' ' && isPanMode) {
        e.preventDefault();
        return;
    }

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

document.addEventListener('keyup', (e) => {
    if (e.key === ' ') {
        const pageDisplay = document.getElementById('pageDisplay');
        isPanMode = false;
        pageDisplay.classList.remove('pan-mode');
    }
});
