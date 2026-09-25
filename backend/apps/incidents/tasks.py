"""
Celery tasks for incidents: SLA sweeps, auto-escalation, media processing.
"""

import logging

from celery import shared_task

logger = logging.getLogger("safecity")


@shared_task(name="apps.incidents.tasks.sla_breach_sweep")
def sla_breach_sweep():
    """Flag incidents past SLA and notify departments. Runs every 5 minutes."""
    from apps.incidents.services import sla_breach_sweep as run

    count = run()
    if count:
        logger.info("SLA breach sweep flagged %s incidents", count)
    return count


@shared_task(name="apps.incidents.tasks.escalation_sweep")
def escalation_sweep():
    """Auto-escalate breached emergency incidents. Runs every 15 minutes."""
    from apps.incidents.services import escalation_sweep as run

    count = run()
    if count:
        logger.info("Escalation sweep escalated %s incidents", count)
    return count


@shared_task(name="apps.incidents.tasks.process_media")
def process_media(media_id: str):
    """
    Post-upload media pipeline:
      1. Strip EXIF/GPS metadata from images (privacy requirement).
      2. Generate a thumbnail.
      3. Run the malware-scan adapter (mock in dev).
    """
    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image

    from apps.incidents.models import IncidentMedia

    try:
        media = IncidentMedia.objects.get(pk=media_id)
    except IncidentMedia.DoesNotExist:
        return None

    if media.media_type == "image":
        try:
            media.file.open("rb")
            data = media.file.read()
            media.file.close()
            img = Image.open(BytesIO(data))
            cleaned = BytesIO()
            fmt = "PNG" if img.format == "PNG" else "JPEG"
            img_no_exif = Image.new(img.mode, img.size)
            img_no_exif.putdata(list(img.getdata()))
            img_no_exif.save(cleaned, format=fmt, quality=90)
            # Thumbnail
            img_no_exif.thumbnail((320, 320))
            thumb_buf = BytesIO()
            img_no_exif.save(thumb_buf, format=fmt, quality=80)
            thumb_name = f"thumb_{media.file.name.split('/')[-1]}"
            media.thumbnail.save(thumb_name, ContentFile(thumb_buf.getvalue()), save=False)
            # Re-save stripped image
            media.file.save(media.file.name, ContentFile(cleaned.getvalue()), save=False)
            media.exif_stripped = True
        except Exception:
            logger.warning("Image processing failed for media %s", media_id, exc_info=True)

    # Malware scan adapter (mock: marks clean; swap for ClamAV in prod)
    media.scan_status = "clean"
    media.save(update_fields=["thumbnail", "file", "exif_stripped", "scan_status"])
    return str(media.id)


@shared_task(name="apps.incidents.tasks.update_search_vectors")
def update_search_vectors():
    """Nightly refresh of full-text search vectors (belt-and-braces with triggers)."""
    from django.contrib.postgres.search import SearchVector

    from apps.incidents.models import Incident

    Incident.objects.update(
        search_vector=SearchVector("title", weight="A") + SearchVector("description", weight="B")
    )
    return "ok"
