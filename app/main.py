import asyncio
import hmac

from contextlib import (
    asynccontextmanager
)

from math import ceil
from time import perf_counter

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request
)

from app.whatsapp_worker import (
    whatsapp_job_worker
)

from fastapi.responses import (
    JSONResponse,
    Response
)

from pydantic import (
    BaseModel,
    Field
)

from twilio.twiml.messaging_response import (
    MessagingResponse
)

from app.agent import (
    run_agent
)

from app.config import (
    APP_NAME,
    APP_VERSION,
    ENVIRONMENT,
    MAX_MESSAGE_CHARACTERS,
    API_RATE_LIMIT_REQUESTS,
    API_RATE_LIMIT_WINDOW_SECONDS,
    WHATSAPP_WORKER_SHUTDOWN_TIMEOUT_SECONDS,
    WHATSAPP_RATE_LIMIT_REQUESTS,
    WHATSAPP_RATE_LIMIT_WINDOW_SECONDS,
    ASK_API_KEY,
    get_config_warnings,
    safe_config_snapshot
)

from app.health import (
    get_readiness_status
)

from app.logging_config import (
    setup_logging,
    get_logger
)

from app.memory import (
    initialize_database
)

from app.rate_limiter import (
    SlidingWindowRateLimiter
)

from app.request_context import (
    normalize_request_id,
    get_request_id,
    set_request_id,
    reset_request_id
)

from app.twilio_security import (
    verify_twilio_signature
)

from app.job_store import (
    enqueue_whatsapp_job,
    initialize_job_store,
    recover_incomplete_whatsapp_jobs
)


# ---------------------------------
# HELPERS
# ---------------------------------

def elapsed_ms(
    start_time: float
) -> float:

    return (
        perf_counter()
        - start_time
    ) * 1000


def safe_suffix(
    value: str
) -> str:

    if not value:

        return "-"

    return value[-4:]


# ---------------------------------
# LOGGING
# ---------------------------------

setup_logging()

logger = get_logger(
    "main"
)


# ---------------------------------
# RATE LIMITERS
# ---------------------------------

api_rate_limiter = (
    SlidingWindowRateLimiter(
        max_requests=(
            API_RATE_LIMIT_REQUESTS
        ),
        window_seconds=(
            API_RATE_LIMIT_WINDOW_SECONDS
        )
    )
)

whatsapp_rate_limiter = (
    SlidingWindowRateLimiter(
        max_requests=(
            WHATSAPP_RATE_LIMIT_REQUESTS
        ),
        window_seconds=(
            WHATSAPP_RATE_LIMIT_WINDOW_SECONDS
        )
    )
)


# ---------------------------------
# APPLICATION LIFESPAN
# ---------------------------------

@asynccontextmanager
async def lifespan(
    app: FastAPI
):

    # ---------------------------------
    # DATABASES
    # ---------------------------------

    initialize_database()

    initialize_job_store()

    recovered_jobs = (
        recover_incomplete_whatsapp_jobs()
    )

    # ---------------------------------
    # DURABLE WHATSAPP WORKER
    # ---------------------------------

    worker_stop_event = (
        asyncio.Event()
    )

    worker_task = (
        asyncio.create_task(
            whatsapp_job_worker(
                worker_stop_event
            )
        )
    )

    logger.info(
        "application_startup "
        "recovered_whatsapp_jobs=%s "
        "config=%s",
        recovered_jobs,
        safe_config_snapshot()
    )

    for warning in (
        get_config_warnings()
    ):

        logger.warning(
            "configuration_warning "
            "message=%s",
            warning
        )

    try:

        yield

    finally:

        # ---------------------------------
        # GRACEFUL WORKER SHUTDOWN
        # ---------------------------------

        worker_stop_event.set()

        try:

            await asyncio.wait_for(
                worker_task,
                timeout=(
                    WHATSAPP_WORKER_SHUTDOWN_TIMEOUT_SECONDS
                )
            )

        except TimeoutError:

            logger.warning(
                "whatsapp_worker_shutdown_timeout"
            )

            worker_task.cancel()

            try:

                await worker_task

            except asyncio.CancelledError:

                pass

        logger.info(
            "application_shutdown"
        )

    initialize_database()

    logger.info(
        "application_startup "
        "config=%s",
        safe_config_snapshot()
    )

    for warning in (
        get_config_warnings()
    ):

        logger.warning(
            "configuration_warning "
            "message=%s",
            warning
        )

    yield

    logger.info(
        "application_shutdown"
    )


# ---------------------------------
# FASTAPI
# ---------------------------------

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan
)


# ---------------------------------
# REQUEST TRACING
# ---------------------------------

