import sqlite3

from app.config import (
    DATABASE_PATH,
    MAX_HISTORY_MESSAGES
)

DB_PATH = DATABASE_PATH

def get_connection():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    return connection

def initialize_database():

    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_user_id
            ON conversation_messages(user_id)
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                user_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                last_message_id INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        columns = connection.execute(
            """
            PRAGMA table_info(conversation_summaries)
            """
        ).fetchall()

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(
            user_id,
            memory_type,
            memory_key
        )
    )
    """
)

        connection.execute(
            """
    CREATE INDEX IF NOT EXISTS idx_user_memories_user_id
    ON user_memories(user_id)
    """
)

        column_names = [
            column[1]
            for column in columns
        ]

        if "last_message_id" not in column_names:

            connection.execute(
                """
                ALTER TABLE conversation_summaries
                ADD COLUMN last_message_id
                INTEGER NOT NULL DEFAULT 0
                """
            )

        connection.commit()

def get_summary_state(
    user_id: str
):

    with get_connection() as connection:

        cursor = connection.execute(
            """
            SELECT
                summary,
                last_message_id
            FROM conversation_summaries
            WHERE user_id = ?
            """,
            (user_id,)
        )

        row = cursor.fetchone()

    if row is None:
        return "", 0

    summary = row[0]
    last_message_id = row[1]

    return summary, last_message_id

def get_summary(
    user_id: str
) -> str:

    summary, _ = get_summary_state(
        user_id
    )

    return summary

def save_summary(
    user_id: str,
    summary: str,
    last_message_id: int | None = None
):

    if last_message_id is None:

        _, existing_last_message_id = (
            get_summary_state(user_id)
        )

        last_message_id = (
            existing_last_message_id
        )

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO conversation_summaries (
                user_id,
                summary,
                last_message_id,
                updated_at
            )
            VALUES (
                ?,
                ?,
                ?,
                CURRENT_TIMESTAMP
            )

            ON CONFLICT(user_id)
            DO UPDATE SET
                summary = excluded.summary,
                last_message_id = excluded.last_message_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                summary,
                last_message_id
            )
        )

        connection.commit()

def get_history(
    user_id: str
) -> list:

    _, last_message_id = (
        get_summary_state(user_id)
    )

    with get_connection() as connection:

        cursor = connection.execute(
            """
            SELECT
                role,
                content
            FROM conversation_messages
            WHERE user_id = ?
              AND id > ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                user_id,
                last_message_id,
                MAX_HISTORY_MESSAGES
            )
        )

        rows = cursor.fetchall()

    rows.reverse()

    return [
        {
            "role": role,
            "content": content
        }
        for role, content in rows
    ]

def add_message(
    user_id: str,
    role: str,
    content: str
):

    if role not in {
        "user",
        "assistant"
    }:

        raise ValueError(
            f"Invalid conversation role: {role}"
        )

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO conversation_messages (
                user_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                role,
                content
            )
        )

        connection.commit()

def get_message_count(
    user_id: str
) -> int:

    with get_connection() as connection:

        cursor = connection.execute(
            """
            SELECT COUNT(*)
            FROM conversation_messages
            WHERE user_id = ?
            """,
            (user_id,)
        )

        row = cursor.fetchone()

    return row[0]

def get_unsummarized_message_count(
    user_id: str
) -> int:

    _, last_message_id = (
        get_summary_state(user_id)
    )

    with get_connection() as connection:

        cursor = connection.execute(
            """
            SELECT COUNT(*)
            FROM conversation_messages
            WHERE user_id = ?
              AND id > ?
            """,
            (
                user_id,
                last_message_id
            )
        )

        row = cursor.fetchone()

    return row[0]

def get_messages_for_summary(
    user_id: str,
    limit: int = 8
) -> list:

    _, last_message_id = (
        get_summary_state(user_id)
    )

    with get_connection() as connection:

        cursor = connection.execute(
            """
            SELECT
                id,
                role,
                content
            FROM conversation_messages
            WHERE user_id = ?
              AND id > ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (
                user_id,
                last_message_id,
                limit
            )
        )

        rows = cursor.fetchall()

    return [
        {
            "id": message_id,
            "role": role,
            "content": content
        }
        for (
            message_id,
            role,
            content
        ) in rows
    ]

def save_user_memory(
    user_id: str,
    memory_type: str,
    memory_key: str,
    memory_value: str,
    importance: int = 5
):

    importance = max(
        1,
        min(importance, 10)
    )

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO user_memories (
                user_id,
                memory_type,
                memory_key,
                memory_value,
                importance,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )

            ON CONFLICT(
                user_id,
                memory_type,
                memory_key
            )
            DO UPDATE SET
                memory_value = excluded.memory_value,
                importance = excluded.importance,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                memory_type,
                memory_key,
                memory_value,
                importance
            )
        )

        connection.commit()

def get_user_memories(
    user_id: str,
    limit: int = 20
) -> list:

    with get_connection() as connection:

        cursor = connection.execute(
            """
            SELECT
                memory_type,
                memory_key,
                memory_value,
                importance
            FROM user_memories
            WHERE user_id = ?
            ORDER BY
                importance DESC,
                updated_at DESC
            LIMIT ?
            """,
            (
                user_id,
                limit
            )
        )

        rows = cursor.fetchall()

    return [
        {
            "type": memory_type,
            "key": memory_key,
            "value": memory_value,
            "importance": importance
        }
        for (
            memory_type,
            memory_key,
            memory_value,
            importance
        ) in rows
    ]

def clear_history(
    user_id: str
):

    with get_connection() as connection:

        connection.execute(
            """
            DELETE FROM conversation_messages
            WHERE user_id = ?
            """,
            (user_id,)
        )

        connection.execute(
            """
            DELETE FROM conversation_summaries
            WHERE user_id = ?
            """,
            (user_id,)
        )

        connection.execute(
    """
    DELETE FROM user_memories
    WHERE user_id = ?
    """,
    (user_id,)
)
        connection.commit()

initialize_database()