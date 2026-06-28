# =============================================================
# NEKOVA Standard Library — Crypto Module (Phase 8)
# =============================================================
# Usage in NEKOVA:
#   use crypto
#   let h  = hash("hello")              → SHA-256 hex digest
#   let h2 = hash("hello", "md5")       → MD5 hex digest
#   let hpw = hash_password("secret")   → bcrypt hash
#   show check_password("secret", hpw)  → true
#   let tok = token(32)                 → 32-byte secure random hex
#   let b64 = encode_b64("hello")       → base64 encoded string
#   let raw = decode_b64(b64)           → "hello"
#   let sig = hmac("message", "key")    → HMAC-SHA256 hex
#   show hmac_valid("msg", "key", sig)  → true

import hashlib as _hashlib
import hmac as _hmac_lib
import secrets as _secrets
import base64 as _base64


# ── Hashing ───────────────────────────────────────────────────

def _hash(value: str, algorithm: str = "sha256") -> str:
    """
    Hash a string using the given algorithm.
    Supported: sha256 (default), sha512, sha1, md5, sha3_256
    """
    alg = str(algorithm).lower().replace("-", "_")
    try:
        h = _hashlib.new(alg)
        h.update(str(value).encode("utf-8"))
        return h.hexdigest()
    except ValueError:
        raise RuntimeError(
            f"Unknown hash algorithm '{algorithm}'.\n"
            f"  Supported: sha256, sha512, sha1, md5, sha3_256"
        )


def _hash_file(filepath: str, algorithm: str = "sha256") -> str:
    """Hash the contents of a file."""
    import os
    alg = str(algorithm).lower().replace("-", "_")
    if not os.path.exists(filepath):
        raise RuntimeError(f"File not found: '{filepath}'")
    h = _hashlib.new(alg)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Password hashing (bcrypt-style via hashlib PBKDF2) ────────

def _hash_password(password: str, rounds: int = 260000) -> str:
    """
    Hash a password securely using PBKDF2-HMAC-SHA256.
    Returns a string that includes the salt, so you only
    need to store this one value.
    Format: pbkdf2$<rounds>$<salt_hex>$<hash_hex>
    """
    salt   = _secrets.token_bytes(32)
    dk     = _hashlib.pbkdf2_hmac(
                 "sha256",
                 str(password).encode("utf-8"),
                 salt,
                 int(rounds)
             )
    salt_hex = salt.hex()
    hash_hex = dk.hex()
    return f"pbkdf2${rounds}${salt_hex}${hash_hex}"


def _check_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a hash created by hash_password().
    Returns true if the password matches, false otherwise.
    """
    try:
        parts = str(hashed).split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2":
            return False
        _, rounds_str, salt_hex, stored_hash = parts
        rounds = int(rounds_str)
        salt   = bytes.fromhex(salt_hex)
        dk     = _hashlib.pbkdf2_hmac(
                     "sha256",
                     str(password).encode("utf-8"),
                     salt,
                     rounds
                 )
        return _secrets.compare_digest(dk.hex(), stored_hash)
    except Exception:
        return False


# ── Secure tokens ─────────────────────────────────────────────

def _token(length: int = 32) -> str:
    """Generate a cryptographically secure random hex token."""
    return _secrets.token_hex(int(length))


def _token_bytes(length: int = 32) -> bytes:
    """Generate cryptographically secure random bytes."""
    return _secrets.token_bytes(int(length))


def _token_url(length: int = 32) -> str:
    """Generate a URL-safe random token (no +/= chars)."""
    return _secrets.token_urlsafe(int(length))


# ── Base64 ────────────────────────────────────────────────────

def _encode_b64(value: str) -> str:
    """Base64-encode a string."""
    return _base64.b64encode(str(value).encode("utf-8")).decode("utf-8")


def _decode_b64(value: str) -> str:
    """Decode a base64-encoded string."""
    try:
        return _base64.b64decode(str(value)).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"base64 decode failed: {e}")


def _encode_b64_url(value: str) -> str:
    """URL-safe base64 encode."""
    return _base64.urlsafe_b64encode(str(value).encode("utf-8")).decode("utf-8")


def _decode_b64_url(value: str) -> str:
    """URL-safe base64 decode."""
    try:
        return _base64.urlsafe_b64decode(str(value)).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"base64url decode failed: {e}")


# ── HMAC ──────────────────────────────────────────────────────

def _hmac(message: str, key: str, algorithm: str = "sha256") -> str:
    """
    Compute HMAC of a message with a key.
    Returns hex digest.
    """
    alg = str(algorithm).lower().replace("-", "_")
    sig = _hmac_lib.new(
        str(key).encode("utf-8"),
        str(message).encode("utf-8"),
        digestmod=alg,
    )
    return sig.hexdigest()


def _hmac_valid(message: str, key: str, signature: str, algorithm: str = "sha256") -> bool:
    """Verify an HMAC signature in constant time."""
    try:
        expected = _hmac(message, key, algorithm)
        return _secrets.compare_digest(str(signature), expected)
    except Exception:
        return False


# ── Convenience ───────────────────────────────────────────────

def _md5(value: str) -> str:
    return _hash(value, "md5")


def _sha1(value: str) -> str:
    return _hash(value, "sha1")


def _sha256(value: str) -> str:
    return _hash(value, "sha256")


def _sha512(value: str) -> str:
    return _hash(value, "sha512")


def load() -> dict:
    return {
        # General hashing
        "hash":          _hash,
        "hash_file":     _hash_file,
        "md5":           _md5,
        "sha1":          _sha1,
        "sha256":        _sha256,
        "sha512":        _sha512,

        # Password security
        "hash_password":  _hash_password,
        "check_password": _check_password,

        # Secure tokens
        "token":          _token,
        "token_url":      _token_url,
        "token_bytes":    _token_bytes,

        # Base64
        "encode_b64":     _encode_b64,
        "decode_b64":     _decode_b64,
        "encode_b64_url": _encode_b64_url,
        "decode_b64_url": _decode_b64_url,

        # HMAC
        "hmac":           _hmac,
        "hmac_valid":     _hmac_valid,
    }