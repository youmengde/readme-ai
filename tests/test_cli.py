import json

from click.testing import CliRunner

from readme_ai.cli import cli


def make_repo(path):
    (path / "pyproject.toml").write_text('[project]\ndescription = "Demo project"\n', encoding="utf-8")
    (path / "main.py").write_text("print('hi')\n", encoding="utf-8")


def test_analyze_json(tmp_path):
    make_repo(tmp_path)

    result = CliRunner().invoke(cli, ["analyze", str(tmp_path), "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["description"] == "Demo project"


def test_generate_local_stdout(tmp_path):
    make_repo(tmp_path)

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--local"])

    assert result.exit_code == 0
    assert "Demo project" in result.output


def test_generate_output_refuses_overwrite(tmp_path):
    make_repo(tmp_path)
    out = tmp_path / "README.md"
    out.write_text("existing", encoding="utf-8")

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--output", str(out)])

    assert result.exit_code != 0
    assert "already exists" in result.output
    assert out.read_text(encoding="utf-8") == "existing"


def test_generate_output_force_overwrites(tmp_path):
    make_repo(tmp_path)
    out = tmp_path / "README.md"
    out.write_text("existing", encoding="utf-8")

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--output", str(out), "--force"])

    assert result.exit_code == 0
    assert "Demo project" in out.read_text(encoding="utf-8")


def test_generate_diff_shows_changes(tmp_path):
    make_repo(tmp_path)
    out = tmp_path / "README.md"
    out.write_text("# old content\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--output", str(out), "--diff"])

    assert result.exit_code == 0
    # output file must not be modified
    assert out.read_text(encoding="utf-8") == "# old content\n"
    # diff should reference the file and show added lines
    assert "---" in result.output
    assert "+++" in result.output


def test_generate_diff_no_changes(tmp_path):
    make_repo(tmp_path)
    out = tmp_path / "README.md"
    # First write the generated content, then diff should report no changes
    CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--output", str(out), "--force"])
    current = out.read_text(encoding="utf-8")

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--output", str(out), "--diff"])

    assert result.exit_code == 0
    # No diff markers when content is identical
    assert "--- " not in result.output or "+++" not in result.output
    assert out.read_text(encoding="utf-8") == current


def test_generate_check_fails_when_out_of_date(tmp_path):
    make_repo(tmp_path)
    out = tmp_path / "README.md"
    out.write_text("# old content\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--output", str(out), "--check"])

    assert result.exit_code == 1
    # check must not modify the file
    assert out.read_text(encoding="utf-8") == "# old content\n"


def test_generate_check_passes_when_in_sync(tmp_path):
    make_repo(tmp_path)
    out = tmp_path / "README.md"
    CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--output", str(out), "--force"])

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--output", str(out), "--check"])

    assert result.exit_code == 0


def test_generate_diff_requires_output(tmp_path):
    make_repo(tmp_path)

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--local", "--diff"])

    assert result.exit_code != 0
    assert "--output" in result.output


def test_generate_with_custom_template(tmp_path):
    make_repo(tmp_path)
    template = tmp_path / "my_template.md"
    template.write_text("# $name\n\n$description\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["generate", str(tmp_path), "--template", str(template)])

    assert result.exit_code == 0
    assert "# " in result.output
    assert "Demo project" in result.output
