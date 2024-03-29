from typing import Any
from unittest import mock

import pytest
from django.test import TestCase

from side_effects import decorators, registry
from side_effects.decorators import has_side_effects


class DecoratorTests(TestCase):
    """Tests for the decorators module."""

    def setUp(self) -> None:
        registry._registry.clear()

    def test_http_response_check(self) -> None:
        """Test the HTTP response check rejects 4xx, 5xx status_codes."""
        response = decorators.HttpResponse(status=200)
        self.assertTrue(decorators.http_response_check(response))
        response.status_code = 300
        self.assertTrue(decorators.http_response_check(response))
        response.status_code = 400
        self.assertFalse(decorators.http_response_check(response))
        response.status_code = 500
        self.assertFalse(decorators.http_response_check(response))
        response.status_code = 600
        self.assertTrue(decorators.http_response_check(response))

    @mock.patch("side_effects.decorators.registry")
    def test_has_side_effects(self, mock_registry: mock.Mock) -> None:
        """Decorated functions should call run_side_effects."""

        # call the decorator directly - then call the decorated function
        # as the action takes places post-function call.
        def test_func(arg1: int) -> int:
            return arg1 * 2

        func = decorators.has_side_effects("foo")(test_func)
        self.assertEqual(func(1), 2)
        mock_registry.run_side_effects.assert_called_with("foo", 1, return_value=2)

    @mock.patch("side_effects.decorators.registry")
    def test_has_side_effects__run_on_exit_false(
        self, mock_registry: mock.Mock
    ) -> None:
        """Decorated functions should call run_side_effects."""

        def test_func(*args: Any, **kwargs: Any) -> None:
            pass

        func = decorators.has_side_effects("foo", run_on_exit=lambda r: False)(
            test_func
        )
        func("bar")
        mock_registry.run_side_effects.assert_not_called()

    @mock.patch("side_effects.registry.register_side_effect")
    def test_is_side_effect_of(self, mock_register: mock.Mock) -> Any:
        """Decorated functions should be added to the registry."""

        def test_func(arg1: Any, arg2: Any) -> None:
            return arg1 + arg2

        # call the decorator directly - no need to call the decorated
        # function as the action takes place outside of that.
        func = decorators.is_side_effect_of("foo")(test_func)
        mock_register.assert_called_with("foo", test_func)
        # check the function still works!
        self.assertEqual(func(1, 2), 3)

    @decorators.disable_side_effects()
    def test_disable_side_effects(self, events: list[str]) -> None:
        # simple func that calls the side-effect 'foo'
        def test_func() -> None:
            registry.run_side_effects("foo")

        registry.register_side_effect("foo", test_func)

        test_func()
        self.assertEqual(events, ["foo"])
        test_func()
        self.assertEqual(events, ["foo", "foo"])

    @mock.patch("side_effects.decorators.registry")
    def test_disable_on_error(self, mock_registry: mock.Mock) -> None:
        """Check that run_side_effects is not called on error."""

        @has_side_effects("foo")
        def foo() -> None:
            raise Exception("HELP")

        with pytest.raises(Exception):
            foo()

        assert mock_registry.run_side_effects.call_count == 0
