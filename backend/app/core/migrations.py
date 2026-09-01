"""Controlled SQL migration runner with checksum and failure visibility."""
import hashlib
from pathlib import Path
from sqlalchemy import text


def run_migrations(engine, migrations_dir: str) -> None:
    root = Path(__file__).resolve().parents[2] / migrations_dir
    files = sorted(root.glob("*.sql"))
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS ai_schema_migration (version VARCHAR(128) PRIMARY KEY, checksum VARCHAR(64) NOT NULL, applied_at DATETIME NOT NULL)"))
        for path in files:
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            row = conn.execute(text("SELECT checksum FROM ai_schema_migration WHERE version=:version"), {"version": path.name}).first()
            if row:
                if row[0] != checksum:
                    raise RuntimeError(f"migration checksum mismatch: {path.name}")
                continue
            conn.exec_driver_sql(path.read_text(encoding="utf-8"))
            conn.execute(text("INSERT INTO ai_schema_migration(version, checksum, applied_at) VALUES (:version, :checksum, CURRENT_TIMESTAMP)"), {"version": path.name, "checksum": checksum})
