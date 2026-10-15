"""Database management and SQLite CRUD operations with Multi-User and Account Sharing support."""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from app.config import config


def _get_path(db_path: Optional[str] = None) -> str:
    return db_path or config.DB_PATH


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database tables and apply automatic migrations."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()

        # Users table
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY,
                 username TEXT,
                 first_name TEXT,
                 is_approved INTEGER DEFAULT 0,
                 is_admin INTEGER DEFAULT 0,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
             )"""
        )

        # Accounts table
        c.execute(
            """CREATE TABLE IF NOT EXISTS accounts (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 token TEXT,
                 user_id INTEGER DEFAULT 0
             )"""
        )

        # Account shares table (grants access to view quota info and alerts)
        c.execute(
            """CREATE TABLE IF NOT EXISTS account_shares (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 account_id INTEGER,
                 user_id INTEGER,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 UNIQUE(account_id, user_id)
             )"""
        )

        # Alerts table
        c.execute(
            """CREATE TABLE IF NOT EXISTS alerts (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 account_id INTEGER,
                 alert_type TEXT,
                 limit_unit INTEGER,
                 threshold_pct REAL,
                 last_triggered_reset_time INTEGER DEFAULT 0,
                 user_id INTEGER DEFAULT 0
             )"""
        )

        # --- Migrations for existing schemas ---
        # 1. Check user_id in accounts
        c.execute("PRAGMA table_info(accounts)")
        acc_cols = [col[1] for col in c.fetchall()]
        if "user_id" not in acc_cols:
            c.execute("ALTER TABLE accounts ADD COLUMN user_id INTEGER DEFAULT 0")

        # 2. Check user_id in alerts
        c.execute("PRAGMA table_info(alerts)")
        alert_cols = [col[1] for col in c.fetchall()]
        if "user_id" not in alert_cols:
            c.execute("ALTER TABLE alerts ADD COLUMN user_id INTEGER DEFAULT 0")

        # Assign existing unassigned accounts/alerts to OWNER_ID if configured
        if config.OWNER_ID:
            c.execute(
                "UPDATE accounts SET user_id = ? WHERE user_id = 0 OR user_id IS NULL",
                (config.OWNER_ID,),
            )
            c.execute(
                "UPDATE alerts SET user_id = ? WHERE user_id = 0 OR user_id IS NULL",
                (config.OWNER_ID,),
            )
            # Ensure OWNER_ID exists in users with admin rights
            c.execute(
                """INSERT INTO users (user_id, username, first_name, is_approved, is_admin)
                     VALUES (?, 'owner', 'Owner', 1, 1)
                     ON CONFLICT(user_id) DO UPDATE SET is_approved=1, is_admin=1""",
                (config.OWNER_ID,),
            )

        conn.commit()


# --- User Management CRUD ---


def upsert_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    is_approved: int = 0,
    is_admin: int = 0,
    db_path: Optional[str] = None,
) -> None:
    """Insert or update user record."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO users (user_id, username, first_name, is_approved, is_admin)
                 VALUES (?, ?, ?, ?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(?, username),
                    first_name = COALESCE(?, first_name)""",
            (user_id, username, first_name, is_approved, is_admin, username, first_name),
        )
        conn.commit()


def get_user(user_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve user by user_id."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT user_id, username, first_name, is_approved, is_admin, created_at
                 FROM users WHERE user_id = ?""",
            (user_id,),
        )
        row = c.fetchone()
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "is_approved": bool(row[3]),
                "is_admin": bool(row[4]),
                "created_at": row[5],
            }
        return None


def set_user_approval(user_id: int, is_approved: int, db_path: Optional[str] = None) -> None:
    """Approve (1) or revoke/reject (0) a user."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_approved = ? WHERE user_id = ?", (is_approved, user_id))
        conn.commit()


def get_all_users(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all registered users."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT user_id, username, first_name, is_approved, is_admin, created_at
                 FROM users ORDER BY created_at DESC"""
        )
        rows = c.fetchall()
        return [
            {
                "user_id": r[0],
                "username": r[1],
                "first_name": r[2],
                "is_approved": bool(r[3]),
                "is_admin": bool(r[4]),
                "created_at": r[5],
            }
            for r in rows
        ]


