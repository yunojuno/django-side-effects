from env_utils import get_bool

from django.conf import settings

# If True then instead of logging exceptions in side-effects
# functions, raise them, which will abort processing.
# Default = False
ABORT_ON_ERROR = getattr(
    settings, 'SIDE_EFFECTS_ABORT_ON_ERROR',
    get_bool('SIDE_EFFECTS_ABORT_ON_ERROR', False)
)

# In test mode no side-effects are run
# Default = False
TEST_MODE = getattr(
    settings, 'SIDE_EFFECTS_TEST_MODE',
    get_bool('SIDE_EFFECTS_TEST_MODE', False)
)
