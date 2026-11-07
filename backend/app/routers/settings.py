import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import STORAGE_DIR, engine, load_config, save_config_value, save_storage_dir

router = APIRouter(prefix="/api/settings", tags=["settings"])


class DataDirOut(BaseModel):
    data_dir: str
    # Kept in the app config file rather than browser storage: the desktop
    # window uses a fresh port and private storage on every launch.
    onboarding_done: bool = False


class OnboardingState(BaseModel):
    done: bool


class DataDirChange(BaseModel):
    new_path: str


@router.get("", response_model=DataDirOut)
def get_settings():
    return DataDirOut(
        data_dir=str(STORAGE_DIR), onboarding_done=bool(load_config().get("onboarding_done"))
    )


@router.post("/onboarding")
def set_onboarding(payload: OnboardingState):
    save_config_value("onboarding_done", payload.done)
    return {"ok": True}


@router.post("/data-dir")
def change_data_dir(payload: DataDirChange):
    new_path = Path(payload.new_path).expanduser().resolve()
    current = STORAGE_DIR.resolve()
    if new_path == current:
        raise HTTPException(status_code=400, detail="新路径和当前路径相同")

    try:
        new_path.mkdir(parents=True, exist_ok=True)
        probe = new_path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"目标路径不可写：{exc}") from exc

    for name in ("patent.db", "uploads", "case_files"):
        if (new_path / name).exists():
            raise HTTPException(
                status_code=400,
                detail=f"目标目录里已经存在「{name}」，请换一个空目录，避免覆盖已有内容",
            )

    # SQLite keeps the db file open on Windows, which blocks moving/renaming
    # it — release the connection pool first. The engine is now unusable in
    # this process, which is fine: the app must be restarted for the new
    # path to take effect anyway.
    engine.dispose()

    for name in ("patent.db", "uploads", "case_files"):
        src = current / name
        if src.exists():
            shutil.move(str(src), str(new_path / name))

    save_storage_dir(new_path)

    return {"ok": True, "message": "数据已迁移，请关闭并重新打开程序以生效"}
