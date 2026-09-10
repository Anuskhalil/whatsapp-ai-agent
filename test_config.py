from app.config import (
    APP_NAME,
    APP_VERSION,
    ENVIRONMENT,
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_MAX_TOOL_ROUNDS,
    TAVILY_API_KEY,
    MAX_HISTORY_MESSAGES,
    MEMORY_LLM_TIMEOUT_SECONDS,
    SUMMARY_TRIGGER_MESSAGES,
    SUMMARY_BATCH_SIZE,
    MAX_MESSAGE_CHARACTERS,
    API_RATE_LIMIT_REQUESTS,
    WHATSAPP_RATE_LIMIT_REQUESTS,
    LOG_LEVEL,
    safe_config_snapshot,
    get_config_warnings
)


def main():

    assert APP_NAME

    assert APP_VERSION

    assert ENVIRONMENT in {
        "development",
        "test",
        "production"
    }

    assert OLLAMA_URL

    assert OLLAMA_MODEL

    assert (
        OLLAMA_MAX_TOOL_ROUNDS
        >= 1
    )

    assert (
        MAX_HISTORY_MESSAGES
        >= 2
    )

    assert (
        MEMORY_LLM_TIMEOUT_SECONDS
        > 0
    )

    assert (
        SUMMARY_BATCH_SIZE
        < SUMMARY_TRIGGER_MESSAGES
    )

    assert (
        MAX_MESSAGE_CHARACTERS
        >= 100
    )

    assert (
        API_RATE_LIMIT_REQUESTS
        >= 1
    )

    assert (
        WHATSAPP_RATE_LIMIT_REQUESTS
        >= 1
    )

    assert LOG_LEVEL in {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL"
    }

    snapshot = (
        safe_config_snapshot()
    )

    # Actual secret must never be
    # exposed by the safe snapshot.
    if TAVILY_API_KEY:

        assert (
            TAVILY_API_KEY
            not in str(snapshot)
        )

    print(
        "PASS: application configuration"
    )

    print(
        "PASS: Ollama configuration"
    )

    print(
        "PASS: memory configuration"
    )

    print(
        "PASS: rate-limit configuration"
    )

    print(
        "PASS: safe config snapshot"
    )

    print()

    print(
        "Environment:",
        ENVIRONMENT
    )

    print(
        "Model:",
        OLLAMA_MODEL
    )

    print(
        "Tavily configured:",
        bool(
            TAVILY_API_KEY
        )
    )

    warnings = (
        get_config_warnings()
    )

    if warnings:

        print()

        print(
            "Configuration warnings:"
        )

        for warning in warnings:

            print(
                "-",
                warning
            )

    print()

    print(
        "All configuration tests passed."
    )


if __name__ == "__main__":

    main()