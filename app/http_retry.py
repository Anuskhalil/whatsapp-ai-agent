import asyncio

from time import perf_counter

import httpx

from app.errors import (
    classify_http_status,
    classify_request_error
)

from app.logging_config import (
    get_logger
)


logger = get_logger(
    "http"
)


RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504
}


def elapsed_ms(
    start_time: float
) -> float:

    return (
        perf_counter() - start_time
    ) * 1000


def calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float
) -> float:

    delay = (
        base_delay
        * (2 ** (attempt - 1))
    )

    return min(
        delay,
        max_delay
    )


def get_retry_after(
    response: httpx.Response
) -> float | None:

    value = response.headers.get(
        "Retry-After"
    )

    if not value:

        return None

    try:

        retry_after = float(
            value
        )

    except ValueError:

        return None

    if retry_after < 0:

        return None

    return min(
        retry_after,
        10.0
    )


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    service_name: str,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 2.0,
    **request_kwargs
) -> httpx.Response:

    if max_attempts < 1:

        raise ValueError(
            "max_attempts must be at least 1"
        )

    for attempt in range(
        1,
        max_attempts + 1
    ):

        attempt_start = perf_counter()

        try:

            response = await client.request(
                method=method,
                url=url,
                **request_kwargs
            )

            status_code = (
                response.status_code
            )

            # ---------------------------------
            # RETRYABLE HTTP STATUS
            # ---------------------------------

            if (
                status_code
                in RETRYABLE_STATUS_CODES
                and
                attempt < max_attempts
            ):

                error_code = (
                    classify_http_status(
                        status_code
                    )
                )

                retry_after = (
                    get_retry_after(
                        response
                    )
                )

                if retry_after is None:

                    delay = calculate_delay(
                        attempt=attempt,
                        base_delay=base_delay,
                        max_delay=max_delay
                    )

                else:

                    delay = retry_after

                logger.warning(
                    "external_request_retry "
                    "service=%s "
                    "error_code=%s "
                    "attempt=%s/%s "
                    "status=%s "
                    "delay_s=%.2f "
                    "latency_ms=%.2f",
                    service_name,
                    error_code.value,
                    attempt,
                    max_attempts,
                    status_code,
                    delay,
                    elapsed_ms(
                        attempt_start
                    )
                )

                await asyncio.sleep(
                    delay
                )

                continue

            # This raises for:
            # - final retryable failure
            # - immediate permanent failure
            response.raise_for_status()

            logger.info(
                "external_request_succeeded "
                "service=%s "
                "attempt=%s/%s "
                "status=%s "
                "latency_ms=%.2f",
                service_name,
                attempt,
                max_attempts,
                status_code,
                elapsed_ms(
                    attempt_start
                )
            )

            return response

        # ---------------------------------
        # HTTP FAILURE
        # ---------------------------------

        except httpx.HTTPStatusError as e:

            status_code = (
                e.response.status_code
            )

            error_code = (
                classify_http_status(
                    status_code
                )
            )

            if (
                status_code
                in RETRYABLE_STATUS_CODES
            ):

                logger.error(
                    "external_request_failed "
                    "service=%s "
                    "error_code=%s "
                    "attempt=%s/%s "
                    "status=%s "
                    "latency_ms=%.2f",
                    service_name,
                    error_code.value,
                    attempt,
                    max_attempts,
                    status_code,
                    elapsed_ms(
                        attempt_start
                    )
                )

            else:

                logger.error(
                    "external_request_nonretryable "
                    "service=%s "
                    "error_code=%s "
                    "status=%s "
                    "latency_ms=%.2f",
                    service_name,
                    error_code.value,
                    status_code,
                    elapsed_ms(
                        attempt_start
                    )
                )

            raise

        # ---------------------------------
        # CONNECTION / TIMEOUT FAILURE
        # ---------------------------------

        except httpx.RequestError as e:

            error_code = (
                classify_request_error(
                    e
                )
            )

            if attempt >= max_attempts:

                logger.error(
                    "external_request_failed "
                    "service=%s "
                    "error_code=%s "
                    "attempt=%s/%s "
                    "error_type=%s "
                    "latency_ms=%.2f",
                    service_name,
                    error_code.value,
                    attempt,
                    max_attempts,
                    type(e).__name__,
                    elapsed_ms(
                        attempt_start
                    )
                )

                raise

            delay = calculate_delay(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=max_delay
            )

            logger.warning(
                "external_request_retry "
                "service=%s "
                "error_code=%s "
                "attempt=%s/%s "
                "error_type=%s "
                "delay_s=%.2f "
                "latency_ms=%.2f",
                service_name,
                error_code.value,
                attempt,
                max_attempts,
                type(e).__name__,
                delay,
                elapsed_ms(
                    attempt_start
                )
            )

            await asyncio.sleep(
                delay
            )

    raise RuntimeError(
        "Retry loop ended unexpectedly."
    )