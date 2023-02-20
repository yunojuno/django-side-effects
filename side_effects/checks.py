from __future__ import annotations

import inspect
from typing import Any, Callable, List

from django.apps import AppConfig
from django.core.checks import messages, register

from . import registry

REGISTRY = registry._registry
CHECK_ID_MULTIPLE_SIGNATURES = "side_effects.W001"
CHECK_ID_NO_ANNOTATIONS = "side_effects.W002"


def _message(label: str) -> messages.CheckMessage:
    """
    Message printed if varying function signatures for same event.

    Create Error or Warning message based on STRICT_MODE."""
    msg = f'Multiple function signatures for event: "{label}"'
    hint = (
        f"Ensure that all functions decorated "
        f'`@is_side_effect_of("{label}")` have identical signatures.'
    )
    return messages.Warning(msg, hint=hint, id=CHECK_ID_MULTIPLE_SIGNATURES)


def _message_annotations(label: str) -> messages.CheckMessage:
    """
    Message printed if file missing __future__.annotations.

    Create Error or Warning message based on STRICT_MODE.
    """
    msg = f'Files with functions for event "{label}" missing __future__.annotations'
    hint = (
        f"Ensure that all files with functions decorated "
        f'`@is_side_effect_of("{label}")` import'
        f"`from __future__ import annotations`."
    )
    return messages.Warning(msg, hint=hint, id=CHECK_ID_NO_ANNOTATIONS)


def trim_signature(func: Callable) -> inspect.Signature:
    # Return a Signature for the func that ignores return_value kwarg
    sig = inspect.signature(func)
    # remove return_value from the signature params as it's dynamic
    # and may/ may not exist depending on the usage.
    params = [sig.parameters[p] for p in sig.parameters if p != "return_value"]
    return sig.replace(parameters=params, return_annotation=sig.return_annotation)


def has_class_annotations(functions: list[Callable]) -> bool:
    """
    Check if functions have class annotations.
    If any function annotations are not in string format, this will return `True`.
    """
    for func in functions:
        func_annotations = list(inspect.get_annotations(func).values())
        for annotation in func_annotations:
            if not annotation in [str, None]:
                return True
    return False


def find_fixes(label: str) -> messages.CheckMessage | None:
    """
    Check for similar function signatures, and returns a fix if found.
    """
    functions = [func for func in registry._registry[label]]
    signatures = [trim_signature(func) for func in functions]
    if len(set(signatures)) > 1:
        if has_class_annotations(functions):
            return _message_annotations(label)
        else:
            return _message(label)


@register()
def check_function_signatures(app_configs: list[AppConfig], **kwargs: Any) -> list[str]:
    """Check that all registered functions have the same signature."""
    errors: list[str] = []
    for label in REGISTRY:
        if error := find_fixes(label):
            errors.append(error)
    return errors
