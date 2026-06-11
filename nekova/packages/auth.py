# NEKOVA Package — auth
# Basic authentication utilities

import hashlib
import secrets

def load() -> dict:
    return {
        "hash_password":    _hash_password,
        "check_password":   _check_password,
        "generate_token":   _generate_token,
    }

def _hash_password(password: str) -> str:
    salt   = secrets.token_hex(16)
    hashed = hashlib.sha256(
        (salt + str(password)).encode()
    ).hexdigest()
    return f"{salt}:{hashed}"

def _check_password(password: str, hashed: str) -> bool:
    try:
        salt, hash_val = hashed.split(":")
        check = hashlib.sha256(
            (salt + str(password)).encode()
        ).hexdigest()
        return check == hash_val
    except Exception:
        return False

def _generate_token(length: int = 32) -> str:
    return secrets.token_hex(int(length))

