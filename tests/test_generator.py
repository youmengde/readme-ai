from readme_ai.analyzer import analyze_repo
from readme_ai.generator import generate_readme_local
import json


def test_local_generator_for_python_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndescription = "Demo project"\n', encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_ok(): assert True", encoding="utf-8")

    info = analyze_repo(tmp_path)
    readme = generate_readme_local(info, str(tmp_path))

    assert "# " in readme
    assert "Demo project" in readme
    assert "python3 -m pip install -e ." in readme
    assert "python3 -m pytest" in readme


def test_local_generator_minimal_is_shorter_than_detailed(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")
    info = analyze_repo(tmp_path)

    minimal = generate_readme_local(info, str(tmp_path), style="minimal")
    detailed = generate_readme_local(info, str(tmp_path), style="detailed")

    assert "## Project Structure" not in minimal
    assert "## Project Structure" in detailed
    assert len(detailed) > len(minimal)


def test_local_generator_for_node_project(tmp_path):
    pkg = {
        "name": "my-cli",
        "description": "Node CLI demo",
        "engines": {"node": ">=18"},
        "dependencies": {"commander": "^11.0.0"},
        "scripts": {"test": "vitest"},
        "bin": {"my-cli": "./bin/cli.js"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (tmp_path / "index.js").write_text("console.log('hi')\n", encoding="utf-8")
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 6.0\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.js").write_text("// test", encoding="utf-8")

    info = analyze_repo(tmp_path)
    readme = generate_readme_local(info, str(tmp_path))

    assert "Node CLI demo" in readme
    assert "Requires Node.js >=18" in readme
    assert "pnpm install" in readme
    assert "my-cli" in readme
    assert "pnpm test" in readme
