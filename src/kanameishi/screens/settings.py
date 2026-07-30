"""設定モーダル画面"""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static, Switch

from .. import notify
from ..api.models import scale_name
from ..config import PREFECTURES, SELECTABLE_SCALES, Config, NotifyConfig, config_path


class SettingsScreen(ModalScreen[Optional[Config]]):
    """通知設定を編集するモーダル

    保存すると設定ファイルに書き出し、更新後の Config を返す。
    キャンセル・Esc の場合は None を返す。
    """

    BINDINGS = [
        Binding("escape", "cancel", "閉じる"),
        Binding("s", "save", "保存"),
        # Textual の既定でフォーカス移動は Tab のみ。メイン画面と揃えて上下キーでも動かす。
        # Select は up/down を「ドロップダウンを開く」に使うため、その行では Select 側が優先される
        Binding("down", "focus_next_row", "次へ", show=False),
        Binding("up", "focus_prev_row", "前へ", show=False),
        Binding("j", "focus_next_row", "次へ", show=False),
        Binding("k", "focus_prev_row", "前へ", show=False),
    ]

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-dialog {
        width: 60;
        max-width: 100%;
        height: auto;
        padding: 1 2;
        border: round #2e2e48;
        background: #10101c;
        border-title-color: #8b8bb8;
        border-title-style: bold;
    }

    .setting-row {
        height: 3;
        align: left middle;
    }

    /* 操作中の行を分かりやすくする */
    .setting-row:focus-within {
        background: #1c1c2e;
    }

    .setting-label {
        width: 1fr;
        height: 3;
        content-align: left middle;
    }

    #notify-min-scale, #region {
        width: 16;
    }

    /* ドロップダウンのリストは Select より左に広げる。
       開いたリストは下の行 (ラベル + スイッチ) に重なるが、Textual は重なった
       ウィジェットの境界でリストを分割するため、境界に全角文字がまたがると
       その1文字が空白に潰れる (「栃木県」が「栃　県」になる)。
       スイッチ列の左端から十分離しておけば、境界は項目名より右の余白に落ちる */
    #notify-min-scale SelectOverlay, #region SelectOverlay {
        width: 30;
        offset: -14 0;
    }

    #settings-note {
        height: auto;
        margin-top: 1;
        color: #ffc832;
    }

    #settings-path {
        height: auto;
        margin-top: 1;
        color: #8b8bb8;
    }

    #settings-buttons {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    #settings-buttons Button {
        margin: 0 1;
    }

    #settings-footer {
        height: 1;
        margin-top: 1;
        text-align: center;
        color: #8b8bb8;
    }
    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config

    def compose(self) -> ComposeResult:
        n = self._config.notify

        with Container(id="settings-dialog") as dialog:
            dialog.border_title = "設定"

            with Horizontal(classes="setting-row"):
                yield Label("自分の地域 (都道府県)", classes="setting-label")
                yield Select(
                    [("未設定", "")] + [(p, p) for p in PREFECTURES],
                    value=self._config.region,
                    allow_blank=False,
                    id="region",
                )

            with Horizontal(classes="setting-row"):
                yield Label("OS通知", classes="setting-label")
                yield Switch(value=n.enabled, id="notify-enabled")

            with Horizontal(classes="setting-row"):
                yield Label("通知する最小震度", classes="setting-label")
                yield Select(
                    [(f"震度{scale_name(s)}", s) for s in SELECTABLE_SCALES],
                    value=n.min_scale,
                    allow_blank=False,
                    id="notify-min-scale",
                )

            with Horizontal(classes="setting-row"):
                yield Label("音アラート (端末ベル)", classes="setting-label")
                yield Switch(value=n.sound, id="notify-sound")

            with Horizontal(classes="setting-row"):
                yield Label("緊急地震速報は震度によらず通知", classes="setting-label")
                yield Switch(value=n.eew_always, id="notify-eew-always")

            with Horizontal(classes="setting-row"):
                yield Label("津波予報は震度によらず通知", classes="setting-label")
                yield Switch(value=n.tsunami_always, id="notify-tsunami-always")

            with Horizontal(classes="setting-row"):
                yield Label("自分の地域が揺れたら震度によらず通知", classes="setting-label")
                yield Switch(value=n.region_always, id="notify-region-always")

            if not notify.is_supported():
                yield Static(
                    "⚠ この環境ではOS通知を利用できません (Linux では notify-send が必要)。"
                    "音アラートのみ動作します。",
                    id="settings-note",
                )

            yield Static(f"保存先: {config_path()}", id="settings-path")

            with Horizontal(id="settings-buttons"):
                yield Button("保存", variant="primary", id="save")
                yield Button("キャンセル", id="cancel")

            yield Static(
                "↑↓/JK 移動   Space 切替   Enter 決定   S 保存   Esc 閉じる",
                id="settings-footer",
            )

    def _collect(self) -> Config:
        """画面の入力値から Config を組み立てる"""
        return Config(
            NotifyConfig(
                enabled=self.query_one("#notify-enabled", Switch).value,
                min_scale=self.query_one("#notify-min-scale", Select).value,
                sound=self.query_one("#notify-sound", Switch).value,
                eew_always=self.query_one("#notify-eew-always", Switch).value,
                tsunami_always=self.query_one("#notify-tsunami-always", Switch).value,
                region_always=self.query_one("#notify-region-always", Switch).value,
            ),
            region=self.query_one("#region", Select).value,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        self.action_save()

    def _overlay_open(self) -> bool:
        """ドロップダウンが開いているか (開いている間はフォーカスを動かさない)"""
        return any(select.expanded for select in self.query(Select))

    def action_focus_next_row(self) -> None:
        if not self._overlay_open():
            self.focus_next()

    def action_focus_prev_row(self) -> None:
        if not self._overlay_open():
            self.focus_previous()

    def action_save(self) -> None:
        config = self._collect()
        try:
            config.save()
        except OSError as e:
            self.notify(f"設定を保存できませんでした: {e}", severity="error", timeout=8)
            return
        self.dismiss(config)

    def action_cancel(self) -> None:
        self.dismiss(None)
