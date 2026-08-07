"""設定モーダル画面"""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Label, Select, Static

from .. import notify
from ..api.models import scale_name
from ..config import PREFECTURES, SELECTABLE_SCALES, Config, NotifyConfig, config_path


class SettingsScreen(ModalScreen[Optional[Config]]):
    """通知設定を編集するモーダル

    保存すると設定ファイルに書き出し、更新後の Config を返す。
    取消・esc の場合は None を返す。
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
        /* 端末が低いときは項目が入りきらないのでスクロールさせる */
        max-height: 100%;
        overflow-y: auto;
        padding: 1 2;
        border: round ansi_bright_black;
        /* 背後のメイン画面を透かさないよう、端末の背景色で塗りつぶす */
        background: ansi_default;
        border-title-color: ansi_default;
        border-title-style: bold;
    }

    #settings-dialog Label {
        margin-top: 1;
        color: ansi_default;
        text-style: dim;
    }

    /* プルダウンは枠を省いて高さを詰めている (端末が低くてもフォームが収まる
       ように)。代わりに背景で選択欄の範囲を示す。
       中身 (現在値・▼) は Textual のテーマ色を持つので個別に上書きする */
    #settings-dialog Select > SelectCurrent,
    #settings-dialog Select > SelectCurrent Static#label,
    #settings-dialog Select > SelectCurrent .arrow {
        background: ansi_bright_black;
        color: ansi_default;
    }

    /* Select は枠線でしかフォーカスを示さない作りなので、枠を消すと変化が無くなる。
       履歴表のカーソルと同じく前景色と背景色の反転で示す (ansi_white などの
       固定色はライト端末で地の色と同化してフォーカスが見えなくなるため) */
    #settings-dialog Select:focus > SelectCurrent,
    #settings-dialog Select:focus > SelectCurrent Static#label,
    #settings-dialog Select:focus > SelectCurrent .arrow {
        background: ansi_default;
        color: ansi_default;
        text-style: reverse;
    }

    /* チェックボックスもアプリの配色に寄せる (既定は Textual のテーマ色)。
       ✕印の地に色を敷くと、ライト端末では ansi_green と明度が近くなって
       印が消えるため、地は端末の背景のままにして印の色と太さだけで示す */
    #settings-dialog Checkbox > .toggle--button {
        color: ansi_default;
        background: ansi_default;
        text-style: dim;
    }

    #settings-dialog Checkbox.-on > .toggle--button {
        color: ansi_green;
        background: ansi_default;
        text-style: bold;
    }

    /* Checkbox のラベルは Visual 経由で描かれ text-style: reverse が落ちるため、
       フォーカスは履歴表のカーソルと同じ ansi_bright_black の帯で示す */
    #settings-dialog Checkbox:focus > .toggle--label {
        background: ansi_bright_black;
        color: ansi_default;
    }

    /* ボタンの既定色もテーマ由来の RGB なので端末の色に置き換える */
    #settings-dialog Button {
        color: ansi_default;
    }

    #settings-dialog Button.-primary {
        color: ansi_blue;
        text-style: bold;
    }

    #settings-dialog Button:focus {
        text-style: bold reverse;
    }

    /* ここから下が通知の設定。上の「自分の地域」と続いて見えないよう間を空ける */
    #notify-enabled {
        margin-top: 1;
    }

    /* 「最小震度」は「OS通知」に属する設定なので、Label の既定の余白を打ち消して
       通知の設定を「OS通知」の下にひと塊で並べる */
    #settings-dialog #min-scale-label {
        margin-top: 0;
    }

    #settings-note {
        height: auto;
        margin-top: 1;
        color: ansi_yellow;
    }

    #settings-path {
        height: auto;
        margin-top: 1;
        color: ansi_default;
        text-style: dim;
    }

    #settings-buttons {
        height: auto;
        margin-top: 1;
        align-horizontal: right;
    }

    #settings-buttons Button {
        margin-left: 2;
    }

    #settings-footer {
        height: auto;
        margin-top: 1;
        color: ansi_default;
        text-style: dim;
    }
    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config

    def compose(self) -> ComposeResult:
        n = self._config.notify

        with Container(id="settings-dialog") as dialog:
            dialog.border_title = "設定"

            yield Label("自分の地域 (都道府県)")
            yield Select(
                [("未設定", "")] + [(p, p) for p in PREFECTURES],
                value=self._config.region,
                allow_blank=False,
                compact=True,
                id="region",
            )

            yield Checkbox("OS通知", value=n.enabled, compact=True, id="notify-enabled")

            yield Label("通知する最小震度", id="min-scale-label")
            yield Select(
                [(f"震度{scale_name(s)}", s) for s in SELECTABLE_SCALES],
                value=n.min_scale,
                allow_blank=False,
                compact=True,
                id="notify-min-scale",
            )

            yield Checkbox(
                "音アラート (端末ベル)", value=n.sound, compact=True, id="notify-sound"
            )
            yield Checkbox(
                "緊急地震速報は震度によらず通知",
                value=n.eew_always,
                compact=True,
                id="notify-eew-always",
            )
            yield Checkbox(
                "津波予報は震度によらず通知",
                value=n.tsunami_always,
                compact=True,
                id="notify-tsunami-always",
            )
            yield Checkbox(
                "自分の地域が揺れたら震度によらず通知",
                value=n.region_always,
                compact=True,
                id="notify-region-always",
            )

            if not notify.is_supported():
                yield Static(
                    "⚠ この環境ではOS通知を利用できません (Linux では notify-send が必要)。"
                    "音アラートのみ動作します。",
                    id="settings-note",
                )

            yield Static(f"保存先: {config_path()}", id="settings-path")

            with Horizontal(id="settings-buttons"):
                yield Button("保存", variant="primary", compact=True, id="save")
                yield Button("取消", compact=True, id="cancel")

            yield Static(
                "↑↓/jk 移動  space 切替  ⏎ 決定  s 保存  esc 閉じる",
                id="settings-footer",
            )

    def _collect(self) -> Config:
        """画面の入力値から Config を組み立てる"""
        return Config(
            NotifyConfig(
                enabled=self.query_one("#notify-enabled", Checkbox).value,
                min_scale=self.query_one("#notify-min-scale", Select).value,
                sound=self.query_one("#notify-sound", Checkbox).value,
                eew_always=self.query_one("#notify-eew-always", Checkbox).value,
                tsunami_always=self.query_one("#notify-tsunami-always", Checkbox).value,
                region_always=self.query_one("#notify-region-always", Checkbox).value,
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
