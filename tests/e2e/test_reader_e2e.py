import pytest

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
