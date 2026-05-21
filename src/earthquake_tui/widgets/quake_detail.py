"""地震詳細パネルウィジェット"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import QuakeInfo, scale_name, scale_color, tsunami_label


class QuakeDetailWidget(Widget):
    """最新の地震情報の詳細を表示するパネル"""

    DEFAULT_CSS = """
    QuakeDetailWidget {
        height: auto;
        min-height: 12;
        padding: 1 2;
    }
    """

    quake_data: reactive[QuakeInfo | None] = reactive(None)

    def render(self) -> Text:
        text = Text()
        quake = self.quake_data

        if quake is None:
            text.append("  データ取得中...\n", style="dim italic")
            text.append("  \n")
            text.append("  P2P地震情報APIに接続しています", style="dim")
            return text

        eq = quake.earthquake
        hypo = eq.hypocenter

        # マグニチュードと震源
        mag_str = f"M{hypo.magnitude:.1f}" if hypo.magnitude > 0 else "M---"
        max_s = eq.max_scale
        color = scale_color(max_s)

        text.append("  🔴 ", style="bold red")
        text.append(f"{mag_str}", style=f"bold {color}")
        text.append(f"  {hypo.name or '震源調査中'}\n", style="bold")

        # 震度 / 深さ
        text.append("  ")
        text.append(f"震度{scale_name(max_s)}", style=f"bold {color}")
        depth_str = f"{hypo.depth}km" if hypo.depth > 0 else "ごく浅い"
        text.append(f"  /  深さ {depth_str}\n", style="")

        # 時刻
        time_str = eq.time or quake.time
        text.append(f"  🕐 {time_str}\n", style="dim")
        text.append("\n")

        # 津波情報
        tsunami = eq.domestic_tsunami
        t_label = tsunami_label(tsunami)
        if tsunami in ("Warning",):
            text.append(f"  🌊 津波: {t_label}\n", style="bold bright_red blink")
        elif tsunami in ("Watch",):
            text.append(f"  🌊 津波: {t_label}\n", style="bold yellow")
        elif tsunami in ("Checking",):
            text.append(f"  🌊 津波: {t_label}\n", style="bold dark_orange")
        else:
            text.append(f"  🌊 津波: {t_label}\n", style="dim")

        return text

    def update_quake(self, quake: QuakeInfo | None) -> None:
        self.quake_data = quake
