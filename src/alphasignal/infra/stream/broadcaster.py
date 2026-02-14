import json
import asyncio
import redis.asyncio as redis
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger

class RealtimeHub:
    """
    Production-grade Real-time Message Hub.
    Uses Redis Pub/Sub to decouple calculation from delivery.
    """
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis = None

    async def connect(self):
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            logger.info("✅ Connected to Real-time Hub (Redis)")

    async def publish(self, channel: str, message: dict):
        """Publish a message to a specific Redis channel."""
        await self.connect()
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str):
        """Generator for SSE endpoints to subscribe to Redis events."""
        await self.connect()
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    yield message['data']
        finally:
            await pubsub.unsubscribe(channel)

hub = RealtimeHub()
