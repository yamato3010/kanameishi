"""「このアプリについて」モーダル画面"""

from __future__ import annotations

from rich.cells import cell_len
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Static

from .. import __version__

APP_NAME = "Kanameishi(要石)"
APP_DESCRIPTION = "ターミナルで動くリアルタイム地震情報モニター"

# ラベルと値 (値は右側で桁を揃えて表示する)
ENTRIES: list[tuple[str, str]] = [
    ("バージョン", __version__),
    ("作者", "Yamato3010"),
    ("ライセンス", "MIT"),
    ("データソース", "P2P地震情報 API v2"),
    # 2021/4/4までの地震情報・津波予報はCC BY 4.0のため出典表示が必要
    ("情報提供", "気象庁"),
]

# 値を揃える位置 (全角ラベルを含むためセル幅で計算する)
LABEL_WIDTH = 14


def build_about_text() -> Text:
    """モーダルに表示する本文を組み立てる"""
    text = Text()
    text.append(f"🗾 {APP_NAME}\n", style="bold white")
    text.append(f"{APP_DESCRIPTION}\n\n", style="dim")

    for label, value in ENTRIES:
        padding = " " * max(1, LABEL_WIDTH - cell_len(label))
        text.append(f"{label}{padding}", style="dim")
        text.append(f"{value}\n", style="")

    return text


class AboutScreen(ModalScreen):
    """アプリ名・バージョン・作者などを表示するモーダル"""

    BINDINGS = [
        Binding("escape", "dismiss", "閉じる"),
    ]

    DEFAULT_CSS = """
    AboutScreen {
        align: center middle;
    }

    #about-dialog {
        width: 52;
        max-width: 100%;
        height: auto;
        padding: 1 2;
        border: round #2e2e48;
        background: #10101c;
        border-title-color: #8b8bb8;
        border-title-style: bold;
    }

    #about-body {
        height: auto;
    }

    #about-footer {
        height: 1;
        margin-top: 1;
        color: #8b8bb8;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="about-dialog") as dialog:
            dialog.border_title = "このアプリについて"
            yield Static(build_about_text(), id="about-body")
            yield Static("esc 閉じる", id="about-footer")
