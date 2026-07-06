"""津波情報パネルウィジェット"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive

from ..api.models import TsunamiInfo

# 津波予報グレード: API値 → (表示名, スタイル)
GRADE_STYLES: dict[str, tuple[str, str]] = {
    "MajorWarning": ("大津波警報", "bold white on #8c14a0"),
    "Warning": ("津波警報", "bold white on #e51e28"),
    "Watch": ("津波注意報", "bold black on #ffc832"),
    "Unknown": ("不明", "dim"),
}


class TsunamiPanelWidget(Widget):
    """発表中の津波予報をグレード別に表示するパネル"""

    DEFAULT_CSS = """
    TsunamiPanelWidget {
        height: auto;
        min-height: 3;
        padding: 1 2;
    }
    """

    tsunami_data: reactive[TsunamiInfo | None] = reactive(None)

    def render(self) -> Text:
        text = Text()
        tsunami = self.tsunami_data

        if tsunami is None or tsunami.cancelled or not tsunami.areas:
            text.append("✓ ", style="bold #22c55e")
            text.append("発表中の津波予報はありません", style="dim")
            return text

        text.append(f"発表: {tsunami.time[:19]}\n", style="dim")

        # グレード別に地域をまとめる (重大なものから)
        for grade in ("MajorWarning", "Warning", "Watch", "Unknown"):
            names = list(dict.fromkeys(
                a.name for a in tsunami.areas if a.grade == grade
            ))
            if not names:
                continue
            label, style = GRADE_STYLES[grade]
            text.append(f" {label} ", style=style)
            shown = "、".join(names[:8])
            more = f" ほか{len(names) - 8}地域" if len(names) > 8 else ""
            text.append(f" {shown}{more}\n", style="")

        return text

    def update_tsunami(self, tsunami: TsunamiInfo | None) -> None:
        self.tsunami_data = tsunami
