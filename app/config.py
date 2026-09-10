import os

from pathlib import Path

from dotenv import (
    load_dotenv
)


# ---------------------------------
# PROJECT PATHS
# ---------------------------------

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

DATABASE_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        str(
            BASE_DIR
            / "nexusai_memory.db"
        )
    )
).expanduser()

ENV_FILE = (
    BASE_DIR / ".env"
)


# ---------------------------------
# LOAD ENVIRONMENT
# ---------------------------------

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False
)


# ---------------------------------
# HELPERS
# ---------------------------------

def get_text(
    name: str,
    default: str
) -> str:

    value = os.getenv(
        name,
        default
    ).strip()

    if not value:

        raise RuntimeError(
            f"{name} cannot be empty."
        )

    return value


def get_optional_text(
    name: str,
    default: str = ""
) -> str:

    return os.getenv(
        name,
        default
    ).strip()


def get_int(
    name: str,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None
) -> int:

    raw_value = os.getenv(
        name,
        str(default)
    ).strip()

    try:

        value = int(
            raw_value
        )

    except ValueError as e:

        raise RuntimeError(
            f"{name} must be an integer."
        ) from e

    if (
        minimum is not None
        and
        value < minimum
    ):

        raise RuntimeError(
            f"{name} must be >= {minimum}."
        )

    if (
        maximum is not None
        and
        value > maximum
    ):

        raise RuntimeError(
            f"{name} must be <= {maximum}."
        )

    return value


def get_float(
    name: str,
    default: float,
    minimum: float | None = None,
    maximum: float | None = None
) -> float:

    raw_value = os.getenv(
        name,
        str(default)
    ).strip()

    try:

        value = float(
            raw_value
        )

    except ValueError as e:

        raise RuntimeError(
            f"{name} must be a number."
        ) from e

    if (
        minimum is not None
        and
        value < minimum
    ):

        raise RuntimeError(
            f"{name} must be >= {minimum}."
        )

    if (
        maximum is not None
        and
        value > maximum
    ):

        raise RuntimeError(
            f"{name} must be <= {maximum}."
        )

    return value


def get_bool(
    name: str,
    default: bool
) -> bool:

    raw_value = os.getenv(
        name,
        str(default)
    ).strip().lower()

    truthy = {
        "1",
        "true",
        "yes",
        "on"
    }

    falsy = {
        "0",
        "false",
        "no",
        "off"
    }

    if raw_value in truthy:

        return True

    if raw_value in falsy:

        return False

    raise RuntimeError(
        f"{name} must be true or false."
    )


# ---------------------------------
# APPLICATION
# ---------------------------------

APP_NAME = get_text(
    "APP_NAME",
    "NexusAI"
)

APP_VERSION = get_text(
    "APP_VERSION",
    "1.0.0"
)

ENVIRONMENT = get_text(
    "ENVIRONMENT",
    "development"
).lower()


VALID_ENVIRONMENTS = {
    "development",
    "test",
    "production"
}


if (
    ENVIRONMENT
    not in VALID_ENVIRONMENTS
):

    raise RuntimeError(
        "ENVIRONMENT must be one of: "
        "development, test, production."
    )


APP_HOST = get_text(
    "APP_HOST",
    "0.0.0.0"
)


if os.getenv(
    "PORT"
):

    APP_PORT = get_int(
        "PORT",
        8000,
        minimum=1,
        maximum=65535
    )

else:

    APP_PORT = get_int(
        "APP_PORT",
        8000,
        minimum=1,
        maximum=65535
    )


# ---------------------------------
# OLLAMA
# ---------------------------------

OLLAMA_URL = get_text(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat"
)

OLLAMA_HEALTH_URL = get_text(
    "OLLAMA_HEALTH_URL",
    "http://localhost:11434/api/tags"
)

OLLAMA_MODEL = get_text(
    "OLLAMA_MODEL",
    "llama3.2:3b"
)

OLLAMA_CONNECT_TIMEOUT_SECONDS = (
    get_float(
        "OLLAMA_CONNECT_TIMEOUT_SECONDS",
        10.0,
        minimum=1.0
    )
)

OLLAMA_READ_TIMEOUT_SECONDS = (
    get_float(
        "OLLAMA_READ_TIMEOUT_SECONDS",
        120.0,
        minimum=1.0
    )
)

OLLAMA_WRITE_TIMEOUT_SECONDS = (
    get_float(
        "OLLAMA_WRITE_TIMEOUT_SECONDS",
        30.0,
        minimum=1.0
    )
)

