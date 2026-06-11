# NEKOVA Package — validation
# Input validation helpers

import re

def load() -> dict:
    return {
        "is_email":           _is_email,
        "is_phone":           _is_phone,
        "is_url":             _is_url,
        "is_strong_password": _is_strong_password,
    }

def _is_email(value: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, str(value)))

def _is_phone(value: str) -> bool:
    pattern = r"^\+?[0-9]{7,15}$"
    return bool(re.match(pattern, str(value).replace(" ", "")))

def _is_url(value: str) -> bool:
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, str(value)))

def _is_strong_password(value: str) -> bool:
    s = str(value)
    return (len(s) >= 8 and
            any(c.isupper() for c in s) and
            any(c.islower() for c in s) and
            any(c.isdigit() for c in s))

