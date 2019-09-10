"""
This module contains the Registry class that is responsible for managing
all of the registered side-effects.
"""
import inspect
import logging
import threading
from collections import defaultdict
from inspect import signature

from django.dispatch import Signal

from . import settings

logger = logging.getLogger(__name__)


def fname(func):
    """Return fully-qualified function name."""
    return "%s.%s" % (func.__module__, func.__name__)


def docstring(func):
    """Split and strip function docstrings into a list of lines."""
    try:
        lines = func.__doc__.strip().split("\n")
        return [line.strip() for line in lines]
    except AttributeError:
        return None


class SideEffectsTestFailure(Exception):
    def __init__(self, label):
        super().__init__(f"Side-effects for '{label}' aborted; TEST_MODE_FAIL=True")


class SignatureMismatch(Exception):
    """Error raised when a function with a signature that does
    not match other functions registered to the same side-effect
    is registered."""
    def __init__(self, label, func):
        super().__init__(f"Signature mismatch for label '{label}': {signature(func)}")


def signature_mismatch(label, func):
    """Handle a signature mismatch."""
    if settings.STRICT_MODE:
        raise SignatureMismatch(label, func)
    logger.warning("Signature mismatch for '%s': ", label, signature(func))


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
        self._signatures = defaultdict(set)
        super().__init__(list)

    def by_label(self, value):
        """Filter registry by label (exact match)."""
        return {k: v for k, v in self.items() if k == value}

    def by_label_contains(self, value):
        """Filter registry by label (contains string)."""
        return {k: v for k, v in self.items() if value in k}

    def contains(self, label, func):
        """
        Lookup label: function mapping in the registry.

        The fname of the function is used in the lookup, as running
        a simple `func in list` check doesn't work.

        """
        return fname(func) in [fname(f) for f in self[label]]


    def _check_signature(self, label: str, func: callable):
        """
        Checks that the signature of a function matches any previously stored signature.

        Raises SignatureMismatch error if the functions do not match.
        """
        func_sig = signature(func)
        signatures = self._signatures[label]
        count = len(signatures)
        self._signatures[label].add(func_sig)

        # A single signature for the label is expected
        if len(signatures) == 1:
            return

        # We have more than one, but the overall count hasn't changed
        if len(signatures) == count:
            return

        # At this point we know that the function we are checking is
        # out of line with whatever was there before. Remember we have
        # no control over the order in which we are checking, so we
        # can't tell whether this function is wrong - just that it is
        # different.
        signature_mismatch(label, func)


    def add(self, label: str, func: callable):
        """Add a function to the registry."""
        with self._lock:
            self._check_signature(label, func)
            self[label].append(func)

    def _run_side_effects(self, label, *args, **kwargs):
        if settings.TEST_MODE_FAIL:
            raise SideEffectsTestFailure(label)
        for func in self[label]:
            try:
                signature(func).bind(*args, **kwargs)
            except TypeError:
                signature_mismatch(label, func)
            else:
                _run_func(func, *args, **kwargs)

    def run_side_effects(self, label, *args, **kwargs):
        """Run registered side-effects functions, or suppress as appropriate.

        If TEST_MODE is on, or the _suppress attr is True, then the side-effects
        are not run, but the `suppressed_side_effect` signal is sent - this is
        primarily used by the disable_side_effects context manager to register
        which side-effects events were suppressed (for testing purposes).

        """
        if self._suppress or settings.TEST_MODE:
            self.suppressed_side_effect.send(Registry, label=label)
        else:
            self._run_side_effects(label, *args, **kwargs)


class disable_side_effects:

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
        _registry.suppressed_side_effect.connect(self.on_event, dispatch_uid="suppress")
        _registry._suppress = True
        return self.events

    def __exit__(self, *args):
        _registry._suppress = False
        _registry.suppressed_side_effect.disconnect(self.on_event)

    def on_event(self, sender, **kwargs):
        self.events.append(kwargs["label"])


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
    if not pass_return_value(func):
        kwargs.pop("return_value", None)
    try:
        func(*args, **kwargs)
    except Exception:
        logger.exception("Error running side_effect function '%s'", fname(func))
        if settings.ABORT_ON_ERROR or settings.TEST_MODE_FAIL:
            raise


def pass_return_value(func):
    """
    Inspect func signature looking for **kwargs.

    If the function defines a variable kwargs parameter named "kwargs",
    then we return True, which means we keep the side-effect origin
    return value in the kwargs. If False  then we strip 'return_value'
    from the kwargs before calling the function.

    """
    spec = inspect.getfullargspec(func)
    return (
        "return_value" in spec.args
        or "return_value" in spec.kwonlyargs
        or spec.varkw == "kwargs"
    )


# global registry
_registry = Registry()
