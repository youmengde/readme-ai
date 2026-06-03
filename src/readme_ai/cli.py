"""CLI entry point for readme-ai."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from .analyzer import analyze_repo, repo_info_to_dict
from .differ import is_in_sync, read_existing, render_diff
from .generator import GenerationError, generate_readme, generate_readme_local

console = Console()


@click.group()
@click.version_option()
def cli():
    """AI-powered README generator — analyze your repo, generate a beautiful README."""
    pass


def _analysis_panel(info) -> Panel:
    return Panel(
        f"[bold]Name:[/bold] {info.name}\n"
        f"[bold]Description:[/bold] {info.description or 'N/A'}\n"
        f"[bold]Languages:[/bold] {', '.join(f'{k} ({v})' for k, v in list(info.languages.items())[:5])}\n"
        f"[bold]Entry points:[/bold] {', '.join(info.entry_points[:5]) or 'N/A'}\n"
        f"[bold]Dependency files:[/bold] {', '.join(info.dependencies[:5]) or 'N/A'}\n"
        f"[bold]Has tests:[/bold] {info.has_tests}\n"
        f"[bold]Has CI:[/bold] {info.has_ci}\n"
        f"[bold]Has Docker:[/bold] {info.has_docker}\n"
        f"[bold]Has license:[/bold] {info.has_license}",
        title="Repository Analysis",
    )


def _write_output(path: str, content: str, force: bool):
    output = Path(path)
    if output.exists() and not force:
        raise click.ClickException(f"{path} already exists. Use --force to overwrite.")
    output.write_text(content, encoding="utf-8")
    console.print(f"[green]README written to {path}[/green]")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--model", "-m", default=None, help="LLM model to use (e.g. gpt-4o, claude-sonnet-4-20250514)")
@click.option("--provider", type=click.Choice(["auto", "openai", "anthropic"]), default="auto", help="LLM provider")
@click.option("--style", "-s", type=click.Choice(["standard", "minimal", "detailed"]), default="standard", help="README style")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path (default: stdout)")
@click.option("--api-key", default=None, help="API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY)")
@click.option("--local", "use_local", is_flag=True, help="Generate without LLM (template mode)")
@click.option("--dry-run", is_flag=True, help="Show repo analysis without generating README")
@click.option("--force", is_flag=True, help="Overwrite output file if it exists")
@click.option("--yes", "assume_yes", is_flag=True, help="Skip AI privacy confirmation")
@click.option("--diff", "show_diff", is_flag=True, help="Show diff against existing --output file instead of writing")
@click.option("--check", is_flag=True, help="Exit non-zero if generated README differs from existing --output file")
def generate(
    repo_path: str,
    model: str | None,
    provider: str,
    style: str,
    output: str | None,
    api_key: str | None,
    use_local: bool,
    dry_run: bool,
    force: bool,
    assume_yes: bool,
    show_diff: bool,
    check: bool,
):
    """Generate a README for a repository.

    \b
    $ readme-ai generate /path/to/repo
    $ readme-ai generate . --local
    $ readme-ai generate . --output README.md --force
    $ readme-ai generate . --local --output README.md --diff
    $ readme-ai generate . --local --output README.md --check
    """
    if (show_diff or check) and not output:
        raise click.ClickException("--diff and --check require --output to point at the existing README path.")
    try:
        with console.status("Analyzing repository..."):
            info = analyze_repo(repo_path)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    if dry_run:
        console.print(_analysis_panel(info))
        console.print("\n[dim]Directory Structure:[/dim]")
        console.print(info.dir_tree)
        return

    has_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if use_local or not has_key:
        if not use_local:
            console.print("[yellow]No API key found. Using template mode (--local).[/yellow]")
        content = generate_readme_local(info, repo_path, style=style)
    else:
        if not assume_yes:
            click.confirm(
                "AI mode sends repository structure and selected file contents to the selected LLM provider. Continue?",
                abort=True,
            )
        try:
            with console.status(f"Generating README with AI ({model or provider})..."):
                content = generate_readme(
                    info,
                    repo_path,
                    style=style,
                    model=model,
                    api_key=api_key,
                    provider=provider,
                )
        except GenerationError as exc:
            raise click.ClickException(str(exc)) from exc

    if check or show_diff:
        existing = read_existing(output)
        if check:
            if is_in_sync(existing, content):
                console.print(f"[green]{output} is up to date.[/green]")
                return
            console.print(f"[red]{output} is out of date.[/red]")
            diff = render_diff(existing, content, existing_label=output, generated_label=f"{output} (generated)")
            if diff:
                click.echo(diff)
            raise click.exceptions.Exit(1)
        # show_diff
        diff = render_diff(existing, content, existing_label=output, generated_label=f"{output} (generated)")
        if not diff:
            console.print(f"[green]{output} matches the generated content. No changes.[/green]")
        else:
            click.echo(diff)
        return

    if output:
        _write_output(output, content, force=force)
    else:
        console.print(content)


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("-f", "--format", "fmt", type=click.Choice(["table", "json"]), default="table", help="Output format")
def analyze(repo_path: str, fmt: str):
    """Analyze a repository and show its metadata.

    \b
    $ readme-ai analyze /path/to/repo
    $ readme-ai analyze . --format json
    """
    try:
        with console.status("Analyzing..."):
            info = analyze_repo(repo_path)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    if fmt == "json":
        click.echo(json.dumps(repo_info_to_dict(info), ensure_ascii=False, indent=2))
        return

    console.print(_analysis_panel(info))


if __name__ == "__main__":
    cli()
