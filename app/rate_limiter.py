import asyncio

from collections import deque
from dataclasses import dataclass
from time import monotonic


# ---------------------------------
# RESULT
# ---------------------------------

@dataclass
class RateLimitResult:

    allowed: bool
    remaining: int
    retry_after_seconds: float


# ---------------------------------
# SLIDING WINDOW RATE LIMITER
# ---------------------------------

class SlidingWindowRateLimiter:

    def __init__(
        self,
        max_requests: int,
        window_seconds: float
    ):

        if max_requests < 1:

            raise ValueError(
                "max_requests must be at least 1"
            )

        if window_seconds <= 0:

            raise ValueError(
                "window_seconds must be greater than 0"
            )

        self.max_requests = (
            max_requests
        )

        self.window_seconds = (
            window_seconds
        )

        self._buckets = {}

        self._lock = (
            asyncio.Lock()
        )

    # ---------------------------------
    # REMOVE EXPIRED ENTRIES
    # ---------------------------------

    def _remove_expired(
        self,
        bucket: deque,
        now: float
    ):

        cutoff = (
            now
            - self.window_seconds
        )

        while (
            bucket
            and
            bucket[0] <= cutoff
        ):

            bucket.popleft()

    # ---------------------------------
    # OCCASIONAL GLOBAL CLEANUP
    # ---------------------------------

    def _cleanup_stale_buckets(
        self,
        now: float
    ):

        if len(
            self._buckets
        ) < 1000:

            return

        stale_keys = []

        for (
            key,
            bucket
        ) in self._buckets.items():

            self._remove_expired(
                bucket,
                now
            )

            if not bucket:

                stale_keys.append(
                    key
                )

        for key in stale_keys:

            self._buckets.pop(
                key,
                None
            )

    # ---------------------------------
    # CHECK LIMIT
    # ---------------------------------

    async def check(
        self,
        key: str
    ) -> RateLimitResult:

        if not key:

            raise ValueError(
                "Rate-limit key cannot be empty"
            )

        async with self._lock:

            now = monotonic()

            self._cleanup_stale_buckets(
                now
            )

            bucket = (
                self._buckets.setdefault(
                    key,
                    deque()
                )
            )

            self._remove_expired(
                bucket,
                now
            )

            # ---------------------------------
            # BLOCK
            # ---------------------------------

            if (
                len(bucket)
                >= self.max_requests
            ):

                oldest_request = (
                    bucket[0]
                )

                retry_after = (
                    self.window_seconds
                    - (
                        now
                        - oldest_request
                    )
                )

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=max(
                        retry_after,
                        0.0
                    )
                )

            # ---------------------------------
            # ALLOW
            # ---------------------------------

            bucket.append(
                now
            )

            remaining = (
                self.max_requests
                - len(bucket)
            )

            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after_seconds=0.0
            )

    # ---------------------------------
    # TEST / MAINTENANCE HELPER
    # ---------------------------------

    async def clear(
        self
    ):

        async with self._lock:

            self._buckets.clear()