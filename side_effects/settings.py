from __future__ import annotations

from typing import Any

from django.conf import settings


def get_setting(setting_name: str, default_value: Any) -> Any:
    return getattr(settings, setting_name, default_value)


# If True then instead of logging exceptions in side-effects
# functions, raise them, which will abort processing.
# Default = False
ABORT_ON_ERROR: bool = get_setting("SIDE_EFFECTS_ABORT_ON_ERROR", False)

# In test mode no side-effects are run
# Default = False
TEST_MODE: bool = get_setting("SIDE_EFFECTS_TEST_MODE", False)
