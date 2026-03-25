import asyncio
from abc import ABC, abstractmethod


class BaseChannel(ABC):
    @abstractmethod
    def send(self, title, message, source_url=None, db_id=None):
        pass

    async def send_message_async(
        self,
        *,
        title,
        body,
        source_url=None,
        db_id=None,
        group=None,
    ):
        """
        Async wrapper for alert channels.

        Engine uses `await channel.send_message_async(...)`, while concrete channels
        typically only implement sync `send(...)`.
        """
        # `group` is currently informational; concrete implementations may ignore it.
        _ = group
        await asyncio.to_thread(self.send, title, body, source_url=source_url, db_id=db_id)
