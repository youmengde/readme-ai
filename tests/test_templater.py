from readme_ai.analyzer import RepoInfo
from readme_ai.templater import render_custom


def test_render_custom_fills_variables(tmp_path):
    template = tmp_path / "template.md"
    template.write_text(
        "# $name\n\n$description\n\nLanguages: $languages\nHas tests: $has_tests\n",
        encoding="utf-8",
    )

    info = RepoInfo(
        name="myproject",
        description="A cool tool",
        languages={"Python": 10, "JavaScript": 3},
        has_tests=True,
    )

    result = render_custom(template, info)

    assert "# myproject" in result
    assert "A cool tool" in result
    assert "Python, JavaScript" in result
    assert "Has tests: true" in result


def test_render_custom_leaves_unknown_variables_unchanged(tmp_path):
    template = tmp_path / "template.md"
    template.write_text("# $name\n\n$unknown_var\n", encoding="utf-8")

    info = RepoInfo(name="myproject")

    result = render_custom(template, info)

    assert "# myproject" in result
    assert "$unknown_var" in result


def test_render_custom_missing_file_raises():
    info = RepoInfo(name="myproject")

    try:
        render_custom("/nonexistent/template.md", info)
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_render_custom_curly_brace_syntax(tmp_path):
    template = tmp_path / "template.md"
    template.write_text("${name} - ${description}\n", encoding="utf-8")

    info = RepoInfo(name="myproject", description="A cool tool")

    result = render_custom(template, info)

    assert "myproject - A cool tool" in result
