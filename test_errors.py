import asyncio

from app.errors import (
    ErrorCode,
    classify_http_status,
    normalize_tool_error
)

from app.tools import (
    execute_tool
)


def test_http_classification():

    assert (
        classify_http_status(401)
        == ErrorCode.AUTH_ERROR
    )

    assert (
        classify_http_status(403)
        == ErrorCode.AUTH_ERROR
    )

    assert (
        classify_http_status(404)
        == ErrorCode.NOT_FOUND
    )

    assert (
        classify_http_status(429)
        == ErrorCode.RATE_LIMITED
    )

    assert (
        classify_http_status(503)
        == ErrorCode.UPSTREAM_UNAVAILABLE
    )

    print(
        "PASS: HTTP status classification"
    )


def test_tool_normalization():

    timeout_error = (
        normalize_tool_error(
            "web_search",
            (
                "Web search service "
                "timed out."
            )
        )
    )

    assert (
        timeout_error[
            "error"
        ]["code"]
        == "TIMEOUT"
    )

    assert (
        timeout_error[
            "error"
        ]["retryable"]
        is True
    )

    location_error = (
        normalize_tool_error(
            "get_weather",
            (
                "Could not find "
                "location: Test City"
            )
        )
    )

    assert (
        location_error[
            "error"
        ]["code"]
        == "NOT_FOUND"
    )

    print(
        "PASS: Tool error normalization"
    )


async def test_execute_tool():

    divide_zero = (
        await execute_tool(
            "calculator",
            {
                "operation": "divide",
                "a": 10,
                "b": 0
            }
        )
    )

    assert (
        divide_zero["ok"]
        is False
    )

    assert (
        divide_zero[
            "error"
        ]["code"]
        == "INVALID_INPUT"
    )

    unknown_tool = (
        await execute_tool(
            "does_not_exist",
            {}
        )
    )

    assert (
        unknown_tool["ok"]
        is False
    )

    assert (
        unknown_tool[
            "error"
        ]["code"]
        == "UNKNOWN_TOOL"
    )

    print(
        "PASS: execute_tool standardized errors"
    )


async def main():

    test_http_classification()

    test_tool_normalization()

    await test_execute_tool()

    print()
    print(
        "All error classification "
        "tests passed."
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )