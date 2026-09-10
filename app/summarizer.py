import asyncio

from app.llm import ask_llm

from app.memory import (
    get_summary_state,
    get_unsummarized_message_count,
    get_messages_for_summary,
    save_summary
)

from app.config import (
    SUMMARY_TRIGGER_MESSAGES,
    SUMMARY_BATCH_SIZE,
    SUMMARY_LLM_TIMEOUT_SECONDS
)

from app.logging_config import (
    get_logger
)


logger = get_logger(
    "memory"
)


async def summarize_conversation(
    old_summary: str,
    messages: list
) -> str:

    conversation_lines = []

    for message in messages:

        role = message["role"]

        content = message[
            "content"
        ]

        conversation_lines.append(
            f"{role}: {content}"
        )

    conversation_text = "\n".join(
        conversation_lines
    )

    prompt = f"""
You are maintaining long-term conversation memory for NexusAI.

Existing memory summary:
{old_summary or "No previous memory summary exists."}

New conversation messages:
{conversation_text}

Update the memory summary using the existing memory and the new messages.

Keep only useful facts and context that may matter in future conversations.

Examples:
- User's name
- User preferences
- User goals
- Projects the user is working on
- Things the user is learning
- Important personal context explicitly shared by the user
- Decisions
- Ongoing tasks
- Important continuing constraints

Rules:
- Preserve useful facts from the existing summary.
- Add useful new facts from the new conversation.
- Do not invent information.
- Do not treat assistant guesses as user facts.
- Do not include greetings or small talk.
- Do not include tool calls.
- Do not include temporary calculations.
- Do not include transient weather results.
- Do not include temporary search results unless they matter to an ongoing task.
- Keep the summary concise.
- Return only the updated memory summary.
"""

    messages_for_summary = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    try:

        result = await asyncio.wait_for(
            ask_llm(
                messages_for_summary,
                use_tools=False
            ),
            timeout=(
                SUMMARY_LLM_TIMEOUT_SECONDS
            )
        )

    except TimeoutError:

        logger.warning(
            "memory_summary_timeout "
            "timeout_s=%.1f",
            SUMMARY_LLM_TIMEOUT_SECONDS
        )

        return ""

    result = result.strip()

    if not result:

        return ""

    failure_prefixes = (
        "AI is taking too long",
        "AI service is currently unavailable",
        "AI service returned an error",
        "Could not communicate with the AI service",
        "Something went wrong while generating"
    )

    if result.startswith(
        failure_prefixes
    ):

        logger.warning(
            "memory_summary_llm_failed"
        )

        return ""

    return result


async def maybe_update_summary(
    user_id: str
) -> bool:

    unsummarized_count = (
        get_unsummarized_message_count(
            user_id
        )
    )

    if (
        unsummarized_count
        < SUMMARY_TRIGGER_MESSAGES
    ):

        return False

    old_summary, _ = (
        get_summary_state(
            user_id
        )
    )

    messages = (
        get_messages_for_summary(
            user_id,
            limit=SUMMARY_BATCH_SIZE
        )
    )

    if not messages:

        return False

    new_summary = (
        await summarize_conversation(
            old_summary,
            messages
        )
    )

    if not new_summary:

        return False

    last_message_id = (
        messages[-1]["id"]
    )

    save_summary(
        user_id,
        new_summary,
        last_message_id
    )

    logger.info(
        "memory_summary_updated "
        "user_suffix=%s "
        "last_message_id=%s",
        user_id[-4:],
        last_message_id
    )

    return True