@app.middleware("http")
async def request_tracing_middleware(
    request: Request,
    call_next
):

    request_start = (
        perf_counter()
    )

    incoming_request_id = (
        request.headers.get(
            "X-Request-ID"
        )
    )

    request_id = (
        normalize_request_id(
            incoming_request_id
        )
    )

    request_token = (
        set_request_id(
            request_id
        )
    )

    try:

        logger.info(
            "http_request_started "
            "method=%s path=%s",
            request.method,
            request.url.path
        )

        response = await call_next(
            request
        )

        response.headers[
            "X-Request-ID"
        ] = request_id

        logger.info(
            "http_request_completed "
            "method=%s "
            "path=%s "
            "status=%s "
            "latency_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms(
                request_start
            )
        )

        return response

    except Exception:

        logger.exception(
            "http_request_failed "
            "method=%s "
            "path=%s "
            "latency_ms=%.2f",
            request.method,
            request.url.path,
            elapsed_ms(
                request_start
            )
        )

        raise

    finally:

        reset_request_id(
            request_token
        )


# ---------------------------------
# REQUEST MODEL
# ---------------------------------

class MessageRequest(
    BaseModel
):

    user_id: str = Field(
        min_length=1,
        max_length=128
    )

    message: str = Field(
        min_length=1,
        max_length=(
            MAX_MESSAGE_CHARACTERS
        )
    )


# ---------------------------------
# HOME
# ---------------------------------

@app.get("/")
def home():

    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "status": "running"
    }


# ---------------------------------
# ABOUT
# ---------------------------------

@app.get("/about")
def about():

    return {
        "name": APP_NAME,
        "type": (
            "WhatsApp AI Agent"
        ),
        "version": APP_VERSION,
        "environment": ENVIRONMENT
    }


# ---------------------------------
# LIVENESS
# ---------------------------------

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# ---------------------------------
# READINESS
# ---------------------------------

@app.get("/ready")
async def ready():

    readiness = (
        await get_readiness_status()
    )

    status_code = (
        200
        if readiness["ready"]
        else 503
    )

    return JSONResponse(
        status_code=status_code,
        content=readiness
    )

# ---------------------------------
# ASK API AUTHENTICATION
# ---------------------------------

async def verify_ask_api_key(
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key"
    )
):

    if not ASK_API_KEY:

        logger.error(
            "ask_api_key_not_configured"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "API authentication "
                "is not configured."
            )
        )

    if (
        not x_api_key
        or
        not hmac.compare_digest(
            x_api_key,
            ASK_API_KEY
        )
    ):

        logger.warning(
            "ask_api_auth_failed"
        )

        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )


# ---------------------------------
# GENERIC AGENT API
# ---------------------------------

@app.post(
    "/ask",
    dependencies=[
        Depends(
            verify_ask_api_key
        )
    ]
)
async def ask(
    message: MessageRequest
):

    user_id = (
        message.user_id.strip()
    )

    user_message = (
        message.message.strip()
    )

    if not user_id:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_INPUT",
                "message": (
                    "user_id cannot be empty."
                ),
                "request_id": (
                    get_request_id()
                )
            }
        )

    if not user_message:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_INPUT",
                "message": (
                    "message cannot be empty."
                ),
                "request_id": (
                    get_request_id()
                )
            }
        )

    # ---------------------------------
    # RATE LIMIT
    # ---------------------------------

    rate_result = (
        await api_rate_limiter.check(
            f"api_user:{user_id}"
        )
    )

    if not rate_result.allowed:

        retry_after = max(
            1,
            ceil(
                rate_result
                .retry_after_seconds
            )
        )

        logger.warning(
            "rate_limit_exceeded "
            "scope=api "
            "user_suffix=%s "
            "retry_after_s=%s",
            safe_suffix(
                user_id
            ),
            retry_after
        )

        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": (
                    "Too many requests. "
                    "Please try again shortly."
                ),
                "retry_after_seconds": (
                    retry_after
                ),
                "request_id": (
                    get_request_id()
                )
            },
            headers={
                "Retry-After": str(
                    retry_after
                )
            }
        )

    logger.info(
        "rate_limit_allowed "
        "scope=api "
        "user_suffix=%s "
        "remaining=%s",
        safe_suffix(
            user_id
        ),
        rate_result.remaining
    )

    try:

        answer = await run_agent(
            user_id=user_id,
            user_message=user_message
        )

        return {
            "status": "success",
            "request_id": (
                get_request_id()
            ),
            "user_id": user_id,
            "response": answer
        }

    except Exception:

        logger.exception(
            "ask_endpoint_failed"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": (
                    "NexusAI could not "
                    "process the request."
                ),
                "request_id": (
                    get_request_id()
                )
            }
        )


