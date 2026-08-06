"""地震詳細モーダル画面"""

from __future__ import annotations

from rich.cells import cell_len
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Static

from ..api.models import (
    ObservationPoint,
    QuakeInfo,
    relative_time,
    scale_color,
    scale_hex,
    scale_name,
    tsunami_label,
)
from ..widgets.intensity_bar import pack_names, short_addr
from ..widgets.quake_detail import ISSUE_TYPE_LABELS

# 値を揃える位置 (全角ラベルを含むためセル幅で計算する)
LABEL_WIDTH = 10


def format_coordinate(latitude: float, longitude: float) -> str:
    """緯度経度を「北緯 33.6° 東経 136.3°」形式にする (遠地地震の南緯・西経も扱う)"""
    lat_label = "北緯" if latitude >= 0 else "南緯"
    lon_label = "東経" if longitude >= 0 else "西経"
    return f"{lat_label} {abs(latitude):g}°  {lon_label} {abs(longitude):g}°"


def build_summary(quake: QuakeInfo) -> Text:
    """震源・発表情報のブロックを組み立てる"""
    eq = quake.earthquake
    hypo = eq.hypocenter
    max_s = eq.max_scale
    hex_color = scale_hex(max_s)

    text = Text()

    # 震度バッジ + マグニチュード + 相対時刻
    badge_fg = "black" if max_s in (40, 45) else "white"
    text.append(f" 震度 {scale_name(max_s)} ", style=f"bold {badge_fg} on {hex_color}")
    mag = f" M{hypo.magnitude:.1f}" if hypo.magnitude > 0 else " M---"
    text.append(mag, style=f"bold {hex_color}")
    rel = relative_time(quake.display_time)
    if rel:
        text.append(f"  {rel}", style="dim italic")
    text.append("\n\n")

    text.append(f" {hypo.name or '震源調査中'}\n\n", style="bold white")

    # (ラベル, 値, 値のスタイル)。値が無い項目は行ごと省く
    rows: list[tuple[str, str, str]] = []
    if eq.time:
        rows.append(("発生時刻", eq.time[:19], ""))
    # 発表時刻は続報で更新されるため、発生時刻と別に出す
    if quake.time and quake.time[:19] != eq.time[:19]:
        rows.append(("発表時刻", quake.time[:19], ""))
    # 震度速報は震源が未確定で深さ -1 が入るため「ごく浅い」(0) と区別する
    if hypo.depth > 0:
        depth = f"約{hypo.depth}km"
    elif hypo.depth == 0:
        depth = "ごく浅い"
    else:
        depth = "不明"
    rows.append(("深さ", depth, ""))
    if hypo.latitude or hypo.longitude:
        rows.append(("座標", format_coordinate(hypo.latitude, hypo.longitude), ""))
    rows.append(
        ("発表種別", ISSUE_TYPE_LABELS.get(quake.issue_type, quake.issue_type or "---"), "")
    )
    rows.append(("観測地点", f"{len(quake.points)}地点" if quake.points else "---", ""))

    tsunami = eq.domestic_tsunami
    tsunami_style = {
        "Warning": "bold #e51e28",
        "Watch": "bold #ffc832",
        "Checking": "bold #ff8c00",
    }.get(tsunami, "")
    rows.append(("津波", tsunami_label(tsunami), tsunami_style))

    if quake.id:
        rows.append(("情報ID", quake.id, "dim"))

    for label, value, style in rows:
        padding = " " * max(1, LABEL_WIDTH - cell_len(label))
        text.append(f" {label}{padding}", style="dim")
        text.append(f"{value}\n", style=style)

    # 末尾の改行を落として、下のブロックとの間隔を margin だけに任せる
    text.rstrip()
    return text


def build_region_line(quake: QuakeInfo, region: str) -> Text:
    """「自分の地域」で観測された震度の行を組み立てる"""
    text = Text()
    scale = quake.max_scale_in(region)
    text.append(f" 📍 {region}  ", style="bold white")
    if scale > 0:
        text.append(f"震度{scale_name(scale)}", style=f"bold {scale_color(scale)}")
        text.append(" (この地震での最大)", style="dim")
    else:
        text.append("揺れの観測なし", style="dim")
    return text


