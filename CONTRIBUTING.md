# Contributing

Thanks for helping improve readme-ai.

## Setup

```bash
git clone https://github.com/youmengde/readme-ai.git
cd readme-ai
python3 -m pip install -e ".[dev]"
```

## Checks

```bash
python3 -m ruff check src tests
python3 -m pytest
```

## Testing rules

- Do not call real OpenAI or Anthropic APIs in tests.
- Use temporary repositories created with `tmp_path` for analyzer tests.
- Keep generated README output deterministic in local mode.

## Pull requests

Please include:

- A short explanation of the change
- Tests for behavior changes
- README updates if user-facing commands change
