# uv-demo

[![CI](https://github.com/IA1906AS/miniLMS-G5/actions/workflows/ci.yml/badge.svg)](https://github.com/IA1906AS/miniLMS-G5/actions/workflows/ci.yml)

Dự án mẫu quản lý bằng **uv**, cấu hình sẵn Linter (`ruff`), Type Checker (`mypy`), Unit Test (`pytest`, `pytest-cov`), Quét bảo mật (`pip-audit`) và GitHub Actions CI.

## Yêu cầu
- Python: 3.12
- Quản lý gói: [uv](https://docs.astral.sh/uv/)

## Cài đặt & phát triển

```bash
# Cài đặt toàn bộ môi trường và dependencies
uv sync

# Chạy linter & formatter
uv run ruff check src tests
uv run ruff format src tests

# Kiểm tra kiểu dữ liệu (type check)
uv run mypy src tests

# Chạy kiểm thử đơn vị & đo coverage
uv run pytest

# Quét lỗ hổng bảo mật
uv run pip-audit
```
