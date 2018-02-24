from functools import wraps

from django.http import HttpResponse

from . import registry


def http_response_check(response):
    """Return True for anything other than 4xx, 5xx status_codes."""
    if isinstance(response, HttpResponse):
        return not (400 <= response.status_code < 600)
    else:
        return True


def has_side_effects(label, run_on_exit=http_response_check):
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

    The run_on_exit kwarg can be used for fine-grained control over the exact
    behaviour required. The canonical use case for this is when decorating
    view functions - as they will typically always return a valid HttpResponse
    object, and use the status_code property to indicate whether the view
    function ran OK.

    Args:
        label: string, an identifier that is used in the receiver to determine
            which event has occurred. This is required because the function name
            won't be sufficient in most cases.

    Kwargs:
        run_on_exit: function used to determine whether the side effects should
            run, based on the return value of the innner function. This can be
            used to inspect the result for fine grained control. The default is
            `http_response_check`, which will return False for 4xx, 5xx status
            codes.

    """
    def decorator(func):
        @wraps(func)
        def inner_func(*args, **kwargs):
            """Run the original function and send the signal if successful."""
            result = func(*args, **kwargs)
            if run_on_exit(result):
                registry.run_side_effects(label, *args, **kwargs)
            return result
        return inner_func
    return decorator


def is_side_effect_of(label):
    """Register a function as a side-effect."""
    def decorator(func):
        registry.register_side_effect(label, func)

        @wraps(func)
        def inner_func(*args, **kwargs):
            return func(*args, **kwargs)
        return inner_func
    return decorator


def disable_side_effects():
    """Disable side-effects from firing - used for testing."""
    def decorator(func):
        @wraps(func)
        def inner_func(*args, **kwargs):
            with registry.disable_side_effects() as events:
                return func(*args, events, **kwargs)
        return inner_func
    return decorator
