import datetime
from pathlib import Path
from loguru import logger
import json
import platformdirs

from jrnl.tasks.journal import get_journal_file_path

CACHE_DIR = platformdirs.user_cache_dir("jrnl")
PREFERENCE_PATH = CACHE_DIR + "/preferences.json"

BACKUP_DIR = Path(platformdirs.user_config_dir("jrnl") + "/backup")


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


def get_current_backup(interval: str = 'weekly') -> Path | None:
    current_backup = list(BACKUP_DIR.glob(f"{interval}_*.txt"))
    return current_backup[0] if current_backup else None

def make_backup_of_journal():
    journal_path = get_journal_file_path()
    backup_intervals = {
        'weekly': {'days': 7},
        'monthly': {'days': 30},
        'yearly': {'days': 365},
    }
    now = datetime.datetime.now()

    for interval, criteria in backup_intervals.items():
        new_backup = BACKUP_DIR / f'{interval}_{now:%Y%m%d}_journal.txt'
        if backup := get_current_backup(interval=interval):
            backup_create_dt = datetime.datetime.fromtimestamp(backup.stat().st_ctime)
            backup_name_type = backup.name.split("_")[0]
            if backup_name_type != interval:
                continue
            if now - backup_create_dt > datetime.timedelta(**criteria):
                new_backup.write_bytes(Path(journal_path).read_bytes())
                backup.unlink()
                logger.info(f"Created updated backup: {new_backup.as_posix()} and removed old backup: {backup.as_posix()}")
                continue
        else:
            new_backup.write_bytes(Path(journal_path).read_bytes())
            logger.info(f"Created new backup: {new_backup.as_posix()} for {interval}")


if not Path(CACHE_DIR).exists():
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"Created cache directory: {CACHE_DIR}")


if not Path(BACKUP_DIR).exists():
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(
        f"Created backup directory: {BACKUP_DIR}. This directory will be used to backup your journal files."
    )

make_backup_of_journal()