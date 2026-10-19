# Mini LMS

Dự án LMS nhỏ phục vụ bài tập môn Web Security. Nhóm sử dụng Python 3.12 và
[`uv`](https://docs.astral.sh/uv/) để quản lý môi trường, dependency và chạy ứng dụng.

## Yêu cầu

- Python 3.12
- `uv`

## Bắt đầu

Nếu chưa có `uv`, cài theo hướng dẫn chính thức tại
[docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).

Trong thư mục dự án, đồng bộ môi trường và tạo `uv.lock`:

```powershell
uv sync
```

Chạy ứng dụng ở chế độ phát triển:

```powershell
uv run flask --app minilms.app run --debug
```

Mở http://127.0.0.1:5000 để xem trang khởi đầu.

## Cấu trúc

```text
src/minilms/       Mã nguồn ứng dụng
pyproject.toml     Metadata và dependency của project
uv.lock            Phiên bản dependency đã khóa (được tạo bởi `uv sync`)
.python-version    Phiên bản Python được uv ưu tiên sử dụng
```

Khi thêm dependency, dùng `uv add ten-goi`; khi cần dependency chỉ dùng lúc phát
triển, dùng `uv add --dev ten-goi`. Commit `uv.lock` cùng mã nguồn để hai thành
viên cài cùng một bộ dependency.
