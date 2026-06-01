"""LLM-backed README generation."""

from __future__ import annotations

import os

from .analyzer import RepoInfo, build_context

SYSTEM_PROMPT = """You are an expert technical writer who generates high-quality GitHub README files.
Generate a complete, well-structured README.md in Markdown. Follow these rules:

1. Start with a clear project name as H1 and a one-line description
2. Add badge placeholders (PyPI version, license, etc.) where appropriate
3. Include these sections as relevant:
   - Features (bullet list)
   - Installation (with code blocks)
   - Usage (with realistic examples and code blocks)
   - Configuration / Options (if applicable)
   - Development (how to set up dev environment)
   - License
4. Use realistic example commands and output based on the repo's actual structure
5. Keep it concise — no filler, no buzzwords
6. Use proper Markdown formatting: code blocks with language tags, tables where appropriate
7. Do NOT include placeholder text like "Add description here" — write actual content
8. If the project has tests, CI, or Docker, mention them
9. Output ONLY the README content, no explanations outside the Markdown
"""

USER_PROMPT_TEMPLATE = """Generate a README.md for this repository:

{context}"""


def generate_readme(
    info: RepoInfo,
    repo_path: str,
    style: str = "standard",
    model: str | None = None,
    api_key: str | None = None,
) -> str:
    """Generate a README using an LLM.

    Supports OpenAI and Anthropic backends.
    """
    context = build_context(info, repo_path)

    # Determine provider
    provider = _detect_provider(model, api_key)

    if provider == "anthropic":
        return _generate_anthropic(context, model or "claude-sonnet-4-20250514", api_key)
    else:
        return _generate_openai(context, model or "gpt-4o", api_key)


def _detect_provider(model: str | None, api_key: str | None) -> str:
    """Detect which LLM provider to use."""
    if model and model.startswith("claude"):
        return "anthropic"
    if os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return "anthropic"
    return "openai"


def _generate_openai(context: str, model: str, api_key: str | None) -> str:
    """Generate using OpenAI API."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(context=context)},
        ],
        temperature=0.4,
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


def _generate_anthropic(context: str, model: str, api_key: str | None) -> str:
    """Generate using Anthropic API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("Install anthropic package: pip install readme-ai[anthropic]")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(context=context)},
        ],
    )
    return response.content[0].text


def generate_readme_local(info: RepoInfo, repo_path: str, style: str = "standard") -> str:
    """Generate a basic README without an LLM (fallback/template mode)."""
    lines = [
        f"# {info.name}",
        "",
        info.description or "A software project.",
        "",
        "## Features",
        "",
    ]

    # Add features based on what we detected
    if info.has_tests:
        lines.append("- Tested codebase")
    if info.has_ci:
        lines.append("- CI/CD pipeline")
    if info.has_docker:
        lines.append("- Docker support")
    if info.has_license:
        lines.append("- Open source license")

    lines.extend([
        f"- Written in {', '.join(list(info.languages.keys())[:3])}",
        "",
        "## Installation",
        "",
        "```bash",
        f"git clone https://github.com/user/{info.name}.git",
        f"cd {info.name}",
        "```",
        "",
    ])

    if info.dependencies:
        dep = info.dependencies[0]
        if "requirements.txt" in dep:
            lines.extend([
                "```bash",
                "pip install -r requirements.txt",
                "```",
                "",
            ])
        elif "package.json" in dep:
            lines.extend([
                "```bash",
                "npm install",
                "```",
                "",
            ])

    lines.extend([
        "## Usage",
        "",
        "See documentation for usage details.",
        "",
    ])

    if info.has_tests:
        lines.extend([
            "## Development",
            "",
            "```bash",
            "pip install -e .",
            "pytest",
            "```",
            "",
        ])

    lines.extend([
        "## License",
        "",
        "MIT" if info.has_license else "See LICENSE file.",
        "",
    ])

    return "\n".join(lines)
