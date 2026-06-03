from cao_engine.serving._paths import is_safe_cao_id


def test_plain_id_is_safe():
    assert is_safe_cao_id("1004-achmea-v2") is True


def test_empty_is_unsafe():
    assert is_safe_cao_id("") is False


def test_traversal_is_unsafe():
    assert is_safe_cao_id("../../etc/passwd") is False
    assert is_safe_cao_id("..") is False


def test_separators_are_unsafe():
    assert is_safe_cao_id("a/b") is False
    assert is_safe_cao_id("a\\b") is False


def test_nul_byte_is_unsafe():
    assert is_safe_cao_id("a\x00b") is False


def test_whitespace_only_is_unsafe():
    assert is_safe_cao_id("   ") is False


def test_single_dot_is_unsafe():
    assert is_safe_cao_id(".") is False


def test_leading_dot_is_unsafe():
    assert is_safe_cao_id(".hidden") is False
