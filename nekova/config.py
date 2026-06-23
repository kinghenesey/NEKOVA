# =============================================================
# NEKOVA Language — Configuration & Version Info
# =============================================================
NEKOVA_VERSION  = "1.3.0"
NEKOVA_CODENAME = "Genesis"
NEKOVA_EXTENSION = ".nk"
# Legacy aliases — keeps old imports working during transition
NEKOVA_VERSION   = NEKOVA_VERSION
NEKOVA_CODENAME  = NEKOVA_CODENAME
NEKOVA_EXTENSION = NEKOVA_EXTENSION
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

# ── Phase 3: nekova.toml support ──────────────────────────
from nekova.toml_loader import (
    NekovaConfig, ProjectConfig, AIConfig,
    DependenciesConfig, RunConfig,
    ConfigError, load_config, parse_config,
)