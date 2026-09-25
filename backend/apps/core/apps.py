from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "SafeCity Core"

    def ready(self):
        # Import for side effect: registers SafeCity models with django admin.
        from apps.core import admin_registry  # noqa: F401
