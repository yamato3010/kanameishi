"""Kanameishi - メインアプリケーション"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static
from textual.binding import Binding

from .api.client import P2PQuakeClient
from .api.websocket import P2PQuakeWebSocket
from .api.models import (
    EEWArea,
    EEWInfo,
    Hypocenter,
    QuakeInfo,
    TsunamiInfo,
    now_jst,
    scale_hex,
    scale_name,
)
from .widgets.header import HeaderWidget
from .widgets.japan_map import JapanMapWidget, build_legend
from .widgets.eew_panel import EEWPanelWidget
from .widgets.tsunami_panel import TsunamiPanelWidget
from .widgets.quake_detail import QuakeDetailWidget
from .widgets.quake_table import QuakeTableWidget
from .widgets.intensity_bar import IntensityBarWidget
from .widgets.status_bar import StatusBarWidget
from .screens.about import AboutScreen

log = logging.getLogger(__name__)

CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"

# 自動更新間隔 (秒)
POLL_INTERVAL = 60

# 緊急地震速報の表示継続時間 (発生からの秒数)
EEW_DISPLAY_SECONDS = 180


class EarthquakeApp(App):
    """Kanameishi アプリケーション"""

    TITLE = "Kanameishi"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("q", "quit", "終了", priority=True),
        Binding("r", "refresh", "更新"),
        Binding("d", "show_detail", "詳細"),
        Binding("question_mark", "about", "情報"),
        Binding("e", "demo_eew", "EEWデモ", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._client = P2PQuakeClient()
        self._ws = P2PQuakeWebSocket()
        self._quakes: list[QuakeInfo] = []
        self._latest_quake: QuakeInfo | None = None
        self._eew: EEWInfo | None = None
        self._eew_received_at: datetime | None = None

    def compose(self) -> ComposeResult:
        # ヘッダー + EEW/津波警告バナー (通常は非表示)
        yield HeaderWidget(id="app-header")
        yield Static("", id="eew-banner")
        yield Static("", id="tsunami-banner")

        # メインコンテンツ
        with Horizontal(id="main-content"):
            # 左: 日本地図 (凡例は下部に固定)
            with Container(id="map-panel") as map_panel:
                map_panel.border_title = "🗾 日本地図"
                yield JapanMapWidget(id="japan-map")
                yield Static(build_legend(), id="map-legend")

            # 右: EEW(発表中のみ) + 地震詳細 + 震度分布 + 津波情報
            with Vertical(id="info-panel"):
                with Container(id="eew-panel") as eew_panel:
                    eew_panel.border_title = "🚨 緊急地震速報"
                    yield EEWPanelWidget(id="eew-info")

                with Container(id="detail-panel") as detail_panel:
                    detail_panel.border_title = "📋 最新地震情報"
                    yield QuakeDetailWidget(id="quake-detail")

                with Container(id="intensity-panel") as intensity_panel:
                    intensity_panel.border_title = "📊 震度分布・観測地点"
                    yield IntensityBarWidget(id="intensity-bar")

                with Container(id="tsunami-panel") as tsunami_panel:
                    tsunami_panel.border_title = "🌊 津波情報"
                    yield TsunamiPanelWidget(id="tsunami-info")

        # 下部: 地震履歴
        with Container(id="history-panel") as history_panel:
            history_panel.border_title = "📜 地震履歴"
            yield QuakeTableWidget(id="quake-table")

        # ステータスバー
        yield StatusBarWidget(id="status-bar")

    async def on_mount(self) -> None:
        """アプリ起動時の初期化"""
        # WebSocket コールバック設定
        self._ws.on_quake(self._on_ws_quake)
        self._ws.on_tsunami(self._on_ws_tsunami)
        self._ws.on_eew(self._on_ws_eew)
        self._ws.on_status_change(self._on_ws_status)

        # 初期データ取得
        await self._fetch_initial_data()

        # WebSocket 接続開始
        self._ws.start()

        # 定期ポーリング (REST フォールバック)
        self.set_interval(POLL_INTERVAL, self._poll_data)

        # 詳細パネルの相対時刻 (「n分前」) を定期更新
        self.set_interval(30, self._refresh_detail)

        # EEW表示の期限切れチェック
        self.set_interval(5, self._check_eew_expiry)

    def _refresh_detail(self) -> None:
        self.query_one("#quake-detail", QuakeDetailWidget).refresh()

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

        # 発表中の津波予報があればバナー表示
        try:
            tsunamis = await self._client.get_tsunami_list(limit=1)
            if tsunamis:
                self._update_tsunami_banner(tsunamis[0])
        except Exception as e:
            log.warning("津波情報取得エラー: %s", e)

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
        """WebSocketから地震情報を受信

        WebSocket はアプリと同じイベントループ上のタスクで動くため直接呼べる。
        """
        self._handle_new_quake(quake)

    def _on_ws_tsunami(self, tsunami: TsunamiInfo) -> None:
        """WebSocketから津波情報を受信"""
        self._handle_tsunami(tsunami)

    def _on_ws_eew(self, eew: EEWInfo) -> None:
        """WebSocketから緊急地震速報〔警報〕を受信"""
        if eew.cancelled:
            self._clear_eew()
            self.notify("緊急地震速報は取り消されました", severity="information", timeout=10)
            return

        self._eew = eew
        self._eew_received_at = now_jst()

        # 地図に到達予想円、パネルにカウントダウンを表示
        self.query_one("#japan-map", JapanMapWidget).update_eew(eew)
        self.query_one("#eew-info", EEWPanelWidget).update_eew(eew)
        self.query_one("#eew-panel").display = True

        # バナー表示
        banner = self.query_one("#eew-banner", Static)
        mag = f" M{eew.magnitude:.1f}" if eew.magnitude > 0 else ""
        test = "【テスト】" if eew.test else ""
        banner.update(
            f"🚨 {test}緊急地震速報〔警報〕 ─ {eew.location}{mag}"
            f" 予想最大震度 {scale_name(eew.max_expected_scale)}"
        )
        banner.display = True

        self.notify(
            f"🚨 緊急地震速報: {eew.location}{mag} 予想最大震度{scale_name(eew.max_expected_scale)}",
            severity="error",
            timeout=20,
        )

    def _clear_eew(self) -> None:
        """EEW表示を終了"""
        self._eew = None
        self._eew_received_at = None
        self.query_one("#japan-map", JapanMapWidget).update_eew(None)
        self.query_one("#eew-info", EEWPanelWidget).update_eew(None)
        self.query_one("#eew-panel").display = False
        self.query_one("#eew-banner", Static).display = False

    def _check_eew_expiry(self) -> None:
        """発生から一定時間が過ぎたEEW表示を消す"""
        if self._eew is None:
            return
        elapsed = self._eew.elapsed_seconds()
        if elapsed is None and self._eew_received_at is not None:
            elapsed = (now_jst() - self._eew_received_at).total_seconds()
        if elapsed is not None and elapsed > EEW_DISPLAY_SECONDS:
            self._clear_eew()

    def _on_ws_status(self, connected: bool) -> None:
        """WebSocket接続状態変更"""
        self._update_ws_status(connected)

    def _handle_new_quake(self, quake: QuakeInfo) -> None:
        """新しい地震情報を処理"""
        table = self.query_one("#quake-table", QuakeTableWidget)
        # 履歴を遡って閲覧中 (先頭以外を選択中) なら詳細表示を奪わない
        following = not self._quakes or table.cursor_row in (0, None)

        # 同一地震の続報 (震度速報→震源情報→詳細) は既存行を置き換える
        existing = self._find_same_quake(quake)
        if existing is not None:
            previous_scale = self._quakes[existing].max_scale
            self._quakes[existing] = quake
        else:
            previous_scale = -1
            self._quakes.insert(0, quake)
            self._quakes = self._quakes[:50]  # 最大50件

        table.update_quakes(self._quakes)

        # 詳細表示を更新 (最新を追従中のみ)
        if following:
            table.move_cursor(row=0)
            self._select_quake(self._quakes[0])
        self._update_timestamp()

        # 通知 (続報は震度が上がったときだけ再通知する)
        if existing is None or quake.max_scale > previous_scale:
            # 震度速報はマグニチュード未定で -1 が入るため省略する
            mag = f" M{quake.magnitude:.1f}" if quake.magnitude > 0 else ""
            self.notify(
                f"🔴 地震速報: {quake.location}{mag} 最大震度{quake.max_scale_name}",
                severity="warning",
                timeout=10,
            )

    def _find_same_quake(self, quake: QuakeInfo) -> int | None:
        """同一地震の既存エントリを探す (発生時刻が一致すれば同一とみなす)"""
        for i, q in enumerate(self._quakes):
            if quake.id and q.id == quake.id:
                return i
            if quake.earthquake.time and q.earthquake.time == quake.earthquake.time:
                return i
        return None

    def _handle_tsunami(self, tsunami: TsunamiInfo) -> None:
        """津波情報を処理"""
        self._update_tsunami_banner(tsunami)
        if not tsunami.cancelled:
            areas = ", ".join(a.name for a in tsunami.areas[:3])
            self.notify(
                f"🌊 津波予報: {areas}",
                severity="error",
                timeout=15,
            )

    def _update_tsunami_banner(self, tsunami: TsunamiInfo) -> None:
        """津波予報バナー・津波パネルを更新"""
        panel = self.query_one("#tsunami-info", TsunamiPanelWidget)
        panel.update_tsunami(tsunami)

        banner = self.query_one("#tsunami-banner", Static)
        if tsunami.cancelled or not tsunami.areas:
            banner.display = False
            return

        # 重複を除いた地域名 (先頭6件まで)
        names = list(dict.fromkeys(a.name for a in tsunami.areas))
        shown = "、".join(names[:6])
        more = f" ほか{len(names) - 6}地域" if len(names) > 6 else ""
        banner.update(f"🌊 津波予報 発表中 ─ {shown}{more}")
        banner.display = True

    def _update_ws_status(self, connected: bool) -> None:
        """WebSocket接続状態UIを更新"""
        status_bar = self.query_one("#status-bar", StatusBarWidget)
        status_bar.ws_connected = connected
        header = self.query_one("#app-header", HeaderWidget)
        header.ws_connected = connected

    def _select_quake(self, quake: QuakeInfo) -> None:
        """地震を選択して詳細表示を更新"""
        self._latest_quake = quake

        detail = self.query_one("#quake-detail", QuakeDetailWidget)
        detail.update_quake(quake)

        # 詳細パネルの枠色を最大震度に連動させる
        detail_panel = self.query_one("#detail-panel")
        detail_panel.styles.border = ("round", scale_hex(quake.max_scale))

        japan_map = self.query_one("#japan-map", JapanMapWidget)
        japan_map.update_quake(quake)

        intensity = self.query_one("#intensity-bar", IntensityBarWidget)
        intensity.update_quake(quake)

    def _update_timestamp(self) -> None:
        """最終更新時刻を更新"""
        now = now_jst().strftime("%H:%M:%S")
        status_bar = self.query_one("#status-bar", StatusBarWidget)
        status_bar.last_update = now

    # ── アクション ──────────────────────────

    def action_refresh(self) -> None:
        """手動更新"""
        self.run_worker(self._fetch_initial_data())

    def action_demo_eew(self) -> None:
        """デモ用の緊急地震速報を発生させる (eキー、動作確認用)"""
        from .data.japan_map import PREF_COORDINATES, haversine_km

        now = now_jst()
        origin = now - timedelta(seconds=3)
        hypo_lat, hypo_lon, depth = 33.6, 136.3, 30

        # 予報区の到達予測時刻をS波の走時から逆算して生成
        targets = [
            ("三重県", "三重県南部", 55),
            ("和歌山県", "和歌山県南部", 55),
            ("奈良県", "奈良県", 50),
            ("愛知県", "愛知県西部", 50),
            ("大阪府", "大阪府南部", 45),
            ("静岡県", "静岡県西部", 45),
            ("京都府", "京都府南部", 40),
            ("東京都", "東京都２３区", 40),
        ]
        areas = []
        for pref, name, scale in targets:
            lat, lon = PREF_COORDINATES[pref]
            dist = haversine_km(hypo_lat, hypo_lon, lat, lon)
            travel = (dist**2 + depth**2) ** 0.5 / 4.0
            arrival = origin + timedelta(seconds=travel)
            areas.append(
                EEWArea(
                    pref=pref,
                    name=name,
                    scale_from=scale,
                    scale_to=scale,
                    kind_code="10",
                    arrival_time=arrival.strftime("%Y/%m/%d %H:%M:%S"),
                )
            )

        eew = EEWInfo(
            id="demo",
            test=True,
            time=now.strftime("%Y/%m/%d %H:%M:%S"),
            origin_time=origin.strftime("%Y/%m/%d %H:%M:%S"),
            hypocenter=Hypocenter(
                name="紀伊半島南東沖",
                latitude=hypo_lat,
                longitude=hypo_lon,
                depth=depth,
                magnitude=7.2,
            ),
            areas=areas,
        )
        self._on_ws_eew(eew)

    def action_about(self) -> None:
        """「このアプリについて」を表示 (?キー)"""
        if not isinstance(self.screen, AboutScreen):
            self.push_screen(AboutScreen())

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
