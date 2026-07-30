"""アプリヘッダーウィジェット - タイトルとライブ時計"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import now_jst, relative_time, scale_hex, scale_name

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]


class HeaderWidget(Widget):
    """タイトル・「自分の地域」の震度・接続状態・現在時刻を1行で表示するヘッダー"""

    DEFAULT_CSS = """
    HeaderWidget {
        height: 1;
        dock: top;
    }
    """

    clock: reactive[str] = reactive("")
    ws_connected: reactive[bool] = reactive(False)
    # 「自分の地域」(設定の region) と、その地域を最後に揺らした地震の震度・発生時刻
    region_pref: reactive[str] = reactive("")
    region_scale: reactive[int] = reactive(-1)
    region_time: reactive[str] = reactive("")

    def on_mount(self) -> None:
        self._tick()
        self.set_interval(1, self._tick)

    def _tick(self) -> None:
        now = now_jst()
        wd = WEEKDAYS_JA[now.weekday()]
        self.clock = now.strftime(f"%Y/%m/%d ({wd}) %H:%M:%S JST")

    def _region_text(self) -> Text:
        """「あなたの地域: 震度3」の表示 (地域が未設定なら空)"""
        text = Text()
        if not self.region_pref:
            return text
        text.append(f"   📍{self.region_pref}", style="bold #a1a1c2")
        if self.region_scale > 0:
            fg = "black" if self.region_scale in (40, 45) else "white"
            text.append(
                f" 震度{scale_name(self.region_scale)} ",
                style=f"bold {fg} on {scale_hex(self.region_scale)}",
            )
            rel = relative_time(self.region_time)
            if rel:
                text.append(f" {rel}", style="dim")
        else:
            text.append(" 揺れなし", style="dim")
        return text

    def render(self) -> Text:
        if self.ws_connected:
            live = Text(" ● LIVE ", style="bold #22c55e")
        else:
            live = Text(" ○ 切断 ", style="bold #71717a")
        clock = Text(f" {self.clock}  ", style="bold #a1a1c2")
        right_len = live.cell_len + clock.cell_len

        text = Text()
        text.append(" ▌", style="bold #e51e28")
        text.append("Kanameishi ", style="bold white")

        # 幅が足りないときは副題を落として「自分の地域」を優先する
        subtitle = Text("─ リアルタイム地震情報", style="dim")
        region = self._region_text()
        used = text.cell_len + subtitle.cell_len + region.cell_len + right_len
        if self.size.width - used >= 1:
            text.append(subtitle)
        text.append(region)

        remaining = max(1, self.size.width - text.cell_len - right_len)
        text.append(" " * remaining)
        text.append(live)
        text.append(clock)
        return text
