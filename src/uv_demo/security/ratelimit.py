import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from uv_demo.services.backoff import compute_backoff_delay


class InMemoryRateLimiter:
    """Bộ giới hạn tốc độ kết hợp Exponential Backoff chống Brute-Force.

    Khi số lần thử vượt ngưỡng cho phép, thời gian chờ (Retry-After) sẽ tăng
    theo cấp số nhân (Exponential Backoff) tương ứng với số lần vi phạm liên tiếp.
    """

    def __init__(self, max_requests: int = 15, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > window_start
        ]

        attempts = len(self._requests[client_ip])
        if attempts >= self.max_requests:
            excess = attempts - self.max_requests
            retry_after = int(
                compute_backoff_delay(
                    attempt=excess,
                    base_delay=2.0,
                    max_delay=float(self.window_seconds),
                    backoff_factor=2.0,
                    jitter=False,
                )
            )
            self._requests[client_ip].append(now)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Bạn đã thực hiện quá nhiều yêu cầu xác thực. "
                    f"Vui lòng đợi {retry_after} giây (Exponential Backoff)."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        self._requests[client_ip].append(now)


login_rate_limiter = InMemoryRateLimiter(max_requests=15, window_seconds=60)
