from __future__ import annotations

from typing import Any

from django.conf import settings
from env_utils import get_bool


def get_setting(setting_name: str, default_value: Any) -> Any:
    return getattr(settings, setting_name, get_bool(setting_name, default_value))


# If True then instead of logging exceptions in side-effects
# functions, raise them, which will abort processing.
# Default = False
ABORT_ON_ERROR = get_setting("SIDE_EFFECTS_ABORT_ON_ERROR", False)  # type: bool

# In test mode no side-effects are run
# Default = False
TEST_MODE = get_setting("SIDE_EFFECTS_TEST_MODE", False)  # type: bool

# In FAIL test mode any call to run_side_effects will raise an Exception
# This is used to uncover any tests that are running side-effects when
# they shouldn't be.
# Default = False
TEST_MODE_FAIL = get_setting("SIDE_EFFECTS_TEST_MODE_FAIL", False)  # type: bool
