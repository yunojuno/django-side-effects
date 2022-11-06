from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from django.http import HttpResponse

from . import registry


def http_response_check(response: HttpResponse) -> bool:
    """Return True for anything other than 4xx, 5xx status_codes."""
    if isinstance(response, HttpResponse):
        return not (400 <= response.status_code < 600)
    else:
        return True


def has_side_effects(label: str) -> Callable:
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

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def inner_func(*args: object, **kwargs: object) -> Any:
            """Run the original function and send the signal if successful."""
            return_value = func(*args, **kwargs)
            kwargs["return_value"] = return_value
            registry.run_side_effects(label, *args, **kwargs)
            return return_value

        return inner_func

    return decorator


def is_side_effect_of(label: str) -> Callable:
    """Register a function as a side-effect."""

    def decorator(func: Callable) -> Callable:
        registry.register_side_effect(label, func)

        @wraps(func)
        def inner_func(*args: object, **kwargs: object) -> Any:
            return func(*args, **kwargs)

        return inner_func

    return decorator


def disable_side_effects() -> Callable:
    """Disable side-effects from firing - used for testing."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def inner_func(*args: object, **kwargs: object) -> Any:
            with registry.disable_side_effects() as events:
                return func(*args, events, **kwargs)

        return inner_func

    return decorator
