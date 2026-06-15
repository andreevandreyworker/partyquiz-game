import asyncio
import json

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.config import settings


class Realtime:
    def __init__(self) -> None:
        self._redis = aioredis.from_url(settings.redis_url)
        self._local: dict[str, set[WebSocket]] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    async def publish(self, room_code: str, event: dict) -> None:
        await self._redis.publish(
            f"room:{room_code}", json.dumps(event)
        )

    async def connect(self, room_code: str, ws: WebSocket) -> None:
        await ws.accept()
        conns = self._local.setdefault(room_code, set())
        conns.add(ws)
        if room_code not in self._tasks:
            self._tasks[room_code] = asyncio.create_task(
                self._listen(room_code)
            )

    async def disconnect(self, room_code: str, ws: WebSocket) -> None:
        conns = self._local.get(room_code)
        if not conns:
            return
        conns.discard(ws)
        if not conns:
            self._local.pop(room_code, None)
            task = self._tasks.pop(room_code, None)
            if task:
                task.cancel()

    async def _listen(self, room_code: str) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(f"room:{room_code}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                await self._fanout(room_code, message["data"])
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(f"room:{room_code}")
            await pubsub.aclose()

    async def _fanout(self, room_code: str, data: bytes) -> None:
        event = json.loads(data)
        dead: list[WebSocket] = []
        for ws in list(self._local.get(room_code, set())):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(room_code, ws)


realtime = Realtime()
