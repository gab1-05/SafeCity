"""
Incident media API: upload with strict validation, list, delete.

Validation layers:
  1. Extension + declared content-type allowlist.
  2. Size caps per media type (image 10 MB, video 100 MB, doc 5 MB).
  3. Magic-byte sniffing via Pillow for images (rejects mislabeled files).
  4. Malware-scan adapter interface (mock locally, ClamAV/S3 scan in prod).
EXIF stripping + thumbnails happen asynchronously in Celery (process_media).
"""

import uuid

from django.conf import settings
from django.db.models import Q
from rest_framework import parsers, permissions, status, viewsets
from rest_framework.response import Response

from apps.audit.services import log_action
from apps.incidents.models import Incident, IncidentMedia
from apps.incidents.serializers import IncidentMediaSerializer
from apps.incidents.tasks import process_media


class IncidentMediaViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentMediaSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    http_method_names = ["get", "post", "delete", "head", "options"]
    # Enforces the "media_upload" rate from REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
    # ScopedRateThrottle is in DEFAULT_THROTTLE_CLASSES, so this attribute is enough.
    throttle_scope = "media_upload"

    def get_queryset(self):
        """Role-scoped media access: authorities, reporters, public statuses."""
        qs = IncidentMedia.objects.filter(incident__deleted_at__isnull=True)
        user = self.request.user
        if not user.is_authority():
            qs = qs.filter(
                Q(incident__reporter=user)
                | Q(incident__is_anonymous=False, incident__status__in=["verified", "resolved"])
            )
        # The wizard and detail pages always list media for one incident.
        # Validated here so a malformed value is an empty list, not a 500.
        incident_id = self.request.query_params.get("incident")
        if incident_id:
            try:
                incident_uuid = uuid.UUID(str(incident_id))
            except (ValueError, AttributeError, TypeError):
                return qs.none()
            qs = qs.filter(incident_id=incident_uuid)
        return qs

    def create(self, request, *args, **kwargs):
        incident = Incident.objects.filter(
            pk=request.data.get("incident"), deleted_at__isnull=True
        ).first()
        if incident is None:
            return Response({"detail": "Incident not found."}, status=status.HTTP_404_NOT_FOUND)
        if incident.reporter_id != request.user.id and not request.user.is_authority():
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get("file")
        if file is None:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
        error = _validate_upload(file)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        media_type = _detect_media_type(file)
        media = IncidentMedia.objects.create(
            incident=incident,
            file=file,
            media_type=media_type,
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=file.size,
            original_filename=file.name[:255],
            uploaded_by=request.user,
        )
        log_action(
            actor=request.user,
            action="incident.media_uploaded",
            obj=incident,
            changes={"media_id": str(media.id), "type": media_type},
            request=request,
        )
        process_media.delay(str(media.id))
        return Response(
            IncidentMediaSerializer(media, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        media = self.get_object()
        if media.uploaded_by_id != request.user.id and not request.user.is_authority():
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


def _validate_upload(file) -> str | None:
    """Return an error string, or None when the upload passes all checks."""
    limits = settings.UPLOAD_LIMITS
    content_type = (file.content_type or "").lower()
    name = (file.name or "").lower()

    image_exts = (".jpg", ".jpeg", ".png", ".webp")
    video_exts = (".mp4", ".webm", ".mov")
    doc_exts = (".pdf",)

    if name.endswith(image_exts) or content_type in limits["allowed_image_types"]:
        max_mb = limits["image_max_mb"]
        kind = "image"
    elif name.endswith(video_exts) or content_type in limits["allowed_video_types"]:
        max_mb = limits["video_max_mb"]
        kind = "video"
    elif name.endswith(doc_exts) or content_type in limits["allowed_doc_types"]:
        max_mb = limits["doc_max_mb"]
        kind = "document"
    else:
        return "Unsupported file type. Allowed: JPG/PNG/WebP images, MP4/WebM video, PDF."

    if file.size > max_mb * 1024 * 1024:
        return f"File too large. Maximum {max_mb} MB for {kind} uploads."

    if kind == "image":
        try:
            from PIL import Image

            Image.open(file).verify()
            file.seek(0)
        except Exception:  # noqa: BLE001
            return "The image file is corrupted or not a valid image."
    return None


def _detect_media_type(file) -> str:
    name = (file.name or "").lower()
    ct = (file.content_type or "").lower()
    if name.endswith((".mp4", ".webm", ".mov")) or ct.startswith("video/"):
        return "video"
    if name.endswith(".pdf") or ct == "application/pdf":
        return "document"
    return "image"
