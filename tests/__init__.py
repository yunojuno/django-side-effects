from side_effects.decorators import has_side_effects, is_side_effect_of

@is_side_effect_of('foo')
def no_docstring():
    pass


@is_side_effect_of('foo')
def one_line_docstring():
    """This is a one-line docstring."""
    pass


@is_side_effect_of('foo')
def multi_line_docstring():
    """
    This is a multi-line docstring.

    It has more information here.

    """
    pass
