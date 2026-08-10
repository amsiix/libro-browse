def test_fixture_books_dir_has_two_books(fixture_books_dir):
    assert (fixture_books_dir / 'test-pdf-book' / 'book.pdf').exists()
    assert (fixture_books_dir / 'test-pdf-book' / 'metadata.json').exists()
    assert (fixture_books_dir / 'test-image-book' / '001.jpg').exists()


def test_app_client_lists_fixture_books(app_client):
    response = app_client.get('/api/books')
    data = response.get_json()
    assert data['success'] is True
    ids = {b['id'] for b in data['books']}
    assert ids == {'test-pdf-book', 'test-image-book'}
