"""地震履歴テーブルウィジェット"""

from __future__ import annotations

from rich.text import Text
from textual.binding import Binding
from textual.widgets import DataTable
from textual.reactive import reactive

from ..api.models import QuakeInfo, scale_name, scale_color, tsunami_label


class QuakeTableWidget(DataTable):
    """地震履歴を一覧表示するDataTable"""

    # 矢印キー (DataTable標準) に加えて vim 風の hjkl でも操作できるようにする
    BINDINGS = [
        Binding("k", "cursor_up", "上へ", show=False),
        Binding("j", "cursor_down", "下へ", show=False),
        Binding("h", "cursor_left", "左へ", show=False),
        Binding("l", "cursor_right", "右へ", show=False),
    ]

    DEFAULT_CSS = """
    QuakeTableWidget {
        height: 1fr;
        min-height: 8;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._quake_list: list[QuakeInfo] = []
        self.cursor_type = "row"
        self.zebra_stripes = True

    def on_mount(self) -> None:
        self.add_columns(
            "時刻", "震源地", "M", "深さ", "最大震度", "津波"
        )

    def update_quakes(self, quakes: list[QuakeInfo]) -> None:
        """地震リストを更新 (選択中の行は維持する)"""
        selected = self.get_selected_quake()

        self._quake_list = quakes
        self.clear()

        for q in quakes:
            eq = q.earthquake
            hypo = eq.hypocenter

            time_str = (eq.time or q.time)[:16]
            location = hypo.name or "---"
            mag = f"{hypo.magnitude:.1f}" if hypo.magnitude > 0 else "---"
            depth = f"{hypo.depth}km" if hypo.depth > 0 else ("浅い" if hypo.name else "---")
            max_s = Text(scale_name(eq.max_scale), style=scale_color(eq.max_scale))
            tsunami = tsunami_label(eq.domestic_tsunami)

            self.add_row(
                time_str,
                location,
                mag,
                depth,
                max_s,
                tsunami,
            )

        # 更新前に選択していた地震があればカーソルを復元
        if selected is not None:
            for i, q in enumerate(quakes):
                if self._is_same_quake(q, selected):
                    self.move_cursor(row=i)
                    break

    @staticmethod
    def _is_same_quake(a: QuakeInfo, b: QuakeInfo) -> bool:
        """同一地震かどうか (idまたは発生時刻の一致で判定)"""
        if a.id and a.id == b.id:
            return True
        return bool(a.earthquake.time) and a.earthquake.time == b.earthquake.time

    def get_selected_quake(self) -> QuakeInfo | None:
        """現在選択中の地震情報を返す"""
        if self.cursor_row is not None and 0 <= self.cursor_row < len(self._quake_list):
            return self._quake_list[self.cursor_row]
        return None
