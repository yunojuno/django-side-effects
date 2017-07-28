from env_utils import get_bool

from django.conf import settings

# If True then do not raise exceptions caught when running
# side-effects, but just log them instead.
# Default = True
SUPPRESS_ERRORS = getattr(
    settings, 'SIDE_EFFECTS_SUPPRESS_ERRORS',
    get_bool('SIDE_EFFECTS_SUPPRESS_ERRORS', True)
)
