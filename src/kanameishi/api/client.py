"""P2P地震情報 REST API クライアント"""

from __future__ import annotations

import httpx

from .. import __version__
from .models import QuakeInfo, TsunamiInfo

BASE_URL = "https://api.p2pquake.net/v2"


class P2PQuakeClient:
    """P2P地震情報 JSON API v2 クライアント"""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=15.0,
            headers={"User-Agent": f"kanameishi/{__version__}"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_quake_list(self, limit: int = 20, offset: int = 0) -> list[QuakeInfo]:
        """地震情報リストを取得"""
        resp = await self._client.get(
            "/jma/quake",
            params={"limit": limit, "offset": offset},
        )
        resp.raise_for_status()
        data = resp.json()
        return [QuakeInfo.from_dict(item) for item in data]

    async def get_tsunami_list(self, limit: int = 5) -> list[TsunamiInfo]:
        """津波予報リストを取得"""
        resp = await self._client.get(
            "/jma/tsunami",
            params={"limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
        return [TsunamiInfo.from_dict(item) for item in data]

    async def get_history(self, codes: int = 551, limit: int = 20) -> list[dict]:
        """履歴を取得"""
        resp = await self._client.get(
            "/history",
            params={"codes": codes, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()
