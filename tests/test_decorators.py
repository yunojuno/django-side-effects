from unittest import mock

import pytest
from django.db import transaction
from django.test import TestCase

from side_effects import decorators, registry
from side_effects.decorators import has_side_effects


class DecoratorTests(TestCase):
    """Tests for the decorators module."""

    def setUp(self):
        registry._registry.clear()

    def test_http_response_check(self):
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
    def test_has_side_effects(self, mock_registry):
        """Decorated functions should call run_side_effects."""
        # call the decorator directly - then call the decorated function
        # as the action takes places post-function call.
        def test_func(arg1: int):
            return arg1 * 2

        func = decorators.has_side_effects("foo")(test_func)
        func(1)
        mock_registry.run_side_effects_on_commit.assert_called_with(
            "foo", 1, return_value=2
        )

    @mock.patch("side_effects.decorators.registry")
    def test_has_side_effects__run_on_exit_false(self, mock_registry):
        """Decorated functions should call run_side_effects."""

        def test_func(*args, **kwargs):
            pass

        func = decorators.has_side_effects("foo", run_on_exit=lambda r: False)(
            test_func
        )
        func("bar")
        mock_registry.run_side_effects.assert_not_called()

    @mock.patch("side_effects.registry.register_side_effect")
    def test_is_side_effect_of(self, mock_register):
        """Decorated functions should be added to the registry."""

        def test_func(arg1, arg2):
            return arg1 + arg2

        # call the decorator directly - no need to call the decorated
        # function as the action takes place outside of that.
        func = decorators.is_side_effect_of("foo")(test_func)
        mock_register.assert_called_with("foo", test_func)
        # check the function still works!
        self.assertEqual(func(1, 2), 3)

    @decorators.disable_side_effects()
    def test_disable_side_effects(self, events):

        # simple func that calls the side-effect 'foo'
        def test_func():
            registry.run_side_effects("foo")

        registry.register_side_effect("foo", test_func)

        test_func()
        self.assertEqual(events, ["foo"])
        test_func()
        self.assertEqual(events, ["foo", "foo"])

    @mock.patch("side_effects.decorators.registry")
    def test_disable_on_error(self, mock_registry):
        """Check that run_side_effects is not called on error."""

        @has_side_effects("foo")
        def foo():
            raise Exception("HELP")

        with pytest.raises(Exception):
            foo()

        assert mock_registry.run_side_effects.call_count == 0

    def test_transaction_rollback(self):
        """Test the transaction awareness of the decorator."""

        @transaction.atomic
        def outer_func() -> None:
            inner_func()
            raise Exception("Rolling back transaction")

        @has_side_effects("foo")
        @transaction.atomic
        def inner_func() -> None:
            conn = transaction.get_connection()
            assert conn.in_atomic_block

        # calling inner_func directly will trigger has_side_effects, which
        # will defer the run_side_effects_on_commit call by passing it to
        # the transaction.on_commit function.
        with TestCase.captureOnCommitCallbacks() as callbacks:
            inner_func()
        assert len(callbacks) == 1
        assert callbacks[0].func == registry._registry.run_side_effects
        assert callbacks[0].args == ("foo",)
        assert callbacks[0].keywords == {"return_value": None}

        # calling outer_func will rollback the transaction, which will
        # in turn clear out the callbacks registered with on_commit - so
        # no side-effects will run.
        with TestCase.captureOnCommitCallbacks() as callbacks:
            try:
                outer_func()
            except:  # noqa
                pass
        assert callbacks == []


class ContextManagerTests(TestCase):
    @mock.patch("side_effects.registry._run_func")
    def test_disable_side_effects(self, mock_func):
        """Side-effects can be temporarily disabled."""

        def test_func():
            pass

        registry._registry.clear()
        registry.register_side_effect("foo", test_func)

        registry.run_side_effects("foo")
        self.assertEqual(mock_func.call_count, 1)

        # shouldn't get another call inside the CM
        with registry.disable_side_effects() as events:
            registry.run_side_effects("foo")
            self.assertEqual(mock_func.call_count, 1)
            self.assertEqual(events, ["foo"])

        # re-enabled
        registry.run_side_effects("foo")
        self.assertEqual(mock_func.call_count, 2)
