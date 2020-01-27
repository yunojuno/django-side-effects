from __future__ import annotations

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SideEffectsConfig(AppConfig):

    name = "side_effects"
    verbose_name = "External Side Effects"

    def ready(self) -> None:
        logger.debug("Initialising side_effects registry")
        from . import registry  # noqa: F401

        logger.debug("Registering side_effects checks")
        from . import checks  # noqa: F401
