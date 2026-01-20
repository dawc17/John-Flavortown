"""
Secure storage for encrypted API keys.

Uses SQLite for persistence. Only encrypted data is stored - 
the bot operator cannot read actual API keys.
"""

import sqlite3
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "keys.db"

_db_initialized = False


def _get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the database and tables if needed."""
    global _db_initialized
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    if not _db_initialized:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_keys (
                discord_id INTEGER PRIMARY KEY,
                encrypted_key TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        _db_initialized = True
    
    return conn


def init_db():
    """Initialize the database schema."""
    conn = _get_connection()
    conn.close()


def store_encrypted_key(discord_id: int, encrypted_key: str, salt: str):
    """
    Store an encrypted API key for a user.
    
    Args:
        discord_id: The user's Discord ID
        encrypted_key: Base64-encoded encrypted API key
        salt: Base64-encoded salt used for key derivation
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_keys (discord_id, encrypted_key, salt, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(discord_id) DO UPDATE SET
            encrypted_key = excluded.encrypted_key,
            salt = excluded.salt,
            updated_at = CURRENT_TIMESTAMP
    """, (discord_id, encrypted_key, salt))
    conn.commit()
    conn.close()


def get_encrypted_key(discord_id: int) -> tuple[str, str] | None:
    """
    Retrieve the encrypted key and salt for a user.
    
    Returns:
        tuple of (encrypted_key, salt) or None if user not found.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT encrypted_key, salt FROM user_keys WHERE discord_id = ?",
        (discord_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row["encrypted_key"], row["salt"]
    return None


def delete_user_key(discord_id: int) -> bool:
    """
    Delete a user's stored key.
    
    Returns:
        True if a key was deleted, False if user had no stored key.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_keys WHERE discord_id = ?", (discord_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def user_has_key(discord_id: int) -> bool:
    """Check if a user has a stored (encrypted) API key."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM user_keys WHERE discord_id = ?",
        (discord_id,)
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


init_db()
