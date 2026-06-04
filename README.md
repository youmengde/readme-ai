# readme-ai

AI-powered README generator — analyze a repository and generate a practical README.

<p align="center">
  <img src="https://img.shields.io/github/license/youmengde/readme-ai" />
  <img src="https://img.shields.io/github/actions/workflow/status/youmengde/readme-ai/ci.yml?branch=master" />
</p>

## Features

- Analyze repository structure, languages, entry points, dependency files, tests, CI, Docker, and license
- Generate README files with OpenAI or Anthropic models
- Local template mode that works without an API key or network calls
- `minimal`, `standard`, and `detailed` README styles
- JSON output for repository analysis
- Safe output behavior: existing files require `--force` to overwrite
- `--diff` and `--check` modes for previewing changes and CI integration
- Custom template support with `--template` (`$variable` syntax, zero dependencies)
- `.gitignore` aware scanning

## Install

This project is not published to PyPI yet. Install from source:

```bash
git clone https://github.com/youmengde/readme-ai.git
cd readme-ai
python3 -m pip install -e .
```

For development:

```bash
python3 -m pip install -e ".[dev]"
```

For Anthropic support:

```bash
python3 -m pip install -e ".[anthropic]"
```

## Usage

### Analyze a repository

```bash
readme-ai analyze /path/to/repo
readme-ai analyze . --format json
```

### Generate without an API key

```bash
readme-ai generate . --local
readme-ai generate . --local --style detailed
readme-ai generate . --local --output README.generated.md
```

### Generate with AI

```bash
export OPENAI_API_KEY=...
readme-ai generate . --provider openai --model gpt-4o --yes

export ANTHROPIC_API_KEY=...
readme-ai generate . --provider anthropic --model claude-sonnet-4-20250514 --yes
```

### Write to README.md

Existing files are not overwritten unless you pass `--force`:

```bash
readme-ai generate . --local --output README.md --force
```

### Preview changes or check README freshness

`--diff` shows what would change without writing the file. `--check` exits
non-zero if the existing README does not match the generated content, which
is convenient for CI:

```bash
# Preview the diff between the current README and what would be generated
readme-ai generate . --local --output README.md --diff

# In CI: fail the build when README is out of date
readme-ai generate . --local --output README.md --check
```

### Use a custom template

Provide a template file with `$variable` placeholders. Available variables:
`name`, `description`, `languages`, `has_tests`, `has_ci`, `has_license`,
`has_docker`, `entry_points`, `dependencies`, `console_scripts`,
`python_requires`, `python_deps`, `dir_tree`.

```bash
readme-ai generate . --template my_template.md
```

Example template:

```markdown
# $name

$description

Built with $languages.

## Install

\`\`\`bash
pip install $name
\`\`\`
```

## Privacy

`--local` mode does not call any external service.

AI mode sends repository structure and selected file contents (entry points and dependency manifests) to the selected LLM provider. Do not use AI mode on private or sensitive code unless you are allowed to share that context with the provider.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m ruff check src tests
python3 -m pytest
```

Tests do not call real LLM APIs.

## License

[MIT](LICENSE)
