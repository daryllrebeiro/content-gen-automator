"""Apply ordered PostgreSQL migrations once, recording completed files."""

import os
from pathlib import Path

import psycopg


MIGRATIONS = Path(__file__).resolve().parents[1] / "database" / "migrations"


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
            cursor.execute("SELECT version FROM schema_migrations")
            applied = {row[0] for row in cursor.fetchall()}
            for migration in sorted(MIGRATIONS.glob("*.sql")):
                if migration.name in applied:
                    continue
                cursor.execute(migration.read_text(encoding="utf-8"))
                cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (migration.name,))
        connection.commit()
    print("Migrations applied.")


if __name__ == "__main__":
    main()
