"""Database management and SQLite CRUD operations."""

import sqlite3
from typing import Any, Dict, List, Optional
from app.config import config


def _get_path(db_path: Optional[str] = None) -> str:
    return db_path or config.DB_PATH


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database tables."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS accounts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT,
                      token TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS alerts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      account_id INTEGER,
                      alert_type TEXT,
                      limit_unit INTEGER,
                      threshold_pct REAL,
                      last_triggered_reset_time INTEGER DEFAULT 0)"""
        )
        conn.commit()


def add_account(name: str, token: str, db_path: Optional[str] = None) -> int:
    """Add a new account to the database and return its ID."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO accounts (name, token) VALUES (?, ?)", (name, token))
        conn.commit()
        return c.lastrowid or 0


def get_accounts(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all accounts from the database."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, token FROM accounts")
        rows = c.fetchall()
        return [{"id": r[0], "name": r[1], "token": r[2]} for r in rows]


def get_account_by_id(acc_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve account by ID, or None if not found."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, token FROM accounts WHERE id = ?", (acc_id,))
        row = c.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "token": row[2]}
        return None


def delete_account(acc_id: int, db_path: Optional[str] = None) -> None:
    """Delete account and its associated alerts."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
        c.execute("DELETE FROM alerts WHERE account_id = ?", (acc_id,))
        conn.commit()


def add_alert(
    account_id: int,
    alert_type: str,
    limit_unit: int,
    threshold_pct: float,
    db_path: Optional[str] = None,
) -> int:
    """Add a new alert for an account and return its ID."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO alerts (account_id, alert_type, limit_unit, threshold_pct, last_triggered_reset_time)
                     VALUES (?, ?, ?, ?, 0)""",
            (account_id, alert_type, limit_unit, threshold_pct),
        )
        conn.commit()
        return c.lastrowid or 0


def get_alerts_by_account(
    account_id: int, db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve all alerts configured for a specific account."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT id, account_id, alert_type, limit_unit, threshold_pct, last_triggered_reset_time
                     FROM alerts WHERE account_id = ?""",
            (account_id,),
        )
        rows = c.fetchall()
        return [
            {
                "id": r[0],
                "account_id": r[1],
                "alert_type": r[2],
                "limit_unit": r[3],
                "threshold_pct": r[4],
                "last_triggered_reset_time": r[5],
            }
            for r in rows
        ]


def get_all_alerts(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all active alerts across all accounts."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT id, account_id, alert_type, limit_unit, threshold_pct, last_triggered_reset_time
                     FROM alerts"""
        )
        rows = c.fetchall()
        return [
            {
                "id": r[0],
                "account_id": r[1],
                "alert_type": r[2],
                "limit_unit": r[3],
                "threshold_pct": r[4],
                "last_triggered_reset_time": r[5],
            }
            for r in rows
        ]


def update_alert_triggered(
    alert_id: int, reset_time: int, db_path: Optional[str] = None
) -> None:
    """Update last_triggered_reset_time for an alert to prevent repeat notifications."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE alerts SET last_triggered_reset_time = ? WHERE id = ?",
            (reset_time, alert_id),
        )
        conn.commit()


def delete_alert(alert_id: int, db_path: Optional[str] = None) -> None:
    """Delete an alert by its ID."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
