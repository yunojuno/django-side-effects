from __future__ import annotations

import inspect
from typing import Any, Callable, List

from django.apps import AppConfig
from django.core.checks import messages, register

from . import registry

REGISTRY = registry._registry
CHECK_ID_MULTIPLE_SIGNATURES = "side_effects.W001"


def _message(label: str) -> messages.CheckMessage:
    """Create Error or Warning message based on STRICT_MODE."""
    msg = f'Multiple function signatures for event: "{label}"'
    hint = (
        f"Ensure that all functions decorated "
        f'`@is_side_effect_of("{label}")` have identical signatures.'
    )
    return messages.Warning(msg, hint=hint, id=CHECK_ID_MULTIPLE_SIGNATURES)


def signature_count(label: str) -> int:
    """Return number of unique function signatures for an event."""

    def trim_signature(func: Callable) -> inspect.Signature:
        # Return a Signature for the func that ignores return_value kwarg
        sig = inspect.signature(func)
        # remove return_value from the signature params as it's dynamic
        # and may/ may not exist depending on the usage.
        params = [sig.parameters[p] for p in sig.parameters if p != "return_value"]
        return sig.replace(parameters=params, return_annotation=sig.return_annotation)

    signatures = [trim_signature(func) for func in registry._registry[label]]
    return len(set(signatures))


@register()
def check_function_signatures(app_configs: list[AppConfig], **kwargs: Any) -> list[str]:
    """Check that all registered functions have the same signature."""
    errors = []  # type: List[str]
    for label in REGISTRY:
        if signature_count(label) > 1:
            errors.append(_message(label))
    return errors
