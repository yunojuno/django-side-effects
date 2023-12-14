from __future__ import annotations

from typing import Any
from unittest import mock

from django.test import TestCase

from side_effects import registry, settings


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
            """This is also a one line docstring."""
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

    def test_try_bind__with_return_value(self):
        def foo1(return_value):
            pass

        def foo2(arg1, return_value):
            pass

        def foo3(*args, return_value):
            pass

        def foo4(return_value, **kwargs):
            pass

        def foo5(arg1, **kwargs):
            pass

        self.assertTrue(registry.try_bind(foo1, return_value=1))
        self.assertTrue(registry.try_bind(foo2, 1, return_value=1))
        self.assertTrue(registry.try_bind(foo3, 1, 2, 3, return_value=1))
        self.assertTrue(registry.try_bind(foo4, bar="baz", return_value=1))
        self.assertTrue(registry.try_bind(foo5, 1, return_value=1))

    def test_try_bind__without_return_value(self):
        def foo1():
            pass

        def foo2(arg1):
            pass

        def foo3(*args):
            pass

        self.assertFalse(registry.try_bind(foo1, return_value=1))
        self.assertFalse(registry.try_bind(foo2, 1, return_value=1))
        self.assertFalse(registry.try_bind(foo3, 1, 2, 3, return_value=1))

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

        meta = registry.SideEffectMeta(label="foo", return_value=None)
        registry._run_func(test_func, meta=meta)

    def test__run_func__with_return_value(self):
        """Test the _run_func function passes through the return_value if required."""

        def test_func(**kwargs):
            assert "return_value" in kwargs

        meta = registry.SideEffectMeta(label="foo", return_value=None)
        registry._run_func(test_func, meta=meta)

    def test__run_func__aborts_on_error(self):
        """Test the _run_func function handles ABORT_ON_ERROR correctly."""

        def test_func():
            raise Exception("Pah")

        meta = registry.SideEffectMeta(label="foo", return_value=None)

        # error is logged, but not raised
        with mock.patch.object(settings, "ABORT_ON_ERROR", False):
            self.assertFalse(settings.ABORT_ON_ERROR)
            registry._run_func(test_func, meta=meta)

        # error is raised
        with mock.patch.object(settings, "ABORT_ON_ERROR", True):
            self.assertTrue(settings.ABORT_ON_ERROR)
            self.assertRaises(Exception, registry._run_func, test_func, meta=meta)

    def test__run_func__signature_mismatch(self):
        """Test the _run_func function always raises SignatureMismatch."""

        def test_func():
            raise Exception("Pah")

        meta = registry.SideEffectMeta(label="foo", return_value=None)
        with mock.patch.object(settings, "ABORT_ON_ERROR", False):
            self.assertRaises(
                registry.SignatureMismatch,
                registry._run_func,
                test_func,
                1,
                meta=meta,
            )


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

    def test__run_side_effects__with_side_effect_meta(self) -> None:
        """Test the meta object is passed if the function requires it explictly."""
        actual_call_a = mock.Mock()
        actual_call_b = mock.Mock()
        actual_call_c = mock.Mock()
        r = registry.Registry()

        def handler_a(*, side_effect_meta: registry.SideEffectMeta) -> None:
            actual_call_a(side_effect_meta=side_effect_meta)

        def handler_b(*args: Any, side_effect_meta: registry.SideEffectMeta) -> None:
            actual_call_b(*args, side_effect_meta=side_effect_meta)

        def handler_c(
            *, side_effect_meta: registry.SideEffectMeta, **kwargs: Any
        ) -> None:
            actual_call_c(side_effect_meta=side_effect_meta, **kwargs)

        r.add("a", handler_a)
        r.add("b", handler_b)
        r.add("c", handler_c)

        meta_a = registry.SideEffectMeta(label="a", return_value=None)
        r._run_side_effects(meta=meta_a)
        actual_call_a.assert_called_once_with(side_effect_meta=meta_a)

        meta_b = registry.SideEffectMeta(label="b", return_value=None)
        r._run_side_effects(1, 2, 3, meta=meta_b)
        actual_call_b.assert_called_once_with(1, 2, 3, side_effect_meta=meta_b)

        meta_c = registry.SideEffectMeta(label="c", return_value=None)
        r._run_side_effects(meta=meta_c, x=1, y=2)
        actual_call_c.assert_called_once_with(side_effect_meta=meta_c, x=1, y=2)

    def test__run_side_effects__side_effect_meta_must_be_keyword_only(self) -> None:
        """Test that the meta object is not passed if not a keyword-only param."""
        meta = registry.SideEffectMeta(label="foo", return_value=None)
        r = registry.Registry()

        def handler(side_effect_meta: registry.SideEffectMeta, *args, **kwargs: Any) -> None:
            pass

        r.add(meta.label, handler)
        self.assertRaises(registry.SignatureMismatch, r._run_side_effects, meta=meta)

    def test__run_side_effects__with_return_value(self):
        """Test return_value is passed if the function has **kwargs."""
        actual_call = mock.Mock()
        r = registry.Registry()

        def has_return_value(*args, **kwargs):
            actual_call(*args, **kwargs)

        r.add("foo", has_return_value)
        meta = registry.SideEffectMeta(label="foo", return_value=None)
        r._run_side_effects(meta=meta)
        actual_call.assert_called_once_with(return_value=None)

    def test_try_bind_all(self):
        def foo1(return_value):
            pass

        def foo2(arg1, return_value):
            pass

        def foo3(*args, return_value):
            pass

        def foo4(return_value, **kwargs):
            pass

        def foo5(arg1, **kwargs):
            pass

        r = registry.Registry()
        r.add("foo", foo1)
        r.add("foo", foo2)
        r.add("foo", foo3)
        r.add("foo", foo4)
        r.add("foo", foo5)
        meta = registry.SideEffectMeta(label="foo", return_value=None)
        r.try_bind_all(1, meta=meta)
        self.assertRaises(
            registry.SignatureMismatch, r.try_bind_all, 1, 2, meta=meta
        )
