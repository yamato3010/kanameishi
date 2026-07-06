"""P2P地震情報 API v2 データモデル"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# 震度スケール: API値 → 表示文字列
SCALE_NAMES: dict[int, str] = {
    -1: "不明",
    10: "1",
    20: "2",
    30: "3",
    40: "4",
    45: "5弱",
    50: "5強",
    55: "6弱",
    60: "6強",
    70: "7",
}

# 震度スケール: API値 → Rich カラー
SCALE_COLORS: dict[int, str] = {
    -1: "dim",
    10: "grey70",
    20: "dodger_blue1",
    30: "green3",
    40: "gold1",
    45: "dark_orange",
    50: "orange_red1",
    55: "red1",
    60: "deep_pink1",
    70: "white on dark_magenta",
}

# 震度スケール: API値 → HEXカラー (バッジ背景・枠線など Textual スタイル用)
SCALE_HEX: dict[int, str] = {
    -1: "#3a3a4a",
    10: "#8a8a9a",
    20: "#1e88ff",
    30: "#43a047",
    40: "#ffc832",
    45: "#ff8c00",
    50: "#ff4514",
    55: "#e51e28",
    60: "#e91e8c",
    70: "#8c14a0",
}

# 津波情報
TSUNAMI_LABELS: dict[str, str] = {
    "None": "なし",
    "Unknown": "不明",
    "Checking": "調査中",
    "NonEffective": "被害の心配なし",
    "Watch": "注意報",
    "Warning": "⚠ 警報",
}


def scale_name(scale: int) -> str:
    """震度API値を表示文字列に変換"""
    return SCALE_NAMES.get(scale, "不明")


def scale_color(scale: int) -> str:
    """震度API値をRichカラーに変換"""
    return SCALE_COLORS.get(scale, "dim")


def scale_hex(scale: int) -> str:
    """震度API値をHEXカラーに変換"""
    return SCALE_HEX.get(scale, SCALE_HEX[-1])


def tsunami_label(key: str) -> str:
    """津波キーを表示文字列に変換"""
    return TSUNAMI_LABELS.get(key, key)


def relative_time(time_str: str) -> str:
    """'2026/07/06 15:20:00' 形式の時刻を「3分前」のような相対表記に変換"""
    try:
        dt = datetime.strptime(time_str[:19], "%Y/%m/%d %H:%M:%S")
    except ValueError:
        return ""
    delta = datetime.now() - dt
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return ""
    if seconds < 60:
        return "たった今"
    if seconds < 3600:
        return f"{seconds // 60}分前"
    if seconds < 86400:
        return f"{seconds // 3600}時間前"
    return f"{seconds // 86400}日前"


@dataclass
class Hypocenter:
    """震源情報"""
    name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    depth: int = 0
    magnitude: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> Hypocenter:
        return cls(
            name=data.get("name", ""),
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            depth=data.get("depth", 0),
            magnitude=data.get("magnitude", 0.0),
        )


@dataclass
class ObservationPoint:
    """観測点情報"""
    pref: str = ""
    addr: str = ""
    scale: int = -1
    is_area: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> ObservationPoint:
        return cls(
            pref=data.get("pref", ""),
            addr=data.get("addr", ""),
            scale=data.get("scale", -1),
            is_area=data.get("isArea", False),
        )


@dataclass
class EarthquakeDetail:
    """地震詳細"""
    time: str = ""
    max_scale: int = -1
    hypocenter: Hypocenter = field(default_factory=Hypocenter)
    domestic_tsunami: str = "None"

    @classmethod
    def from_dict(cls, data: dict) -> EarthquakeDetail:
        return cls(
            time=data.get("time", ""),
            max_scale=data.get("maxScale", -1),
            hypocenter=Hypocenter.from_dict(data.get("hypocenter", {})),
            domestic_tsunami=data.get("domesticTsunami", "None"),
        )


@dataclass
class QuakeInfo:
    """地震情報 (code: 551)"""
    id: str = ""
    code: int = 551
    time: str = ""
    issue_type: str = ""
    earthquake: EarthquakeDetail = field(default_factory=EarthquakeDetail)
    points: list[ObservationPoint] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> QuakeInfo:
        eq_data = data.get("earthquake", {})
        points_data = data.get("points", [])
        issue = data.get("issue", {})
        return cls(
            id=data.get("id", data.get("_id", "")),
            code=data.get("code", 551),
            time=data.get("time", ""),
            issue_type=issue.get("type", ""),
            earthquake=EarthquakeDetail.from_dict(eq_data),
            points=[ObservationPoint.from_dict(p) for p in points_data],
        )

    @property
    def display_time(self) -> str:
        """表示用時刻"""
        return self.earthquake.time or self.time

    @property
    def location(self) -> str:
        """震源地名"""
        return self.earthquake.hypocenter.name or "不明"

    @property
    def magnitude(self) -> float:
        return self.earthquake.hypocenter.magnitude

    @property
    def depth(self) -> int:
        return self.earthquake.hypocenter.depth

    @property
    def max_scale(self) -> int:
        return self.earthquake.max_scale

    @property
    def max_scale_name(self) -> str:
        return scale_name(self.earthquake.max_scale)

    @property
    def tsunami_text(self) -> str:
        return tsunami_label(self.earthquake.domestic_tsunami)

    @property
    def latitude(self) -> float:
        return self.earthquake.hypocenter.latitude

    @property
    def longitude(self) -> float:
        return self.earthquake.hypocenter.longitude


@dataclass
class TsunamiArea:
    """津波予報対象地域"""
    grade: str = ""
    immediate: bool = False
    name: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> TsunamiArea:
        return cls(
            grade=data.get("grade", ""),
            immediate=data.get("immediate", False),
            name=data.get("name", ""),
        )


@dataclass
class TsunamiInfo:
    """津波予報 (code: 552)"""
    id: str = ""
    code: int = 552
    time: str = ""
    cancelled: bool = False
    areas: list[TsunamiArea] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> TsunamiInfo:
        areas_data = data.get("areas", [])
        return cls(
            id=data.get("id", data.get("_id", "")),
            code=data.get("code", 552),
            time=data.get("time", ""),
            cancelled=data.get("cancelled", False),
            areas=[TsunamiArea.from_dict(a) for a in areas_data],
        )
