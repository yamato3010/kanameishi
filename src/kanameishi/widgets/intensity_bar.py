"""震度分布バーチャートウィジェット"""

from __future__ import annotations

from collections import Counter

from rich.cells import cell_len
from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import (
    ObservationPoint,
    QuakeInfo,
    scale_badge,
    scale_name,
    scale_color,
    SCALE_NAMES,
)

# 観測地点リストの表示上限
MAX_ADDRS_PER_PREF = 4   # 都道府県ごとに挙げる地点名
MAX_PREFS_PER_SCALE = 5  # 震度ごとに挙げる都道府県


def short_addr(point: ObservationPoint) -> str:
    """表示用の地点名

    震度速報の地域名は「熊本県熊本」のように都道府県名から始まるため、
    見出しと重複する接頭辞を落とす。
    """
    addr = point.addr or point.pref or "不明"
    if point.pref and addr != point.pref and addr.startswith(point.pref):
        return addr[len(point.pref):]
    return addr


def pack_names(names: list[str], suffix: str, width: int) -> list[str]:
    """地名を「、」でつないで表示幅に収まる行に分割する

    suffix ("ほか3地点" など) は最終行に空白区切りで足し、入らなければ改行する。
    """
    lines: list[str] = []
    current = ""
    for name in names:
        joined = f"{current}、{name}" if current else name
        if current and cell_len(joined) > width:
            lines.append(current)
            current = name
        else:
            current = joined
    if suffix:
        if current and cell_len(f"{current} {suffix}") <= width:
            current = f"{current} {suffix}"
        else:
            if current:
                lines.append(current)
            current = suffix
    if current:
        lines.append(current)
    return lines


class IntensityBarWidget(Widget):
    """震度ごとの観測点数をバーチャートと観測地点名で表示"""

    DEFAULT_CSS = """
    IntensityBarWidget {
        height: auto;
        min-height: 5;
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

        max_count = max(counter.values())
        total = sum(counter.values())
        # ウィジェット幅に合わせてバーを伸縮 (震度名+件数表示のぶんを引く)
        bar_max_width = max(8, self.size.width - 16)

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
            bar = "█" * bar_len + "▏"
            text.append(f" {name} ", style="bold")
            text.append(f"{bar}", style=color)
            text.append(f" {count}\n", style="dim")

        text.append(f"\n 計 {total}地点で観測\n\n", style="dim italic")

        self._append_point_names(text, quake.points, scale_keys)
        return text

    def _append_point_names(
        self,
        text: Text,
        points: list[ObservationPoint],
        scale_keys: list[int],
    ) -> None:
        """震度ごと・都道府県ごとに観測地点名を列挙 (大きい震度から)"""
        # 行頭インデント3桁を除いた使用可能幅
        avail = max(12, self.size.width - 5)

        for s in scale_keys:
            # 都道府県ごとに地点名をまとめる (APIが返した順を保つ)
            by_pref: dict[str, list[str]] = {}
            for p in points:
                if p.scale == s:
                    by_pref.setdefault(p.pref or "不明", []).append(short_addr(p))
            if not by_pref:
                continue

            prefs = list(by_pref.items())
            for pref, addrs in prefs[:MAX_PREFS_PER_SCALE]:
                text.append(f" 震度{scale_name(s)} ", style=scale_badge(s))
                text.append(f" {pref}\n", style="bold")
                shown = addrs[:MAX_ADDRS_PER_PREF]
                hidden = len(addrs) - len(shown)
                suffix = f"ほか{hidden}地点" if hidden > 0 else ""
                for line in pack_names(shown, suffix, avail):
                    text.append(f"   {line}\n", style="dim")

            remaining_prefs = len(prefs) - MAX_PREFS_PER_SCALE
            if remaining_prefs > 0:
                text.append(f"   ほか{remaining_prefs}都道府県\n", style="dim")

    def update_quake(self, quake: QuakeInfo | None) -> None:
        self.quake_data = quake
