"""地震履歴テーブルウィジェット"""

from __future__ import annotations

from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.widgets import DataTable
from textual.reactive import reactive

from ..api.models import QuakeInfo, scale_name, scale_color, tsunami_label

# 末尾から何行手前で次ページを読み始めるか
LOAD_MORE_MARGIN = 10


class QuakeTableWidget(DataTable):
    """地震履歴を一覧表示するDataTable"""

    class LoadMore(Message):
        """末尾近くまでスクロールされた (続きの読み込み要求)"""

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

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        """末尾付近まで来たら続きの読み込みを要求する

        カーソル移動でも表示がスクロールするため、キー操作・マウスホイールの
        どちらでも同じように発火する。
        """
        super().watch_scroll_y(old_value, new_value)
        if self._quake_list and new_value >= self.max_scroll_y - LOAD_MORE_MARGIN:
            self.post_message(self.LoadMore())

    def update_quakes(self, quakes: list[QuakeInfo]) -> None:
        """地震リストを更新 (選択中の行は維持する)"""
        selected = self.get_selected_quake()

        # append_quakes で伸ばすため、呼び出し元のリストとは別に保持する
        self._quake_list = list(quakes)
        self.clear()

        for q in quakes:
            self._add_quake_row(q)

        # 更新前に選択していた地震があればカーソルを復元
        if selected is not None:
            for i, q in enumerate(quakes):
                if self._is_same_quake(q, selected):
                    self.move_cursor(row=i)
                    break

    def append_quakes(self, quakes: list[QuakeInfo]) -> None:
        """古い地震を末尾に追加する (無限スクロールの続き読み込み)

        全行を組み直すとスクロール位置が飛ぶため、行の追加だけを行う。
        """
        self._quake_list.extend(quakes)
        for q in quakes:
            self._add_quake_row(q)

    def _add_quake_row(self, quake: QuakeInfo) -> None:
        """地震1件を行として追加する"""
        eq = quake.earthquake
        hypo = eq.hypocenter

        time_str = (eq.time or quake.time)[:16]
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
