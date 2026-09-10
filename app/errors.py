from enum import Enum
import re

import httpx


# ---------------------------------
# STANDARD ERROR CODES
# ---------------------------------

class ErrorCode(
    str,
    Enum
):

    INVALID_INPUT = "INVALID_INPUT"

    NOT_FOUND = "NOT_FOUND"

    TIMEOUT = "TIMEOUT"

    CONNECTION_ERROR = (
        "CONNECTION_ERROR"
    )

    RATE_LIMITED = "RATE_LIMITED"

    AUTH_ERROR = "AUTH_ERROR"

    CONFIGURATION_ERROR = (
        "CONFIGURATION_ERROR"
    )

    UPSTREAM_UNAVAILABLE = (
        "UPSTREAM_UNAVAILABLE"
    )

    UPSTREAM_ERROR = (
        "UPSTREAM_ERROR"
    )

    UNKNOWN_TOOL = (
        "UNKNOWN_TOOL"
    )

    TOOL_EXECUTION_ERROR = (
        "TOOL_EXECUTION_ERROR"
    )

    INTERNAL_ERROR = (
        "INTERNAL_ERROR"
    )


# ---------------------------------
# RETRYABLE ERROR CODES
# ---------------------------------

RETRYABLE_ERROR_CODES = {
    ErrorCode.TIMEOUT,
    ErrorCode.CONNECTION_ERROR,
    ErrorCode.RATE_LIMITED,
    ErrorCode.UPSTREAM_UNAVAILABLE,
}


def is_retryable_error_code(
    error_code: ErrorCode
) -> bool:

    return (
        error_code
        in RETRYABLE_ERROR_CODES
    )


# ---------------------------------
# HTTP STATUS CLASSIFICATION
# ---------------------------------

def classify_http_status(
    status_code: int
) -> ErrorCode:

    if status_code == 429:

        return (
            ErrorCode.RATE_LIMITED
        )

    if status_code in {
        401,
        403
    }:

        return (
            ErrorCode.AUTH_ERROR
        )

    if status_code == 404:

        return (
            ErrorCode.NOT_FOUND
        )

    if status_code in {
        500,
        502,
        503,
        504
    }:

        return (
            ErrorCode.UPSTREAM_UNAVAILABLE
        )

    return (
        ErrorCode.UPSTREAM_ERROR
    )


# ---------------------------------
# NETWORK ERROR CLASSIFICATION
# ---------------------------------

def classify_request_error(
    error: httpx.RequestError
) -> ErrorCode:

    if isinstance(
        error,
        httpx.TimeoutException
    ):

        return (
            ErrorCode.TIMEOUT
        )

    if isinstance(
        error,
        httpx.ConnectError
    ):

        return (
            ErrorCode.CONNECTION_ERROR
        )

    return (
        ErrorCode.CONNECTION_ERROR
    )


# ---------------------------------
# STANDARD ERROR PAYLOAD
# ---------------------------------

def make_error_result(
    code: ErrorCode,
    message: str,
    service: str | None = None
) -> dict:

    return {
        "ok": False,
        "error": {
            "code": code.value,
            "message": message,
            "service": service,
            "retryable": (
                is_retryable_error_code(
                    code
                )
            )
        }
    }


# ---------------------------------
# LEGACY TOOL ERROR NORMALIZATION
# ---------------------------------

def normalize_tool_error(
    tool_name: str,
    message: str
) -> dict:

    normalized = (
        message
        .strip()
        .lower()
    )

    # -----------------------------
    # CONFIGURATION
    # -----------------------------

    if (
        "not configured"
        in normalized
    ):

        code = (
            ErrorCode.CONFIGURATION_ERROR
        )

    # -----------------------------
    # TIMEOUT
    # -----------------------------

    elif "timed out" in normalized:

        code = ErrorCode.TIMEOUT

    # -----------------------------
    # CONNECTION
    # -----------------------------

    elif (
        "could not connect"
        in normalized
    ):

        code = (
            ErrorCode.CONNECTION_ERROR
        )

    # -----------------------------
    # NOT FOUND
    # -----------------------------

    elif (
        "could not find"
        in normalized
        or
        "not found"
        in normalized
    ):

        code = ErrorCode.NOT_FOUND

    # -----------------------------
    # INVALID INPUT
    # -----------------------------

    elif any(
        phrase in normalized
        for phrase in [
            "cannot be empty",
            "must be valid",
            "division by zero",
            "unsupported calculator",
            "invalid tool arguments"
        ]
    ):

        code = ErrorCode.INVALID_INPUT

    # -----------------------------
    # UNKNOWN TOOL
    # -----------------------------

    elif (
        "unknown tool"
        in normalized
    ):

        code = (
            ErrorCode.UNKNOWN_TOOL
        )

    else:

        # -------------------------
        # HTTP STATUS IN MESSAGE
        # -------------------------

        http_match = re.search(
            r"http\s+(\d{3})",
            normalized
        )

        if http_match:

            status_code = int(
                http_match.group(1)
            )

            code = classify_http_status(
                status_code
            )

        else:

            code = (
                ErrorCode.TOOL_EXECUTION_ERROR
            )

    return make_error_result(
        code=code,
        message=message,
        service=tool_name
    )