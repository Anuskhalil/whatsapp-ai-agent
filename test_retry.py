import asyncio

import httpx

from app.http_retry import (
    request_with_retry
)


async def test_retryable_503():

    attempt_count = 0

    def handler(
        request: httpx.Request
    ) -> httpx.Response:

        nonlocal attempt_count

        attempt_count += 1

        if attempt_count < 3:

            return httpx.Response(
                status_code=503,
                request=request
            )

        return httpx.Response(
            status_code=200,
            json={
                "status": "ok"
            },
            request=request
        )

    transport = httpx.MockTransport(
        handler
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:

        response = await request_with_retry(
            client=client,
            method="GET",
            url="https://example.com/test",
            service_name="retry_test_503",
            max_attempts=3,
            base_delay=0.01,
            max_delay=0.02
        )

    assert response.status_code == 200
    assert attempt_count == 3

    print(
        "PASS: 503 retried and succeeded"
    )


async def test_nonretryable_401():

    attempt_count = 0

    def handler(
        request: httpx.Request
    ) -> httpx.Response:

        nonlocal attempt_count

        attempt_count += 1

        return httpx.Response(
            status_code=401,
            request=request
        )

    transport = httpx.MockTransport(
        handler
    )

    try:

        async with httpx.AsyncClient(
            transport=transport
        ) as client:

            await request_with_retry(
                client=client,
                method="GET",
                url="https://example.com/test",
                service_name="retry_test_401",
                max_attempts=3,
                base_delay=0.01,
                max_delay=0.02
            )

    except httpx.HTTPStatusError:

        pass

    else:

        raise AssertionError(
            "Expected HTTPStatusError"
        )

    assert attempt_count == 1

    print(
        "PASS: 401 was not retried"
    )


async def test_connection_failure():

    attempt_count = 0

    def handler(
        request: httpx.Request
    ) -> httpx.Response:

        nonlocal attempt_count

        attempt_count += 1

        if attempt_count < 3:

            raise httpx.ConnectError(
                "Temporary connection failure",
                request=request
            )

        return httpx.Response(
            status_code=200,
            json={
                "status": "ok"
            },
            request=request
        )

    transport = httpx.MockTransport(
        handler
    )

    async with httpx.AsyncClient(
        transport=transport
    ) as client:

        response = await request_with_retry(
            client=client,
            method="GET",
            url="https://example.com/test",
            service_name="retry_test_connection",
            max_attempts=3,
            base_delay=0.01,
            max_delay=0.02
        )

    assert response.status_code == 200
    assert attempt_count == 3

    print(
        "PASS: connection error retried "
        "and succeeded"
    )


async def main():

    await test_retryable_503()

    await test_nonretryable_401()

    await test_connection_failure()

    print()
    print(
        "All retry tests passed."
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )