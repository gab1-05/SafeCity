"""
Realtime notification consumer.

Clients connect to /ws/notifications/ with ?token=<access JWT>. The token is
validated on connect; the socket joins a per-user group so the notification
service can push events from anywhere in the codebase (including Celery).
"""

import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger("safecity")


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Per-user notification stream."""

    async def connect(self):
        user_id = await self._authenticate(self.scope["query_string"].decode())
        if not user_id:
            await self.close(code=4401)
            return
        self.user_id = user_id
        self.group_name = f"user-{user_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "user_id": str(user_id)})

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify(self, event):
        """Handler for group messages sent by notifications.services.push()."""
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _authenticate(self, query_string: str):
        """Return user id from a valid access token, else None."""
        from django.contrib.auth import get_user_model

        token = None
        for part in query_string.split("&"):
            key, _, value = part.partition("=")
            if key == "token":
                token = value
                break
        if not token:
            return None
        try:
            validated = AccessToken(token)
        except TokenError:
            return None
        try:
            user = get_user_model().objects.filter(id=validated["user_id"], is_active=True).exists()
        except Exception:  # noqa: BLE001 — any failure means unauthenticated
            return None
        if not user:
            return None
        return validated["user_id"]