OLLAMA_POOL_TIMEOUT_SECONDS = (
    get_float(
        "OLLAMA_POOL_TIMEOUT_SECONDS",
        10.0,
        minimum=1.0
    )
)

OLLAMA_HEALTH_TIMEOUT_SECONDS = (
    get_float(
        "OLLAMA_HEALTH_TIMEOUT_SECONDS",
        5.0,
        minimum=1.0,
        maximum=30.0
    )
)

OLLAMA_MAX_TOOL_ROUNDS = (
    get_int(
        "OLLAMA_MAX_TOOL_ROUNDS",
        5,
        minimum=1,
        maximum=10
    )
)


# ---------------------------------
# TAVILY
# ---------------------------------

TAVILY_API_KEY = get_optional_text(
    "TAVILY_API_KEY"
)

TAVILY_SEARCH_URL = get_text(
    "TAVILY_SEARCH_URL",
    "https://api.tavily.com/search"
)

TAVILY_MAX_RESULTS = get_int(
    "TAVILY_MAX_RESULTS",
    3,
    minimum=1,
    maximum=10
)

TAVILY_SNIPPET_CHARACTERS = (
    get_int(
        "TAVILY_SNIPPET_CHARACTERS",
        700,
        minimum=100,
        maximum=3000
    )
)


# ---------------------------------
# OPEN-METEO
# ---------------------------------

OPEN_METEO_GEOCODING_URL = (
    get_text(
        "OPEN_METEO_GEOCODING_URL",
        (
            "https://geocoding-api."
            "open-meteo.com/v1/search"
        )
    )
)

OPEN_METEO_WEATHER_URL = (
    get_text(
        "OPEN_METEO_WEATHER_URL",
        (
            "https://api.open-meteo.com/"
            "v1/forecast"
        )
    )
)


# ---------------------------------
# EXTERNAL HTTP
# ---------------------------------

EXTERNAL_HTTP_CONNECT_TIMEOUT_SECONDS = (
    get_float(
        "EXTERNAL_HTTP_CONNECT_TIMEOUT_SECONDS",
        10.0,
        minimum=1.0
    )
)

EXTERNAL_HTTP_READ_TIMEOUT_SECONDS = (
    get_float(
        "EXTERNAL_HTTP_READ_TIMEOUT_SECONDS",
        30.0,
        minimum=1.0
    )
)

EXTERNAL_HTTP_WRITE_TIMEOUT_SECONDS = (
    get_float(
        "EXTERNAL_HTTP_WRITE_TIMEOUT_SECONDS",
        15.0,
        minimum=1.0
    )
)

EXTERNAL_HTTP_POOL_TIMEOUT_SECONDS = (
    get_float(
        "EXTERNAL_HTTP_POOL_TIMEOUT_SECONDS",
        10.0,
        minimum=1.0
    )
)

EXTERNAL_HTTP_MAX_ATTEMPTS = (
    get_int(
        "EXTERNAL_HTTP_MAX_ATTEMPTS",
        3,
        minimum=1,
        maximum=5
    )
)

EXTERNAL_HTTP_BASE_DELAY_SECONDS = (
    get_float(
        "EXTERNAL_HTTP_BASE_DELAY_SECONDS",
        0.5,
        minimum=0.0,
        maximum=10.0
    )
)

EXTERNAL_HTTP_MAX_DELAY_SECONDS = (
    get_float(
        "EXTERNAL_HTTP_MAX_DELAY_SECONDS",
        2.0,
        minimum=0.0,
        maximum=30.0
    )
)


# ---------------------------------
# MEMORY
# ---------------------------------

MAX_HISTORY_MESSAGES = (
    get_int(
        "MAX_HISTORY_MESSAGES",
        20,
        minimum=2,
        maximum=100
    )
)

MEMORY_LLM_TIMEOUT_SECONDS = (
    get_float(
        "MEMORY_LLM_TIMEOUT_SECONDS",
        20.0,
        minimum=1.0,
        maximum=120.0
    )
)

SUMMARY_TRIGGER_MESSAGES = (
    get_int(
        "SUMMARY_TRIGGER_MESSAGES",
        12,
        minimum=4,
        maximum=100
    )
)

SUMMARY_BATCH_SIZE = (
    get_int(
        "SUMMARY_BATCH_SIZE",
        8,
        minimum=2,
        maximum=50
    )
)

