# thrustly

Typed-first Python web framework for fast, stable APIs.

## Installation

Install using pip:

```bash
pip install thrustly
```

Or using uv (recommended):

```bash
uv add thrustly
```

## Quick Start

```python
import thrustly

print(thrustly.__version__)
```

## Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for package management

### Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/ritwiktiwari/thrustly.git
cd thrustly
uv sync --group dev
```

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run ty check
```

### Prek Hooks

Install prek hooks:

```bash
prek install
```

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](https://github.com/ritwiktiwari/thrustly/blob/main/LICENSE) file for details.
