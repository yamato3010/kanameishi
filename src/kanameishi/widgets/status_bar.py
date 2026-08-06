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

        # キーバインド (Textual 標準の Footer と同じ「キー + 説明」の並べ方に揃える)
        bindings = [
            ("q", "終了"),
            ("r", "更新"),
            ("↑↓/jk", "選択"),
            ("d", "詳細"),
            (",", "設定"),
            ("?", "情報"),
        ]
        for key, label in bindings:
            text.append(f" {key} ", style="bold #a1a1c2")
            text.append(f"{label} ")

        # 右側: データソース / 最終更新 / 接続状態
        right = Text()
        right.append("P2P地震情報", style="dim")
        if self.last_update:
            right.append("  │  ", style="#3f3f5a")
            right.append(f"更新 {self.last_update}", style="dim")
        right.append("  │  ", style="#3f3f5a")
        if self.ws_connected:
            right.append("● 接続中 ", style="bold #22c55e")
        else:
            right.append("● 再接続中... ", style="bold #f59e0b")

        remaining = max(1, self.size.width - text.cell_len - right.cell_len)
        text.append(" " * remaining)
        text.append(right)
        return text
