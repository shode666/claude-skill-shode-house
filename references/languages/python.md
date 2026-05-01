# Python — Best Practices

> **Use cases**: AI/ML, data, automation, backend, scripting, scientific
> **Why**: PoC เร็ว, AI/ML ecosystem ใหญ่สุด

## Setup
- **Version**: 3.12+ (3.13 ถ้า lib รองรับ)
- **PM**: **uv** (Rust-based, 10x pip+poetry) — `uv pip` / `uv venv` / `uv sync`
- **Lint+Format**: **ruff** (Rust-based, replace black+flake8+isort+pylint)
- **Type**: **mypy --strict** หรือ pyright (Microsoft)
- **Project**: `pyproject.toml` (PEP 621)

## Type Discipline
- Type hint ทุก function signature (return + params)
- `from __future__ import annotations` (lazy eval)
- `TypedDict`, `Protocol`, `Self`, `Annotated`, `ParamSpec`
- `Literal` สำหรับ enum-like
- Generic via `class Foo[T]:` (PEP 695, Py 3.12+)
- ห้าม `Any` — ใช้ `object`/`Unknown`

## Backend Stack
- **FastAPI** (default — async + Pydantic + OpenAPI auto-gen)
- **Django 5+** (full-stack, ORM rich, admin)
- **Litestar** (modern alt, faster than FastAPI สำหรับ heavy use)
- **Flask** (micro, classic)

## Data / ORM
- **SQLAlchemy 2.0** async (typed `Mapped[T]`)
- **Alembic** for migration
- **Pydantic v2** (Rust-based, 10x v1)
- **polars** > pandas สำหรับ large data (Rust, lazy eval)

## Testing
- **pytest** (default), `pytest-asyncio`, `pytest-cov`, `hypothesis` (property-based)
- Fixture > setUp/tearDown
- `conftest.py` shared fixture
- Parametrize > loop in test

## AI / ML
- **PyTorch** > TensorFlow (research+prod)
- **transformers** (HuggingFace), **vLLM** (inference)
- **LangChain** (caution), **LlamaIndex**, **DSPy** (programmatic)
- **Pydantic AI** (typed LLM)
- **Ray** (distributed compute)

## Concurrency
- async/await (default)
- `asyncio.TaskGroup` (Py 3.11+) > `asyncio.gather`
- `concurrent.futures` for CPU-bound
- GIL-aware (multiprocessing for CPU)
- **Free-threaded Py 3.13** (no-GIL build, experimental)

## Best Practices
- File ≤ 300 lines, function ≤ 30
- Pathlib > os.path
- f-string > %/format
- Dataclass / Pydantic > dict (typed)
- Context manager (`with`) สำหรับ resource
- Walrus `:=` (สำหรับ readability)
- `match` statement (Py 3.10+) สำหรับ pattern

## ห้าม
- Mutable default arg (`def f(x=[]):`)
- `eval`, `exec` raw
- `import *`
- Bare `except:` (use `except Exception:`)
- Global mutable state
- `time.sleep` ใน async (use `asyncio.sleep`)
- Logging via `print` (use `logging`)
- `requirements.txt` legacy (use `pyproject.toml`)
