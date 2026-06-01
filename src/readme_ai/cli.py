"""CLI entry point for readme-ai."""

from __future__ import annotations

import os
import sys

import click
from rich.console import Console
from rich.panel import Panel

from .analyzer import analyze_repo
from .generator import generate_readme, generate_readme_local

console = Console()


@click.group()
@click.version_option()
def cli():
    """AI-powered README generator — analyze your repo, generate a beautiful README."""
    pass


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--model", "-m", default=None, help="LLM model to use (e.g. gpt-4o, claude-sonnet-4-20250514)")
@click.option("--style", "-s", type=click.Choice(["standard", "minimal", "detailed"]), default="standard", help="README style")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path (default: stdout)")
@click.option("--api-key", envvar="OPENAI_API_KEY", default=None, help="API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY)")
@click.option("--local", "use_local", is_flag=True, help="Generate without LLM (template mode)")
@click.option("--dry-run", is_flag=True, help="Show repo analysis without generating README")
def generate(repo_path: str, model: str | None, style: str, output: str | None, api_key: str | None, use_local: bool, dry_run: bool):
    """Generate a README for a repository.

    \b
    $ readme-ai generate /path/to/repo
    $ readme-ai generate . --model gpt-4o --output README.md
    $ readme-ai generate . --local  # no API key needed
    """
    with console.status("Analyzing repository..."):
        info = analyze_repo(repo_path)

    if dry_run:
        console.print(Panel(
            f"[bold]Name:[/bold] {info.name}\n"
            f"[bold]Description:[/bold] {info.description or 'N/A'}\n"
            f"[bold]Languages:[/bold] {', '.join(f'{k} ({v})' for k, v in list(info.languages.items())[:5])}\n"
            f"[bold]Entry points:[/bold] {', '.join(info.entry_points[:5]) or 'N/A'}\n"
            f"[bold]Has tests:[/bold] {info.has_tests}\n"
            f"[bold]Has CI:[/bold] {info.has_ci}\n"
            f"[bold]Has Docker:[/bold] {info.has_docker}\n"
            f"[bold]Has license:[/bold] {info.has_license}\n"
            f"[bold]Dependencies:[/bold] {', '.join(info.dependencies[:5]) or 'N/A'}",
            title="Repository Analysis",
        ))
        console.print("\n[dim]Directory Structure:[/dim]")
        console.print(info.dir_tree)
        return

    if use_local:
        with console.status("Generating README (template mode)..."):
            content = generate_readme_local(info, repo_path, style=style)
    else:
        has_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not has_key:
            console.print("[yellow]No API key found. Using template mode (--local).[/yellow]")
            console.print("[dim]Set OPENAI_API_KEY or ANTHROPIC_API_KEY for AI-powered generation.[/dim]\n")
            content = generate_readme_local(info, repo_path, style=style)
        else:
            with console.status(f"Generating README with AI ({model or 'auto'})..."):
                content = generate_readme(info, repo_path, style=style, model=model, api_key=api_key)

    if output:
        with open(output, "w") as f:
            f.write(content)
        console.print(f"[green]README written to {output}[/green]")
    else:
        console.print(content)


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
def analyze(repo_path: str):
    """Analyze a repository and show its metadata.

    \b
    $ readme-ai analyze /path/to/repo
    """
    with console.status("Analyzing..."):
        info = analyze_repo(repo_path)

    console.print(Panel(
        f"[bold]Name:[/bold] {info.name}\n"
        f"[bold]Description:[/bold] {info.description or 'N/A'}\n"
        f"[bold]Languages:[/bold] {', '.join(f'{k} ({v})' for k, v in info.languages.items())}\n"
        f"[bold]Files analyzed:[/bold] {len(info.top_files)}\n"
        f"[bold]Entry points:[/bold] {', '.join(info.entry_points) or 'N/A'}\n"
        f"[bold]Dependencies:[/bold] {', '.join(info.dependencies) or 'N/A'}\n"
        f"[bold]Has tests:[/bold] {info.has_tests}\n"
        f"[bold]Has CI:[/bold] {info.has_ci}\n"
        f"[bold]Has Docker:[/bold] {info.has_docker}\n"
        f"[bold]Has license:[/bold] {info.has_license}",
        title=f"Repo Analysis: {info.name}",
    ))


if __name__ == "__main__":
    cli()
