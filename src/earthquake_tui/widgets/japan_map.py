"""日本地図ウィジェット - 震源・観測点を地図上に表示"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import QuakeInfo, scale_color
from ..data.japan_map import (
    JAPAN_MAP_RAW,
    MAP_HEIGHT,
    MAP_WIDTH,
    latlon_to_grid,
    pref_to_grid,
)


class JapanMapWidget(Widget):
    """ASCIIアート日本地図に地震情報をオーバーレイ表示"""

    DEFAULT_CSS = """
    JapanMapWidget {
        height: auto;
        min-height: 35;
        padding: 0 1;
    }
    """

    quake_data: reactive[QuakeInfo | None] = reactive(None)

    def render(self) -> Text:
        # 地図をグリッドにコピー
        grid: list[list[tuple[str, str]]] = []
        for row_idx, row_str in enumerate(JAPAN_MAP_RAW):
            row: list[tuple[str, str]] = []
            padded = row_str.ljust(MAP_WIDTH)
            for ch in padded:
                if ch == "#":
                    row.append(("░", "rgb(60,70,90)"))
                else:
                    row.append((" ", ""))
            grid.append(row)

        # 地震データがあればオーバーレイ
        quake = self.quake_data
        if quake is not None:
            # 震源をプロット
            if quake.latitude and quake.longitude:
                pos = latlon_to_grid(quake.latitude, quake.longitude)
                if pos:
                    r, c = pos
                    if 0 <= r < MAP_HEIGHT and 0 <= c < MAP_WIDTH:
                        grid[r][c] = ("★", "bold bright_red")

            # 観測点をプロット
            plotted: set[tuple[int, int]] = set()
            for point in quake.points:
                pos = pref_to_grid(point.pref)
                if pos and pos not in plotted:
                    r, c = pos
                    if 0 <= r < MAP_HEIGHT and 0 <= c < MAP_WIDTH:
                        color = scale_color(point.scale)
                        grid[r][c] = ("●", f"bold {color}")
                        plotted.add(pos)

        # Text に変換
        text = Text()
        for row_idx, row in enumerate(grid):
            for ch, style in row:
                text.append(ch, style=style)
            if row_idx < len(grid) - 1:
                text.append("\n")

        return text

    def update_quake(self, quake: QuakeInfo | None) -> None:
        """表示する地震情報を更新"""
        self.quake_data = quake
