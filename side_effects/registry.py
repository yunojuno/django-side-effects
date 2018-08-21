"""
This module contains the Registry class that is responsible for managing
all of the registered side-effects.
"""
from collections import defaultdict
import logging
import threading

from django.dispatch import Signal

from . import settings

logger = logging.getLogger(__name__)


def fname(func):
    """Return fully-qualified function name."""
    return '%s.%s' % (func.__module__, func.__name__)


def docstring(func):
    """Split and strip function docstrings into a list of lines."""
    try:
        lines = func.__doc__.strip().split('\n')
        return [line.strip() for line in lines]
    except AttributeError:
        return None


class Registry(defaultdict):

    """
    Registry of side effect functions.

    This class is a defaultdict(list) that contains a
    mapping of the side-effect label to the functions
    that should run after the function has completed.

    It has two additional methods - `add`, which is used
    to register a new function against a label, and
    `contains` which is used to look up a function against
    a label.

    """

    # if using the disable_side_effects context manager or decorator,
    # then this signal is used to communicate details of events that
    # would have fired, but have been suppressed.
    suppressed_side_effect = Signal(providing_args=["label"])

    def __init__(self):
        self._lock = threading.Lock()
        self._suppress = False
        super(Registry, self).__init__(list)

    def by_label(self, value):
        """Filter registry by label (exact match)."""
        return {k:v for k, v in self.items() if k == value}

    def by_label_contains(self, value):
        """Filter registry by label (contains string)."""
        return {k:v for k, v in self.items() if value in k}

    def contains(self, label, func):
        """
        Lookup label: function mapping in the registry.

        The fname of the function is used in the lookup, as running
        a simple `func in list` check doesn't work.

        """
        return fname(func) in [fname(f) for f in self[label]]

    def add(self, label, func):
        """
        Add a function to the registry.

        Args:
            label: string, the name of the side-effect - this is used
                to bind two function - the function that @has_side_effects
                and the function that @is_side_effect.
            func: a function that will be called when the side-effects are
                executed - this will be passed all of the args and kwargs
                of the original function.

        """
        with self._lock:
            self[label].append(func)

    def _run_side_effects(self, label, *args, **kwargs):
        for func in self[label]:
            _run_func(func, *args, **kwargs)

    def run_side_effects(self, label, *args, **kwargs):
        """Run registered side-effects functions, or suppress as appropriate.

        If TEST_MODE is True, then no side-effects are run.

        If the _suppress attr is True, then the side-effects are not run, but the
        suppressed_side_effect signal is sent - this is primarily used by the
        disable_side_effects context manager to register which side-effects events
        were suppressed (for testing purposes).

        """
        if settings.TEST_MODE:
            logger.debug("Ignoring all side-effects (TEST_MODE)")
        elif self._suppress:
            self.suppressed_side_effect.send(Registry, label=label)
        else:
            self._run_side_effects(label, *args, **kwargs)


class disable_side_effects():

    """Context manager used to disable side-effects temporarily.

    This works by setting the _suppress attribute on the registry object,
    and then connecting a receiver to the Signal that emits details of
    events that were suppressed.

    NB this changes global state and, ironically, may have unintended consequences

    """

    def __init__(self):
        self.events = []
        pass

    def __enter__(self):
        _registry.suppressed_side_effect.connect(self.on_event, dispatch_uid='suppress')
        _registry._suppress = True
        return self.events

    def __exit__(self, *args):
        _registry._suppress = False
        _registry.suppressed_side_effect.disconnect(self.on_event)

    def on_event(self, sender, **kwargs):
        self.events.append(kwargs['label'])


def register_side_effect(label, func):
    """Helper function to add a side-effect function to the registry."""
    if func in _registry[label]:
        return
    _registry.add(label, func)


def run_side_effects(label, *args, **kwargs):
    """Run all of the side-effect functions registered for a label."""
    _registry.run_side_effects(label, *args, **kwargs)


def _run_func(func, *args, **kwargs):
    """Run a single side-effect function and handle errors."""
    try:
        func(*args, **kwargs)
    except Exception:
        if settings.ABORT_ON_ERROR:
            raise
        else:
            logger.exception("Error running side_effect function '%s'", fname(func))


# global registry
_registry = Registry()
