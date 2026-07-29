"""日本地図ウィジェット - 震源・観測点を地図上に表示"""

from __future__ import annotations

from rich.cells import cell_len
from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import EEWInfo, QuakeInfo, SCALE_NAMES, scale_color, scale_name
from ..data.japan_map import (
    JAPAN_MAP_RAW,
    MAP_HEIGHT,
    MAP_WIDTH,
    grid_to_latlon,
    haversine_km,
    is_inset_cell,
    latlon_to_grid,
    pref_to_grid,
)

# 地震波の伝播速度 (km/s) — 定数速度による近似
P_WAVE_SPEED = 7.0
S_WAVE_SPEED = 4.0


def plot_cell(
    grid: list[list[tuple[str, str]]], r: int, c: int, ch: str, style: str
) -> None:
    """グリッドの1セルを書き換える (全角文字のセル対を壊さない)

    「沖縄」ラベルのような幅2の文字に重なると行の表示幅が変わってしまうため、
    対になるもう片方のセルを空白にして行の幅を保つ。
    """
    if grid[r][c][0] == "":             # 全角文字の後半セル
        grid[r][c - 1] = (" ", "")
    elif cell_len(grid[r][c][0]) == 2:  # 全角文字の前半セル
        grid[r][c + 1] = (" ", "")
    grid[r][c] = (ch, style)


class JapanMapWidget(Widget):
    """ASCIIアート日本地図に地震情報をオーバーレイ表示"""

    # 地図は MAP_WIDTH セル固定幅。幅が縮むと折り返して絵が崩れるため width を固定する
    DEFAULT_CSS = """
    JapanMapWidget {
        width: 45;
        height: auto;
        min-height: 33;
        padding: 0;
    }
    """

    quake_data: reactive[QuakeInfo | None] = reactive(None)
    eew_data: reactive[EEWInfo | None] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._eew_timer = None

    def render(self) -> Text:
        # 地図をグリッドにコピー (1要素 = 表示1セル。列番号とセル位置を一致させる)
        grid: list[list[tuple[str, str]]] = []
        for row_str in JAPAN_MAP_RAW:
            row: list[tuple[str, str]] = []
            for ch in row_str:
                if ch == "#":
                    row.append(("░", "rgb(60,70,90)"))
                elif ch == " ":
                    row.append((" ", ""))
                else:
                    # 沖縄インセットの枠線・ラベルはそのまま描画
                    row.append((ch, "rgb(90,100,120)"))
                if cell_len(ch) == 2:
                    # 全角文字は2セル占めるため、後半セル分の空要素を足して列をずらさない
                    row.append(("", ""))
            # 文字数ではなく表示セル数で MAP_WIDTH に揃える
            row.extend((" ", "") for _ in range(MAP_WIDTH - len(row)))
            grid.append(row)

        # 地震データがあればオーバーレイ
        quake = self.quake_data
        if quake is not None:
            # 観測点をプロット。1セルに複数の観測点・都道府県が載るため最大震度で塗る
            cell_scale: dict[tuple[int, int], int] = {}
            for point in quake.points:
                pos = pref_to_grid(point.pref)
                if pos is None:
                    continue
                r, c = pos
                if not (0 <= r < MAP_HEIGHT and 0 <= c < MAP_WIDTH):
                    continue
                if point.scale > cell_scale.get(pos, -1):
                    cell_scale[pos] = point.scale
            for (r, c), scale in cell_scale.items():
                plot_cell(grid, r, c, "●", f"bold {scale_color(scale)}")

            # 震源をプロット (観測点と同セルの場合は震源を優先)
            if quake.latitude and quake.longitude:
                pos = latlon_to_grid(quake.latitude, quake.longitude)
                if pos:
                    r, c = pos
                    if 0 <= r < MAP_HEIGHT and 0 <= c < MAP_WIDTH:
                        plot_cell(grid, r, c, "★", "bold bright_red")

        # 緊急地震速報があればP波・S波の到達予想円をオーバーレイ
        eew = self.eew_data
        if eew is not None and eew.latitude and eew.longitude:
            self._overlay_eew(grid, eew)

        # Text に変換
        text = Text()
        for row_idx, row in enumerate(grid):
            for ch, style in row:
                text.append(ch, style=style)
            if row_idx < len(grid) - 1:
                text.append("\n")

        return text

    def _overlay_eew(self, grid: list[list[tuple[str, str]]], eew: EEWInfo) -> None:
        """P波・S波の到達予想円と震央をグリッドに描画"""
        elapsed = max(0.0, eew.elapsed_seconds() or 0.0)
        depth = max(eew.depth, 0)

        # 震源からの波の到達半径を地表での半径に換算
        def surface_radius(wave_dist: float) -> float:
            if wave_dist <= depth:
                return 0.0
            return (wave_dist**2 - depth**2) ** 0.5

        p_radius = surface_radius(P_WAVE_SPEED * elapsed)
        s_radius = surface_radius(S_WAVE_SPEED * elapsed)

        # 本土グリッド各セルの震央からの距離 (インセット枠内は対象外)
        dist: list[list[float | None]] = [
            [None] * MAP_WIDTH for _ in range(MAP_HEIGHT)
        ]
        for r in range(MAP_HEIGHT):
            for c in range(MAP_WIDTH):
                if is_inset_cell(r, c):
                    continue
                lat, lon = grid_to_latlon(r, c)
                dist[r][c] = haversine_km(lat, lon, eew.latitude, eew.longitude)

        # 円の内側と外側の境界セルをリングとして描画 (P波→S波の順で上書き)
        for radius, ch, style in (
            (p_radius, "○", "bold deep_sky_blue1"),
            (s_radius, "●", "bold orange_red1"),
        ):
            if radius <= 0:
                continue
            for r in range(MAP_HEIGHT):
                for c in range(MAP_WIDTH):
                    d = dist[r][c]
                    if d is None or d > radius:
                        continue
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < MAP_HEIGHT and 0 <= nc < MAP_WIDTH:
                            nd = dist[nr][nc]
                            if nd is not None and nd > radius:
                                plot_cell(grid, r, c, ch, style)
                                break

        # 震央
        pos = latlon_to_grid(eew.latitude, eew.longitude)
        if pos:
            r, c = pos
            if 0 <= r < MAP_HEIGHT and 0 <= c < MAP_WIDTH:
                plot_cell(grid, r, c, "✕", "bold bright_red blink")

    def update_quake(self, quake: QuakeInfo | None) -> None:
        """表示する地震情報を更新"""
        self.quake_data = quake

    def update_eew(self, eew: EEWInfo | None) -> None:
        """緊急地震速報の表示を更新。表示中は円のアニメーション用タイマーを回す"""
        self.eew_data = eew
        if eew is not None and self._eew_timer is None:
            self._eew_timer = self.set_interval(0.5, self.refresh)
        elif eew is None and self._eew_timer is not None:
            self._eew_timer.stop()
            self._eew_timer = None


def build_legend() -> Text:
    """地図パネル下部に固定表示する凡例"""
    text = Text()
    text.append("★", style="bold bright_red")
    text.append("震源 ", style="dim")
    for s in sorted(k for k in SCALE_NAMES if k > 0):
        text.append("●", style=f"bold {scale_color(s)}")
        text.append(f"{scale_name(s)} ", style="dim")
    return text
