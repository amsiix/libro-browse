import os
import socket
import subprocess
import sys
import time
from pathlib import Path

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


@pytest.fixture
def live_server(fixture_books_dir):
    """Launches a real `python app.py` subprocess pointed at fixture_books_dir
    on a free local port, for tests that need actual PDF.js rendering in a
    real browser. Never touches the user's real books/ folder."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    env = os.environ.copy()
    env['LIBRO_BOOKS_DIR'] = str(fixture_books_dir)
    env['LIBRO_PORT'] = str(port)
    env['LIBRO_DEBUG'] = '0'

    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / 'app.py')],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    base_url = f'http://127.0.0.1:{port}'
    deadline = time.time() + 15
    started = False
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                started = True
                break
        except OSError:
            time.sleep(0.2)

    if not started:
        proc.terminate()
        raise RuntimeError('Server did not start in time')

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
