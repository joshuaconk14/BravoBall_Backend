#!/usr/bin/env python3
"""
generate_encryption_keys.py
Generate encryption keys for secure data storage.

Run this script to generate the required encryption keys for your .env file.
"""

from cryptography.fernet import Fernet
import secrets
import hashlib

def generate_encryption_key():
    """Generate a Fernet encryption key."""
    return Fernet.generate_key().decode()

def generate_hash_salt():
    """Generate a random salt for hashing."""
    return secrets.token_urlsafe(32)

def main():
    print("=" * 60)
    print("Encryption Key Generator")
    print("=" * 60)
    print()
    print("Add these to your .env file:")
    print()
    
    encryption_key = generate_encryption_key()
    hash_salt = generate_hash_salt()
    
    print(f"ENCRYPTION_KEY={encryption_key}")
    print(f"HASH_SALT={hash_salt}")
    print()
    print("=" * 60)
    print("Security Notes:")
    print("- Keep these keys secure and never commit them to version control")
    print("- Use different keys for development, staging, and production")
    print("- If keys are compromised, regenerate them and re-encrypt all data")
    print("=" * 60)

if __name__ == "__main__":
    main()

