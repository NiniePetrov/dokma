# config.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# ─── Diretórios ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH  = DATA_DIR / "validador.db"

# ─── Modelo — Claude via API ──────────────────────────────────
# Usado por todos os agentes
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME        = "claude-sonnet-4-20250514"

# ─── Parâmetros ───────────────────────────────────────────────
TEMPERATURE = 0.2
MAX_TOKENS  = 4096

# ─── Aplicação ────────────────────────────────────────────────
APP_TITLE   = "Dokma"
APP_VERSION = "0.1.0"
LANGUAGE    = "pt-BR"

# ─── Garantir que data/ existe ────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)