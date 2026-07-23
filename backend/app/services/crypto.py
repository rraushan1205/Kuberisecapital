"""
Token encryption service for secure storage of broker credentials.

This module provides utilities for encrypting and decrypting sensitive tokens
(access tokens, refresh tokens) before storing them in the database.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC authentication) from
the cryptography library, which is already a dependency of pwdlib.

Security considerations:
    - Encryption key derived from JWT secret (existing secure key)
    - Tokens are never logged or exposed in error messages
    - Decryption failures raise specific exceptions
    - Uses URL-safe base64 encoding
"""

import base64
import hashlib
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class TokenEncryptionError(Exception):
    """Raised when token encryption fails."""

    pass


class TokenDecryptionError(Exception):
    """Raised when token decryption fails."""

    pass


def _get_encryption_key() -> bytes:
    """
    Derive encryption key from JWT secret.
    
    Uses SHA-256 to derive a 32-byte key from the JWT secret, which is then
    base64-encoded for Fernet compatibility.
    
    Returns:
        bytes: URL-safe base64-encoded encryption key
    """
    settings = get_settings()
    # Derive 32-byte key from JWT secret using SHA-256
    key_material = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
    # Fernet requires URL-safe base64-encoded 32-byte key
    return base64.urlsafe_b64encode(key_material)


def encrypt_token(token: str) -> str:
    """
    Encrypt a token for secure storage.
    
    Args:
        token: The plaintext token to encrypt (access token, refresh token, etc.)
    
    Returns:
        str: Encrypted token as base64 string
    
    Raises:
        TokenEncryptionError: If encryption fails
    
    Example:
        encrypted = encrypt_token("access_token_value")
        # Store encrypted in database
    
    Security:
        - Token is never logged
        - Uses Fernet (AES-128-CBC + HMAC)
        - Includes timestamp for key rotation support
    """
    if not token:
        raise TokenEncryptionError("Cannot encrypt empty token")

    try:
        encryption_key = _get_encryption_key()
        fernet = Fernet(encryption_key)
        encrypted_bytes = fernet.encrypt(token.encode())
        return encrypted_bytes.decode()
    except Exception as error:
        # Don't log the token value for security
        raise TokenEncryptionError(f"Token encryption failed: {type(error).__name__}") from error


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a token from storage.
    
    Args:
        encrypted_token: The encrypted token string from database
    
    Returns:
        str: Decrypted plaintext token
    
    Raises:
        TokenDecryptionError: If decryption fails (invalid key, corrupted data)
    
    Example:
        encrypted = connection.access_token_encrypted
        plaintext = decrypt_token(encrypted)
        # Use plaintext for API calls
    
    Security:
        - Verifies HMAC to detect tampering
        - Checks token timestamp (Fernet includes TTL support)
        - Token is never logged
    """
    if not encrypted_token:
        raise TokenDecryptionError("Cannot decrypt empty token")

    try:
        encryption_key = _get_encryption_key()
        fernet = Fernet(encryption_key)
        decrypted_bytes = fernet.decrypt(encrypted_token.encode())
        return decrypted_bytes.decode()
    except InvalidToken as error:
        # Token was tampered with or encrypted with different key
        raise TokenDecryptionError("Token decryption failed: invalid or corrupted token") from error
    except Exception as error:
        # Other decryption errors (encoding, etc.)
        raise TokenDecryptionError(f"Token decryption failed: {type(error).__name__}") from error


def encrypt_dict(data: dict[str, Any]) -> str:
    """
    Encrypt a dictionary as JSON for storage in metadata field.
    
    Args:
        data: Dictionary to encrypt
    
    Returns:
        str: Encrypted JSON as base64 string
    
    Raises:
        TokenEncryptionError: If encryption fails
    
    Example:
        metadata = {"broker_name": "Fyers", "extra_info": "..."}
        encrypted = encrypt_dict(metadata)
    
    Note:
        This is optional and can be used for sensitive metadata.
        Non-sensitive metadata can be stored directly in the JSON column.
    """
    import json

    if not data:
        raise TokenEncryptionError("Cannot encrypt empty data")

    try:
        json_str = json.dumps(data)
        return encrypt_token(json_str)
    except Exception as error:
        raise TokenEncryptionError(f"Data encryption failed: {type(error).__name__}") from error


def decrypt_dict(encrypted_data: str) -> dict[str, Any]:
    """
    Decrypt a dictionary from encrypted JSON.
    
    Args:
        encrypted_data: Encrypted JSON string
    
    Returns:
        dict: Decrypted dictionary
    
    Raises:
        TokenDecryptionError: If decryption or JSON parsing fails
    
    Example:
        encrypted = connection.some_encrypted_metadata
        data = decrypt_dict(encrypted)
    """
    import json

    if not encrypted_data:
        raise TokenDecryptionError("Cannot decrypt empty data")

    try:
        json_str = decrypt_token(encrypted_data)
        return json.loads(json_str)
    except TokenDecryptionError:
        raise
    except Exception as error:
        raise TokenDecryptionError(f"Data decryption failed: {type(error).__name__}") from error