def get_pending_users(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve users waiting for approval."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT user_id, username, first_name, is_approved, is_admin, created_at
                 FROM users WHERE is_approved = 0 ORDER BY created_at ASC"""
        )
        rows = c.fetchall()
        return [
            {
                "user_id": r[0],
                "username": r[1],
                "first_name": r[2],
                "is_approved": False,
                "is_admin": bool(r[4]),
                "created_at": r[5],
            }
            for r in rows
        ]


# --- Account Management CRUD ---


def add_account(
    name: str,
    token: str,
    user_id: Optional[Any] = None,
    db_path: Optional[str] = None,
) -> int:
    """Add a new account owned by user_id."""
    if isinstance(user_id, str) and db_path is None:
        db_path = user_id
        user_id = None
    path = _get_path(db_path)
    uid = int(user_id) if isinstance(user_id, (int, float)) else (config.OWNER_ID or 0)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO accounts (name, token, user_id) VALUES (?, ?, ?)",
            (name, token, uid),
        )

        conn.commit()
        return c.lastrowid or 0


def get_accounts(
    user_id: Optional[Any] = None, db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve accounts.
    If user_id is specified: returns owned accounts + shared accounts.
    If user_id is None: returns all accounts (global/admin view).
    """
    if isinstance(user_id, str) and db_path is None:
        db_path = user_id
        user_id = None
    path = _get_path(db_path)

    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        if user_id is None:
            c.execute("SELECT id, name, token, user_id FROM accounts")
            rows = c.fetchall()
            return [
                {"id": r[0], "name": r[1], "token": r[2], "user_id": r[3], "is_shared": False}
                for r in rows
            ]

        # 1. Accounts owned by user_id
        c.execute(
            "SELECT id, name, token, user_id FROM accounts WHERE user_id = ?",
            (user_id,),
        )
        owned_rows = c.fetchall()
        result = [
            {"id": r[0], "name": r[1], "token": r[2], "user_id": r[3], "is_shared": False}
            for r in owned_rows
        ]

        # 2. Accounts shared with user_id
        c.execute(
            """SELECT a.id, a.name, a.token, a.user_id
                 FROM accounts a
                 JOIN account_shares s ON a.id = s.account_id
                 WHERE s.user_id = ?""",
            (user_id,),
        )
        shared_rows = c.fetchall()
        for r in shared_rows:
            result.append(
                {"id": r[0], "name": r[1], "token": r[2], "user_id": r[3], "is_shared": True}
            )

        return result


def get_account_by_id(acc_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve account by ID."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, token, user_id FROM accounts WHERE id = ?", (acc_id,))
        row = c.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "token": row[2], "user_id": row[3]}
        return None


def check_account_access(
    acc_id: int, user_id: int, db_path: Optional[str] = None
) -> Tuple[bool, bool]:
    """
    Check if user_id can access acc_id.
    Returns (has_access, is_owner).
    """
    acc = get_account_by_id(acc_id, db_path)
    if not acc:
        return False, False
    if acc["user_id"] == user_id or (config.OWNER_ID and user_id == config.OWNER_ID):
        return True, (acc["user_id"] == user_id)

    # Check shared access
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT 1 FROM account_shares WHERE account_id = ? AND user_id = ?",
            (acc_id, user_id),
        )
        has_share = c.fetchone() is not None
        return has_share, False


def delete_account(acc_id: int, db_path: Optional[str] = None) -> None:
    """Delete account and all its alerts and shared permissions."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
        c.execute("DELETE FROM alerts WHERE account_id = ?", (acc_id,))
        c.execute("DELETE FROM account_shares WHERE account_id = ?", (acc_id,))
        conn.commit()


# --- Account Sharing CRUD ---


def share_account(account_id: int, target_user_id: int, db_path: Optional[str] = None) -> None:
    """Grant target_user_id read/alert access to account_id."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO account_shares (account_id, user_id) VALUES (?, ?)
                 ON CONFLICT(account_id, user_id) DO NOTHING""",
            (account_id, target_user_id),
        )
        conn.commit()


def unshare_account(account_id: int, target_user_id: int, db_path: Optional[str] = None) -> None:
    """Revoke target_user_id access to account_id and delete their alerts for it."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM account_shares WHERE account_id = ? AND user_id = ?",
            (account_id, target_user_id),
        )
        c.execute(
            "DELETE FROM alerts WHERE account_id = ? AND user_id = ?",
            (account_id, target_user_id),
        )
        conn.commit()


def get_shared_users_for_account(
    account_id: int, db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve all users who have been granted access to account_id."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT u.user_id, u.username, u.first_name
                 FROM users u
                 JOIN account_shares s ON u.user_id = s.user_id
                 WHERE s.account_id = ?""",
            (account_id,),
        )
        rows = c.fetchall()
        return [{"user_id": r[0], "username": r[1], "first_name": r[2]} for r in rows]


# --- Alert Management CRUD ---


def add_alert(
    account_id: int,
    alert_type: str,
    limit_unit: int,
    threshold_pct: float,
    user_id: Optional[Any] = None,
    db_path: Optional[str] = None,
) -> int:
    """Add a new alert for an account, notifying user_id."""
    if isinstance(user_id, str) and db_path is None:
        db_path = user_id
        user_id = None
    path = _get_path(db_path)
    uid = int(user_id) if isinstance(user_id, (int, float)) else (config.OWNER_ID or 0)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO alerts (account_id, alert_type, limit_unit, threshold_pct, last_triggered_reset_time, user_id)
                     VALUES (?, ?, ?, ?, 0, ?)""",
            (account_id, alert_type, limit_unit, threshold_pct, uid),
        )

        conn.commit()
        return c.lastrowid or 0


def get_alerts_by_account(
    account_id: int,
    user_id: Optional[Any] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve alerts configured for account_id (optionally filtered by user_id)."""
    if isinstance(user_id, str) and db_path is None:
        db_path = user_id
        user_id = None
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        if user_id is not None:

            c.execute(
                """SELECT id, account_id, alert_type, limit_unit, threshold_pct, last_triggered_reset_time, user_id
                         FROM alerts WHERE account_id = ? AND user_id = ?""",
                (account_id, user_id),
            )
        else:
            c.execute(
                """SELECT id, account_id, alert_type, limit_unit, threshold_pct, last_triggered_reset_time, user_id
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
                "user_id": r[6],
            }
            for r in rows
        ]


def get_all_alerts(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all active alerts across all accounts."""
    path = _get_path(db_path)
    with sqlite3.connect(path) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT id, account_id, alert_type, limit_unit, threshold_pct, last_triggered_reset_time, user_id
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
                "user_id": r[6],
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
