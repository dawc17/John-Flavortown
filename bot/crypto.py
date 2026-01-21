"""
Cryptographic utilities for secure API key storage.

Uses Fernet symmetric encryption with PBKDF2 key derivation.
The bot operator cannot decrypt keys without knowing each user's password.
"""

import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # thats a lot :D
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_api_key(api_key: str, password: str) -> tuple[str, str]:
    """
    Encrypt an API key with a user-provided password.
    
    Returns:
        tuple of (encrypted_key_b64, salt_b64) - both base64 encoded strings
        suitable for database storage.
    """
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(api_key.encode())
    
    return base64.urlsafe_b64encode(encrypted).decode(), base64.urlsafe_b64encode(salt).decode()


def decrypt_api_key(encrypted_key_b64: str, salt_b64: str, password: str) -> str | None:
    """
    Decrypt an API key using the user's password.
    
    Returns:
        The decrypted API key, or None if decryption fails (wrong password).
    """
    try:
        encrypted = base64.urlsafe_b64decode(encrypted_key_b64.encode())
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        key = _derive_key(password, salt)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode()
    except (InvalidToken, ValueError):
        return None
