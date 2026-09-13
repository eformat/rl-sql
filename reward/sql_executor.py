"""Dual-backend SQL executor: SQLite (BIRD) and Trino (NNDSS).

SQLite execution adapted from ReViSQL (tinker_cookbook/recipes/sql_rl/sql_utils.py).
Trino execution adapted from mcp-for-public-health (agents/nndss-agent/tools.py).
"""

import os
import re
import sqlite3
import time
import logging

logger = logging.getLogger(__name__)

_BLOCKED_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
_STRING_LITERAL = re.compile(r"'[^']*'")


def is_read_only(sql: str) -> bool:
    return not _BLOCKED_SQL.search(_STRING_LITERAL.sub("''", sql))


def execute_sqlite(sql: str, db_file: str, timeout: int = 30):
    """Execute SQL against a SQLite database file (read-only).

    Returns (rows: list[tuple] | None, error: str | None).
    """
    conn = sqlite3.connect(f"file:{db_file}?mode=ro", timeout=5, uri=True)
    try:
        conn.execute("PRAGMA query_only=ON;")
        start = time.monotonic()

        def progress():
            return 1 if (time.monotonic() - start) > timeout else 0

        conn.set_progress_handler(progress, 10_000)
        cur = conn.execute(sql)
        return cur.fetchall(), None
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e).lower():
            return None, f"Timeout after {timeout}s"
        return None, f"SQLite error: {e}"
    except Exception as e:
        return None, f"SQLite error: {e}"
    finally:
        conn.set_progress_handler(None, 0)
        conn.close()


def execute_trino(sql: str, host: str = None, port: int = None, timeout: int = 30):
    """Execute SQL against the NNDSS Trino lakehouse (read-only).

    Returns (rows: list[tuple] | None, error: str | None).
    """
    if not is_read_only(sql):
        return None, "Only SELECT queries allowed"

    host = host or os.environ.get("TRINO_HOST", "trino.rl-sql.svc.cluster.local")
    port = port or int(os.environ.get("TRINO_PORT", "8080"))

    try:
        from trino.dbapi import connect as trino_connect

        conn = trino_connect(
            host=host, port=port, user="admin",
            catalog="lakehouse", schema="nndss",
        )
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchmany(500)
        conn.close()
        return [tuple(row) for row in rows], None
    except Exception as e:
        return None, f"Trino error: {e}"


def execute_sql(sql: str, db_type: str, db_id: str = None,
                bird_db_root: str = None, **kwargs):
    """Route SQL execution to the appropriate backend.

    Args:
        sql: The SQL query to execute.
        db_type: "bird" for SQLite execution, "nndss" for Trino.
        db_id: BIRD database ID (used to locate the SQLite file).
        bird_db_root: Root directory containing BIRD SQLite databases.

    Returns (rows: list[tuple] | None, error: str | None).
    """
    if db_type == "bird":
        if not db_id or not bird_db_root:
            return None, "db_id and bird_db_root required for BIRD execution"
        db_file = os.path.join(bird_db_root, db_id, f"{db_id}.sqlite")
        if not os.path.exists(db_file):
            return None, f"Database file not found: {db_file}"
        return execute_sqlite(sql, db_file, **kwargs)
    elif db_type == "nndss":
        return execute_trino(sql, **kwargs)
    else:
        return None, f"Unknown db_type: {db_type}"
