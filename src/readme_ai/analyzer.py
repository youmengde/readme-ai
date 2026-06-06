"""Repo analysis — extract structure, language, and metadata."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pathspec

DEFAULT_IGNORE = """
.git
.gitignore
__pycache__
*.pyc
node_modules
.venv
venv
.env
.env.*
dist
build
*.egg-info
.DS_Store
.idea
.vscode
*.swp
*.swo
.tox
.mypy_cache
.pytest_cache
.ruff_cache
coverage
htmlcov
"""


@dataclass
class RepoInfo:
    """Analyzed repository information."""
    name: str = ""
    description: str = ""
    languages: dict[str, int] = field(default_factory=dict)
    top_files: list[str] = field(default_factory=list)
    dir_tree: str = ""
    has_tests: bool = False
    has_ci: bool = False
    has_license: bool = False
    has_docker: bool = False
    dependencies: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    readme_exists: bool = False
    # Python-specific metadata
    python_requires: str = ""
    python_deps: list[str] = field(default_factory=list)
    console_scripts: list[str] = field(default_factory=list)
    # Node.js-specific metadata
    node_version: str = ""
    node_deps: list[str] = field(default_factory=list)
    node_dev_deps: list[str] = field(default_factory=list)
    node_scripts: list[str] = field(default_factory=list)
    node_bin: list[str] = field(default_factory=list)
    node_pm: str = ""


LANG_EXTENSIONS = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".cpp": "C++",
    ".c": "C", ".swift": "Swift", ".scala": "Scala", ".r": "R",
    ".jl": "Julia", ".lua": "Lua", ".sh": "Shell", ".bash": "Shell",
    ".zsh": "Shell", ".sql": "SQL", ".hs": "Haskell", ".ex": "Elixir",
    ".exs": "Elixir", ".erl": "Erlang", ".dart": "Dart",
}

ENTRY_FILES = {
    "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
    "index.js", "index.ts", "main.go", "main.rs", "lib.rs",
    "src/main.rs", "cmd/main.go",
}

DEP_FILES = {
    "requirements.txt", "pyproject.toml", "setup.py", "Pipfile",
    "package.json", "go.mod", "Cargo.toml", "Gemfile",
    "pom.xml", "build.gradle", "composer.json",
}


def _build_spec(repo_path: Path) -> pathspec.PathSpec:
    """Build a combined ignore spec from defaults and .gitignore."""
    lines = DEFAULT_IGNORE.strip().splitlines()
    gitignore = repo_path / ".gitignore"
    if gitignore.exists():
        lines.extend(gitignore.read_text(errors="ignore").splitlines())
    return pathspec.PathSpec.from_lines("gitignore", lines)


def _read_description(repo_path: Path, dep_file: str) -> str:
    fpath = repo_path / dep_file
    if not fpath.exists():
        return ""
    try:
        content = fpath.read_text(errors="ignore")
        if dep_file.endswith("pyproject.toml"):
            for line in content.splitlines():
                if line.strip().startswith("description"):
                    return line.split("=", 1)[-1].strip().strip('"').strip("'")
        if dep_file.endswith("package.json"):
            return json.loads(content).get("description", "")
    except Exception:
        return ""
    return ""


def _parse_pyproject_toml(content: str) -> dict:
    """Lightweight pyproject.toml parser — no toml dependency needed."""
    result: dict = {"deps": [], "scripts": [], "requires": "", "description": ""}
    in_project = False
    in_scripts = False
    in_deps = False

    for line in content.splitlines():
        stripped = line.strip()

        if stripped == "[project]":
            in_project = True
            in_scripts = False
            in_deps = False
            continue
        if stripped.startswith("["):
            if stripped in ("[project.scripts]", "[tool.poetry.scripts]"):
                in_scripts = True
                in_deps = False
                continue
            in_project = False
            in_scripts = False
            in_deps = False
            continue

        if in_project:
            if stripped.startswith("description"):
                result["description"] = stripped.split("=", 1)[-1].strip().strip('"').strip("'")
            elif stripped.startswith("requires-python"):
                result["requires"] = stripped.split("=", 1)[-1].strip().strip('"').strip("'")
            elif stripped.startswith("dependencies"):
                in_deps = True
                continue

        if in_deps:
            if stripped.startswith("]") or (not stripped.startswith("-") and not stripped.startswith('"') and "=" not in stripped and stripped):
                in_deps = False
                continue
            dep = stripped.lstrip("- ").strip('",').strip()
            if dep:
                result["deps"].append(dep)

        if in_scripts:
            if stripped.startswith("]") or (not stripped and not line.startswith(" ")):
                in_scripts = False
                continue
            if "=" in stripped:
                name = stripped.split("=", 1)[0].strip().strip('"')
                if name:
                    result["scripts"].append(name)

    return result


def _parse_setup_cfg(content: str) -> dict:
    """Lightweight setup.cfg parser for console_scripts and install_requires."""
    result: dict = {"deps": [], "scripts": []}
    in_scripts = False
    in_deps = False

    for line in content.splitlines():
        stripped = line.strip()

        if stripped.lower() == "[options.entry_points]":
            in_scripts = False
            in_deps = False
            # next section header or console_scripts line
            continue

        if stripped.lower().startswith("console_scripts"):
            in_scripts = True
            in_deps = False
            # the actual definitions may follow on next lines
            if "=" in stripped:
                _, rest = stripped.split("=", 1)
                rest = rest.strip()
                if rest:
                    # inline: console_scripts = foo = module:main
                    for entry in rest.split("\n"):
                        name = entry.split("=")[0].strip().strip('"')
                        if name:
                            result["scripts"].append(name)
            continue

        if stripped.lower() == "[options]" or stripped.lower().startswith("install_requires"):
            in_deps = stripped.lower().startswith("install_requires") or in_deps
            in_scripts = False
            continue

        if stripped.startswith("[") and stripped != "[options.entry_points]":
            in_scripts = False
            in_deps = False
            continue

        if in_scripts and "=" in stripped:
            name = stripped.split("=")[0].strip().strip('"')
            if name:
                result["scripts"].append(name)

        if in_deps:
            dep = stripped.strip()
            if dep and not dep.startswith("["):
                result["deps"].append(dep)

    return result


def _extract_python_metadata(repo_path: Path, info: RepoInfo) -> None:
    """Enrich RepoInfo with Python-specific metadata from pyproject.toml / setup.cfg."""
    pyproject = repo_path / "pyproject.toml"
    setup_cfg = repo_path / "setup.cfg"
    setup_py = repo_path / "setup.py"

    if pyproject.exists():
        try:
            parsed = _parse_pyproject_toml(pyproject.read_text(errors="ignore"))
            info.python_requires = parsed["requires"]
            info.python_deps = parsed["deps"]
            info.console_scripts = parsed["scripts"]
            if parsed["description"] and not info.description:
                info.description = parsed["description"]
        except Exception:
            pass

    if setup_cfg.exists():
        try:
            parsed = _parse_setup_cfg(setup_cfg.read_text(errors="ignore"))
            if parsed["scripts"] and not info.console_scripts:
                info.console_scripts = parsed["scripts"]
            if parsed["deps"] and not info.python_deps:
                info.python_deps = parsed["deps"]
        except Exception:
            pass

    # Also try setup.py for console_scripts if nothing found yet
    if setup_py.exists() and not info.console_scripts:
        try:
            content = setup_py.read_text(errors="ignore")
            for line in content.splitlines():
                if "console_scripts" in line:
                    # crude extraction from e.g. 'console_scripts=["foo=module:main"]'
                    for part in line.split("="):
                        part = part.strip().strip(" '\"[")
                        if part and "." not in part and ":" not in part and part != "console_scripts":
                            info.console_scripts.append(part)
                            break
        except Exception:
            pass


NODE_LOCKFILES = {
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "bun",
    "bun.lock": "bun",
}


def _detect_node_package_manager(repo_path: Path) -> str:
    """Detect the package manager from lockfile presence."""
    for lockfile, pm in NODE_LOCKFILES.items():
        if (repo_path / lockfile).exists():
            return pm
    return ""


def _extract_node_metadata(repo_path: Path, info: RepoInfo) -> None:
    """Enrich RepoInfo with Node.js metadata from package.json."""
    pkg = repo_path / "package.json"
    if not pkg.exists():
        return

    try:
        data = json.loads(pkg.read_text(errors="ignore"))
    except Exception:
        return

    if not isinstance(data, dict):
        return

    engines = data.get("engines")
    if isinstance(engines, dict) and isinstance(engines.get("node"), str):
        info.node_version = engines["node"]

    deps = data.get("dependencies")
    if isinstance(deps, dict):
        info.node_deps = sorted(deps.keys())

    dev_deps = data.get("devDependencies")
    if isinstance(dev_deps, dict):
        info.node_dev_deps = sorted(dev_deps.keys())

    scripts = data.get("scripts")
    if isinstance(scripts, dict):
        info.node_scripts = sorted(scripts.keys())

    bin_field = data.get("bin")
    if isinstance(bin_field, str):
        info.node_bin = [data.get("name", "")] if data.get("name") else []
    elif isinstance(bin_field, dict):
        info.node_bin = sorted(bin_field.keys())

    info.node_pm = _detect_node_package_manager(repo_path)

    if not info.description:
        desc = data.get("description")
        if isinstance(desc, str) and desc:
            info.description = desc


def analyze_repo(repo_path: str | Path) -> RepoInfo:
    """Analyze a repository and extract metadata."""
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    info = RepoInfo(name=repo_path.name)
    spec = _build_spec(repo_path)

    lang_counts: dict[str, int] = {}
    all_files: list[str] = []
    tree_lines: list[str] = []
    max_depth = 4
    max_files = 500

    for root, dirs, files in os.walk(repo_path):
        if len(all_files) >= max_files:
            dirs[:] = []
            break

        rel_root = Path(root).relative_to(repo_path)
        depth = len(rel_root.parts)

        dirs[:] = [d for d in dirs if not spec.match_file(str(rel_root / d))]
        dirs.sort()

        if depth <= max_depth:
            indent = "  " * depth
            tree_lines.append(f"{indent}{rel_root.name if str(rel_root) != '.' else repo_path.name}/")

        for fname in sorted(files):
            rel_file = str(rel_root / fname)
            if spec.match_file(rel_file):
                continue

            all_files.append(rel_file)
            if depth <= max_depth:
                indent = "  " * (depth + 1)
                tree_lines.append(f"{indent}{fname}")

            ext = Path(fname).suffix.lower()
            if ext in LANG_EXTENSIONS:
                lang = LANG_EXTENSIONS[ext]
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

            if fname in ENTRY_FILES or rel_file in ENTRY_FILES:
                info.entry_points.append(rel_file)

            if fname in DEP_FILES:
                info.dependencies.append(rel_file)

            if len(all_files) >= max_files:
                dirs[:] = []
                break

    info.languages = dict(sorted(lang_counts.items(), key=lambda x: -x[1]))
    info.top_files = all_files[:50]
    info.dir_tree = "\n".join(tree_lines[:80])
    info.has_tests = any(Path(f).parts[0] in {"test", "tests"} or Path(f).name.startswith("test_") for f in all_files)
    info.has_ci = any(
        f.startswith(".github/workflows") or f in {".travis.yml", "Jenkinsfile", ".gitlab-ci.yml"}
        for f in all_files
    )
    info.has_license = any(Path(f).name.startswith("LICENSE") for f in all_files)
    info.has_docker = any(Path(f).name == "Dockerfile" or "docker-compose" in Path(f).name for f in all_files)
    info.readme_exists = any(Path(f).name.upper().startswith("README") for f in all_files)

    for dep_file in info.dependencies:
        desc = _read_description(repo_path, dep_file)
        if desc:
            info.description = desc
            break

    if "Python" in info.languages:
        _extract_python_metadata(repo_path, info)

    if "JavaScript" in info.languages or "TypeScript" in info.languages or (repo_path / "package.json").exists():
        _extract_node_metadata(repo_path, info)

    return info


def repo_info_to_dict(info: RepoInfo) -> dict:
    """Convert RepoInfo to a JSON-serializable dictionary."""
    return asdict(info)


def build_context(info: RepoInfo, repo_path: str | Path) -> str:
    """Build a context string for the LLM prompt."""
    repo_path = Path(repo_path).resolve()
    parts = [
        f"Repository: {info.name}",
        f"Description: {info.description or 'N/A'}",
        f"Languages: {', '.join(f'{k} ({v} files)' for k, v in list(info.languages.items())[:5])}",
        f"Has tests: {info.has_tests}",
        f"Has CI: {info.has_ci}",
        f"Has Docker: {info.has_docker}",
        f"Has license: {info.has_license}",
        f"Entry points: {', '.join(info.entry_points[:5]) or 'N/A'}",
        f"Dependency files: {', '.join(info.dependencies[:5]) or 'N/A'}",
        f"Python requires: {info.python_requires or 'N/A'}",
        f"Python dependencies: {', '.join(info.python_deps[:10]) or 'N/A'}",
        f"Console scripts: {', '.join(info.console_scripts[:5]) or 'N/A'}",
        f"Node engines: {info.node_version or 'N/A'}",
        f"Node package manager: {info.node_pm or 'N/A'}",
        f"Node dependencies: {', '.join(info.node_deps[:10]) or 'N/A'}",
        f"Node scripts: {', '.join(info.node_scripts[:10]) or 'N/A'}",
        f"Node bin entries: {', '.join(info.node_bin[:5]) or 'N/A'}",
        "",
        "Directory structure:",
        info.dir_tree,
    ]

    for ep in info.entry_points[:3]:
        fpath = repo_path / ep
        if fpath.exists():
            try:
                content = fpath.read_text(errors="ignore")[:2000]
                parts.append(f"\n--- {ep} (first 2000 chars) ---\n{content}")
            except Exception:
                pass

    for dep in info.dependencies[:2]:
        fpath = repo_path / dep
        if fpath.exists():
            try:
                content = fpath.read_text(errors="ignore")[:2000]
                parts.append(f"\n--- {dep} ---\n{content}")
            except Exception:
                pass

    return "\n".join(parts)
