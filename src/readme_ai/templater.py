"""Custom template rendering — fill user-provided templates with repo metadata."""

from __future__ import annotations

from pathlib import Path
from string import Template

from .analyzer import RepoInfo


def load_template(path: str | Path) -> Template:
    """Load a template file and return a string.Template object."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Template file not found: {path}")
    content = p.read_text(encoding="utf-8")
    return Template(content)


def _template_vars(info: RepoInfo) -> dict[str, str]:
    """Build a flat dict of template variables from RepoInfo."""
    languages = ", ".join(list(info.languages.keys())[:5]) or "N/A"
    entry_points = ", ".join(info.entry_points[:5]) or "N/A"
    deps = ", ".join(info.dependencies[:5]) or "N/A"
    scripts = ", ".join(info.console_scripts[:5]) or "N/A"
    py_deps = ", ".join(info.python_deps[:10]) or "N/A"

    return {
        "name": info.name,
        "description": info.description or "",
        "languages": languages,
        "has_tests": str(info.has_tests).lower(),
        "has_ci": str(info.has_ci).lower(),
        "has_license": str(info.has_license).lower(),
        "has_docker": str(info.has_docker).lower(),
        "entry_points": entry_points,
        "dependencies": deps,
        "console_scripts": scripts,
        "python_requires": info.python_requires or "",
        "python_deps": py_deps,
        "dir_tree": info.dir_tree,
    }


def render_custom(template_path: str | Path, info: RepoInfo) -> str:
    """Render a custom template file with repository metadata.

    Template syntax uses ``$variable`` or ``${variable}`` placeholders.
    Available variables: name, description, languages, has_tests, has_ci,
    has_license, has_docker, entry_points, dependencies, console_scripts,
    python_requires, python_deps, dir_tree.
    """
    tmpl = load_template(template_path)
    variables = _template_vars(info)
    return tmpl.safe_substitute(variables)