SUMMARY_LLM_TIMEOUT_SECONDS = (
    get_float(
        "SUMMARY_LLM_TIMEOUT_SECONDS",
        30.0,
        minimum=1.0,
        maximum=120.0
    )
)


if (
    SUMMARY_BATCH_SIZE
    >= SUMMARY_TRIGGER_MESSAGES
):

    raise RuntimeError(
        "SUMMARY_BATCH_SIZE must be "
        "smaller than "
        "SUMMARY_TRIGGER_MESSAGES."
    )


# ---------------------------------
# MESSAGE / RATE LIMITS
# ---------------------------------

MAX_MESSAGE_CHARACTERS = (
    get_int(
        "MAX_MESSAGE_CHARACTERS",
        4000,
        minimum=100,
        maximum=20000
    )
)

API_RATE_LIMIT_REQUESTS = (
    get_int(
        "API_RATE_LIMIT_REQUESTS",
        10,
        minimum=1
    )
)

API_RATE_LIMIT_WINDOW_SECONDS = (
    get_float(
        "API_RATE_LIMIT_WINDOW_SECONDS",
        60.0,
        minimum=1.0
    )
)

WHATSAPP_RATE_LIMIT_REQUESTS = (
    get_int(
        "WHATSAPP_RATE_LIMIT_REQUESTS",
        8,
        minimum=1
    )
)

WHATSAPP_RATE_LIMIT_WINDOW_SECONDS = (
    get_float(
        "WHATSAPP_RATE_LIMIT_WINDOW_SECONDS",
        60.0,
        minimum=1.0
    )
)


# ---------------------------------
# TWILIO WEBHOOK SECURITY
# ---------------------------------

PUBLIC_BASE_URL = (
    get_optional_text(
        "PUBLIC_BASE_URL"
    ).rstrip("/")
)

VERIFY_TWILIO_SIGNATURE = (
    get_bool(
        "VERIFY_TWILIO_SIGNATURE",
        False
    )
)

TWILIO_AUTH_TOKEN = (
    get_optional_text(
        "TWILIO_AUTH_TOKEN"
    )
)

TWILIO_ACCOUNT_SID = (
    get_optional_text(
        "TWILIO_ACCOUNT_SID"
    )
)

TWILIO_WHATSAPP_FROM = (
    get_optional_text(
        "TWILIO_WHATSAPP_FROM"
    )
)

TWILIO_OUTBOUND_ENABLED = (
    get_bool(
        "TWILIO_OUTBOUND_ENABLED",
        False
    )
)

TWILIO_MAX_OUTBOUND_CHARACTERS = (
    get_int(
        "TWILIO_MAX_OUTBOUND_CHARACTERS",
        1500,
        minimum=100,
        maximum=1600
    )
)


if TWILIO_OUTBOUND_ENABLED:

    if not TWILIO_ACCOUNT_SID:

        raise RuntimeError(
            "TWILIO_ACCOUNT_SID is required "
            "when TWILIO_OUTBOUND_ENABLED=true."
        )

    if not TWILIO_AUTH_TOKEN:

        raise RuntimeError(
            "TWILIO_AUTH_TOKEN is required "
            "when TWILIO_OUTBOUND_ENABLED=true."
        )

    if not TWILIO_WHATSAPP_FROM:

        raise RuntimeError(
            "TWILIO_WHATSAPP_FROM is required "
            "when TWILIO_OUTBOUND_ENABLED=true."
        )

    if not TWILIO_WHATSAPP_FROM.startswith(
        "whatsapp:+"
    ):

        raise RuntimeError(
            "TWILIO_WHATSAPP_FROM must begin "
            "with whatsapp:+"
        )


if PUBLIC_BASE_URL:

    if not (
        PUBLIC_BASE_URL.startswith(
            "https://"
        )
        or
        PUBLIC_BASE_URL.startswith(
            "http://"
        )
    ):

        raise RuntimeError(
            "PUBLIC_BASE_URL must begin "
            "with http:// or https://."
        )


if VERIFY_TWILIO_SIGNATURE:

    if not TWILIO_AUTH_TOKEN:

        raise RuntimeError(
            "TWILIO_AUTH_TOKEN is required "
            "when VERIFY_TWILIO_SIGNATURE=true."
        )

    if not PUBLIC_BASE_URL:

        raise RuntimeError(
            "PUBLIC_BASE_URL is required "
            "when VERIFY_TWILIO_SIGNATURE=true."
        )


