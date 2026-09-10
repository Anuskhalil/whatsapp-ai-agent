import asyncio

from time import perf_counter

from app.agent import (
    run_agent
)

from app.config import (
    WHATSAPP_JOB_POLL_SECONDS
)

from app.job_store import (
    claim_next_whatsapp_job,
    mark_whatsapp_job_completed,
    mark_whatsapp_job_failed,
    save_whatsapp_job_response
)

from app.logging_config import (
    get_logger
)

from app.request_context import (
    set_request_id,
    reset_request_id
)

from app.twilio_client import (
    send_whatsapp_message
)


logger = get_logger(
    "whatsapp"
)


def elapsed_ms(
    start_time: float
) -> float:

    return (
        perf_counter()
        - start_time
    ) * 1000


# ---------------------------------
# PROCESS ONE DURABLE JOB
# ---------------------------------

async def process_whatsapp_job(
    job: dict
):

    start_time = (
        perf_counter()
    )

    job_id = job[
        "job_id"
    ]

    sender = job[
        "sender"
    ]

    request_id = job[
        "request_id"
    ]

    attempts = job[
        "attempts"
    ]

    max_attempts = job[
        "max_attempts"
    ]

    request_token = (
        set_request_id(
            request_id
        )
    )

    try:

        logger.info(
            "whatsapp_job_started "
            "job_suffix=%s "
            "sender_suffix=%s "
            "attempt=%s/%s",
            job_id[-6:],
            sender[-4:],
            attempts,
            max_attempts
        )

        # ---------------------------------
        # REUSE GENERATED ANSWER
        # ---------------------------------

        answer = (
            job.get(
                "response_text"
            )
        )

        response_reused = bool(
            answer
        )

        # ---------------------------------
        # RUN AGENT ONLY IF NEEDED
        # ---------------------------------

        if not answer:

            answer = await run_agent(
                user_id=sender,
                user_message=job[
                    "user_message"
                ]
            )

            save_whatsapp_job_response(
                job_id=job_id,
                response_text=answer
            )

        logger.info(
            "whatsapp_job_answer_ready "
            "job_suffix=%s "
            "response_reused=%s "
            "latency_ms=%.2f",
            job_id[-6:],
            response_reused,
            elapsed_ms(
                start_time
            )
        )

        # ---------------------------------
        # SEND THROUGH TWILIO
        # ---------------------------------

        send_result = (
            await send_whatsapp_message(
                to=sender,
                body=answer
            )
        )

        if not send_result.get(
            "ok"
        ):

            reason = (
                send_result.get(
                    "reason",
                    "send_failed"
                )
            )

            raise RuntimeError(
                f"WhatsApp send failed: "
                f"{reason}"
            )

        mark_whatsapp_job_completed(
            job_id
        )

        logger.info(
            "whatsapp_job_completed "
            "job_suffix=%s "
            "status=success "
            "latency_ms=%.2f",
            job_id[-6:],
            elapsed_ms(
                start_time
            )
        )

    except asyncio.CancelledError:

        logger.warning(
            "whatsapp_job_cancelled "
            "job_suffix=%s",
            job_id[-6:]
        )

        raise

    except Exception as error:

        next_status = (
            mark_whatsapp_job_failed(
                job_id=job_id,
                error_message=(
                    type(error).__name__
                )
            )
        )

        logger.exception(
            "whatsapp_job_failed "
            "job_suffix=%s "
            "next_status=%s "
            "attempt=%s/%s "
            "latency_ms=%.2f",
            job_id[-6:],
            next_status,
            attempts,
            max_attempts,
            elapsed_ms(
                start_time
            )
        )

    finally:

        reset_request_id(
            request_token
        )


# ---------------------------------
# DURABLE WORKER LOOP
# ---------------------------------

async def whatsapp_job_worker(
    stop_event: asyncio.Event
):

    logger.info(
        "whatsapp_worker_started"
    )

    try:

        while not stop_event.is_set():

            try:

                job = (
                    claim_next_whatsapp_job()
                )

            except Exception:

                logger.exception(
                    "whatsapp_worker_poll_failed"
                )

                await asyncio.sleep(
                    WHATSAPP_JOB_POLL_SECONDS
                )

                continue

            if job is not None:

                await process_whatsapp_job(
                    job
                )

                continue

            try:

                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=(
                        WHATSAPP_JOB_POLL_SECONDS
                    )
                )

            except TimeoutError:

                pass

    finally:

        logger.info(
            "whatsapp_worker_stopped"
        )