import json

import book_utils
from tests.fixtures.build_books import build_pdf_book, build_image_book


def test_is_pdf_book_true_for_pdf_metadata(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one'])
    is_pdf, pdf_file = book_utils.is_pdf_book(book_dir)
    assert is_pdf is True
    assert pdf_file == 'book.pdf'


def test_is_pdf_book_false_for_image_metadata(tmp_path):
    book_dir = build_image_book(tmp_path, 'b1')
    is_pdf, pdf_file = book_utils.is_pdf_book(book_dir)
    assert is_pdf is False
    assert pdf_file is None


def test_is_pdf_book_false_when_metadata_missing(tmp_path):
    book_dir = tmp_path / 'no-metadata'
    book_dir.mkdir()
    is_pdf, pdf_file = book_utils.is_pdf_book(book_dir)
    assert is_pdf is False
    assert pdf_file is None


def test_get_pdf_page_count_reads_actual_pdf(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one', 'two', 'three'])
    count = book_utils.get_pdf_page_count(book_dir / 'book.pdf')
    assert count == 3


def test_get_pdf_page_count_none_for_missing_file(tmp_path):
    assert book_utils.get_pdf_page_count(tmp_path / 'nope.pdf') is None


def test_compute_pdf_fingerprint_changes_when_file_changes(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one'])
    pdf_path = book_dir / 'book.pdf'
    fp1 = book_utils.compute_pdf_fingerprint(pdf_path)
    assert fp1['size'] == pdf_path.stat().st_size

    other_dir = build_pdf_book(tmp_path, 'b2', pages_text=['completely different text'])
    fp2 = book_utils.compute_pdf_fingerprint(other_dir / 'book.pdf')
    assert fp2['sha256'] != fp1['sha256']


def test_check_book_flags_page_count_mismatch(tmp_path):
    book_dir = build_pdf_book(
        tmp_path, 'b1', pages_text=['one', 'two'],
        metadata_overrides={'page_count': 999}
    )
    warnings = book_utils.check_book(book_dir)
    assert any('page_count' in w for w in warnings)


def test_check_book_no_warnings_for_correct_pdf_book(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one', 'two'])
    warnings = book_utils.check_book(book_dir)
    assert warnings == []


def test_check_book_flags_missing_pdf_file(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one'])
    (book_dir / 'book.pdf').unlink()
    warnings = book_utils.check_book(book_dir)
    assert any('does not exist' in w for w in warnings)


def test_check_book_flags_fingerprint_drift(tmp_path):
    book_dir = build_pdf_book(tmp_path, 'b1', pages_text=['one'])
    warnings = book_utils.check_book(book_dir, backfill_fingerprint=True)
    assert warnings == []

    # Swap in a different PDF without updating metadata.json
    other = build_pdf_book(tmp_path, 'b2', pages_text=['a totally different book'])
    (book_dir / 'book.pdf').write_bytes((other / 'book.pdf').read_bytes())

    warnings = book_utils.check_book(book_dir)
    assert any('changed since its fingerprint' in w for w in warnings)


def test_check_book_flags_missing_cover_for_image_book(tmp_path):
    book_dir = build_image_book(tmp_path, 'b1', metadata_overrides={'cover': 'missing.jpg'})
    warnings = book_utils.check_book(book_dir)
    assert any('missing.jpg' in w for w in warnings)


def test_check_all_books_only_returns_books_with_issues(tmp_path):
    build_pdf_book(tmp_path, 'good', pages_text=['one'])
    build_pdf_book(tmp_path, 'bad', pages_text=['one', 'two'], metadata_overrides={'page_count': 5})

    issues = book_utils.check_all_books(tmp_path)
    assert set(issues.keys()) == {'bad'}


def test_get_authors_single_string():
    assert book_utils.get_authors({'author': 'Seneca'}) == ['Seneca']


def test_get_authors_list_of_strings():
    metadata = {'author': ['Wolfgang Karl Härdle', 'Léopold Simar']}
    assert book_utils.get_authors(metadata) == ['Wolfgang Karl Härdle', 'Léopold Simar']


def test_get_authors_strips_whitespace_and_drops_empties():
    metadata = {'author': [' Ada Lovelace ', '', '  ']}
    assert book_utils.get_authors(metadata) == ['Ada Lovelace']


def test_get_authors_defaults_to_unknown_when_missing():
    assert book_utils.get_authors({}) == ['Unknown']


def test_get_authors_defaults_to_unknown_when_blank_string():
    assert book_utils.get_authors({'author': '   '}) == ['Unknown']
