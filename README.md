# thrustly

[![CI](https://github.com/ritwiktiwari/thrustly/actions/workflows/ci.yml/badge.svg)](https://github.com/ritwiktiwari/thrustly/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/thrustly.svg)](https://badge.fury.io/py/thrustly)
[![codecov](https://codecov.io/gh/ritwiktiwari/thrustly/branch/main/graph/badge.svg)](https://codecov.io/gh/ritwiktiwari/thrustly)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/badge/type--checked-ty-blue?labelColor=orange)](https://github.com/astral-sh/ty)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-yellow.svg)](https://github.com/ritwiktiwari/thrustly/blob/main/LICENSE)

Typed-first Python web framework for fast, stable APIs.

## Features

- Fast and modern Python toolchain using Astral's tools (uv, ruff, ty)
- Type-safe with full type annotations
- Comprehensive documentation with MkDocs — [View Docs](https://ritwiktiwari.github.io/thrustly/)

## Installation

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

```bash
git clone https://github.com/ritwiktiwari/thrustly.git
cd thrustly
make install
```

### Running Tests

```bash
make test

# With coverage
make test-cov

# Across all Python versions
make test-matrix
```

### Code Quality

```bash
# Run all checks (lint, format, type-check)
make verify

# Auto-fix lint and format issues
make fix
```

### Prek

```bash
prek install
prek run --all-files
```

### Documentation

```bash
make docs-serve
```

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.
