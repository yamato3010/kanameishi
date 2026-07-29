"""アプリヘッダーウィジェット - タイトルとライブ時計"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import now_jst

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]


class HeaderWidget(Widget):
    """タイトル・接続状態・現在時刻を1行で表示するヘッダー"""

    DEFAULT_CSS = """
    HeaderWidget {
        height: 1;
        dock: top;
    }
    """

    clock: reactive[str] = reactive("")
    ws_connected: reactive[bool] = reactive(False)

    def on_mount(self) -> None:
        self._tick()
        self.set_interval(1, self._tick)

    def _tick(self) -> None:
        now = now_jst()
        wd = WEEKDAYS_JA[now.weekday()]
        self.clock = now.strftime(f"%Y/%m/%d ({wd}) %H:%M:%S JST")

    def render(self) -> Text:
        text = Text()
        text.append(" ▌", style="bold #e51e28")
        text.append("強震モニタ ", style="bold white")
        text.append("─ リアルタイム地震情報", style="dim")

        if self.ws_connected:
            live = Text(" ● LIVE ", style="bold #22c55e")
        else:
            live = Text(" ○ 切断 ", style="bold #71717a")
        clock = Text(f" {self.clock}  ", style="bold #a1a1c2")

        right_len = live.cell_len + clock.cell_len
        remaining = max(1, self.size.width - text.cell_len - right_len)
        text.append(" " * remaining)
        text.append(live)
        text.append(clock)
        return text
