from pathlib import Path
from loguru import logger

import platformdirs

CACHE_DIR = platformdirs.user_cache_dir("jrnl")
if not Path(CACHE_DIR).exists():
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"Created cache directory: {CACHE_DIR}")