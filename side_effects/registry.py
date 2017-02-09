# -*- coding: utf-8 -*-
"""
This module contains the Registry class that is responsible for managing
all of the registered side-effects.
"""
from collections import defaultdict
import logging
import threading

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

    def __init__(self):
        self._lock = threading.Lock()
        super(Registry, self).__init__(list)

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


def register_side_effect(label, func):
    """Helper function to add a side-effect function to the registry."""
    if func in _registry[label]:
        return
    _registry.add(label, func)


def run_side_effects(label, *args, **kwargs):
    """Run all of the side-effect functions registered for a label."""
    for func in _registry[label]:
        _run_func(func, *args, **kwargs)


def _run_func(func, *args, **kwargs):
    """Run a single side-effect function and handle errors."""
    try:
        func(*args, **kwargs)
    except:
        logger.exception("Error running side_effect function '%s'", fname(func))


# global registry
_registry = Registry()
