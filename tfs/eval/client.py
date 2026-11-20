"""The evaluation talks to the running service over HTTP, as a shop or an agent would."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import aiohttp

URL = os.environ.get("TFS_URL", "http://localhost:8080")


@dataclass
class Answer:
    status: int
    ms: float
    body: dict | None


class Service:
    def __init__(self, session: aiohttp.ClientSession, url: str = URL):
        self.session = session
        self.url = url.rstrip("/")

    async def health(self) -> bool:
        try:
            async with self.session.get(f"{self.url}/health") as r:
                return r.status == 200
        except aiohttp.ClientError:
            return False

    async def clear(self, tenant: str) -> None:
        async with self.session.delete(f"{self.url}/v1/tenants/{tenant}/products") as r:
            r.raise_for_status()

    async def index(self, tenant: str, feed: list[dict], chunk: int = 2000) -> int:
        n = 0
        for i in range(0, len(feed), chunk):
            async with self.session.post(f"{self.url}/v1/tenants/{tenant}/products", json=feed[i : i + chunk]) as r:
                r.raise_for_status()
                n += (await r.json())["indexed"]
        return n

    async def search(
        self, tenant: str, body: dict, design: str | None = None, admission: str | None = None, timeout: float = 10.0
    ) -> Answer:
        headers = {}
        if design:
            headers["X-Design"] = design
        if admission:
            headers["X-Admission"] = admission
        start = time.perf_counter()
        try:
            async with self.session.post(
                f"{self.url}/v1/tenants/{tenant}/search",
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as r:
                data = await r.json(content_type=None) if r.status == 200 else None
                return Answer(r.status, (time.perf_counter() - start) * 1000.0, data)
        except (TimeoutError, aiohttp.ClientError):
            return Answer(0, (time.perf_counter() - start) * 1000.0, None)


def session(limit: int = 512) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=limit, force_close=False))
