"""震度分布バーチャートウィジェット"""

from __future__ import annotations

from collections import Counter

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import QuakeInfo, scale_name, scale_color, SCALE_NAMES


class IntensityBarWidget(Widget):
    """震度ごとの観測点数をバーチャートで表示"""

    DEFAULT_CSS = """
    IntensityBarWidget {
        height: auto;
        min-height: 10;
        padding: 1 2;
    }
    """

    quake_data: reactive[QuakeInfo | None] = reactive(None)

    def render(self) -> Text:
        text = Text()

        quake = self.quake_data
        if quake is None or not quake.points:
            text.append("  データなし\n", style="dim")
            return text

        # 震度ごとにカウント
        counter: Counter[int] = Counter()
        for p in quake.points:
            if p.scale > 0:
                counter[p.scale] += 1

        if not counter:
            text.append("  データなし\n", style="dim")
            return text

        max_count = max(counter.values()) if counter else 1
        bar_max_width = 18

        # 大きい震度から表示
        scale_keys = sorted(
            [k for k in SCALE_NAMES.keys() if k > 0], reverse=True
        )

        for s in scale_keys:
            count = counter.get(s, 0)
            if count == 0:
                continue
            name = scale_name(s).rjust(3)
            color = scale_color(s)
            bar_len = max(1, int(count / max_count * bar_max_width))
            bar = "█" * bar_len
            text.append(f"  {name} ", style="bold")
            text.append(f"{bar}", style=color)
            text.append(f" {count}\n", style="dim")

        return text

    def update_quake(self, quake: QuakeInfo | None) -> None:
        self.quake_data = quake
