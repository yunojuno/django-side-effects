from django.test import TestCase

from side_effects import registry


class TestRunSideEffects(TestCase):
    """
    Test the run_side_effects function.

    This uses TestCase as we are using transaction.on_commit internally
    and the easiest way to test this is with the captureOnCommitCallbacks
    method.

    """

    def test_run_side_effects__on_commit(self) -> None:
        def foo() -> None:
            pass

        registry._registry.clear()
        registry.register_side_effect("foo", foo)
        with self.captureOnCommitCallbacks() as callbacks:
            registry.run_side_effects("foo")
        assert callbacks[0].func == registry._registry.run_side_effects
        assert callbacks[0].args == ("foo",)
        assert callbacks[0].keywords == {"return_value": None}

    def test_run_side_effects__suppressed(self) -> None:
        def foo() -> None:
            pass

        registry._registry.clear()
        registry.register_side_effect("foo", foo)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with registry.disable_side_effects() as events:
                registry.run_side_effects("foo")
            assert events == ["foo"]
        assert len(callbacks) == 0
