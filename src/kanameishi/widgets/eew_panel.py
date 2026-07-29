"""緊急地震速報パネルウィジェット - 予報区ごとの主要動到達カウントダウンを表示"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import EEWInfo, scale_color, scale_hex, scale_name

# 表示する予報区の最大数
MAX_AREAS = 8


class EEWPanelWidget(Widget):
    """緊急地震速報〔警報〕の詳細と到達予想カウントダウン"""

    DEFAULT_CSS = """
    EEWPanelWidget {
        height: auto;
        padding: 0 1;
    }
    """

    eew_data: reactive[EEWInfo | None] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._timer = None

    def render(self) -> Text:
        text = Text()
        eew = self.eew_data
        if eew is None:
            return text

        max_s = eew.max_expected_scale
        hex_color = scale_hex(max_s)
        badge_fg = "black" if max_s in (40, 45) else "white"

        # 見出し行: 予想最大震度 + M + 震源名
        text.append(f" 予想最大震度 {scale_name(max_s)} ", style=f"bold {badge_fg} on {hex_color}")
        if eew.magnitude > 0:
            text.append(f" M{eew.magnitude:.1f}", style=f"bold {hex_color}")
        text.append(f" {eew.location}", style="bold white")
        if eew.test:
            text.append(" [テスト]", style="bold yellow")
        text.append("\n")

        # 深さ / 経過秒数
        depth_str = f"約{eew.depth}km" if eew.depth > 0 else "ごく浅い"
        text.append(f" 深さ {depth_str}", style="dim")
        elapsed = eew.elapsed_seconds()
        if elapsed is not None and elapsed >= 0:
            text.append(f"   発生から {int(elapsed)}秒", style="dim")
        text.append("\n")

        # 予報区ごとのカウントダウン (到達が早い順)
        areas = sorted(
            eew.areas,
            key=lambda a: (
                a.seconds_until_arrival() is None,
                a.seconds_until_arrival() or 0,
            ),
        )
        for area in areas[:MAX_AREAS]:
            color = scale_color(area.scale)
            text.append(" ●", style=f"bold {color}")
            text.append(f" {area.name[:10]:　<10}", style="white")
            text.append(f" 震度{scale_name(area.scale)}", style=f"bold {color}")
            remain = area.seconds_until_arrival()
            if remain is None:
                text.append("  ---", style="dim")
            elif remain <= 0:
                text.append("  到達", style="bold red1")
            else:
                text.append(f"  あと{remain:2d}秒", style="bold gold1")
            text.append("\n")
        if len(eew.areas) > MAX_AREAS:
            text.append(f" ほか{len(eew.areas) - MAX_AREAS}地域\n", style="dim")

        return text

    def update_eew(self, eew: EEWInfo | None) -> None:
        """表示するEEWを更新。表示中はカウントダウン用タイマーを回す"""
        self.eew_data = eew
        if eew is not None and self._timer is None:
            self._timer = self.set_interval(0.5, self.refresh)
        elif eew is None and self._timer is not None:
            self._timer.stop()
            self._timer = None
