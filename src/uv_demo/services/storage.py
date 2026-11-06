import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from uv_demo.config import settings


class StorageService:
    @staticmethod
    def validate_extension(filename: str, allowed_extensions: set[str]) -> str:
        ext = Path(filename).suffix.lower()
        if not ext or ext not in allowed_extensions:
            allowed = ", ".join(sorted(allowed_extensions))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Định dạng tệp '{ext}' không được chấp nhận. Định dạng hợp lệ: {allowed}",
            )
        return ext

    @staticmethod
    async def save_upload_file(
        file: UploadFile, subfolder: str, allowed_extensions: set[str]
    ) -> tuple[str, str]:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Tên tệp không hợp lệ"
            )

        original_filename = Path(file.filename).name  # strip path components
        ext = StorageService.validate_extension(original_filename, allowed_extensions)

        # Generate unique storage filename to completely prevent path traversal
        stored_name = f"{uuid.uuid4().hex}{ext}"
        target_dir = settings.UPLOAD_DIR / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / stored_name

        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE_BYTES:
            max_mb = settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kích thước tệp vượt quá giới hạn cho phép ({max_mb} MB)",
            )

        target_path.write_bytes(content)
        relative_path = f"{subfolder}/{stored_name}"
        return original_filename, relative_path

    @staticmethod
    def get_absolute_path(relative_path: str) -> Path:
        resolved = (settings.UPLOAD_DIR / relative_path).resolve()
        # Security check: ensure resolved path is strictly inside UPLOAD_DIR (prevent path traversal)
        if not str(resolved).startswith(str(settings.UPLOAD_DIR.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Truy cập tệp bất hợp pháp",
            )
        if not resolved.exists() or not resolved.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tệp yêu cầu",
            )
        return resolved


storage_service = StorageService()
