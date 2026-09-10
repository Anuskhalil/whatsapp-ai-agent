import asyncio

from app.rate_limiter import (
    SlidingWindowRateLimiter
)


async def test_basic_limit():

    limiter = (
        SlidingWindowRateLimiter(
            max_requests=3,
            window_seconds=0.2
        )
    )

    result_1 = await limiter.check(
        "user_a"
    )

    result_2 = await limiter.check(
        "user_a"
    )

    result_3 = await limiter.check(
        "user_a"
    )

    result_4 = await limiter.check(
        "user_a"
    )

    assert result_1.allowed is True

    assert result_2.allowed is True

    assert result_3.allowed is True

    assert result_4.allowed is False

    assert (
        result_4.retry_after_seconds
        > 0
    )

    print(
        "PASS: limit blocks "
        "excess requests"
    )


async def test_window_reset():

    limiter = (
        SlidingWindowRateLimiter(
            max_requests=2,
            window_seconds=0.2
        )
    )

    await limiter.check(
        "user_a"
    )

    await limiter.check(
        "user_a"
    )

    blocked = await limiter.check(
        "user_a"
    )

    assert blocked.allowed is False

    await asyncio.sleep(
        0.25
    )

    allowed_again = (
        await limiter.check(
            "user_a"
        )
    )

    assert (
        allowed_again.allowed
        is True
    )

    print(
        "PASS: user allowed "
        "after window expires"
    )


async def test_user_isolation():

    limiter = (
        SlidingWindowRateLimiter(
            max_requests=1,
            window_seconds=1
        )
    )

    user_a_1 = await limiter.check(
        "user_a"
    )

    user_a_2 = await limiter.check(
        "user_a"
    )

    user_b_1 = await limiter.check(
        "user_b"
    )

    assert (
        user_a_1.allowed
        is True
    )

    assert (
        user_a_2.allowed
        is False
    )

    assert (
        user_b_1.allowed
        is True
    )

    print(
        "PASS: rate limits "
        "are isolated by user"
    )


async def test_concurrency():

    limiter = (
        SlidingWindowRateLimiter(
            max_requests=3,
            window_seconds=1
        )
    )

    results = await asyncio.gather(
        *[
            limiter.check(
                "concurrent_user"
            )
            for _ in range(10)
        ]
    )

    allowed_count = sum(
        1
        for result in results
        if result.allowed
    )

    blocked_count = sum(
        1
        for result in results
        if not result.allowed
    )

    assert allowed_count == 3

    assert blocked_count == 7

    print(
        "PASS: concurrent requests "
        "cannot bypass limit"
    )


async def main():

    await test_basic_limit()

    await test_window_reset()

    await test_user_isolation()

    await test_concurrency()

    print()

    print(
        "All rate-limit tests passed."
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )