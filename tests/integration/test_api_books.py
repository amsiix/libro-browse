import importlib
import os


def test_books_dir_honors_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv('LIBRO_BOOKS_DIR', str(tmp_path))
    import app as app_module
    importlib.reload(app_module)
    try:
        assert app_module.BOOKS_DIR == tmp_path
    finally:
        monkeypatch.delenv('LIBRO_BOOKS_DIR', raising=False)
        importlib.reload(app_module)


from tests.fixtures.build_books import build_pdf_book, build_image_book


def test_api_books_lists_fixture_books(app_client):
    response = app_client.get('/api/books')
    data = response.get_json()
    assert data['success'] is True
    ids = {b['id'] for b in data['books']}
    assert {'test-pdf-book', 'test-image-book'} == ids


def test_api_books_multi_author_joined_with_comma(fixture_books_dir, monkeypatch):
    build_pdf_book(
        fixture_books_dir, 'multi-author-book', pages_text=['one'],
        metadata_overrides={'author': ['Wolfgang Karl Härdle', 'Léopold Simar']}
    )
    import app as app_module
    monkeypatch.setattr(app_module, 'BOOKS_DIR', fixture_books_dir)
    with app_module.app.test_client() as client:
        data = client.get('/api/books').get_json()
    book = next(b for b in data['books'] if b['id'] == 'multi-author-book')
    assert book['author'] == 'Wolfgang Karl Härdle, Léopold Simar'


def test_api_book_detail_returns_pdf_book(app_client):
    response = app_client.get('/api/books/test-pdf-book')
    data = response.get_json()
    assert data['success'] is True
    assert data['book']['type'] == 'pdf'
    assert data['book']['renderMode'] == 'native-pdf'
    assert data['book']['pageCount'] == 2


def test_api_book_detail_404_for_missing_book(app_client):
    response = app_client.get('/api/books/does-not-exist')
    assert response.status_code == 404


def test_api_book_page_serves_rendered_pdf_page(app_client):
    response = app_client.get('/api/books/test-pdf-book/page/0')
    assert response.status_code == 200
    assert response.mimetype == 'image/jpeg'


def test_api_book_cover_serves_image(app_client):
    response = app_client.get('/api/books/test-image-book/cover')
    assert response.status_code == 200
