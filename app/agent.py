from time import perf_counter

from app.llm import ask_llm

from app.prompts import (
    SYSTEM_PROMPT
)

from app.memory import (
    get_history,
    add_message,
    get_summary,
    get_user_memories
)

from app.logging_config import (
    get_logger
)

from app.request_context import (
    create_request_id,
    get_request_id,
    set_request_id,
    reset_request_id
)


logger = get_logger(
    "agent"
)


# ---------------------------------
# HELPER
# ---------------------------------

def elapsed_ms(
    start_time: float
) -> float:

    return (
        perf_counter() - start_time
    ) * 1000


# ---------------------------------
# BUILD AGENT CONTEXT
# ---------------------------------

def build_agent_messages(
    user_id: str,
    user_message: str
) -> list:

    summary = get_summary(
        user_id
    )

    history = get_history(
        user_id
    )

    structured_memories = (
        get_user_memories(
            user_id
        )
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # ---------------------------------
    # STRUCTURED LONG-TERM MEMORY
    # ---------------------------------

    if structured_memories:

        memory_lines = []

        for memory in structured_memories:

            memory_lines.append(
                f"- {memory['type']}: "
                f"{memory['key']} = "
                f"{memory['value']}"
            )

        structured_memory_text = (
            "\n".join(memory_lines)
        )

        messages.append({
            "role": "system",
            "content": (
                "Known long-term facts about "
                "this user:\n"
                f"{structured_memory_text}\n\n"
                "Use these facts only when "
                "relevant to the user's request. "
                "Do not mention internal memory "
                "storage or database details."
            )
        })

    # ---------------------------------
    # CONVERSATION SUMMARY
    # ---------------------------------

    if summary:

        messages.append({
            "role": "system",
            "content": (
                "Relevant long-term "
                "conversation summary:\n"
                f"{summary}"
            )
        })

    # ---------------------------------
    # RECENT HISTORY
    # ---------------------------------

    messages.extend(
        history
    )

    # ---------------------------------
    # CURRENT MESSAGE
    # ---------------------------------

    messages.append({
        "role": "user",
        "content": user_message
    })

    return messages


# ---------------------------------
# MEMORY MAINTENANCE
# ---------------------------------

async def maintain_memory(
    user_id: str,
    user_message: str
):

    total_start = perf_counter()

    # ---------------------------------
    # STRUCTURED MEMORY EXTRACTION
    # ---------------------------------

    extraction_start = perf_counter()

    try:

        from app.memory_extractor import (
            extract_and_store_memories
        )

        await extract_and_store_memories(
            user_id,
            user_message
        )

        logger.info(
            "memory_extraction_completed "
            "latency_ms=%.2f",
            elapsed_ms(
                extraction_start
            )
        )

    except Exception:

        logger.exception(
            "memory_extraction_failed "
            "latency_ms=%.2f",
            elapsed_ms(
                extraction_start
            )
        )

    # ---------------------------------
    # SUMMARY UPDATE
    # ---------------------------------

    summary_start = perf_counter()

    try:

        from app.summarizer import (
            maybe_update_summary
        )

        summary_updated = (
            await maybe_update_summary(
                user_id
            )
        )

        logger.info(
            "memory_summary_check_completed "
            "updated=%s latency_ms=%.2f",
            summary_updated,
            elapsed_ms(
                summary_start
            )
        )

    except Exception:

        logger.exception(
            "memory_summary_failed "
            "latency_ms=%.2f",
            elapsed_ms(
                summary_start
            )
        )

    logger.info(
        "memory_maintenance_completed "
        "latency_ms=%.2f",
        elapsed_ms(
            total_start
        )
    )


# ---------------------------------
# COMPLETE AGENT WORKFLOW
# ---------------------------------

async def run_agent(
    user_id: str,
    user_message: str
) -> str:

    request_token = None

    if get_request_id() == "-":

        request_token = set_request_id(
            create_request_id()
        )

    total_start = perf_counter()

    try:

        user_message = (
            user_message.strip()
        )

        if not user_message:

            logger.warning(
                "agent_empty_message"
            )

            logger.info(
                "agent_request_completed "
                "status=empty "
                "latency_ms=%.2f",
                elapsed_ms(
                    total_start
                )
            )

            return (
                "Please send me a message."
            )

        logger.info(
            "agent_request_started "
            "user_suffix=%s",
            user_id[-4:]
        )

        # ---------------------------------
        # BUILD CONTEXT
        # ---------------------------------

        context_start = perf_counter()

        messages = build_agent_messages(
            user_id=user_id,
            user_message=user_message
        )

        logger.info(
            "agent_context_built "
            "message_count=%s "
            "latency_ms=%.2f",
            len(messages),
            elapsed_ms(
                context_start
            )
        )

        # ---------------------------------
        # RUN LLM
        # ---------------------------------

        llm_start = perf_counter()

        answer = await ask_llm(
            messages
        )

        logger.info(
            "agent_llm_completed "
            "latency_ms=%.2f",
            elapsed_ms(
                llm_start
            )
        )

        # ---------------------------------
        # SAVE CONVERSATION
        # ---------------------------------

        persistence_start = (
            perf_counter()
        )

        add_message(
            user_id,
            "user",
            user_message
        )

        add_message(
            user_id,
            "assistant",
            answer
        )

        logger.info(
            "conversation_persisted "
            "latency_ms=%.2f",
            elapsed_ms(
                persistence_start
            )
        )

        # ---------------------------------
        # LONG-TERM MEMORY
        # ---------------------------------

        await maintain_memory(
            user_id,
            user_message
        )

        # ---------------------------------
        # COMPLETE
        # ---------------------------------

        logger.info(
            "agent_request_completed "
            "status=success "
            "user_suffix=%s "
            "latency_ms=%.2f",
            user_id[-4:],
            elapsed_ms(
                total_start
            )
        )

        return answer

    except Exception:

        logger.exception(
            "agent_request_failed "
            "user_suffix=%s "
            "latency_ms=%.2f",
            user_id[-4:],
            elapsed_ms(
                total_start
            )
        )

        raise

    finally:

        if request_token is not None:

            reset_request_id(
                request_token
            )