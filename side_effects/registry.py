"""Registry is responsible for managing all of the registered side-effects."""
from __future__ import annotations

import inspect
import logging
import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from django.dispatch import Signal

from . import settings

RegistryType = Dict[str, List[Callable]]
logger = logging.getLogger(__name__)


def fname(func: Callable) -> str:
    """Return fully-qualified function name."""
    return "%s.%s" % (func.__module__, func.__name__)


def docstring(func: Callable) -> Optional[List[str]]:
    """Split and strip function docstrings into a list of lines."""
    try:
        lines = func.__doc__.strip().split("\n")  # type: ignore
        return [line.strip() for line in lines]
    except AttributeError:
        return None


class SideEffectsTestFailure(Exception):
    def __init__(self, label: str):
        super().__init__(f"Side-effects for '{label}' aborted; TEST_MODE_FAIL=True")


class SignatureMismatch(Exception):
    def __init__(self, func: Callable):
        super().__init__(
            f"Side-effect signature mismatch for function "
            f"`{func.__name__}{inspect.signature(func)}`."
        )

    pass


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

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._suppress = False
        super(Registry, self).__init__(list)

    def by_label(self, value: str) -> RegistryType:
        """Filter registry by label (exact match)."""
        return {k: v for k, v in self.items() if k == value}

    def by_label_contains(self, value: str) -> RegistryType:
        """Filter registry by label (contains string)."""
        return {k: v for k, v in self.items() if value in k}

    def contains(self, label: str, func: Callable) -> bool:
        """
        Lookup label: function mapping in the registry.

        The fname of the function is used in the lookup, as running
        a simple `func in list` check doesn't work.

        """
        return fname(func) in [fname(f) for f in self[label]]

    def add(self, label: str, func: Callable) -> None:
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

    def _run_side_effects(
        self, label: str, *args: Any, return_value: Optional[Any] = None, **kwargs: Any
    ) -> None:
        if settings.TEST_MODE_FAIL:
            raise SideEffectsTestFailure(label)
        for func in self[label]:
            _run_func(func, *args, return_value=return_value, **kwargs)

    def run_side_effects(
        self, label: str, *args: Any, return_value: Optional[Any] = None, **kwargs: Any
    ) -> None:
        """
        Run registered side-effects functions, or suppress as appropriate.

        If TEST_MODE is on, or the _suppress attr is True, then the side-effects
        are not run, but the `suppressed_side_effect` signal is sent - this is
        primarily used by the disable_side_effects context manager to register
        which side-effects events were suppressed (for testing purposes).

        NB even if the side-effects themselves are not run, this method will try
        to bind all of the receiver functions - this is to ensure that incompatible
        functions fail hard and early.

        """
        # TODO: this is all becoming over-complex - need to simplify this
        self.try_bind_all(label, *args, return_value=return_value, **kwargs)
        if self._suppress or settings.TEST_MODE:
            self.suppressed_side_effect.send(Registry, label=label)
        else:
            self._run_side_effects(label, *args, return_value=return_value, **kwargs)

    def try_bind_all(
        self, label: str, *args: Any, return_value: Optional[Any] = None, **kwargs: Any
    ) -> None:
        """
        Test all receivers for signature compatibility.

        Raise SignatureMismatch if any function does not match.

        """
        for func in self[label]:
            if not (
                try_bind(func, *args, return_value=return_value, **kwargs)
                or try_bind(func, *args, **kwargs)
            ):
                raise SignatureMismatch(func)


class disable_side_effects:
    """
    Context manager used to disable side-effects temporarily.

    This works by setting the _suppress attribute on the registry object,
    and then connecting a receiver to the Signal that emits details of
    events that were suppressed.

    NB this changes global state and, ironically, may have unintended consequences

    """

    def __init__(self) -> None:
        self.events = []  # type: List[str]
        pass

    def __enter__(self) -> List[str]:
        _registry.suppressed_side_effect.connect(self.on_event, dispatch_uid="suppress")
        _registry._suppress = True
        return self.events

    def __exit__(self, *args: Any) -> None:
        _registry._suppress = False
        _registry.suppressed_side_effect.disconnect(self.on_event)

    def on_event(self, sender: Callable, **kwargs: Any) -> None:
        self.events.append(kwargs["label"])


def register_side_effect(label: str, func: Callable) -> None:
    """Add a side-effect function to the registry."""
    if func in _registry[label]:
        return
    _registry.add(label, func)


def run_side_effects(
    label: str, *args: Any, return_value: Optional[Any] = None, **kwargs: Any
) -> None:
    """Run all of the side-effect functions registered for a label."""
    _registry.run_side_effects(label, *args, return_value=return_value, **kwargs)


def _run_func(
    func: Callable, *args: Any, return_value: Optional[Any] = None, **kwargs: Any
) -> None:
    """Run a single side-effect function and handle errors."""
    try:
        if try_bind(func, *args, return_value=return_value, **kwargs):
            func(*args, return_value=return_value, **kwargs)
        elif try_bind(func, *args, **kwargs):
            func(*args, **kwargs)
        else:
            raise SignatureMismatch(func)
    except SignatureMismatch:
        # always re-raise SignatureMismatch as this means we have been unable
        # to run the side-effect function at all.
        raise
    except Exception:  # pylint: disable=broad-except
        logger.exception("Error running side_effect function '%s'", fname(func))
        if settings.ABORT_ON_ERROR or settings.TEST_MODE_FAIL:
            raise


def try_bind(func: Callable, *args: Any, **kwargs: Any) -> bool:
    """Try binding args & kwargs to a given func."""
    try:
        inspect.signature(func).bind(*args, **kwargs)
    except TypeError:
        return False
    else:
        return True


# global registry
_registry = Registry()
