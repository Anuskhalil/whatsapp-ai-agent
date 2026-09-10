import asyncio

from pathlib import Path
from tempfile import TemporaryDirectory

import app.job_store as job_store


async def main():

    original_db_path = (
        job_store.DB_PATH
    )

    with TemporaryDirectory() as temp_dir:

        job_store.DB_PATH = (
            Path(temp_dir)
            / "test_jobs.db"
        )

        try:

            job_store.initialize_job_store()

            # ---------------------------------
            # ENQUEUE
            # ---------------------------------

            (
                job_id,
                created
            ) = (
                job_store
                .enqueue_whatsapp_job(
                    sender=(
                        "whatsapp:+123456789"
                    ),
                    user_message=(
                        "Calculate 2 plus 2."
                    ),
                    request_id=(
                        "request-test-001"
                    ),
                    source_message_sid=(
                        "SM-test-001"
                    )
                )
            )

            assert created is True

            print(
                "PASS: job enqueued"
            )

            # ---------------------------------
            # DUPLICATE MESSAGE SID
            # ---------------------------------

            (
                duplicate_job_id,
                duplicate_created
            ) = (
                job_store
                .enqueue_whatsapp_job(
                    sender=(
                        "whatsapp:+123456789"
                    ),
                    user_message=(
                        "Calculate 2 plus 2."
                    ),
                    request_id=(
                        "request-test-002"
                    ),
                    source_message_sid=(
                        "SM-test-001"
                    )
                )
            )

            assert (
                duplicate_created
                is False
            )

            assert (
                duplicate_job_id
                == job_id
            )

            print(
                "PASS: duplicate Twilio "
                "message prevented"
            )

            # ---------------------------------
            # CLAIM
            # ---------------------------------

            claimed = (
                job_store
                .claim_next_whatsapp_job()
            )

            assert claimed is not None

            assert (
                claimed["job_id"]
                == job_id
            )

            assert (
                claimed["status"]
                == "processing"
            )

            assert (
                claimed["attempts"]
                == 1
            )

            print(
                "PASS: job claimed"
            )

            # ---------------------------------
            # SAVE ANSWER
            # ---------------------------------

            job_store.save_whatsapp_job_response(
                job_id,
                "The answer is 4."
            )

            stored = (
                job_store
                .get_whatsapp_job(
                    job_id
                )
            )

            assert (
                stored["response_text"]
                == "The answer is 4."
            )

            print(
                "PASS: generated answer "
                "persisted"
            )

            # ---------------------------------
            # COMPLETE
            # ---------------------------------

            job_store.mark_whatsapp_job_completed(
                job_id
            )

            completed = (
                job_store
                .get_whatsapp_job(
                    job_id
                )
            )

            assert (
                completed["status"]
                == "completed"
            )

            print(
                "PASS: job completed"
            )

            # ---------------------------------
            # RETRY
            # ---------------------------------

            (
                retry_job_id,
                _
            ) = (
                job_store
                .enqueue_whatsapp_job(
                    sender=(
                        "whatsapp:+123456789"
                    ),
                    user_message="Retry test",
                    request_id=(
                        "request-test-003"
                    ),
                    source_message_sid=(
                        "SM-test-002"
                    )
                )
            )

            retry_claim = (
                job_store
                .claim_next_whatsapp_job()
            )

            assert (
                retry_claim["attempts"]
                == 1
            )

            next_status = (
                job_store
                .mark_whatsapp_job_failed(
                    retry_job_id,
                    "temporary",
                    retry_delay_seconds=0.01
                )
            )

            assert (
                next_status
                == "pending"
            )

            await asyncio.sleep(
                0.02
            )

            retry_claim_2 = (
                job_store
                .claim_next_whatsapp_job()
            )

            assert (
                retry_claim_2["job_id"]
                == retry_job_id
            )

            assert (
                retry_claim_2["attempts"]
                == 2
            )

            job_store.mark_whatsapp_job_completed(
                retry_job_id
            )

            print(
                "PASS: failed job retried"
            )

            # ---------------------------------
            # CRASH RECOVERY
            # ---------------------------------

            (
                recovery_job_id,
                _
            ) = (
                job_store
                .enqueue_whatsapp_job(
                    sender=(
                        "whatsapp:+123456789"
                    ),
                    user_message=(
                        "Recovery test"
                    ),
                    request_id=(
                        "request-test-004"
                    ),
                    source_message_sid=(
                        "SM-test-003"
                    )
                )
            )

            recovery_claim = (
                job_store
                .claim_next_whatsapp_job()
            )

            assert (
                recovery_claim["job_id"]
                == recovery_job_id
            )

            recovered_count = (
                job_store
                .recover_incomplete_whatsapp_jobs()
            )

            assert (
                recovered_count == 1
            )

            recovered_job = (
                job_store
                .claim_next_whatsapp_job()
            )

            assert (
                recovered_job["job_id"]
                == recovery_job_id
            )

            assert (
                recovered_job["attempts"]
                == 2
            )

            print(
                "PASS: interrupted job "
                "recovered"
            )

            print()

            print(
                "All durable job queue "
                "tests passed."
            )

        finally:

            job_store.DB_PATH = (
                original_db_path
            )


if __name__ == "__main__":

    asyncio.run(
        main()
    )