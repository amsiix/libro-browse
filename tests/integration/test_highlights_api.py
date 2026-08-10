def test_save_highlight_creates_file_with_citation(app_client, fixture_books_dir):
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'Page one text for testing.',
        'rangeStart': 0, 'rangeEnd': 26,
    })
    data = response.get_json()
    assert response.status_code == 200
    assert data['success'] is True
    assert data['path'].startswith('highlights/1-')

    saved = fixture_books_dir / 'test-pdf-book' / data['path']
    content = saved.read_text()
    assert content.startswith('> Page one text for testing.')
    assert 'Test Author (2020). _Test Book_. book.pdf. p. 1.' in content


def test_save_highlight_writes_index_entry(app_client, fixture_books_dir):
    app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'Page one text for testing.',
        'rangeStart': 0, 'rangeEnd': 26,
    })
    import json as jsonlib
    index_path = fixture_books_dir / 'test-pdf-book' / 'highlights' / '.index.json'
    index = jsonlib.loads(index_path.read_text())
    assert len(index) == 1
    assert index[0]['page'] == 1
    assert index[0]['rangeStart'] == 0
    assert index[0]['rangeEnd'] == 26


def test_save_highlight_404_for_missing_book(app_client):
    response = app_client.post('/api/books/does-not-exist/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 4,
    })
    assert response.status_code == 404


def test_save_highlight_400_for_image_book(app_client):
    response = app_client.post('/api/books/test-image-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 4,
    })
    assert response.status_code == 400


def test_save_highlight_400_for_empty_quote(app_client):
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': '   ', 'rangeStart': 0, 'rangeEnd': 4,
    })
    assert response.status_code == 400


def test_save_highlight_400_for_invalid_range(app_client):
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 10, 'rangeEnd': 5,
    })
    assert response.status_code == 400


def test_save_highlight_409_for_exact_duplicate(app_client):
    payload = {'page': 1, 'quote': 'Page one text for testing.', 'rangeStart': 0, 'rangeEnd': 26}
    first = app_client.post('/api/books/test-pdf-book/highlights', json=payload)
    assert first.status_code == 200

    second = app_client.post('/api/books/test-pdf-book/highlights', json=payload)
    assert second.status_code == 409


def test_save_highlight_409_for_partial_overlap(app_client):
    app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'Page one text', 'rangeStart': 0, 'rangeEnd': 13,
    })
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text for testing', 'rangeStart': 8, 'rangeEnd': 26,
    })
    assert response.status_code == 409


def test_save_highlight_allows_same_text_different_position(app_client, fixture_books_dir):
    app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 4,
    })
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 50, 'rangeEnd': 54,
    })
    assert response.status_code == 200
    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 2


def test_save_highlight_allows_overlapping_ranges_on_different_pages(app_client, fixture_books_dir):
    app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 1, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 10,
    })
    response = app_client.post('/api/books/test-pdf-book/highlights', json={
        'page': 2, 'quote': 'text', 'rangeStart': 0, 'rangeEnd': 10,
    })
    assert response.status_code == 200
    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 2


def test_save_highlight_filename_collision_disambiguated(app_client, fixture_books_dir):
    payload_a = {'page': 1, 'quote': 'repeat', 'rangeStart': 0, 'rangeEnd': 6}
    payload_b = {'page': 1, 'quote': 'repeat', 'rangeStart': 20, 'rangeEnd': 26}

    resp_a = app_client.post('/api/books/test-pdf-book/highlights', json=payload_a)
    resp_b = app_client.post('/api/books/test-pdf-book/highlights', json=payload_b)

    assert resp_a.get_json()['path'] != resp_b.get_json()['path']
    highlights_dir = fixture_books_dir / 'test-pdf-book' / 'highlights'
    assert len(list(highlights_dir.glob('*.md'))) == 2
