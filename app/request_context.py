import re

from contextvars import ContextVar
from uuid import uuid4


# ---------------------------------
# REQUEST ID CONTEXT
# ---------------------------------

_request_id_context = ContextVar(
    "request_id",
    default="-"
)


# Only safe characters are accepted
# from incoming X-Request-ID headers.
REQUEST_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]{1,64}$"
)


def create_request_id() -> str:

    return uuid4().hex[:16]


def normalize_request_id(
    request_id: str | None
) -> str:

    if not request_id:

        return create_request_id()

    request_id = request_id.strip()

    if not REQUEST_ID_PATTERN.fullmatch(
        request_id
    ):

        return create_request_id()

    return request_id


def get_request_id() -> str:

    return _request_id_context.get()


def set_request_id(
    request_id: str
):

    return _request_id_context.set(
        request_id
    )


def reset_request_id(
    token
):

    _request_id_context.reset(
        token
    )