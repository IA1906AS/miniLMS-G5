import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Bộ giới hạn tốc độ (Rate Limiter) dạng sliding-window.

    Bảo vệ các endpoint nhạy cảm như Đăng nhập (/api/auth/login) khỏi các cuộc tấn
    công dò mật khẩu (Brute-Force), Credential Stuffing và DDoS.
    """

    def __init__(self, max_requests: int = 15, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        # Loại bỏ các mốc thời gian ngoài cửa sổ trượt
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > window_start
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bạn đã thực hiện quá nhiều yêu cầu xác thực trong thời gian ngắn. Vui lòng đợi 1 phút.",
            )

        self._requests[client_ip].append(now)


# Áp dụng cho API đăng nhập: tối đa 15 lần trong 60 giây cho mỗi IP
login_rate_limiter = InMemoryRateLimiter(max_requests=15, window_seconds=60)
