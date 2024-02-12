from typing import Any
from unittest import mock

from django.test import TestCase

from side_effects import registry, settings


class RegistryFunctionTests(TestCase):
    """Test the free functions in the registry module."""

    def setUp(self) -> None:
        registry._registry.clear()

    def test_fname(self) -> None:
        self.assertEqual(
            # wait, what?
            registry.fname(registry.fname),
            "side_effects.registry.fname",
        )

    def test_docstring(self) -> None:
        def test_func_no_docstring(arg1: Any) -> None:
            pass

        def test_func_one_line(*args: Any) -> None:
            """This is a one line docstring."""
            return sum(args)

        def test_func_one_line_2() -> None:
            """This is also a one line docstring."""
            pass

        def test_func_multi_line() -> None:
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

    def test_try_bind__with_return_value(self) -> None:
        def foo1(return_value: Any) -> None:
            pass

        def foo2(arg1: Any, return_value: Any) -> None:
            pass

        def foo3(*args: Any, return_value: Any) -> None:
            pass

        def foo4(return_value: Any, **kwargs: Any) -> None:
            pass

        def foo5(arg1: Any, **kwargs: Any) -> None:
            pass

        self.assertTrue(registry.try_bind(foo1, return_value=1))
        self.assertTrue(registry.try_bind(foo2, 1, return_value=1))
        self.assertTrue(registry.try_bind(foo3, 1, 2, 3, return_value=1))
        self.assertTrue(registry.try_bind(foo4, bar="baz", return_value=1))
        self.assertTrue(registry.try_bind(foo5, 1, return_value=1))

    def test_try_bind__without_return_value(self) -> None:
        def foo1() -> None:
            pass

        def foo2(arg1: Any) -> None:
            pass

        def foo3(*args: Any) -> None:
            pass

        self.assertFalse(registry.try_bind(foo1, return_value=1))
        self.assertFalse(registry.try_bind(foo2, 1, return_value=1))
        self.assertFalse(registry.try_bind(foo3, 1, 2, 3, return_value=1))

    def test_register_side_effect(self) -> None:
        def test_func1() -> None:
            pass

        def test_func2() -> None:
            pass

        registry.register_side_effect("foo", test_func1)
        self.assertTrue(registry._registry.contains("foo", test_func1))
        self.assertFalse(registry._registry.contains("foo", test_func2))
        # try adding adding a duplicate
        registry.register_side_effect("foo", test_func1)
        self.assertTrue(registry._registry.contains("foo", test_func1))

    def test_get_side_effects(self) -> None:
        def test_func1() -> None:
            pass

        registry.register_side_effect("foo", test_func1)
        self.assertEqual(registry.get_side_effects("foo"), [test_func1])

    @mock.patch("side_effects.registry.settings.TEST_MODE", False)
    def test_run_side_effects(self) -> None:
        def test_func(x: list) -> None:
            x.append("foo")

        assert registry._registry.is_suppressed is False
        registry.register_side_effect("foo", test_func)
        x: list[str] = []
        registry._registry.run_side_effects("foo", x)
        assert x == ["foo"]

    def test__run_func__no_return_value(self) -> None:
        """Test the _run_func function does not pass return_value if not required."""

        def test_func() -> None:
            pass

        registry._run_func(test_func, return_value=None)

    def test__run_func__with_return_value(self) -> None:
        """Test the _run_func function passes through the return_value if required."""

        def test_func(**kwargs: Any) -> None:
            assert "return_value" in kwargs

        # return_value not passed through, so fails
        registry._run_func(test_func)
        # self.assertRaises(KeyError, registry._run_func, test_func)
        registry._run_func(test_func, return_value=None)

    def test__run_func__aborts_on_error(self) -> None:
        """Test the _run_func function handles ABORT_ON_ERROR correctly."""

        def test_func() -> None:
            raise Exception("Pah")

        # error is logged, but not raised
        with mock.patch.object(settings, "ABORT_ON_ERROR", False):
            self.assertFalse(settings.ABORT_ON_ERROR)
            registry._run_func(test_func, return_value=None)

        # error is raised
        with mock.patch.object(settings, "ABORT_ON_ERROR", True):
            self.assertTrue(settings.ABORT_ON_ERROR)
            self.assertRaises(Exception, registry._run_func, test_func)

    def test__run_func__signature_mismatch(self) -> None:
        """Test the _run_func function always raises SignatureMismatch."""

        def test_func() -> None:
            raise Exception("Pah")

        with mock.patch.object(settings, "ABORT_ON_ERROR", False):
            self.assertRaises(
                registry.SignatureMismatch, registry._run_func, test_func, 1
            )


class RegistryTests(TestCase):
    """Tests for the registry module."""

    def test_registry_add_contains(self) -> None:
        """Check that add and contains functions work together."""

        def test_func() -> None:
            pass

        r = registry.Registry()
        self.assertFalse(r.contains("foo", test_func))
        r.add("foo", test_func)
        self.assertTrue(r.contains("foo", test_func))

    def test_by_label(self) -> None:
        def test_func() -> None:
            pass

        r = registry.Registry()
        r.add("foo", test_func)
        self.assertEqual(r.by_label("foo").items(), r.items())
        self.assertEqual(r.by_label("foo"), {"foo": [test_func]})
        self.assertEqual(r.by_label("bar"), {})

    def test_by_label_contains(self) -> None:
        def test_func() -> None:
            pass

        r = registry.Registry()
        r.add("foo", test_func)
        self.assertEqual(r.by_label_contains("foo").items(), r.items())
        self.assertEqual(r.by_label_contains("f"), {"foo": [test_func]})
        self.assertEqual(r.by_label_contains("fo"), {"foo": [test_func]})
        self.assertEqual(r.by_label_contains("foo"), {"foo": [test_func]})
        self.assertEqual(r.by_label_contains("food"), {})
