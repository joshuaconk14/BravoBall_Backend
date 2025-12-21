"""
encryption.py
Secure encryption utilities for sensitive data at rest.

Best Practices:
- Uses Fernet (symmetric encryption) for reversible encryption
- Uses SHA-256 for one-way hashing
- Keys stored in environment variables
- Deterministic encryption for fields that need to be queried
"""

import os
import hashlib
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class EncryptionService:
    """
    Encryption service for sensitive data at rest.
    
    Uses Fernet symmetric encryption with keys derived from environment variables.
    Follows best practices for key management and encryption.
    """
    
    def __init__(self):
        """Initialize encryption service with keys from environment."""
        # Get encryption key from environment (optional - only needed for reversible encryption)
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if encryption_key:
            # Validate key format
            try:
                self.cipher = Fernet(encryption_key.encode())
            except Exception as e:
                raise ValueError(
                    f"Invalid ENCRYPTION_KEY format. Error: {str(e)}. "
                    "Generate a new key using: python scripts/generate_encryption_keys.py"
                )
        else:
            # Encryption key not required if only using hashing
            self.cipher = None
        
        # Salt for hashing (use env variable or default)
        hash_salt = os.getenv("HASH_SALT", "default_salt_change_in_production")
        self.hash_salt = hash_salt.encode() if isinstance(hash_salt, str) else hash_salt
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string value (reversible encryption).
        
        Requires ENCRYPTION_KEY to be set in environment.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if plaintext is None:
            return None
        
        if not self.cipher:
            raise ValueError(
                "ENCRYPTION_KEY environment variable is required for encryption. "
                "Generate a key using: python scripts/generate_encryption_keys.py"
            )
        
        if not isinstance(plaintext, str):
            plaintext = str(plaintext)
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string value.
        
        Requires ENCRYPTION_KEY to be set in environment.
        
        Args:
            ciphertext: The base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if ciphertext is None:
            return None
        
        if not self.cipher:
            raise ValueError(
                "ENCRYPTION_KEY environment variable is required for decryption. "
                "Generate a key using: python scripts/generate_encryption_keys.py"
            )
        
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {str(e)}")
    
    def encrypt_deterministic(self, plaintext: str) -> str:
        """
        Deterministic encryption for fields that need to be queried.
        
        IMPORTANT: This uses a hash-based approach for true determinism.
        The "encrypted" value is actually a hash, which is one-way.
        Use hash_transaction_id() instead for better semantics.
        
        For true reversible deterministic encryption, we'd need a different
        cipher mode, but for transaction IDs, hashing is sufficient since
        we can query by re-hashing the search value.
        
        Args:
            plaintext: The string to encrypt deterministically
            
        Returns:
            Hashed value (deterministic, same input = same output)
        """
        # For transaction IDs, we use hashing since we don't need to decrypt,
        # just verify uniqueness and query. This is more secure.
        return self.hash_for_query(plaintext)
    
    def decrypt_deterministic(self, ciphertext: str) -> str:
        """
        "Decrypt" a deterministically encrypted value.
        
        Note: Since we're using hashing, this always returns None.
        Use hash_transaction_id() to create searchable hashes instead.
        
        Args:
            ciphertext: The hashed string
            
        Returns:
            None (hashing is one-way)
        """
        # Hashing is one-way, so we can't decrypt
        # Return None to indicate this
        return None
    
    def hash(self, value: str, salt: Optional[str] = None) -> str:
        """
        One-way hash a value (for device fingerprints).
        
        Uses SHA-256 with salt. This is irreversible.
        Use for values that don't need to be decrypted, only verified.
        
        Args:
            value: The string to hash
            salt: Optional salt for additional security (uses HASH_SALT from env if not provided)
            
        Returns:
            Hexadecimal hash string
        """
        if value is None:
            return None
        
        if not isinstance(value, str):
            value = str(value)
        
        # Use salt if provided, otherwise use the instance salt
        if salt:
            salted_value = f"{salt}{value}"
        else:
            salt_str = self.hash_salt.decode() if isinstance(self.hash_salt, bytes) else str(self.hash_salt)
            salted_value = f"{salt_str}{value}"
        
        return hashlib.sha256(salted_value.encode()).hexdigest()
    
    def hash_for_query(self, value: str) -> str:
        """
        Hash a value for database queries (deterministic).
        
        This produces the same hash for the same input, allowing
        database queries to work. Use this for transaction IDs and
        device fingerprints that need to be queried but don't need to be decrypted.
        
        Args:
            value: The string to hash
            
        Returns:
            Hexadecimal hash string (same input = same output)
        """
        return self.hash(value)


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get or create the global encryption service instance.
    
    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def hash_transaction_id(transaction_id: str) -> str:
    """
    Hash a transaction ID deterministically (for database queries and uniqueness).
    
    Uses SHA-256 with salt to create a deterministic hash that can be used
    for database queries and unique constraints. This is one-way (more secure
    than reversible encryption for IDs).
    
    Args:
        transaction_id: The transaction ID to hash
        
    Returns:
        Hashed transaction ID (same input = same output)
    """
    if transaction_id is None:
        return None
    return get_encryption_service().hash_for_query(transaction_id)


def encrypt_transaction_id(transaction_id: str) -> str:
    """
    Encrypt a transaction ID for storage (reversible).
    
    Note: For querying, use hash_transaction_id() instead.
    This encrypts the full value if you need to retrieve the original.
    
    Args:
        transaction_id: The transaction ID to encrypt
        
    Returns:
        Encrypted transaction ID
    """
    if transaction_id is None:
        return None
    return get_encryption_service().encrypt(transaction_id)


def decrypt_transaction_id(encrypted_transaction_id: str) -> str:
    """
    Decrypt a transaction ID.
    
    Args:
        encrypted_transaction_id: The encrypted transaction ID
        
    Returns:
        Decrypted transaction ID
    """
    if encrypted_transaction_id is None:
        return None
    return get_encryption_service().decrypt(encrypted_transaction_id)


def hash_device_fingerprint(device_fingerprint: str) -> str:
    """
    Hash a device fingerprint (one-way, for storage).
    
    Args:
        device_fingerprint: The device fingerprint to hash
        
    Returns:
        Hashed device fingerprint
    """
    if device_fingerprint is None:
        return None
    return get_encryption_service().hash_for_query(device_fingerprint)


def verify_device_fingerprint(device_fingerprint: str, stored_hash: str) -> bool:
    """
    Verify a device fingerprint against a stored hash.
    
    Args:
        device_fingerprint: The device fingerprint to verify
        stored_hash: The stored hash to compare against
        
    Returns:
        True if the fingerprint matches the hash
    """
    if device_fingerprint is None or stored_hash is None:
        return False
    
    computed_hash = hash_device_fingerprint(device_fingerprint)
    return computed_hash == stored_hash

