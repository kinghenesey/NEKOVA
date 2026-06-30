# =============================================================
# NEKOVA Language — Configuration & Version Info
# =============================================================
# ── Single source of truth for the version ────────────────────
# When bumping: change ONLY this line. Every other file reads
# from here. Do NOT hardcode the version anywhere else.
NEKOVA_VERSION   = "1.9.0"
NEKOVA_CODENAME  = "Genesis"
NEKOVA_EXTENSION = ".nk"
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