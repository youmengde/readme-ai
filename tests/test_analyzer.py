import json

from readme_ai.analyzer import analyze_repo, repo_info_to_dict


def test_gitignore_is_respected(tmp_path):
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("print('secret')\n", encoding="utf-8")

    info = analyze_repo(tmp_path)

    assert "main.py" in info.top_files
    assert "ignored.py" not in info.top_files


def test_repo_metadata_detection(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndescription = "Demo project"\n', encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_ok(): assert True", encoding="utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI", encoding="utf-8")

    info = analyze_repo(tmp_path)

    assert info.description == "Demo project"
    assert info.has_license is True
    assert info.has_docker is True
    assert info.has_tests is True
    assert info.has_ci is True
    assert "pyproject.toml" in info.dependencies


def test_repo_info_to_dict_is_json_serializable(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")
    info = analyze_repo(tmp_path)

    data = repo_info_to_dict(info)

    assert data["name"] == tmp_path.name
    json.dumps(data)


def test_python_metadata_from_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\n'
        'description = "My tool"\n'
        'requires-python = ">=3.9"\n'
        'dependencies = [\n'
        '    "click>=8.0",\n'
        '    "rich>=13.0",\n'
        ']\n'
        '\n'
        '[project.scripts]\n'
        'mytool = "mytool.cli:main"\n'
        'mytool-alt = "mytool.cli:alt"\n',
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")

    info = analyze_repo(tmp_path)

    assert info.description == "My tool"
    assert info.python_requires == ">=3.9"
    assert "click>=8.0" in info.python_deps
    assert "rich>=13.0" in info.python_deps
    assert "mytool" in info.console_scripts
    assert "mytool-alt" in info.console_scripts


def test_python_metadata_from_setup_cfg(tmp_path):
    setup_cfg = tmp_path / "setup.cfg"
    setup_cfg.write_text(
        "[metadata]\n"
        "name = oldtool\n\n"
        "[options.entry_points]\n"
        "console_scripts =\n"
        "    oldtool = oldtool.cli:main\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")

    info = analyze_repo(tmp_path)

    assert "oldtool" in info.console_scripts


def test_node_metadata_from_package_json(tmp_path):
    pkg = {
        "name": "my-cli",
        "description": "A nifty CLI",
        "engines": {"node": ">=18"},
        "dependencies": {"chalk": "^5.0.0", "commander": "^11.0.0"},
        "devDependencies": {"vitest": "^1.0.0"},
        "scripts": {"build": "tsc", "test": "vitest"},
        "bin": {"my-cli": "./bin/cli.js", "my-cli-alt": "./bin/alt.js"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (tmp_path / "index.js").write_text("console.log('hi')\n", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    info = analyze_repo(tmp_path)

    assert info.description == "A nifty CLI"
    assert info.node_version == ">=18"
    assert "chalk" in info.node_deps
    assert "commander" in info.node_deps
    assert "vitest" in info.node_dev_deps
    assert "build" in info.node_scripts
    assert "test" in info.node_scripts
    assert "my-cli" in info.node_bin
    assert info.node_pm == "npm"


def test_node_package_manager_detection(tmp_path):
    (tmp_path / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    (tmp_path / "index.js").write_text("\n", encoding="utf-8")
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 6.0\n", encoding="utf-8")

    info = analyze_repo(tmp_path)
    assert info.node_pm == "pnpm"


def test_node_bin_string_form(tmp_path):
    pkg = {"name": "single-bin", "bin": "./cli.js"}
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (tmp_path / "index.js").write_text("\n", encoding="utf-8")

    info = analyze_repo(tmp_path)
    assert info.node_bin == ["single-bin"]


def test_node_metadata_not_populated_without_package_json(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")

    info = analyze_repo(tmp_path)

    assert info.node_deps == []
    assert info.node_version == ""
    assert info.node_pm == ""
