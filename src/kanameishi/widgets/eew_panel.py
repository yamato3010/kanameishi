"""緊急地震速報パネルウィジェット - 予報区ごとの主要動到達カウントダウンを表示"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import (
    EEWArea,
    EEWInfo,
    scale_badge,
    scale_name,
)

# 表示する予報区の最大数
MAX_AREAS = 8

# 「自分の地域」ブロックが占める行数。
# パネルの高さ (max-height) を超えるとスクロールバーのぶん幅が減って各行が折り返すため、
# ブロックを出すときは同じ行数だけ一覧を減らして総行数を変えない。
REGION_BLOCK_LINES = 3


class EEWPanelWidget(Widget):
    """緊急地震速報〔警報〕の詳細と到達予想カウントダウン"""

    DEFAULT_CSS = """
    EEWPanelWidget {
        height: auto;
        padding: 0 1;
    }
    """

    eew_data: reactive[EEWInfo | None] = reactive(None)
    # 「自分の地域」(設定の region)。一致する予報区は先頭で大きく表示する
    region_pref: reactive[str] = reactive("")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._timer = None

    def render(self) -> Text:
        text = Text()
        eew = self.eew_data
        if eew is None:
            return text

        max_s = eew.max_expected_scale

        # 見出し行: 予想最大震度 + M + 震源名
        text.append(f" 予想最大震度 {scale_name(max_s)} ", style=scale_badge(max_s))
        if eew.magnitude > 0:
            text.append(f" M{eew.magnitude:.1f}", style="bold")
        text.append(f" {eew.location}", style="bold")
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

        # 「自分の地域」の予報区は一覧に埋もれさせず、先頭で大きく扱う
        region_area = eew.area_for_pref(self.region_pref) if self.region_pref else None
        max_areas = MAX_AREAS
        if region_area is not None:
            self._append_region_block(text, region_area)
            max_areas -= REGION_BLOCK_LINES

        # 予報区ごとのカウントダウン (到達が早い順)
        areas = sorted(
            eew.areas,
            key=lambda a: (
                a.seconds_until_arrival() is None,
                a.seconds_until_arrival() or 0,
            ),
        )
        for area in areas[:max_areas]:
            mine = bool(self.region_pref) and area.pref == self.region_pref
            text.append(" ")
            text.append("●", style=scale_badge(area.scale))
            text.append(
                f" {area.name[:10]:　<10}",
                style="bold reverse" if mine else "bold",
            )
            text.append(f" 震度{scale_name(area.scale)} ", style=scale_badge(area.scale))
            remain = area.seconds_until_arrival()
            if remain is None:
                text.append("  ---", style="dim")
            elif remain <= 0:
                text.append("  到達", style="bold red")
            else:
                text.append(f"  あと{remain:2d}秒", style="bold yellow")
            text.append("\n")
        if len(eew.areas) > max_areas:
            text.append(f" ほか{len(eew.areas) - max_areas}地域\n", style="dim")

        return text

    def _append_region_block(self, text: Text, area: EEWArea) -> None:
        """「自分の地域」の予想震度と主要動到達カウントダウンを強調表示する"""
        text.append(f" 📍 あなたの地域 {area.name} ", style=scale_badge(area.scale))
        text.append("\n")

        text.append(f"  予想震度 {scale_name(area.scale)} ", style=scale_badge(area.scale))
        remain = area.seconds_until_arrival()
        if remain is None:
            text.append("   到達予測なし", style="dim")
        elif remain <= 0:
            text.append("   主要動 到達", style="bold red")
        else:
            text.append(f"   主要動 あと {remain} 秒", style="bold yellow")
        text.append("\n\n")

    def update_eew(self, eew: EEWInfo | None) -> None:
        """表示するEEWを更新。表示中はカウントダウン用タイマーを回す"""
        self.eew_data = eew
        if eew is not None and self._timer is None:
            self._timer = self.set_interval(0.5, self.refresh)
        elif eew is None and self._timer is not None:
            self._timer.stop()
            self._timer = None
