"""SQLite helpers for the Streamlit annotation tool."""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "annotations.db"


def _utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            document_key TEXT NOT NULL,
            annotation_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Draft',
            reviewer_id INTEGER,
            reviewer_notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            annotation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (annotation_id) REFERENCES annotations(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_annotations_user_document
        ON annotations(user_id, document_key)
        """
    )
    _ensure_annotation_columns(cur)
    conn.commit()
    conn.close()


def _ensure_annotation_columns(cur: sqlite3.Cursor) -> None:
    cur.execute("PRAGMA table_info(annotations)")
    columns = {row[1] for row in cur.fetchall()}
    if "status" not in columns:
        cur.execute("ALTER TABLE annotations ADD COLUMN status TEXT NOT NULL DEFAULT 'Draft'")
    if "reviewer_id" not in columns:
        cur.execute("ALTER TABLE annotations ADD COLUMN reviewer_id INTEGER")
    if "reviewer_notes" not in columns:
        cur.execute("ALTER TABLE annotations ADD COLUMN reviewer_notes TEXT")


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(pwd_hash).decode()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_b64, hash_b64 = stored_hash.split("$")
    except ValueError:
        return False
    salt = base64.b64decode(salt_b64)
    expected = _hash_password(password, salt)
    return expected == stored_hash


def create_user(username: str, password: str) -> Dict[str, Any]:
    username = username.strip().lower()
    if not username or not password:
        raise ValueError("Username and password are required")
    conn = get_connection()
    cur = conn.cursor()
    now = _utcnow_iso()
    password_hash = _hash_password(password)
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, now),
        )
        conn.commit()
    finally:
        conn.close()
    return {"username": username, "created_at": now}


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    username = username.strip().lower()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and _verify_password(password, row["password_hash"]):
        return {"id": row["id"], "username": row["username"]}
    return None


def upsert_annotation(user_id: int, document_key: str, annotation_json: str, status: str = "Draft") -> None:
    now = _utcnow_iso()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO annotations (user_id, document_key, annotation_json, created_at, updated_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, document_key)
        DO UPDATE SET
            annotation_json = excluded.annotation_json,
            updated_at = excluded.updated_at,
            status = excluded.status
        """,
        (user_id, document_key, annotation_json, now, now, status),
    )
    conn.commit()
    conn.close()


def list_annotations(user_id: Optional[int] = None, document_key: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    query = (
        "SELECT annotations.*, users.username AS owner_username "
        "FROM annotations JOIN users ON users.id = annotations.user_id WHERE 1=1"
    )
    params: List[Any] = []
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    if document_key is not None:
        query += " AND document_key = ?"
        params.append(document_key)
    query += " ORDER BY updated_at DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_annotation(annotation_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
    conn.commit()
    conn.close()


def update_annotation_status(
    annotation_id: int, status: str, reviewer_id: Optional[int] = None, reviewer_notes: Optional[str] = None
) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE annotations
        SET status = ?, reviewer_id = ?, reviewer_notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, reviewer_id, reviewer_notes, _utcnow_iso(), annotation_id),
    )
    conn.commit()
    conn.close()


def create_comment(annotation_id: int, user_id: int, message: str) -> Dict[str, Any]:
    if not message.strip():
        raise ValueError("Comment cannot be empty")
    now = _utcnow_iso()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO comments (annotation_id, user_id, message, created_at) VALUES (?, ?, ?, ?)",
        (annotation_id, user_id, message.strip(), now),
    )
    conn.commit()
    conn.close()
    return {"annotation_id": annotation_id, "user_id": user_id, "message": message.strip(), "created_at": now}


def list_comments(annotation_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT comments.*, users.username
        FROM comments
        JOIN users ON users.id = comments.user_id
        WHERE annotation_id = ?
        ORDER BY created_at DESC
        """,
        (annotation_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def export_user_annotations(user_id: int) -> List[Dict[str, Any]]:
    rows = list_annotations(user_id=user_id)
    exports: List[Dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["annotation_json"])
        payload["_meta"] = {
            "annotation_id": row["id"],
            "status": row.get("status", "Draft"),
            "updated_at": row.get("updated_at"),
        }
        exports.append(payload)
    return exports
