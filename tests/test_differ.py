from readme_ai.differ import is_in_sync, read_existing, render_diff


def test_render_diff_returns_empty_when_identical():
    assert render_diff("same\n", "same\n") == ""


def test_render_diff_shows_changes():
    diff = render_diff("# old\n", "# new\n")

    assert diff
    assert "-# old" in diff
    assert "+# new" in diff
    assert "---" in diff
    assert "+++" in diff


def test_is_in_sync():
    assert is_in_sync("a", "a") is True
    assert is_in_sync("a", "b") is False


def test_read_existing_returns_empty_when_missing(tmp_path):
    assert read_existing(tmp_path / "does-not-exist.md") == ""


def test_read_existing_reads_utf8(tmp_path):
    path = tmp_path / "README.md"
    path.write_text("中文 content\n", encoding="utf-8")

    assert read_existing(path) == "中文 content\n"
