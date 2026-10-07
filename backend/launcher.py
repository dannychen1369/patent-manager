"""Desktop entry point: runs the FastAPI app in a background thread and shows
it in a native window via pywebview, instead of requiring the user to open a
browser tab. This is what gets built into the packaged .exe.
"""
import os
import socket
import sys
import threading
import time

# PyInstaller's --windowed mode has no console, so sys.stdout/stderr are None;
# uvicorn/click write startup banners to them and crash without this.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import uvicorn
import webview

from app.main import app


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_server(port: int) -> None:
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def wait_until_up(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("本地服务启动超时")


def main() -> None:
    port = find_free_port()
    threading.Thread(target=run_server, args=(port,), daemon=True).start()
    wait_until_up(port)

    webview.create_window(
        "专利管理系统",
        f"http://127.0.0.1:{port}",
        width=1360,
        height=860,
        min_size=(1024, 700),
    )
    webview.start()


if __name__ == "__main__":
    main()
