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
