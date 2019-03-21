from unittest import mock

from django.test import TestCase

from side_effects import registry, decorators, settings


class RegistryFunctionTests(TestCase):

    """Test the free functions in the registry module."""

    def setUp(self):
        registry._registry.clear()

    def test_fname(self):
        self.assertEqual(
            # wait, what?
            registry.fname(registry.fname),
            "side_effects.registry.fname",
        )

    def test_docstring(self):
        def test_func_no_docstring(arg1):
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

        self.assertEqual(registry.docstring(test_func_no_docstring), None)
        self.assertEqual(
            registry.docstring(test_func_one_line), ["This is a one line docstring."]
        )
        self.assertEqual(
            registry.docstring(test_func_one_line_2),
            ["This is also a one line docstring."],
        )
        self.assertEqual(
            registry.docstring(test_func_multi_line),
            ["This is a multi-line docstring.", "", "It has multiple lines."],
        )

    def test_pass_return_value(self):
        def foo(arg1):
            pass

        def bar(arg1, **kwargz):
            pass

        def baz(*args, **kwargs):
            pass

        def dave(*args, return_value):
            pass

        def dee(arg1, return_value):
            pass

        def dozy(arg1, return_value=None):
            pass

        self.assertFalse(registry.pass_return_value(foo))
        self.assertFalse(registry.pass_return_value(bar))
        self.assertTrue(registry.pass_return_value(baz))
        self.assertTrue(registry.pass_return_value(dave))
        self.assertTrue(registry.pass_return_value(dee))
        self.assertTrue(registry.pass_return_value(dozy))

    def test_register_side_effect(self):
        def test_func1():
            pass

        def test_func2():
            pass

        registry.register_side_effect("foo", test_func1)
        self.assertTrue(registry._registry.contains("foo", test_func1))
        self.assertFalse(registry._registry.contains("foo", test_func2))
        # try adding adding a duplicate
        registry.register_side_effect("foo", test_func1)
        self.assertTrue(registry._registry.contains("foo", test_func1))

    @mock.patch("side_effects.registry._run_func")
    def test_run_side_effects(self, mock_func):
        def test_func1():
            pass

        def test_func2():
            pass

        registry.run_side_effects("foo")
        self.assertEqual(mock_func.call_count, 0)

        mock_func.reset_mock()
        registry.register_side_effect("foo", test_func1)
        registry.run_side_effects("foo")
        self.assertEqual(mock_func.call_count, 1)

        mock_func.reset_mock()
        registry.register_side_effect("foo", test_func2)
        registry.run_side_effects("foo")
        self.assertEqual(mock_func.call_count, 2)

        mock_func.reset_mock()
        with mock.patch("side_effects.settings.TEST_MODE", True):
            registry.run_side_effects("foo")
            self.assertEqual(mock_func.call_count, 0)
        with mock.patch("side_effects.settings.TEST_MODE", False):
            registry.run_side_effects("foo")
            self.assertEqual(mock_func.call_count, 2)

    @mock.patch("side_effects.registry.settings.TEST_MODE_FAIL", True)
    def test_run_side_effects__test_mode_fail(self):
        def test_func():
            pass

        registry.register_side_effect("foo", test_func)
        self.assertRaises(
            registry.SideEffectsTestFailure, registry.run_side_effects, "foo"
        )

    def test__run_func__no_return_value(self):
        """Test the _run_func function does not pass return_value if not required."""

        def test_func():
            pass

        registry._run_func(test_func, return_value=None)

    def test__run_func__with_return_value(self):
        """Test the _run_func function passes through the return_value if required."""

        def test_func(**kwargs):
            assert "return_value" in kwargs

        # return_value not passed through, so fails
        registry._run_func(test_func)
        # self.assertRaises(KeyError, registry._run_func, test_func)
        registry._run_func(test_func, return_value=None)

    def test__run_func__aborts_on_error(self):
        """Test the _run_func function handles ABORT_ON_ERROR correctly."""

        def test_func():
            raise Exception("Pah")

        # error is logged, but not raised
        with mock.patch.object(settings, "ABORT_ON_ERROR", False):
            self.assertFalse(settings.ABORT_ON_ERROR)
            registry._run_func(test_func, return_value=None)

        # error is raised
        with mock.patch.object(settings, "ABORT_ON_ERROR", True):
            self.assertTrue(settings.ABORT_ON_ERROR)
            self.assertRaises(Exception, registry._run_func, test_func)


class RegistryTests(TestCase):

    """Tests for the registry module."""

    def test_registry_add_contains(self):
        """Check that add and contains functions work together."""

        def test_func():
            pass

        r = registry.Registry()
        self.assertFalse(r.contains("foo", test_func))
        r.add("foo", test_func)
        self.assertTrue(r.contains("foo", test_func))

    def test_by_label(self):
        def test_func():
            pass

        r = registry.Registry()
        r.add("foo", test_func)
        self.assertEqual(r.by_label("foo").items(), r.items())
        self.assertEqual(r.by_label("foo"), {"foo": [test_func]})
        self.assertEqual(r.by_label("bar"), {})

    def test_by_label_contains(self):
        def test_func():
            pass

        r = registry.Registry()
        r.add("foo", test_func)
        self.assertEqual(r.by_label_contains("foo").items(), r.items())
        self.assertEqual(r.by_label_contains("f"), {"foo": [test_func]})
        self.assertEqual(r.by_label_contains("fo"), {"foo": [test_func]})
        self.assertEqual(r.by_label_contains("foo"), {"foo": [test_func]})
        self.assertEqual(r.by_label_contains("food"), {})

    @mock.patch("side_effects.registry._run_func")
    def test__run_side_effects__no_return_value(self, mock_run):
        """Test return_value is not passed"""

        def no_return_value(*args, **kwargz):
            assert "return_value" not in kwargz

        r = registry.Registry()
        r.add("foo", no_return_value)
        r._run_side_effects("foo")
        r._run_side_effects("foo", return_value=None)

    def test__run_side_effects__with_return_value(self):
        """Test return_value is passed"""
        r = registry.Registry()

        def has_return_value(*args, **kwargs):
            assert "return_value" in kwargs

        r.add("foo", has_return_value)
        r._run_side_effects("foo", return_value=None)


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
        mock_registry.run_side_effects.assert_called_with("foo", 1, return_value=2)

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
