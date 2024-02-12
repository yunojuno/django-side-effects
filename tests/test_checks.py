from typing import Any

from django.test import TestCase

from side_effects import checks, registry


class SystemCheckTests(TestCase):
    def test_multiple_functions(self) -> None:
        def foo() -> None:
            pass

        def bar() -> None:
            pass

        def baz(arg1: Any) -> None:
            pass

        registry._registry.clear()
        registry.register_side_effect("test", foo)
        registry.register_side_effect("test", bar)
        self.assertEqual(checks.check_function_signatures(None), [])

        registry.register_side_effect("test", baz)
        errors = checks.check_function_signatures(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, checks.CHECK_ID_MULTIPLE_SIGNATURES)
