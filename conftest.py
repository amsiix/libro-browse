import pytest

from tests.fixtures.build_books import build_pdf_book, build_image_book


@pytest.fixture
def fixture_books_dir(tmp_path):
    """A disposable books/ directory with one PDF book and one image book."""
    books_dir = tmp_path / 'books'
    books_dir.mkdir()
    build_pdf_book(
        books_dir, 'test-pdf-book',
        pages_text=['Page one text for testing.', 'Page two has different text.']
    )
    build_image_book(books_dir, 'test-image-book', num_pages=2)
    return books_dir


@pytest.fixture
def app_client(fixture_books_dir, monkeypatch):
    """Flask test_client() pointed at fixture_books_dir via monkeypatch —
    no app refactor needed, since BOOKS_DIR is a plain module global
    resolved fresh on every function call."""
    import app as app_module
    monkeypatch.setattr(app_module, 'BOOKS_DIR', fixture_books_dir)
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        yield client
