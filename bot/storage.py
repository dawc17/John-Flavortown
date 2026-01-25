"""
Secure storage for encrypted API keys.

Uses SQLite for persistence. Only encrypted data is stored.
The bot operator cannot read actual API keys.

Hacky at best, but it works.
"""

import sqlite3
from pathlib import Path
import threading

from bot.errors import StorageError

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "keys.db"

_db_initialized = False
_db_init_lock = threading.Lock()

def _get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the database and tables if needed."""
    global _db_initialized
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    if not _db_initialized:
        with _db_init_lock:
            if not _db_initialized:
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_keys'")
                table_exists = cursor.fetchone()
                
                if table_exists:
                    cursor.execute("PRAGMA table_info(user_keys)")
                    columns = [col['name'] for col in cursor.fetchall()]
                    
                    if 'service' not in columns:
                        cursor.execute("ALTER TABLE user_keys RENAME TO user_keys_v1")
                        
                        # Create new table
                        cursor.execute("""
                            CREATE TABLE user_keys (
                                discord_id INTEGER,
                                service TEXT NOT NULL,
                                encrypted_key TEXT NOT NULL,
                                salt TEXT NOT NULL,
                                metadata TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                PRIMARY KEY (discord_id, service)
                            )
                        """)
                        
                        cursor.execute("""
                            INSERT INTO user_keys (discord_id, service, encrypted_key, salt, updated_at)
                            SELECT discord_id, 'flavortown', encrypted_key, salt, updated_at
                            FROM user_keys_v1
                        """)
                        
                        cursor.execute("DROP TABLE user_keys_v1")
                        conn.commit()
                else:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS user_keys (
                            discord_id INTEGER,
                            service TEXT NOT NULL,
                            encrypted_key TEXT NOT NULL,
                            salt TEXT NOT NULL,
                            metadata TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (discord_id, service)
                        )
                    """)
                    conn.commit()
                    
                _db_initialized = True
    
    return conn


def init_db() -> None:
    """Initialize the database schema."""
    conn = _get_connection()
    conn.close()


def store_encrypted_key(discord_id: int, service: str, encrypted_key: str, salt: str, metadata: str | None = None) -> None:
    """
    Store an encrypted API key for a user and service.
    
    Args:
        discord_id: The user's Discord ID
        service: The service name ('flavortown' or 'hackatime')
        encrypted_key: Base64-encoded encrypted API key
        salt: Base64-encoded salt used for key derivation
        metadata: JSON string of extra data (e.g. username)
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_keys (discord_id, service, encrypted_key, salt, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(discord_id, service) DO UPDATE SET
                encrypted_key = excluded.encrypted_key,
                salt = excluded.salt,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, (discord_id, service, encrypted_key, salt, metadata))
        conn.commit()
    except sqlite3.Error as e:
        raise StorageError("Failed to store API key. Please try again.") from e
    finally:
        conn.close()


def get_encrypted_key(discord_id: int, service: str = "flavortown") -> tuple[str, str, str | None] | None:
    """
    Retrieve the encrypted key, salt, and metadata for a user and service.
    
    Returns:
        tuple of (encrypted_key, salt, metadata) or None if not found.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT encrypted_key, salt, metadata FROM user_keys WHERE discord_id = ? AND service = ?",
            (discord_id, service)
        )
        row = cursor.fetchone()
    except sqlite3.Error as e:
        raise StorageError("Failed to read API key. Please try again.") from e
    finally:
        conn.close()
    
    if row:
        return row["encrypted_key"], row["salt"], row["metadata"]
    return None


def delete_user_key(discord_id: int, service: str | None = None) -> bool:
    """
    Delete a user's stored key(s).
    
    Args:
        discord_id: User ID
        service: Specific service to delete, or None for all.
        
    Returns:
        True if something was deleted.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        
        if service:
            cursor.execute("DELETE FROM user_keys WHERE discord_id = ? AND service = ?", (discord_id, service))
        else:
            cursor.execute("DELETE FROM user_keys WHERE discord_id = ?", (discord_id,))
            
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    except sqlite3.Error as e:
        raise StorageError("Failed to delete API key. Please try again.") from e
    finally:
        conn.close()


def user_has_key(discord_id: int, service: str = "flavortown") -> bool:
    """Check if a user has a stored (encrypted) API key for the given service."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM user_keys WHERE discord_id = ? AND service = ?",
            (discord_id, service)
        )
        exists = cursor.fetchone() is not None
        return exists
    except sqlite3.Error as e:
        raise StorageError("Failed to read API key. Please try again.") from e
    finally:
        conn.close()


init_db()
