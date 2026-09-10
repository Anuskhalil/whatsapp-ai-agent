from time import perf_counter

import httpx

from app.tools import (
    TOOLS,
    execute_tool,
    is_tool_allowed
)

from app.logging_config import (
    get_logger
)

from app.config import (
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_CONNECT_TIMEOUT_SECONDS,
    OLLAMA_READ_TIMEOUT_SECONDS,
    OLLAMA_WRITE_TIMEOUT_SECONDS,
    OLLAMA_POOL_TIMEOUT_SECONDS,
    OLLAMA_MAX_TOOL_ROUNDS
)


logger = get_logger(
    "llm"
)


MODEL_NAME = OLLAMA_MODEL

MAX_TOOL_ROUNDS = (
    OLLAMA_MAX_TOOL_ROUNDS
)


def elapsed_ms(
    start_time: float
) -> float:

    return (
        perf_counter() - start_time
    ) * 1000


def get_latest_user_message(
    messages: list
) -> str:

    for message in reversed(
        messages
    ):

        if message.get(
            "role"
        ) == "user":

            return str(
                message.get(
                    "content",
                    ""
                )
            )

    return ""


async def ask_llm(
    messages: list,
    use_tools: bool = True
):

    total_start = perf_counter()

    timeout = httpx.Timeout(
    connect=(
        OLLAMA_CONNECT_TIMEOUT_SECONDS
    ),
    read=(
        OLLAMA_READ_TIMEOUT_SECONDS
    ),
    write=(
        OLLAMA_WRITE_TIMEOUT_SECONDS
    ),
    pool=(
        OLLAMA_POOL_TIMEOUT_SECONDS
    )
)

    user_message = (
        get_latest_user_message(
            messages
        )
    )

    tool_round = 0

    ollama_call_count = 0

    try:

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            while (
                tool_round
                < MAX_TOOL_ROUNDS
            ):

                payload = {
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0
                    }
                }

                if use_tools:

                    payload["tools"] = (
                        TOOLS
                    )

                # ---------------------------------
                # OLLAMA REQUEST
                # ---------------------------------

                ollama_call_count += 1

                ollama_start = (
                    perf_counter()
                )

                response = await client.post(
                    OLLAMA_URL,
                    json=payload
                )

                response.raise_for_status()

                logger.info(
                    "ollama_request_completed "
                    "call=%s "
                    "latency_ms=%.2f",
                    ollama_call_count,
                    elapsed_ms(
                        ollama_start
                    )
                )

                data = response.json()

                assistant_message = (
                    data["message"]
                )

                # ---------------------------------
                # NO-TOOLS MODE
                # ---------------------------------

                if not use_tools:

                    logger.info(
                        "llm_completed "
                        "mode=no_tools "
                        "ollama_calls=%s "
                        "latency_ms=%.2f",
                        ollama_call_count,
                        elapsed_ms(
                            total_start
                        )
                    )

                    return (
                        assistant_message.get(
                            "content",
                            ""
                        )
                    )

                # ---------------------------------
                # TOOL CALLS
                # ---------------------------------

                tool_calls = (
                    assistant_message.get(
                        "tool_calls"
                    )
                    or []
                )

                if not tool_calls:

                    logger.info(
                        "llm_completed "
                        "mode=tools "
                        "tool_rounds=%s "
                        "ollama_calls=%s "
                        "latency_ms=%.2f",
                        tool_round,
                        ollama_call_count,
                        elapsed_ms(
                            total_start
                        )
                    )

                    return (
                        assistant_message.get(
                            "content",
                            ""
                        )
                    )

                messages.append(
                    assistant_message
                )

                tool_round += 1

                # ---------------------------------
                # PROCESS TOOL CALLS
                # ---------------------------------

                for tool_call in tool_calls:

                    function = (
                        tool_call.get(
                            "function",
                            {}
                        )
                    )

                    function_name = (
                        function.get(
                            "name",
                            ""
                        )
                    )

                    arguments = (
                        function.get(
                            "arguments",
                            {}
                        )
                    )

                    if not isinstance(
                        arguments,
                        dict
                    ):

                        arguments = {}

                    logger.info(
                        "tool_call "
                        "name=%s "
                        "argument_keys=%s",
                        function_name,
                        list(
                            arguments.keys()
                        )
                    )

                    # ---------------------------------
                    # GUARDRAIL
                    # ---------------------------------

                    if not is_tool_allowed(
                        function_name,
                        user_message
                    ):

                        logger.warning(
                            "tool_blocked "
                            "name=%s",
                            function_name
                        )

                        messages.append({
                            "role": "tool",
                            "content": (
                                "No tool execution was "
                                "performed. Respond "
                                "directly to the user's "
                                "original message. "
                                "Do not discuss tools, "
                                "weather, search, "
                                "external capabilities, "
                                "or any additional task "
                                "unless the user "
                                "actually asked about "
                                "them."
                            )
                        })

                        continue

                    # ---------------------------------
                    # EXECUTE TOOL
                    # ---------------------------------

                    tool_start = (
                        perf_counter()
                    )

                    result = (
                        await execute_tool(
                            function_name,
                            arguments
                        )
                    )

                    # ---------------------------------
                    # STANDARDIZED TOOL FAILURE
                    # ---------------------------------

                    if (
                        isinstance(
                            result,
                            dict
                        )
                        and
                        result.get(
                            "ok"
                        ) is False
                    ):

                        error_data = (
                            result.get(
                                "error",
                                {}
                            )
                        )

                        logger.warning(
                            "tool_failed "
                            "name=%s "
                            "error_code=%s "
                            "retryable=%s "
                            "latency_ms=%.2f",
                            function_name,
                            error_data.get(
                                "code",
                                "UNKNOWN"
                            ),
                            error_data.get(
                                "retryable",
                                False
                            ),
                            elapsed_ms(
                                tool_start
                            )
                        )

                    else:

                        logger.info(
                            "tool_completed "
                            "name=%s "
                            "latency_ms=%.2f",
                            function_name,
                            elapsed_ms(
                                tool_start
                            )
                        )

                    messages.append({
                        "role": "tool",
                        "content": str(
                            result
                        )
                    })

            # ---------------------------------
            # TOOL ROUND LIMIT
            # ---------------------------------

            logger.error(
                "maximum_tool_rounds_reached "
                "rounds=%s "
                "latency_ms=%.2f",
                MAX_TOOL_ROUNDS,
                elapsed_ms(
                    total_start
                )
            )

            return (
                "I couldn't complete the "
                "request because the tool "
                "execution limit was reached."
            )

    except httpx.ReadTimeout:

        logger.warning(
            "ollama_read_timeout "
            "ollama_calls=%s "
            "latency_ms=%.2f",
            ollama_call_count,
            elapsed_ms(
                total_start
            )
        )

        return (
            "AI is taking too long to "
            "respond. Please try again."
        )

    except httpx.ConnectError:

        logger.error(
            "ollama_connection_failed "
            "latency_ms=%.2f",
            elapsed_ms(
                total_start
            )
        )

        return (
            "AI service is currently "
            "unavailable."
        )

    except httpx.HTTPStatusError as e:

        logger.error(
            "ollama_http_error "
            "status=%s "
            "latency_ms=%.2f",
            e.response.status_code,
            elapsed_ms(
                total_start
            )
        )

        return (
            "AI service returned an error."
        )

    except httpx.RequestError:

        logger.exception(
            "ollama_request_failed "
            "latency_ms=%.2f",
            elapsed_ms(
                total_start
            )
        )

        return (
            "Could not communicate with "
            "the AI service."
        )

    except Exception:

        logger.exception(
            "unexpected_llm_error "
            "latency_ms=%.2f",
            elapsed_ms(
                total_start
            )
        )

        return (
            "Something went wrong while "
            "generating the AI response."
        )