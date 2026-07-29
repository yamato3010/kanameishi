"""地震詳細パネルウィジェット"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import (
    QuakeInfo,
    relative_time,
    scale_hex,
    scale_name,
    tsunami_label,
)

# 発表種別: API値 → 表示文字列
ISSUE_TYPE_LABELS: dict[str, str] = {
    "ScalePrompt": "震度速報",
    "Destination": "震源情報",
    "ScaleAndDestination": "震度・震源",
    "DetailScale": "詳細情報",
    "Foreign": "遠地地震",
    "Other": "その他",
}


class QuakeDetailWidget(Widget):
    """最新の地震情報の詳細を表示するパネル"""

    DEFAULT_CSS = """
    QuakeDetailWidget {
        height: auto;
        min-height: 9;
        padding: 1 2;
    }
    """

    quake_data: reactive[QuakeInfo | None] = reactive(None)

    def render(self) -> Text:
        text = Text()
        quake = self.quake_data

        if quake is None:
            text.append("データ取得中...\n\n", style="dim italic")
            text.append("P2P地震情報APIに接続しています", style="dim")
            return text

        eq = quake.earthquake
        hypo = eq.hypocenter
        max_s = eq.max_scale
        hex_color = scale_hex(max_s)

        # 震度バッジ + マグニチュード + 震源地
        badge_fg = "black" if max_s in (40, 45) else "white"
        text.append(f" 震度 {scale_name(max_s)} ", style=f"bold {badge_fg} on {hex_color}")
        mag_str = f" M{hypo.magnitude:.1f}" if hypo.magnitude > 0 else " M---"
        text.append(mag_str, style=f"bold {hex_color}")
        rel = relative_time(quake.display_time)
        if rel:
            text.append(f"  {rel}", style="dim italic")
        text.append("\n\n")

        text.append(f" {hypo.name or '震源調査中'}\n", style="bold white")

        # 発生時刻
        text.append(" 発生 ", style="dim")
        text.append(f"{quake.display_time[:19]}\n", style="")

        # 深さ / 座標
        depth_str = f"約{hypo.depth}km" if hypo.depth > 0 else "ごく浅い"
        text.append(" 深さ ", style="dim")
        text.append(f"{depth_str}", style="")
        if hypo.latitude and hypo.longitude:
            text.append(f"   N{hypo.latitude:.1f}° E{hypo.longitude:.1f}°", style="dim")
        text.append("\n")

        # 発表種別 / 観測点数
        issue = ISSUE_TYPE_LABELS.get(quake.issue_type, quake.issue_type or "---")
        text.append(" 発表 ", style="dim")
        text.append(f"{issue}", style="")
        if quake.points:
            text.append(f"   観測 {len(quake.points)}地点", style="dim")
        text.append("\n\n")

        # 津波情報
        tsunami = eq.domestic_tsunami
        t_label = tsunami_label(tsunami)
        if tsunami == "Warning":
            text.append(f" 🌊 津波: {t_label}", style="bold white on #e51e28")
        elif tsunami == "Watch":
            text.append(f" 🌊 津波: {t_label}", style="bold black on #ffc832")
        elif tsunami == "Checking":
            text.append(f" 🌊 津波: {t_label}", style="bold #ff8c00")
        else:
            text.append(f" 🌊 津波: {t_label}", style="dim")

        return text

    def update_quake(self, quake: QuakeInfo | None) -> None:
        self.quake_data = quake
