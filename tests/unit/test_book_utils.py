import json

import pytest

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


def test_build_citation_single_author():
    metadata = {'title': 'The Theory of Probability', 'author': 'B. V. Gnedenko', 'year': '1978'}
    citation = book_utils.build_citation(metadata, 'Gnedenko-Theory of Probability.pdf', 42)
    assert citation == (
        'B. V. Gnedenko (1978). _The Theory of Probability_. '
        'Gnedenko-Theory of Probability.pdf. p. 42.'
    )


def test_build_citation_multi_author_comma_separated():
    metadata = {
        'title': 'Applied Multivariate Statistical Analysis',
        'author': ['Wolfgang Karl Härdle', 'Léopold Simar'],
        'year': '2003',
    }
    citation = book_utils.build_citation(metadata, 'stats.pdf', 5)
    assert citation.startswith('Wolfgang Karl Härdle, Léopold Simar (2003).')


def test_build_citation_falls_back_when_year_missing():
    metadata = {'title': 'Untitled Work', 'author': 'Someone'}
    citation = book_utils.build_citation(metadata, 'book.pdf', 1)
    assert '(n.d.)' in citation


def test_build_citation_falls_back_when_title_missing():
    metadata = {'author': 'Someone', 'year': '2020'}
    citation = book_utils.build_citation(metadata, 'book.pdf', 1)
    assert '_Untitled_' in citation


def test_slugify_quote_basic():
    assert book_utils.slugify_quote('Doubt is not a pleasant condition, but certainty is absurd.') \
        == 'doubt-is-not-a-pleasant-condition'


def test_slugify_quote_truncates_to_max_len():
    quote = 'a very long quote ' * 10
    slug = book_utils.slugify_quote(quote)
    assert len(slug) <= 50
    assert not slug.endswith('-')


def test_slugify_quote_strips_punctuation():
    assert book_utils.slugify_quote("It's--strange, isn't it?") == 'its-strange-isnt-it'


def test_slugify_quote_falls_back_when_empty_after_stripping():
    assert book_utils.slugify_quote('...???!!!') == 'highlight'


def test_load_highlight_index_empty_when_missing(tmp_path):
    assert book_utils.load_highlight_index(tmp_path) == []


def test_load_highlight_index_raises_on_corrupt_json(tmp_path):
    """A present-but-unparseable .index.json must NOT be treated the same
    as "missing" -- doing so would let a caller silently overwrite it
    with a fresh index, discarding every previously recorded highlight's
    range data (the .md files stay on disk but lose overlap protection)."""
    (tmp_path / '.index.json').write_text('{not valid json', encoding='utf-8')
    with pytest.raises(book_utils.HighlightIndexError):
        book_utils.load_highlight_index(tmp_path)


def test_load_highlight_index_raises_when_not_a_list(tmp_path):
    (tmp_path / '.index.json').write_text('{"oops": "an object, not a list"}', encoding='utf-8')
    with pytest.raises(book_utils.HighlightIndexError):
        book_utils.load_highlight_index(tmp_path)


def test_save_and_load_highlight_index_roundtrip(tmp_path):
    index = [{'file': '1-foo.md', 'page': 1, 'rangeStart': 0, 'rangeEnd': 10}]
    book_utils.save_highlight_index(tmp_path, index)
    assert book_utils.load_highlight_index(tmp_path) == index


def test_ranges_overlap_true_for_exact_duplicate():
    assert book_utils.ranges_overlap(5, 15, 5, 15) is True


def test_ranges_overlap_true_for_partial_overlap():
    assert book_utils.ranges_overlap(5, 15, 10, 20) is True


def test_ranges_overlap_false_for_adjacent_ranges():
    assert book_utils.ranges_overlap(5, 15, 15, 25) is False


def test_ranges_overlap_false_for_disjoint_ranges():
    assert book_utils.ranges_overlap(5, 10, 20, 30) is False


def test_find_overlapping_entry_matches_same_page(tmp_path):
    index = [{'file': '1-foo.md', 'page': 1, 'rangeStart': 5, 'rangeEnd': 15}]
    conflict = book_utils.find_overlapping_entry(index, page=1, range_start=10, range_end=20)
    assert conflict == index[0]


def test_find_overlapping_entry_ignores_other_pages(tmp_path):
    index = [{'file': '1-foo.md', 'page': 1, 'rangeStart': 5, 'rangeEnd': 15}]
    conflict = book_utils.find_overlapping_entry(index, page=2, range_start=5, range_end=15)
    assert conflict is None


def test_find_overlapping_entry_none_when_no_overlap(tmp_path):
    index = [{'file': '1-foo.md', 'page': 1, 'rangeStart': 5, 'rangeEnd': 15}]
    conflict = book_utils.find_overlapping_entry(index, page=1, range_start=20, range_end=30)
    assert conflict is None


def test_resolve_highlight_filename_no_collision(tmp_path):
    assert book_utils.resolve_highlight_filename(tmp_path, 42, 'doubt-is-not') == '42-doubt-is-not.md'


def test_resolve_highlight_filename_disambiguates_collision(tmp_path):
    (tmp_path / '42-doubt-is-not.md').write_text('existing')
    assert book_utils.resolve_highlight_filename(tmp_path, 42, 'doubt-is-not') == '42-doubt-is-not-2.md'

    (tmp_path / '42-doubt-is-not-2.md').write_text('existing')
    assert book_utils.resolve_highlight_filename(tmp_path, 42, 'doubt-is-not') == '42-doubt-is-not-3.md'
