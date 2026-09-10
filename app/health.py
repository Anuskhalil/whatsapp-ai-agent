import httpx

from app.config import (
    OLLAMA_HEALTH_URL,
    OLLAMA_HEALTH_TIMEOUT_SECONDS
)

from app.memory import (
    get_message_count
)

from app.logging_config import (
    get_logger
)


logger = get_logger(
    "health"
)


# ---------------------------------
# DATABASE
# ---------------------------------

def check_database() -> dict:

    try:

        get_message_count(
            "__readiness_check__"
        )

        return {
            "ok": True,
            "status": "ok"
        }

    except Exception:

        logger.exception(
            "database_readiness_failed"
        )

        return {
            "ok": False,
            "status": "unavailable"
        }


# ---------------------------------
# OLLAMA
# ---------------------------------

async def check_ollama() -> dict:

    timeout = httpx.Timeout(
        OLLAMA_HEALTH_TIMEOUT_SECONDS
    )

    try:

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.get(
                OLLAMA_HEALTH_URL
            )

            response.raise_for_status()

        return {
            "ok": True,
            "status": "ok"
        }

    except Exception:

        logger.warning(
            "ollama_readiness_failed"
        )

        return {
            "ok": False,
            "status": "unavailable"
        }


# ---------------------------------
# COMPLETE READINESS
# ---------------------------------

async def get_readiness_status() -> dict:

    database = (
        check_database()
    )

    ollama = (
        await check_ollama()
    )

    ready = (
        database["ok"]
        and
        ollama["ok"]
    )

    return {
        "ready": ready,
        "status": (
            "ready"
            if ready
            else
            "not_ready"
        ),
        "checks": {
            "database": (
                database["status"]
            ),
            "ollama": (
                ollama["status"]
            )
        }
    }