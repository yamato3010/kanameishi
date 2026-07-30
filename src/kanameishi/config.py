"""設定ファイルの読み書き

設定は JSON で ``~/.config/kanameishi/config.json`` に保存する。
ファイルが無い・壊れている場合は既定値で動作し、アプリの起動を妨げない。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

# 通知しきい値として選択できる震度 (models.SCALE_NAMES のうち「不明」を除いたもの)
SELECTABLE_SCALES: list[int] = [10, 20, 30, 40, 45, 50, 55, 60, 70]

DEFAULT_MIN_SCALE = 40  # 震度4


def config_dir() -> Path:
    """設定ディレクトリ (XDG_CONFIG_HOME があればそれに従う)"""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "kanameishi"


def config_path() -> Path:
    """設定ファイルのパス"""
    return config_dir() / "config.json"


@dataclass
class NotifyConfig:
    """OS通知の設定"""

    enabled: bool = True
    min_scale: int = DEFAULT_MIN_SCALE
    sound: bool = True
    eew_always: bool = True
    tsunami_always: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> NotifyConfig:
        """不正な値は既定値に落として読み込む"""
        default = cls()
        min_scale = data.get("min_scale", default.min_scale)
        if min_scale not in SELECTABLE_SCALES:
            log.warning("設定の min_scale が不正なため既定値を使います: %r", min_scale)
            min_scale = default.min_scale
        return cls(
            enabled=bool(data.get("enabled", default.enabled)),
            min_scale=min_scale,
            sound=bool(data.get("sound", default.sound)),
            eew_always=bool(data.get("eew_always", default.eew_always)),
            tsunami_always=bool(data.get("tsunami_always", default.tsunami_always)),
        )


@dataclass
class Config:
    """アプリ設定"""

    notify: NotifyConfig = field(default_factory=NotifyConfig)

    @classmethod
    def load(cls) -> Config:
        """設定を読み込む。読めなければ既定値を返す"""
        path = config_path()
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return cls()
        except (OSError, json.JSONDecodeError) as e:
            log.warning("設定ファイルを読み込めないため既定値を使います (%s): %s", path, e)
            return cls()

        if not isinstance(data, dict):
            log.warning("設定ファイルの形式が不正なため既定値を使います: %s", path)
            return cls()

        notify = data.get("notify")
        return cls(NotifyConfig.from_dict(notify if isinstance(notify, dict) else {}))

    def save(self) -> None:
        """設定を保存する。失敗した場合は例外を送出する"""
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump({"notify": asdict(self.notify)}, f, ensure_ascii=False, indent=2)
            f.write("\n")