if (
    ENVIRONMENT == "production"
    and
    VERIFY_TWILIO_SIGNATURE
    and
    not PUBLIC_BASE_URL.startswith(
        "https://"
    )
):

    raise RuntimeError(
        "Production PUBLIC_BASE_URL "
        "must use HTTPS."
    )

# ---------------------------------
# DURABLE WHATSAPP JOBS
# ---------------------------------

WHATSAPP_JOB_POLL_SECONDS = (
    get_float(
        "WHATSAPP_JOB_POLL_SECONDS",
        1.0,
        minimum=0.1,
        maximum=60.0
    )
)

WHATSAPP_JOB_MAX_ATTEMPTS = (
    get_int(
        "WHATSAPP_JOB_MAX_ATTEMPTS",
        3,
        minimum=1,
        maximum=10
    )
)

WHATSAPP_JOB_RETRY_DELAY_SECONDS = (
    get_float(
        "WHATSAPP_JOB_RETRY_DELAY_SECONDS",
        5.0,
        minimum=0.0,
        maximum=300.0
    )
)

WHATSAPP_WORKER_SHUTDOWN_TIMEOUT_SECONDS = (
    get_float(
        "WHATSAPP_WORKER_SHUTDOWN_TIMEOUT_SECONDS",
        10.0,
        minimum=1.0,
        maximum=120.0
    )
)

# ---------------------------------
# API SECURITY
# ---------------------------------

ASK_API_KEY = (
    get_optional_text(
        "ASK_API_KEY"
    )
)

# ---------------------------------
# LOGGING
# ---------------------------------

LOG_LEVEL = get_text(
    "LOG_LEVEL",
    "INFO"
).upper()

VALID_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL"
}


if LOG_LEVEL not in VALID_LOG_LEVELS:

    raise RuntimeError(
        "LOG_LEVEL must be one of: "
        "DEBUG, INFO, WARNING, "
        "ERROR, CRITICAL."
    )


LOG_MAX_BYTES = get_int(
    "LOG_MAX_BYTES",
    2_000_000,
    minimum=100_000
)

LOG_BACKUP_COUNT = get_int(
    "LOG_BACKUP_COUNT",
    3,
    minimum=1,
    maximum=20
)


# ---------------------------------
# SAFE WARNINGS
# ---------------------------------

def get_config_warnings() -> list:

    warnings = []

    if not TAVILY_API_KEY:

        warnings.append(
            (
                "TAVILY_API_KEY is not "
                "configured. Web search "
                "will be unavailable."
            )
        )

    if (
        ENVIRONMENT == "production"
        and
        not VERIFY_TWILIO_SIGNATURE
    ):

        warnings.append(
            (
                "Twilio signature "
                "verification is disabled "
                "in production."
            )
        )

    if (
        ENVIRONMENT == "production"
        and
        (
            "localhost"
            in OLLAMA_URL
            or
            "127.0.0.1"
            in OLLAMA_URL
        )
    ):

        warnings.append(
            (
                "Production uses a local "
                "Ollama URL. Ollama must "
                "run on the same host."
            )
        )

    return warnings


# ---------------------------------
# SAFE SNAPSHOT
# ---------------------------------

def safe_config_snapshot() -> dict:

    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "environment": ENVIRONMENT,
        "app_host": APP_HOST,
        "app_port": APP_PORT,
        "ollama_model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_URL,
        "tavily_configured": bool(
            TAVILY_API_KEY
        ),
        "twilio_signature_verification": (
            VERIFY_TWILIO_SIGNATURE
        ),
        "public_base_url_configured": bool(
            PUBLIC_BASE_URL
        ),
        "max_history_messages": (
            MAX_HISTORY_MESSAGES
        ),
        "max_message_characters": (
            MAX_MESSAGE_CHARACTERS
        ),
        "api_rate_limit_requests": (
            API_RATE_LIMIT_REQUESTS
        ),
        "whatsapp_rate_limit_requests": (
            WHATSAPP_RATE_LIMIT_REQUESTS
        ),
        "twilio_account_configured": bool(
    TWILIO_ACCOUNT_SID
),
"twilio_auth_configured": bool(
    TWILIO_AUTH_TOKEN
),
"twilio_outbound_enabled": (
    TWILIO_OUTBOUND_ENABLED
),
"twilio_sender_configured": bool(
    TWILIO_WHATSAPP_FROM
),
        "log_level": LOG_LEVEL
    }