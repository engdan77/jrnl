from pathlib import Path
from loguru import logger
import json

import platformdirs

CACHE_DIR = platformdirs.user_cache_dir("jrnl")
PREFERENCE_PATH = CACHE_DIR + "/preferences.json"

def load_preference(pref: str) -> str:
    try:
        with open(PREFERENCE_PATH, "r") as f:
            prefs = json.load(f)
            return prefs.get(pref, "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def store_preference(pref: str, value):
    try:
        with open(PREFERENCE_PATH, "r") as f:
            try:
                prefs = json.load(f)
            except json.JSONDecodeError:
                prefs = {}
    except FileNotFoundError:
        prefs = {}
    prefs[pref] = value
    with open(PREFERENCE_PATH, "w") as f:
        json.dump(prefs, f)


if not Path(CACHE_DIR).exists():
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"Created cache directory: {CACHE_DIR}")