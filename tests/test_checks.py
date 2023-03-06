from __future__ import annotations

import inspect

from django.test import TestCase

from side_effects import checks, registry

from .fixtures.checks_fixtures import Goo, gar


class SystemCheckTests(TestCase):
    def test_multiple_functions(self):
        def foo():
            pass

        def bar():
            pass

        def baz(arg1):
            pass

        registry._registry.clear()
        registry.register_side_effect("test", foo)
        registry.register_side_effect("test", bar)
        self.assertEqual(checks.check_function_signatures(None), [])

        registry.register_side_effect("test", baz)
        errors = checks.check_function_signatures(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, checks.CHECK_ID_MULTIPLE_SIGNATURES)

    def test_similar_functions(self):
        def foo(arg1: Goo):
            pass

        check_error = checks.CHECK_ID_NO_ANNOTATIONS
        # inspect.get_annotations is only available in python versions > 3.7
        if not hasattr(inspect, "get_annotations"):
            check_error = checks.CHECK_ID_MULTIPLE_SIGNATURES
        registry._registry.clear()
        registry.register_side_effect("test", foo)
        registry.register_side_effect("test", gar)

        errors = checks.check_function_signatures(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, check_error)