# ---------------------------------
# WHATSAPP WEBHOOK
# ---------------------------------

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request
):

    form = await request.form()

    form_data = {
        str(key): str(value)
        for (
            key,
            value
        ) in form.items()
    }

    sender = (
        form_data.get(
            "From",
            ""
        ).strip()
    )

    user_message = (
        form_data.get(
            "Body",
            ""
        ).strip()
    )

    signature = (
        request.headers.get(
            "X-Twilio-Signature",
            ""
        )
    )

    # ---------------------------------
    # TWILIO SIGNATURE
    # ---------------------------------

    signature_valid = (
        verify_twilio_signature(
            signature=signature,
            form_data=form_data,
            path=request.url.path
        )
    )

    if not signature_valid:

        logger.warning(
            "twilio_signature_invalid "
            "sender_suffix=%s",
            safe_suffix(
                sender
            )
        )

        return Response(
            content="Forbidden",
            status_code=403,
            media_type="text/plain"
        )

    logger.info(
        "twilio_signature_valid "
        "sender_suffix=%s",
        safe_suffix(
            sender
        )
    )

    logger.info(
        "whatsapp_message_received "
        "sender_suffix=%s",
        safe_suffix(
            sender
        )
    )

    # ---------------------------------
    # BASIC VALIDATION
    # ---------------------------------

    if not sender:

        return Response(
            content="Bad Request",
            status_code=400,
            media_type="text/plain"
        )

    if not user_message:

        twilio_response = (
            MessagingResponse()
        )

        twilio_response.message(
            "Please send a message."
        )

        return Response(
            content=str(
                twilio_response
            ),
            media_type=(
                "application/xml"
            )
        )

    # ---------------------------------
    # SIZE LIMIT
    # ---------------------------------

    if (
        len(user_message)
        > MAX_MESSAGE_CHARACTERS
    ):

        logger.warning(
            "message_rejected "
            "reason=too_long "
            "scope=whatsapp "
            "sender_suffix=%s "
            "length=%s",
            safe_suffix(
                sender
            ),
            len(
                user_message
            )
        )

        twilio_response = (
            MessagingResponse()
        )

        twilio_response.message(
            (
                "Your message is too long. "
                "Please shorten it and "
                "try again."
            )
        )

        return Response(
            content=str(
                twilio_response
            ),
            media_type=(
                "application/xml"
            )
        )

    # ---------------------------------
    # RATE LIMIT
    # ---------------------------------

    rate_result = (
        await whatsapp_rate_limiter.check(
            f"whatsapp_user:{sender}"
        )
    )

    if not rate_result.allowed:

        retry_after = max(
            1,
            ceil(
                rate_result
                .retry_after_seconds
            )
        )

        logger.warning(
            "rate_limit_exceeded "
            "scope=whatsapp "
            "sender_suffix=%s "
            "retry_after_s=%s",
            safe_suffix(
                sender
            ),
            retry_after
        )

        twilio_response = (
            MessagingResponse()
        )

        twilio_response.message(
            (
                "You're sending messages "
                "too quickly. Please wait "
                "a moment and try again."
            )
        )

        return Response(
            content=str(
                twilio_response
            ),
            status_code=200,
            headers={
                "Retry-After": str(
                    retry_after
                )
            },
            media_type=(
                "application/xml"
            )
        )

    logger.info(
        "rate_limit_allowed "
        "scope=whatsapp "
        "sender_suffix=%s "
        "remaining=%s",
        safe_suffix(
            sender
        ),
        rate_result.remaining
    )
        # ---------------------------------
    # DURABLE WHATSAPP JOB
    # ---------------------------------

    current_request_id = (
        get_request_id()
    )

    source_message_sid = (
        form_data.get(
            "MessageSid"
        )
        or
        form_data.get(
            "SmsSid"
        )
        or
        ""
    )

    try:

        (
            job_id,
            job_created
        ) = enqueue_whatsapp_job(
            sender=sender,
            user_message=user_message,
            request_id=(
                current_request_id
            ),
            source_message_sid=(
                source_message_sid
            )
        )

    except Exception:

        logger.exception(
            "whatsapp_job_enqueue_failed "
            "sender_suffix=%s",
            safe_suffix(
                sender
            )
        )

        # Returning 500 allows Twilio
        # to retry delivery instead of
        # silently losing the message.
        return Response(
            content=(
                "Temporary failure"
            ),
            status_code=500,
            media_type="text/plain"
        )

    logger.info(
        "whatsapp_job_enqueued "
        "job_suffix=%s "
        "created=%s "
        "sender_suffix=%s",
        job_id[-6:],
        job_created,
        safe_suffix(
            sender
        )
    )

    # Immediate empty TwiML response.
    # The durable worker processes the
    # stored SQLite job separately.
    twilio_response = (
        MessagingResponse()
    )

    return Response(
        content=str(
            twilio_response
        ),
        status_code=200,
        media_type=(
            "application/xml"
        )
    )