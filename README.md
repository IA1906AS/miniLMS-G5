# uv-demo

[![CI](https://github.com/IA1906AS/miniLMS-G5/actions/workflows/ci.yml/badge.svg)](https://github.com/IA1906AS/miniLMS-G5/actions/workflows/ci.yml)

Dự án mẫu quản lý bằng **uv**, cấu hình sẵn Linter (`ruff`), Type Checker (`mypy`), Unit Test (`pytest`, `pytest-cov`), Quét lỗ hổng phụ thuộc (`pip-audit`), Quét bảo mật mã nguồn SAST (`Semgrep`) và GitHub Actions CI.

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

# Quét lỗ hổng bảo mật thư viện (SCA)
uv run pip-audit

# Quét bảo mật mã nguồn tĩnh (SAST qua Docker nếu chạy local)
docker run --rm -v "${PWD}:/src" semgrep/semgrep semgrep scan --config "p/default" --config "p/security-audit"
```

