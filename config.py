from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
USERS_DIR = BASE_DIR / "users"
LOG_DIR = BASE_DIR / "logs"
MEDIA_DIR = BASE_DIR / "downloads"

USERS_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
MEDIA_DIR.mkdir(exist_ok=True)

COMMAND_PREFIX = "."
SAVE_EXTRACTED_TO_SAVED_MESSAGES = True
SAVE_EXTRACTED_TO_LOCAL = True

# Public/free endpoints (no key required).
FREE_AI_ENDPOINTS = [
    "https://devtoolbox.co/api/ai",  # best effort, may change
    "https://api.duckduckgo.com/",
]
FREE_TRANSLATE_ENDPOINT = "https://libretranslate.de/translate"
URL_SHORTENER_ENDPOINT = "https://is.gd/create.php"

DEFAULT_ANTISPAM_LIMIT = 6
DEFAULT_ANTISPAM_WINDOW = 12
