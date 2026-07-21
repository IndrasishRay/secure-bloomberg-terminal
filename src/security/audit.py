import functools
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, db_path: str | Path = "config/audit.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'INFO',
                    action TEXT NOT NULL,
                    user TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}',
                    ip_address TEXT NOT NULL DEFAULT '127.0.0.1'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC)"
            )
            conn.commit()

    def log_action(
        self,
        action: str,
        user: str,
        details: dict[str, Any] | None = None,
        ip_address: str = "127.0.0.1",
        severity: str = "INFO",
    ) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (timestamp, severity, action, user, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    severity.upper(),
                    action,
                    user,
                    json.dumps(details or {}),
                    ip_address,
                ),
            )
            conn.commit()

    def get_recent_actions(self, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]


def audit_log(
    action: str | None = None,
    severity: str = "INFO",
) -> Any:
    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            audit_action = action or func.__name__
            audit_details = {
                "function": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs),
            }
            try:
                logger = AuditLogger()
                logger.log_action(
                    action=audit_action,
                    user=getattr(args[0], "username", "system") if args else "system",
                    details=audit_details,
                    severity=severity,
                )
            except Exception:
                pass
            return result

        return wrapper

    return decorator
