"""ステータスバーウィジェット"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive


class StatusBarWidget(Widget):
    """接続状態・キーバインドを表示するステータスバー"""

    DEFAULT_CSS = """
    StatusBarWidget {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    ws_connected: reactive[bool] = reactive(False)
    last_update: reactive[str] = reactive("")

    def render(self) -> Text:
        text = Text()

        # キーバインド
        bindings = [
            ("Q", "終了"),
            ("R", "更新"),
            ("↑↓", "選択"),
            ("D", "詳細"),
        ]
        for key, label in bindings:
            text.append(f" [{key}]", style="bold cyan")
            text.append(f" {label} ", style="dim")

        # スペーサー
        remaining = max(0, self.size.width - text.cell_len - 20)
        text.append(" " * remaining)

        # 最終更新
        if self.last_update:
            text.append(f"更新: {self.last_update} ", style="dim")

        # 接続状態
        if self.ws_connected:
            text.append(" 接続中 🟢", style="green")
        else:
            text.append(" 未接続 🔴", style="red")

        return text
