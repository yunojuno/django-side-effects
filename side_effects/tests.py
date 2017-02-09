# -*- coding: utf-8 -*-
from __future__ import absolute_import

import mock

from django.test import TestCase

from . import registry, decorators


def test_func_no_docstring(arg1, kwarg1=None):
    pass


def test_func_one_line(*args):
    """This is a one line docstring."""
    return sum(args)


def test_func_one_line_2():
    """
    This is also a one line docstring.
    """
    pass


def test_func_multi_line():
    """
    This is a multi-line docstring.

    It has multiple lines.
    """
    pass


def test_func_exception():
    """This is a test function that raises an error."""
    raise Exception("Pah.")


class RegistryFunctionTests(TestCase):

    """Test the free functions in the registry module."""

    def test_fname(self):
        self.assertEqual(
            # wait, what?
            registry.fname(registry.fname),
            'side_effects.registry.fname'
        )

    def test_docstring(self):
        self.assertEqual(
            registry.docstring(test_func_no_docstring),
            None
        )
        self.assertEqual(
            registry.docstring(test_func_one_line),
            ["This is a one line docstring."]
        )
        self.assertEqual(
            registry.docstring(test_func_one_line_2),
            ["This is also a one line docstring."]
        )
        self.assertEqual(
            registry.docstring(test_func_multi_line),
            ["This is a multi-line docstring.", "", "It has multiple lines."]
        )

    def test_register_side_effect(self):
        registry.register_side_effect('foo', test_func_no_docstring)
        self.assertTrue(registry._registry.contains('foo', test_func_no_docstring))
        self.assertFalse(registry._registry.contains('foo', test_func_one_line))
        # try adding adding a duplicate
        registry.register_side_effect('foo', test_func_no_docstring)
        self.assertTrue(registry._registry.contains('foo', test_func_no_docstring))
        del registry._registry['foo']

    @mock.patch('side_effects.registry._run_func')
    def test_run_side_effects(self, mock_func):
        registry._registry.clear()
        registry.run_side_effects('foo')
        self.assertEqual(mock_func.call_count, 0)

        registry.register_side_effect('foo', test_func_no_docstring)
        registry.run_side_effects('foo')
        self.assertEqual(mock_func.call_count, 1)

        registry.register_side_effect('foo', test_func_one_line)
        registry.run_side_effects('foo')
        self.assertEqual(mock_func.call_count, 3)
        del registry._registry['foo']

    def test__run_func(self):
        """Test the _run_func function handles exceptions gracefully."""
        with mock.patch('side_effects.tests.test_func_no_docstring') as mock_func:
            registry._run_func(test_func_no_docstring)
            self.assertEqual(mock_func.call_count, 1)
        # if the func raises an exception we should log it but not fail
        with mock.patch('side_effects.registry.logger') as mock_logger:
            self.assertRaises(Exception, test_func_exception)
            registry._run_func(test_func_exception)
            self.assertEqual(mock_logger.exception.call_count, 1)


class RegistryTests(TestCase):

    """Tests for the registry module."""

    def test_registry_add_contains(self):
        """Check that add and contains functions work together."""
        r = registry.Registry()
        self.assertFalse(r.contains('foo', test_func_no_docstring))
        r.add('foo', test_func_no_docstring)
        self.assertTrue(r.contains('foo', test_func_no_docstring))


class DecoratorTests(TestCase):

    """Tests for the decorators module."""

    @mock.patch('side_effects.decorators.run_side_effects')
    def test_has_side_effects(self, mock_run):
        """Decorated functions should call run_side_effects."""
        # call the decorator directly - then call the decorated function
        # as the action takes places post-function call.
        func = decorators.has_side_effects('foo')(test_func_no_docstring)
        func('bar', kwarg1='baz')
        mock_run.assert_called_with('foo', 'bar', kwarg1='baz')

    @mock.patch('side_effects.decorators.register_side_effect')
    def test_is_side_effect_of(self, mock_register):
        """Decorated functions should be added to the registry."""
        # call the decorator directly - no need to call the decorated
        # function as the action takes place outside of that.
        func = decorators.is_side_effect_of('foo')(test_func_one_line)
        mock_register.assert_called_with('foo', test_func_one_line)
        # check the function still works!
        self.assertEqual(func(1, 2), 3)
