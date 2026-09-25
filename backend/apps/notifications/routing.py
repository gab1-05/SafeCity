"""
WebSocket URL routes for SafeCity realtime notifications.
"""

from django.urls import re_path

from apps.notifications import consumers

websocket_urlpatterns = [
    re_path(r"^ws/$", consumers.NotificationConsumer.as_asgi()),
    re_path(r"^ws/notifications/$", consumers.NotificationConsumer.as_asgi()),
]
