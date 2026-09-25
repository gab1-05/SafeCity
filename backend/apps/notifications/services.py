"""
Notification service: fan-out to in-app + realtime + optional channels.

Channels are adapters: email uses Django's configured backend (console in
dev); SMS and push are interfaces with no-op defaults until credentials are
configured. User preferences can disable any channel or event.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.notifications.models import Notification, NotificationPreference

logger = logging.getLogger("safecity")


def _event_enabled(prefs: NotificationPreference | None, verb: str) -> bool:
    if prefs is None:
        return True
    events = prefs.events_enabled or {}
    return bool(events.get(verb, True))


def push_realtime(user_id, payload: dict) -> None:
    """Send payload to the user's websocket group (best-effort)."""
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(f"user-{user_id}", {"type": "notify", "payload": payload})
    except Exception:
        logger.warning("Realtime push failed for user %s", user_id, exc_info=True)


def send_email_adapter(user, subject: str, body: str) -> None:
    """Email adapter. Console backend in dev; SMTP in prod when configured."""
    if not user.email or user.email.endswith("@safecity.invalid"):
        return
    try:
        from django.conf import settings
        from django.core.mail import send_mail

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        logger.warning("Email send failed for %s", user.email, exc_info=True)


def send_sms_adapter(user, body: str) -> None:  # pragma: no cover — interface
    """SMS adapter interface. Configure an SMS provider to enable."""
    return


def send_push_adapter(user, payload: dict) -> None:  # pragma: no cover — interface
    """Web-push adapter interface. Configure push credentials to enable."""
    return


def notify(
    *,
    user,
    verb: str,
    title: str,
    body: str = "",
    incident=None,
    payload: dict | None = None,
    request=None,
) -> Notification | None:
    """
    Deliver one notification to a user honoring their preferences.

    Returns the created Notification (or None if the event is disabled).
    """
    if user is None or not getattr(user, "is_active", False):
        return None

    prefs = NotificationPreference.objects.filter(user=user).first()
    if not _event_enabled(prefs, verb):
        return None

    notification = Notification.objects.create(
        recipient=user,
        verb=verb,
        title=title,
        body=body,
        incident=incident,
        payload=payload or {},
    )

    if prefs is None or prefs.in_app:
        push_realtime(
            user.id,
            {
                "type": "notification",
                "id": str(notification.id),
                "verb": verb,
                "title": title,
                "body": body,
                "incident_id": str(incident.id) if incident else None,
                "created_at": notification.created_at.isoformat(),
            },
        )

    if prefs is None or prefs.email:
        send_email_adapter(user, f"SafeCity: {title}", body or title)
    if prefs is not None and prefs.sms:
        send_sms_adapter(user, f"{title} — {body}".strip())
    if prefs is not None and prefs.push:
        send_push_adapter(user, {"title": title, "body": body})

    return notification


def notify_many(users, **kwargs) -> int:
    """Deliver the same notification to many users. Returns delivered count."""
    count = 0
    for user in users:
        if notify(user=user, **kwargs) is not None:
            count += 1
    return count
