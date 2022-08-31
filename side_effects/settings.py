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

# In FAIL test mode any call to run_side_effects will raise an Exception
# This is used to uncover any tests that are running side-effects when
# they shouldn't be.
# Default = False
TEST_MODE_FAIL: bool = get_setting("SIDE_EFFECTS_TEST_MODE_FAIL", False)

# Controls the log level to use when warning if side-effects are running
# inside an atomic transaction. This is not typically the desired
# behaviour, as it can lead to a failure scenarios in which an exception
# in an outer function (outside of run_side_effects) causes a tx
# rollback when the side-effect itself cannot be reverted (e.g. sending
# email), leaving system in an inconsistent state.
ATOMIC_TX_LOG_LEVEL: str = get_setting("SIDE_EFFECTS_ATOMIC_TX_LOG_LEVEL", "debug")
