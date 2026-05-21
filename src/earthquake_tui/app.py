"""強震モニタ TUI - メインアプリケーション"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static
from textual.binding import Binding

from .api.client import P2PQuakeClient
from .api.websocket import P2PQuakeWebSocket
from .api.models import QuakeInfo, TsunamiInfo
from .widgets.japan_map import JapanMapWidget
from .widgets.quake_detail import QuakeDetailWidget
from .widgets.quake_table import QuakeTableWidget
from .widgets.intensity_bar import IntensityBarWidget
from .widgets.status_bar import StatusBarWidget

log = logging.getLogger(__name__)

CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"

# 自動更新間隔 (秒)
POLL_INTERVAL = 60


class EarthquakeApp(App):
    """強震モニタ TUI アプリケーション"""

    TITLE = "強震モニタ"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("q", "quit", "終了", priority=True),
        Binding("r", "refresh", "更新"),
        Binding("d", "show_detail", "詳細"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._client = P2PQuakeClient()
        self._ws = P2PQuakeWebSocket()
        self._quakes: list[QuakeInfo] = []
        self._latest_quake: QuakeInfo | None = None

    def compose(self) -> ComposeResult:
        # ヘッダー
        yield Static("🔴 強震モニタ  ━  リアルタイム地震情報", id="app-header")

        # メインコンテンツ
        with Horizontal(id="main-content"):
            # 左: 日本地図
            with Container(id="map-panel"):
                yield Static("🗾 日本地図", id="map-panel-title")
                yield JapanMapWidget(id="japan-map")

            # 右: 地震詳細 + 震度分布
            with Vertical(id="info-panel"):
                with Container(id="detail-panel"):
                    yield Static("📋 最新地震情報", id="detail-panel-title")
                    yield QuakeDetailWidget(id="quake-detail")

                with Container(id="intensity-panel"):
                    yield Static("📊 震度分布", id="intensity-panel-title")
                    yield IntensityBarWidget(id="intensity-bar")

        # 下部: 地震履歴
        with Container(id="history-panel"):
            yield Static("📜 地震履歴", id="history-panel-title")
            yield QuakeTableWidget(id="quake-table")

        # ステータスバー
        yield StatusBarWidget(id="status-bar")

    async def on_mount(self) -> None:
        """アプリ起動時の初期化"""
        # WebSocket コールバック設定
        self._ws.on_quake(self._on_ws_quake)
        self._ws.on_tsunami(self._on_ws_tsunami)
        self._ws.on_status_change(self._on_ws_status)

        # 初期データ取得
        await self._fetch_initial_data()

        # WebSocket 接続開始
        self._ws.start()

        # 定期ポーリング (REST フォールバック)
        self.set_interval(POLL_INTERVAL, self._poll_data)

    async def on_unmount(self) -> None:
        """アプリ終了時のクリーンアップ"""
        try:
            await self._ws.stop()
        except Exception:
            pass
        try:
            await self._client.close()
        except Exception:
            pass

    async def _fetch_initial_data(self) -> None:
        """初期データをREST APIから取得"""
        try:
            quakes = await self._client.get_quake_list(limit=20)
            self._quakes = quakes

            # テーブル更新
            table = self.query_one("#quake-table", QuakeTableWidget)
            table.update_quakes(quakes)

            # 最新の地震で詳細・地図を更新
            if quakes:
                self._select_quake(quakes[0])

            self._update_timestamp()
        except Exception as e:
            log.error("初期データ取得エラー: %s", e)
            self.notify(f"データ取得エラー: {e}", severity="error", timeout=5)

    async def _poll_data(self) -> None:
        """定期ポーリングでデータ更新"""
        try:
            quakes = await self._client.get_quake_list(limit=20)
            if quakes:
                self._quakes = quakes
                table = self.query_one("#quake-table", QuakeTableWidget)
                table.update_quakes(quakes)
                self._update_timestamp()
        except Exception as e:
            log.warning("ポーリングエラー: %s", e)

    def _on_ws_quake(self, quake: QuakeInfo) -> None:
        """WebSocketから地震情報を受信"""
        self.call_from_thread(self._handle_new_quake, quake)

    def _on_ws_tsunami(self, tsunami: TsunamiInfo) -> None:
        """WebSocketから津波情報を受信"""
        self.call_from_thread(self._handle_tsunami, tsunami)

    def _on_ws_status(self, connected: bool) -> None:
        """WebSocket接続状態変更"""
        self.call_from_thread(self._update_ws_status, connected)

    def _handle_new_quake(self, quake: QuakeInfo) -> None:
        """新しい地震情報を処理"""
        # リストの先頭に追加
        self._quakes.insert(0, quake)
        self._quakes = self._quakes[:50]  # 最大50件

        table = self.query_one("#quake-table", QuakeTableWidget)
        table.update_quakes(self._quakes)

        # 詳細表示を更新
        self._select_quake(quake)
        self._update_timestamp()

        # 通知
        self.notify(
            f"🔴 地震速報: {quake.location} M{quake.magnitude:.1f}",
            severity="warning",
            timeout=10,
        )

    def _handle_tsunami(self, tsunami: TsunamiInfo) -> None:
        """津波情報を処理"""
        if not tsunami.cancelled:
            areas = ", ".join(a.name for a in tsunami.areas[:3])
            self.notify(
                f"🌊 津波予報: {areas}",
                severity="error",
                timeout=15,
            )

    def _update_ws_status(self, connected: bool) -> None:
        """WebSocket接続状態UIを更新"""
        status_bar = self.query_one("#status-bar", StatusBarWidget)
        status_bar.ws_connected = connected

    def _select_quake(self, quake: QuakeInfo) -> None:
        """地震を選択して詳細表示を更新"""
        self._latest_quake = quake

        detail = self.query_one("#quake-detail", QuakeDetailWidget)
        detail.update_quake(quake)

        japan_map = self.query_one("#japan-map", JapanMapWidget)
        japan_map.update_quake(quake)

        intensity = self.query_one("#intensity-bar", IntensityBarWidget)
        intensity.update_quake(quake)

    def _update_timestamp(self) -> None:
        """最終更新時刻を更新"""
        now = datetime.now().strftime("%H:%M:%S")
        status_bar = self.query_one("#status-bar", StatusBarWidget)
        status_bar.last_update = now

    # ── アクション ──────────────────────────

    def action_refresh(self) -> None:
        """手動更新"""
        self.run_worker(self._fetch_initial_data())

    def action_show_detail(self) -> None:
        """選択中の地震の詳細を表示"""
        table = self.query_one("#quake-table", QuakeTableWidget)
        quake = table.get_selected_quake()
        if quake:
            self._select_quake(quake)

    def on_data_table_row_selected(self, event: QuakeTableWidget.RowSelected) -> None:
        """テーブル行選択イベント"""
        table = self.query_one("#quake-table", QuakeTableWidget)
        quake = table.get_selected_quake()
        if quake:
            self._select_quake(quake)

    def on_data_table_row_highlighted(self, event: QuakeTableWidget.RowHighlighted) -> None:
        """テーブル行ハイライト変更イベント（カーソル移動で連動）"""
        table = self.query_one("#quake-table", QuakeTableWidget)
        quake = table.get_selected_quake()
        if quake:
            self._select_quake(quake)
