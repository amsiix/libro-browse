import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_live_server_serves_library_page(live_server, page):
    page.goto(live_server)
    page.wait_for_selector('text=Libro Browse')


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
    # A real-viewport assertion, not just an inline-style substring match:
    # this fails if the bar exists in the DOM but is rendered off-screen
    # (the bug the CSS fix in static/css/reader.css addresses), because
    # to_be_in_viewport() checks actual intersection with the visible
    # viewport, which a human user would also be bound by.
    expect(page.locator('#highlightBar')).to_be_in_viewport(timeout=5000)
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
    expect(page.locator('#highlightBar')).to_be_in_viewport(timeout=5000)
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
    if highlight_bar is None:
        return  # absent entirely -- correctly hidden

    # Checking computed display alone isn't enough: a bar that is present
    # but rendered off-screen (the original CSS bug) would also pass a
    # naive "display !== 'none'" check if it happened to be toggled to
    # display:flex. Require BOTH that it's genuinely display:none AND that
    # it does not intersect the viewport, so a regression that leaves the
    # bar present-but-unreachable for image books is caught too.
    display = page.evaluate(
        "el => window.getComputedStyle(el).display", highlight_bar
    )
    assert display == 'none', (
        f"#highlightBar exists for an image-scanned book with display={display!r}; "
        "expected display:none (no highlight affordance for image books)"
    )
    expect(page.locator('#highlightBar')).not_to_be_in_viewport()


def test_overlapping_highlight_rejected_in_ui(live_server, page, fixture_books_dir):
    page.goto(f'{live_server}/reader/test-pdf-book')
    page.wait_for_selector('#textLayer span')

    page.evaluate(SELECT_FIRST_SPAN_JS)
    expect(page.locator('#highlightBar')).to_be_in_viewport(timeout=5000)
    page.click('#saveHighlightBtn')
    page.wait_for_function(
        "document.getElementById('highlightPreview').textContent.includes('Saved to')",
        timeout=5000
    )

    page.evaluate(SELECT_FIRST_SPAN_JS)
    expect(page.locator('#highlightBar')).to_be_in_viewport(timeout=5000)
    page.click('#saveHighlightBtn')
    page.wait_for_selector('#highlightBar.error', timeout=5000)

    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 1
