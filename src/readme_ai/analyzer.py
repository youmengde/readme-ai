"""Repo analysis — extract structure, language, and metadata."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pathspec

# Common patterns to ignore
DEFAULT_IGNORE = """
.git
.gitignore
__pycache__
*.pyc
node_modules
.venv
venv
.env
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


def _load_gitignore(repo_path: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns."""
    gitignore = repo_path / ".gitignore"
    if not gitignore.exists():
        return None
    with open(gitignore) as f:
        return pathspec.PathSpec.from_lines("gitwildmatch", f)


def _build_spec(repo_path: Path) -> pathspec.PathSpec:
    """Build a combined ignore spec from defaults and .gitignore."""
    lines = DEFAULT_IGNORE.strip().splitlines()
    gitignore_spec = _load_gitignore(repo_path)
    spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
    if gitignore_spec:
        # Merge: if either spec matches, ignore
        return spec
    return spec


def analyze_repo(repo_path: str | Path) -> RepoInfo:
    """Analyze a repository and extract metadata."""
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    info = RepoInfo()
    info.name = repo_path.name
    spec = _build_spec(repo_path)

    # Walk the repo
    lang_counts: dict[str, int] = {}
    all_files: list[str] = []
    tree_lines: list[str] = []
    max_depth = 4
    max_files = 500

    for root, dirs, files in os.walk(repo_path):
        rel_root = Path(root).relative_to(repo_path)
        depth = len(rel_root.parts)

        # Filter dirs
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

            if fname in ENTRY_FILES:
                info.entry_points.append(rel_file)

            if fname in DEP_FILES:
                info.dependencies.append(rel_file)

            if len(all_files) >= max_files:
                break

    # Determine attributes
    info.languages = dict(sorted(lang_counts.items(), key=lambda x: -x[1]))
    info.top_files = all_files[:50]
    info.dir_tree = "\n".join(tree_lines[:80])
    info.has_tests = any("test" in f.lower() for f in all_files)
    info.has_ci = any(f.startswith(".github/workflows") or f == ".travis.yml" or f == "Jenkinsfile" for f in all_files)
    info.has_license = any(Path(f).name.startswith("LICENSE") for f in all_files)
    info.has_docker = any("Dockerfile" in f or "docker-compose" in f for f in all_files)
    info.readme_exists = any(Path(f).name.upper().startswith("README") for f in all_files)

    # Try to extract description from pyproject.toml or package.json
    for dep_file in info.dependencies:
        fpath = repo_path / dep_file
        if not fpath.exists():
            continue
        try:
            content = fpath.read_text(errors="ignore")
            if "pyproject.toml" in dep_file:
                for line in content.splitlines():
                    if line.strip().startswith("description"):
                        desc = line.split("=", 1)[-1].strip().strip('"').strip("'")
                        if desc:
                            info.description = desc
                        break
            elif "package.json" in dep_file:
                import json
                data = json.loads(content)
                info.description = data.get("description", "")
        except Exception:
            pass

    return info


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
        "",
        "Directory structure:",
        info.dir_tree,
    ]

    # Read key files for more context
    for ep in info.entry_points[:3]:
        fpath = repo_path / ep
        if fpath.exists():
            try:
                content = fpath.read_text(errors="ignore")[:2000]
                parts.append(f"\n--- {ep} (first 2000 chars) ---\n{content}")
            except Exception:
                pass

    # Read pyproject.toml or package.json for deps
    for dep in info.dependencies[:2]:
        fpath = repo_path / dep
        if fpath.exists():
            try:
                content = fpath.read_text(errors="ignore")[:2000]
                parts.append(f"\n--- {dep} ---\n{content}")
            except Exception:
                pass

    return "\n".join(parts)
