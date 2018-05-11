import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SideEffectsConfig(AppConfig):

    name = 'side_effects'
    verbose_name = "External Side Effects"
    configs = []

    def ready(self):
        logger.info("Initialising side_effects registry")
        from . import registry  # noqa
