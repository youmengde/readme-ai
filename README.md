# readme-ai

AI-powered README generator — analyze your repo, generate a beautiful README.

<p align="center">
  <img src="https://img.shields.io/pypi/v/readme-ai" />
  <img src="https://img.shields.io/pypi/pyversions/readme-ai" />
  <img src="https://img.shields.io/github/license/youmengde/readme-ai" />
</p>

## Features

- **Smart repo analysis** — automatically detects languages, entry points, dependencies, CI/CD, Docker, and more
- **AI-powered generation** — uses OpenAI or Anthropic to write high-quality READMEs
- **Template fallback** — works without an API key using built-in templates
- **Multiple styles** — standard, minimal, or detailed output
- **.gitignore aware** — respects your ignore patterns
- **Zero config** — just point it at a repo and go

## Install

```bash
pip install readme-ai
```

For Anthropic support:
```bash
pip install "readme-ai[anthropic]"
```

## Usage

### Generate a README

```bash
# AI-powered (requires OPENAI_API_KEY or ANTHROPIC_API_KEY)
readme-ai generate /path/to/repo

# Save to file
readme-ai generate . --output README.md

# Use Claude
readme-ai generate . --model claude-sonnet-4-20250514

# Template mode (no API key needed)
readme-ai generate . --local
```

### Analyze a repo

```bash
readme-ai analyze /path/to/repo
```

### Dry run (analysis only)

```bash
readme-ai generate . --dry-run
```

## How It Works

1. **Scan** — walks your repo, detecting languages, structure, and metadata
2. **Extract** — reads key files (entry points, dependency manifests) for context
3. **Generate** — sends structured context to an LLM which produces a polished README
4. **Output** — writes to file or stdout

## Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key (auto-detected) |

## Development

```bash
git clone https://github.com/youmengde/readme-ai.git
cd readme-ai
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
