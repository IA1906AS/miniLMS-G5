import random
import time
from collections.abc import Callable
from functools import wraps


def compute_backoff_delay(
    attempt: int,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> float:
    """Tính thời gian chờ theo thuật toán Exponential Backoff kèm Jitter."""
    raw_delay = min(max_delay, base_delay * (backoff_factor ** max(0, attempt)))
    if not jitter:
        return raw_delay
    jitter_offset = random.uniform(0.0, raw_delay * 0.25)
    return min(max_delay, raw_delay + jitter_offset)


def run_with_backoff[R](
    func: Callable[[], R],
    *,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep_fn: Callable[[float], None] = time.sleep,
) -> R:
    """Thực thi hàm với cơ chế tự động thử lại theo Exponential Backoff."""
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise
            delay = compute_backoff_delay(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                jitter=jitter,
            )
            sleep_fn(delay)
    raise RuntimeError("Exponential backoff exhausted") from last_exc


def exponential_backoff[**P, R](
    *,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator áp dụng Exponential Backoff cho các tác vụ I/O hoặc Database."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return run_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions,
            )

        return wrapper

    return decorator
