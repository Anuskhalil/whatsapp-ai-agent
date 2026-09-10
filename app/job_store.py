import sqlite3
import time

from pathlib import Path
from uuid import uuid4

from app.config import (
    DATABASE_PATH,
    WHATSAPP_JOB_MAX_ATTEMPTS,
    WHATSAPP_JOB_RETRY_DELAY_SECONDS
)

DB_PATH = DATABASE_PATH


# ---------------------------------
# DATABASE CONNECTION
# ---------------------------------

def get_connection():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    connection.row_factory = (
        sqlite3.Row
    )

    return connection


# ---------------------------------
# INITIALIZE JOB TABLE
# ---------------------------------

def initialize_job_store():

    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS
            whatsapp_jobs (
                id INTEGER PRIMARY KEY
                    AUTOINCREMENT,

                job_id TEXT
                    NOT NULL
                    UNIQUE,

                source_message_sid TEXT
                    NOT NULL
                    UNIQUE,

                sender TEXT
                    NOT NULL,

                user_message TEXT
                    NOT NULL,

                request_id TEXT
                    NOT NULL,

                response_text TEXT,

                status TEXT
                    NOT NULL
                    DEFAULT 'pending',

                attempts INTEGER
                    NOT NULL
                    DEFAULT 0,

                max_attempts INTEGER
                    NOT NULL,

                available_at REAL
                    NOT NULL
                    DEFAULT 0,

                last_error TEXT,

                created_at TEXT
                    NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT
                    NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_whatsapp_jobs_status
            ON whatsapp_jobs (
                status,
                available_at,
                id
            )
            """
        )

        connection.commit()


# ---------------------------------
# ENQUEUE
# ---------------------------------

def enqueue_whatsapp_job(
    sender: str,
    user_message: str,
    request_id: str,
    source_message_sid: str = ""
) -> tuple[str, bool]:

    source_message_sid = (
        source_message_sid.strip()
    )

    if not source_message_sid:

        source_message_sid = (
            "local:"
            + uuid4().hex
        )

    job_id = uuid4().hex

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO
            whatsapp_jobs (
                job_id,
                source_message_sid,
                sender,
                user_message,
                request_id,
                status,
                attempts,
                max_attempts,
                available_at
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                'pending',
                0,
                ?,
                0
            )
            """,
            (
                job_id,
                source_message_sid,
                sender,
                user_message,
                request_id,
                WHATSAPP_JOB_MAX_ATTEMPTS
            )
        )

        created = (
            cursor.rowcount == 1
        )

        connection.commit()

        if created:

            return (
                job_id,
                True
            )

        existing = connection.execute(
            """
            SELECT job_id
            FROM whatsapp_jobs
            WHERE source_message_sid = ?
            """,
            (
                source_message_sid,
            )
        ).fetchone()

        if existing is None:

            raise RuntimeError(
                "Could not resolve "
                "existing WhatsApp job."
            )

        return (
            existing["job_id"],
            False
        )


# ---------------------------------
# CLAIM NEXT JOB
# ---------------------------------

def claim_next_whatsapp_job():

    now = time.time()

    connection = (
        get_connection()
    )

    try:

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        row = connection.execute(
            """
            SELECT *
            FROM whatsapp_jobs
            WHERE
                status = 'pending'
                AND available_at <= ?
                AND attempts < max_attempts
            ORDER BY id ASC
            LIMIT 1
            """,
            (
                now,
            )
        ).fetchone()

        if row is None:

            connection.commit()

            return None

        new_attempts = (
            row["attempts"]
            + 1
        )

        cursor = connection.execute(
            """
            UPDATE whatsapp_jobs
            SET
                status = 'processing',
                attempts = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = ?
                AND status = 'pending'
            """,
            (
                new_attempts,
                row["id"]
            )
        )

        if cursor.rowcount != 1:

            connection.rollback()

            return None

        connection.commit()

        job = dict(
            row
        )

        job["status"] = (
            "processing"
        )

        job["attempts"] = (
            new_attempts
        )

        return job

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# ---------------------------------
# SAVE GENERATED RESPONSE
# ---------------------------------

def save_whatsapp_job_response(
    job_id: str,
    response_text: str
):

    with get_connection() as connection:

        connection.execute(
            """
            UPDATE whatsapp_jobs
            SET
                response_text = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
            """,
            (
                response_text,
                job_id
            )
        )

        connection.commit()


# ---------------------------------
# COMPLETE JOB
# ---------------------------------

def mark_whatsapp_job_completed(
    job_id: str
):

    with get_connection() as connection:

        connection.execute(
            """
            UPDATE whatsapp_jobs
            SET
                status = 'completed',
                last_error = NULL,
                available_at = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
            """,
            (
                job_id,
            )
        )

        connection.commit()


# ---------------------------------
# FAIL / RETRY JOB
# ---------------------------------

def mark_whatsapp_job_failed(
    job_id: str,
    error_message: str,
    retry_delay_seconds: float | None = None
) -> str:

    if retry_delay_seconds is None:

        retry_delay_seconds = (
            WHATSAPP_JOB_RETRY_DELAY_SECONDS
        )

    safe_error = (
        str(
            error_message
        )[:200]
    )

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT
                attempts,
                max_attempts
            FROM whatsapp_jobs
            WHERE job_id = ?
            """,
            (
                job_id,
            )
        ).fetchone()

        if row is None:

            raise RuntimeError(
                "WhatsApp job not found."
            )

        attempts = (
            row["attempts"]
        )

        max_attempts = (
            row["max_attempts"]
        )

        if (
            attempts
            >= max_attempts
        ):

            next_status = (
                "failed"
            )

            available_at = 0

        else:

            next_status = (
                "pending"
            )

            available_at = (
                time.time()
                + retry_delay_seconds
            )

        connection.execute(
            """
            UPDATE whatsapp_jobs
            SET
                status = ?,
                available_at = ?,
                last_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
            """,
            (
                next_status,
                available_at,
                safe_error,
                job_id
            )
        )

        connection.commit()

        return next_status


# ---------------------------------
# RECOVER INTERRUPTED JOBS
# ---------------------------------

def recover_incomplete_whatsapp_jobs() -> int:

    with get_connection() as connection:

        cursor = connection.execute(
            """
            UPDATE whatsapp_jobs
            SET
                status = 'pending',
                available_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'processing'
            """,
            (
                time.time(),
            )
        )

        recovered = (
            cursor.rowcount
        )

        connection.commit()

        return recovered


# ---------------------------------
# READ JOB
# ---------------------------------

def get_whatsapp_job(
    job_id: str
):

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT *
            FROM whatsapp_jobs
            WHERE job_id = ?
            """,
            (
                job_id,
            )
        ).fetchone()

        if row is None:

            return None

        return dict(
            row
        )