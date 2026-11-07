import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent

if getattr(sys, "frozen", False):
    # Packaged exe: Program Files (or wherever it's installed to) isn't
    # guaranteed writable, so the app-data folder is the fixed, always-known
    # location for the small bootstrap config file that says where the
    # user's actual data directory is (which itself can be moved anywhere,
    # see settings router).
    APP_DATA_ROOT = Path(os.environ["LOCALAPPDATA"]) / "PatentManager"
else:
    APP_DATA_ROOT = BASE_DIR

APP_DATA_ROOT.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = APP_DATA_ROOT / "config.json"


def _default_storage_dir() -> Path:
    if getattr(sys, "frozen", False):
        return APP_DATA_ROOT / "storage"
    return BASE_DIR / "storage"


def _load_storage_dir() -> Path:
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            custom = config.get("data_dir")
            if custom:
                return Path(custom)
        except (json.JSONDecodeError, OSError):
            pass
    return _default_storage_dir()


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config_value(key: str, value) -> None:
    config = load_config()
    config[key] = value
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def save_storage_dir(path: Path) -> None:
    save_config_value("data_dir", str(path))


STORAGE_DIR = _load_storage_dir()
UPLOADS_DIR = STORAGE_DIR / "uploads"
CASE_FILES_DIR = STORAGE_DIR / "case_files"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
CASE_FILES_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{STORAGE_DIR / 'patent.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
