"""地震履歴テーブルウィジェット"""

from __future__ import annotations

from textual.widgets import DataTable
from textual.reactive import reactive

from ..api.models import QuakeInfo, scale_name, scale_color, tsunami_label


class QuakeTableWidget(DataTable):
    """地震履歴を一覧表示するDataTable"""

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
            "時刻", "震源地", "M", "最大震度", "津波"
        )

    def update_quakes(self, quakes: list[QuakeInfo]) -> None:
        """地震リストを更新"""
        self._quake_list = quakes
        self.clear()

        for q in quakes:
            eq = q.earthquake
            hypo = eq.hypocenter

            time_str = (eq.time or q.time)[:16]
            location = hypo.name or "---"
            mag = f"{hypo.magnitude:.1f}" if hypo.magnitude > 0 else "---"
            max_s = scale_name(eq.max_scale)
            tsunami = tsunami_label(eq.domestic_tsunami)

            self.add_row(
                time_str,
                location,
                mag,
                max_s,
                tsunami,
            )

    def get_selected_quake(self) -> QuakeInfo | None:
        """現在選択中の地震情報を返す"""
        if self.cursor_row is not None and 0 <= self.cursor_row < len(self._quake_list):
            return self._quake_list[self.cursor_row]
        return None
