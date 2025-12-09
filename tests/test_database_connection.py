import os
import pathlib

import pytest

from src.database.database import Database


def _load_env():
    """Lightweight .env loader to populate PG* vars for tests if not already set."""
    env_path = pathlib.Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and value and key not in os.environ:
            os.environ[key] = value


def _pg_env_present():
    required = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    return all(os.environ.get(k) for k in required)


def test_postgres_connection_and_tables():
    _load_env()
    if not _pg_env_present():
        pytest.skip("PG* env vars not set; skipping Postgres connectivity test.")

    db = Database()
    if not db.use_postgres:
        pytest.skip("PG* env vars incomplete or not usable; skipping Postgres connectivity test.")

    # Initialize tables and verify connectivity.
    db.initialize()
    ping = db.query("SELECT 1 AS ok")
    assert ping and ping[0].get("ok") == 1

    # Ensure the core tables exist.
    table_checks = db.query(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name IN ('feedback','chat_history','documents')
        """
    )
    tables = {row["table_name"] for row in table_checks}
    assert {"feedback", "chat_history", "documents"}.issubset(tables)
