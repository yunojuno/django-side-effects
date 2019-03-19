from side_effects.decorators import has_side_effects, is_side_effect_of
from side_effects.registry import _registry


@has_side_effects("foo")
def origin(message: str):
    print(f"origin: {message}")
    return "origin_return_value"


@is_side_effect_of("foo")
def no_docstring(message: str):
    print(f"no_docstring: {message}")
    return "no_docstring_return_value"


@is_side_effect_of("foo")
def one_line_docstring(message: str):
    """This is a one-line docstring."""
    print(f"one_line_docstring: {message}")
    return "one_line_docstring_return_value"


@is_side_effect_of("foo")
def multi_line_docstring(message: str, return_value=None):
    """
    This is a multi-line docstring.

    It has more information here.

    """
    print(f"return_value: {return_value}")
    return "multi_line_docstring_return_value"
