"""OS通知

ターミナルを見ていないときでも地震を知らせるため、OS のデスクトップ通知を出す。

- macOS: ``osascript`` の ``display notification``
- Linux: ``notify-send`` (未インストールなら何もしない)
- それ以外: 何もしない (音アラートは呼び出し側の端末ベルが担当する)

通知の失敗はアプリの動作を妨げてはいけないため、例外は送出せずログに残すだけにする。
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sys

log = logging.getLogger(__name__)

APP_NAME = "Kanameishi"

# 通知コマンドが応答しない場合に待ち続けないための上限 (秒)
TIMEOUT = 5.0


def is_supported() -> bool:
    """この環境でOS通知を出せるか"""
    if sys.platform == "darwin":
        return shutil.which("osascript") is not None
    return shutil.which("notify-send") is not None


def _applescript_quote(text: str) -> str:
    """AppleScript の文字列リテラルとして安全な形にする"""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _build_command(title: str, message: str, urgent: bool) -> list[str] | None:
    """プラットフォームに応じた通知コマンドを組み立てる"""
    if sys.platform == "darwin":
        if shutil.which("osascript") is None:
            return None
        script = (
            f"display notification {_applescript_quote(message)}"
            f" with title {_applescript_quote(APP_NAME)}"
            f" subtitle {_applescript_quote(title)}"
        )
        return ["osascript", "-e", script]

    if shutil.which("notify-send") is None:
        return None
    return [
        "notify-send",
        "--app-name",
        APP_NAME,
        "--urgency",
        "critical" if urgent else "normal",
        title,
        message,
    ]


async def send(title: str, message: str, *, urgent: bool = False) -> None:
    """OS通知を送る (失敗しても例外を投げない)"""
    command = _build_command(title, message, urgent)
    if command is None:
        return

    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError as e:
        log.warning("OS通知の起動に失敗しました: %s", e)
        return

    try:
        await asyncio.wait_for(proc.wait(), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        log.warning("OS通知がタイムアウトしました: %s", command[0])
        proc.kill()
        await proc.wait()
