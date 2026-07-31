"""Bounded retry with an explicit deterministic fallback."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryOutcome(Generic[T]):
    value: T
    attempts: int
    fallback_used: bool
    errors: tuple[str, ...]


def execute_with_retry(
    operation: Callable[[], T],
    fallback: Callable[[Exception], T],
    *,
    max_attempts: int = 2,
) -> RetryOutcome[T]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    errors: list[str] = []
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return RetryOutcome(operation(), attempt, False, tuple(errors))
        except Exception as exc:
            last_error = exc
            errors.append(f"{type(exc).__name__}: {exc}")
    assert last_error is not None
    return RetryOutcome(
        fallback(last_error),
        max_attempts,
        True,
        tuple(errors),
    )

