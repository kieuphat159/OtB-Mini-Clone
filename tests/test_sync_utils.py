from scraper.sync_utils import normalize_article_id


def test_normalize_article_id_handles_string_and_int():
    assert normalize_article_id(123) == "123"
    assert normalize_article_id("123") == "123"
    assert normalize_article_id(None) is None
