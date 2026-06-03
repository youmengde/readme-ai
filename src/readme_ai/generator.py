"""LLM-backed README generation."""

from __future__ import annotations

import os

from .analyzer import RepoInfo, build_context

SYSTEM_PROMPT = """You are an expert technical writer who generates high-quality GitHub README files.
Generate a complete, well-structured README.md in Markdown. Follow these rules:

1. Start with a clear project name as H1 and a one-line description
2. Include sections that are relevant to the detected project
3. Use realistic installation and usage examples based on the repo structure
4. Keep it concise — no filler, no buzzwords
5. Use proper Markdown formatting with fenced code blocks
6. Do not include placeholder text
7. Output only README Markdown, no explanations outside the Markdown
"""

STYLE_GUIDE = {
    "minimal": "Style: minimal. Keep the README short with only overview, install, usage, and license.",
    "standard": "Style: standard. Include features, install, usage, development, and license when relevant.",
    "detailed": "Style: detailed. Include project structure, configuration, development, and testing when relevant.",
}

USER_PROMPT_TEMPLATE = """Generate a README.md for this repository.

{style_guide}

Repository context:

{context}"""


class GenerationError(RuntimeError):
    """Raised when an LLM provider fails to generate a README."""


def generate_readme(
    info: RepoInfo,
    repo_path: str,
    style: str = "standard",
    model: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
) -> str:
    """Generate a README using an LLM."""
    context = build_context(info, repo_path)
    provider = _detect_provider(provider, model)
    prompt = USER_PROMPT_TEMPLATE.format(
        style_guide=STYLE_GUIDE.get(style, STYLE_GUIDE["standard"]),
        context=context,
    )

    if provider == "anthropic":
        return _generate_anthropic(prompt, model or "claude-sonnet-4-20250514", api_key)
    return _generate_openai(prompt, model or "gpt-4o", api_key)


def _detect_provider(provider: str | None, model: str | None) -> str:
    if provider and provider != "auto":
        return provider
    if model and model.startswith("claude"):
        return "anthropic"
    if os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return "anthropic"
    return "openai"


def _generate_openai(prompt: str, model: str, api_key: str | None) -> str:
    """Generate using OpenAI API."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise GenerationError(f"OpenAI generation failed: {exc}") from exc


def _generate_anthropic(prompt: str, model: str, api_key: str | None) -> str:
    """Generate using Anthropic API."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except ImportError as exc:
        raise GenerationError("Install Anthropic support with: pip install 'readme-ai[anthropic]'") from exc
    except Exception as exc:
        raise GenerationError(f"Anthropic generation failed: {exc}") from exc


def _install_commands(info: RepoInfo) -> list[str]:
    if any(dep.endswith("pyproject.toml") or dep.endswith("setup.py") for dep in info.dependencies):
        return ["python3 -m pip install -e ."]
    if any(dep.endswith("requirements.txt") for dep in info.dependencies):
        return ["python3 -m pip install -r requirements.txt"]
    if any(dep.endswith("package.json") for dep in info.dependencies):
        return ["npm install"]
    if any(dep.endswith("go.mod") for dep in info.dependencies):
        return ["go mod download"]
    if any(dep.endswith("Cargo.toml") for dep in info.dependencies):
        return ["cargo build"]
    return []


def generate_readme_local(info: RepoInfo, repo_path: str, style: str = "standard") -> str:
    """Generate a useful README without an LLM."""
    languages = ", ".join(list(info.languages.keys())[:3]) or "software"
    lines = [
        f"# {info.name}",
        "",
        info.description or f"A {languages} project.",
        "",
    ]

    if style != "minimal":
        lines.extend(["## Features", ""])
        features = []
        if info.entry_points:
            features.append("Detectable application entry points")
        if info.has_tests:
            features.append("Test suite included")
        if info.has_ci:
            features.append("Continuous integration configured")
        if info.has_docker:
            features.append("Docker support")
        if info.has_license:
            features.append("Open source license")
        features.append(f"Written primarily in {languages}")
        lines.extend(f"- {feature}" for feature in features)
        lines.append("")

    lines.extend([
        "## Installation",
        "",
    ])
    if info.python_requires:
        lines.append(f"Requires Python {info.python_requires}")
        lines.append("")
    lines.extend(["```bash", f"git clone https://github.com/user/{info.name}.git", f"cd {info.name}"])
    lines.extend(_install_commands(info))
    lines.extend(["```", ""])

    lines.extend(["## Usage", ""])
    if info.console_scripts:
        lines.append("After installation, the following commands are available:")
        lines.append("")
        lines.extend(f"- `{script}`" for script in info.console_scripts[:5])
        lines.append("")
        lines.extend(["```bash", f"{info.console_scripts[0]} --help", "```", ""])
    elif info.entry_points:
        lines.append("Entry points detected:")
        lines.append("")
        lines.extend(f"- `{entry}`" for entry in info.entry_points[:5])
        lines.append("")
        lines.extend(["```bash", "# Run the relevant entry point for your project", "```", ""])
    else:
        lines.extend(["```bash", "# Add usage examples for this project", "```", ""])

    if style in {"standard", "detailed"} and info.has_tests:
        lines.extend([
            "## Development",
            "",
            "```bash",
            *(_install_commands(info) or ["# Install project dependencies"]),
            "python3 -m pytest",
            "```",
            "",
        ])

    if style == "detailed":
        lines.extend(["## Project Structure", "", "```text", info.dir_tree, "```", ""])

    lines.extend(["## License", "", "MIT" if info.has_license else "See the repository license.", ""])
    return "\n".join(lines)
