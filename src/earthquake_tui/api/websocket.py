"""P2P地震情報 WebSocket リアルタイム接続管理"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Callable, Optional

import websockets
from websockets.asyncio.client import connect

from .models import EEWInfo, QuakeInfo, TsunamiInfo

WS_URL = "wss://api.p2pquake.net/v2/ws"
# 開発用サンドボックス (過去データを繰り返し配信、EEWのテストに使える)
SANDBOX_WS_URL = "wss://api-realtime-sandbox.p2pquake.net/v2/ws"
RECONNECT_DELAY = 5  # 秒
MAX_RECONNECT_DELAY = 60  # 秒

log = logging.getLogger(__name__)


class P2PQuakeWebSocket:
    """P2P地震情報 WebSocket 接続管理

    10分で自動切断されるため、自動再接続ロジックを含む。
    """

    def __init__(self) -> None:
        self._ws = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._on_quake: Optional[Callable[[QuakeInfo], None]] = None
        self._on_tsunami: Optional[Callable[[TsunamiInfo], None]] = None
        self._on_eew: Optional[Callable[[EEWInfo], None]] = None
        self._on_status: Optional[Callable[[bool], None]] = None
        self._reconnect_delay = RECONNECT_DELAY
        # EQTUI_SANDBOX=1 でサンドボックスAPIに接続 (EEW動作確認用)
        self._url = SANDBOX_WS_URL if os.environ.get("EQTUI_SANDBOX") else WS_URL

    def on_quake(self, callback: Callable[[QuakeInfo], None]) -> None:
        self._on_quake = callback

    def on_tsunami(self, callback: Callable[[TsunamiInfo], None]) -> None:
        self._on_tsunami = callback

    def on_eew(self, callback: Callable[[EEWInfo], None]) -> None:
        self._on_eew = callback

    def on_status_change(self, callback: Callable[[bool], None]) -> None:
        self._on_status = callback

    def start(self) -> asyncio.Task:
        """WebSocket接続を開始"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        return self._task

    async def stop(self) -> None:
        """接続を停止"""
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        """再接続ループ"""
        while self._running:
            try:
                await self._connect_and_listen()
            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedError,
                OSError,
                asyncio.TimeoutError,
            ) as e:
                log.warning("WebSocket切断: %s", e)
                self._notify_status(False)
            except Exception as e:
                log.error("WebSocketエラー: %s", e)
                self._notify_status(False)

            if self._running:
                log.info("再接続まで %d秒待機...", self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 1.5, MAX_RECONNECT_DELAY
                )

    async def _connect_and_listen(self) -> None:
        """WebSocket接続して受信"""
        log.info("WebSocket接続中: %s", self._url)
        async with connect(self._url, close_timeout=10) as ws:
            self._ws = ws
            self._reconnect_delay = RECONNECT_DELAY
            self._notify_status(True)
            log.info("WebSocket接続完了")

            async for message in ws:
                try:
                    data = json.loads(message)
                    self._handle_message(data)
                except json.JSONDecodeError:
                    log.warning("不正なJSONを受信")

    def _handle_message(self, data: dict) -> None:
        """受信メッセージの処理"""
        code = data.get("code")

        if code == 551 and self._on_quake:
            quake = QuakeInfo.from_dict(data)
            self._on_quake(quake)
        elif code == 552 and self._on_tsunami:
            tsunami = TsunamiInfo.from_dict(data)
            self._on_tsunami(tsunami)
        elif code == 556 and self._on_eew:
            eew = EEWInfo.from_dict(data)
            self._on_eew(eew)

    def _notify_status(self, connected: bool) -> None:
        if self._on_status:
            self._on_status(connected)
