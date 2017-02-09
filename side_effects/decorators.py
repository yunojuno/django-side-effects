# -*- coding: utf-8 -*-
from functools import wraps

from .registry import (
    register_side_effect,
    run_side_effects
)


def has_side_effects(label):
    """
    Run decorated function and raise side_effects signal when complete.

    This decorator should be used to indicate that a function has external
    side-effects that should be processed after the function has returned -
    you can think of it as a universal post_FOO decorator for any function.

    In its current form it calls the signal handler inside of any external
    transaction - so any error raised will abort the transaction - so please
    bear this in mind.

    Any function decorated with this will be picked up in the side_effects
    module in core. You can use the label to call the appropriate side
    effect function.

    Args:
        label: string, an identifier that is used in the receiver to determine
            which event has occurred. This is required because the function name
            won't be sufficient in most cases.

    """
    def decorator(func):
        @wraps(func)
        def inner_func(*args, **kwargs):
            """Run the original function and send the signal if successful."""
            result = func(*args, **kwargs)
            run_side_effects(label, *args, **kwargs)
            return result
        return inner_func
    return decorator


def is_side_effect_of(label):
    """Register a function as a side-effect."""
    def decorator(func):
        register_side_effect(label, func)

        @wraps(func)
        def inner_func(*args, **kwargs):
            return func(*args, **kwargs)
        return inner_func
    return decorator
