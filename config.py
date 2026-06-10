# =============================================================
# NEKOVA Language — Configuration & Version Info
# =============================================================

NEKOVA_VERSION  = "1.2.0"
NEKOVA_CODENAME = "Genesis"
NEKOVA_EXTENSION = ".nk"

# Legacy aliases — keeps old imports working during transition
AION_VERSION   = NEKOVA_VERSION
AION_CODENAME  = NEKOVA_CODENAME
AION_EXTENSION = NEKOVA_EXTENSION

class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"