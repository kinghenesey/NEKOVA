# =============================================================
# NEKOVA Standard Library — Datetime Module
# =============================================================
# Usage in NEKOVA:
#   use datetime
#   show today()         → 2026-05-13
#   show now()           → 2026-05-13 22:30:00
#   show year()          → 2026
#   show month()         → 5
#   show day()           → 13
#   show hour()          → 22
#   show minute()        → 30
#   show timestamp()     → 1747172200.0

from datetime import datetime, date


def load() -> dict:
    """
    Returns all datetime functions to be loaded
    into the NEKOVA environment.
    """
    return {
        # Current date and time
        "today":      lambda: str(date.today()),
        "now":        lambda: str(datetime.now().strftime(
                          "%Y-%m-%d %H:%M:%S")),
        "timestamp":  lambda: datetime.now().timestamp(),

        # Date parts
        "year":       lambda: datetime.now().year,
        "month":      lambda: datetime.now().month,
        "day":        lambda: datetime.now().day,

        # Time parts
        "hour":       lambda: datetime.now().hour,
        "minute":     lambda: datetime.now().minute,
        "second":     lambda: datetime.now().second,

        # Formatting
        "format_date": lambda fmt="%Y-%m-%d": (
            datetime.now().strftime(str(fmt))
        ),

        # Parsing
        "parse_date": lambda s, fmt="%Y-%m-%d": (
            str(datetime.strptime(str(s), str(fmt)).date())
        ),
    }