class ObservationListWidget(Widget):
    """全観測地点を震度の大きい順に一覧表示する (件数の上限なし)"""

    DEFAULT_CSS = """
    ObservationListWidget {
        height: auto;
    }
    """

    def __init__(self, points: list[ObservationPoint], **kwargs) -> None:
        super().__init__(**kwargs)
        self._points = points

    def render(self) -> Text:
        if not self._points:
            return Text(" 観測地点のデータはありません", style="dim")

        text = Text()
        # 行頭インデント3桁 + 右余白を除いた折り返し幅
        avail = max(12, self.size.width - 5)

        # 震度の大きい順。震度不明 (-1) の地点は最後にまとめる
        scales = sorted({p.scale for p in self._points if p.scale > 0}, reverse=True)
        if any(p.scale <= 0 for p in self._points):
            scales.append(-1)

        for s in scales:
            # 都道府県ごとに地点名をまとめる (APIが返した順を保つ)
            by_pref: dict[str, list[str]] = {}
            for p in self._points:
                matched = p.scale == s if s > 0 else p.scale <= 0
                if matched:
                    by_pref.setdefault(p.pref or "不明", []).append(short_addr(p))

            count = sum(len(addrs) for addrs in by_pref.values())
            text.append(f" 震度{scale_name(s)}", style=f"bold {scale_color(s)}")
            text.append(f"  {count}地点\n", style="dim")

            for pref, addrs in by_pref.items():
                text.append(f"  {pref}\n", style="white")
                for line in pack_names(addrs, "", avail):
                    text.append(f"   {line}\n", style="grey70")
            text.append("\n")

        return text


class QuakeDetailScreen(ModalScreen):
    """選択した地震の全情報 (全観測地点を含む) を表示するモーダル"""

    BINDINGS = [
        Binding("escape", "dismiss", "閉じる"),
        # 開いたキーでそのまま閉じられるようにする
        Binding("d", "dismiss", "閉じる", show=False),
        # メイン画面・設定画面と揃えて vim 風の jk でもスクロールできるようにする
        Binding("j", "scroll_list_down", "下へ", show=False),
        Binding("k", "scroll_list_up", "上へ", show=False),
    ]

    DEFAULT_CSS = """
    QuakeDetailScreen {
        align: center middle;
    }

    #quake-detail-dialog {
        width: 76;
        max-width: 100%;
        height: 90%;
        padding: 1 2;
        border: round #2e2e48;
        background: #10101c;
        border-title-color: #8b8bb8;
        border-title-style: bold;
    }

    #quake-detail-summary {
        height: auto;
    }

    #quake-detail-region {
        height: auto;
        margin-top: 1;
    }

    #quake-detail-list-title {
        height: 1;
        margin-top: 1;
        color: #8b8bb8;
        text-style: bold;
    }

    #quake-detail-scroll {
        height: 1fr;
        scrollbar-size-vertical: 1;
    }

    #quake-detail-footer {
        height: 1;
        margin-top: 1;
        color: #8b8bb8;
    }
    """

    def __init__(self, quake: QuakeInfo, region: str = "") -> None:
        super().__init__()
        self._quake = quake
        self._region = region

    def compose(self) -> ComposeResult:
        with Container(id="quake-detail-dialog") as dialog:
            dialog.border_title = "地震詳細"
            yield Static(build_summary(self._quake), id="quake-detail-summary")

            if self._region:
                yield Static(
                    build_region_line(self._quake, self._region), id="quake-detail-region"
                )

            yield Static(" 観測地点 (震度の大きい順)", id="quake-detail-list-title")
            with VerticalScroll(id="quake-detail-scroll"):
                yield ObservationListWidget(self._quake.points)

            yield Static("↑↓/jk スクロール  esc 閉じる", id="quake-detail-footer")

    def on_mount(self) -> None:
        # 矢印キーでそのままスクロールできるようにする
        self.query_one("#quake-detail-scroll", VerticalScroll).focus()

    def action_scroll_list_down(self) -> None:
        self.query_one("#quake-detail-scroll", VerticalScroll).scroll_down()

    def action_scroll_list_up(self) -> None:
        self.query_one("#quake-detail-scroll", VerticalScroll).scroll_up()
