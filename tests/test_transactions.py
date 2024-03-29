import pytest
from django.core import mail
from django.db import transaction
from django.test import TestCase, TransactionTestCase

from side_effects import registry
from side_effects.decorators import has_side_effects


def email_side_effect() -> None:
    """Dummy function to simulate a side-effect."""
    mail.send_mail(
        "Subject",
        "message.",
        "from@example.com",
        ["to@example.com"],
        fail_silently=False,
    )


class TestTransactionOnCommit(TestCase):
    """
    Test the commit / rollback scenarios that impact side-effects.

    When using the has_side_effects decorator on a function, the
    side-effects should only fire if the transaction within which the
    decorated function is operating is committed. If the source
    (decorated) function completes, but the calling function (outside
    the decorated function) fails, then the transaction is aborted and
    the side-effects should *not* fire.

    This test class is deliberately not parametrized as readability
    trumps efficiency in this case. This is a hard one to follow.

    """

    @has_side_effects("foo")
    @transaction.atomic
    def inner_commit(self) -> None:
        """Run the side-effects as expected."""
        assert transaction.get_connection().in_atomic_block

    @has_side_effects("foo")
    @transaction.atomic
    def inner_rollback(self) -> None:
        """Rollback the source (inner) function - side-effects should *not* fire."""
        raise Exception("Rolling back inner transaction")

    @transaction.atomic
    def outer_commit(self) -> None:
        """Commit the outer function - side-effects should fire."""
        self.inner_commit()

    @transaction.atomic
    def outer_rollback(self) -> None:
        """Rollback outer function - side-effects should *not* fire."""
        self.inner_commit()
        raise Exception("Rolling back outer transaction")

    def test_inner_func_commit(self) -> None:
        with self.captureOnCommitCallbacks() as callbacks:
            self.inner_commit()
        assert len(callbacks) == 1
        assert callbacks[0].func == registry._registry.run_side_effects
        assert callbacks[0].args == ("foo", self)
        assert callbacks[0].keywords == {"return_value": None}

    def test_outer_func_commit(self) -> None:
        with self.captureOnCommitCallbacks() as callbacks:
            self.outer_commit()
        assert len(callbacks) == 1
        assert callbacks[0].func == registry._registry.run_side_effects
        assert callbacks[0].args == ("foo", self)
        assert callbacks[0].keywords == {"return_value": None}

    def test_inner_func_rollback(self) -> None:
        with self.captureOnCommitCallbacks() as callbacks:
            with pytest.raises(Exception):
                self.inner_rollback()
        assert callbacks == []

    def test_outer_func_rollback(self) -> None:
        with self.captureOnCommitCallbacks() as callbacks:
            with pytest.raises(Exception):
                self.outer_rollback()
        assert callbacks == []

    def test_on_commit__rollback(self) -> None:
        registry._registry.clear()
        registry.register_side_effect("foo", email_side_effect)
        try:
            mail.outbox = []
            with transaction.atomic():
                # defers the call to Registry.run_side_effects until
                # the transaction is committed.
                registry.run_side_effects("foo")
                # this will cause the transaction to rollback, and
                # therefore the side-effect should not fire.
                raise Exception("Rolling back transaction")
        except Exception:
            assert len(mail.outbox) == 0


class TestDisableSideEffectsOnCommit(TransactionTestCase):
    """Integration test for the disable_side_effects context manager."""

    def test_outbox_expected(self) -> None:
        registry._registry.clear()
        registry.register_side_effect("foo", email_side_effect)
        with transaction.atomic():
            mail.outbox = []
            registry.run_side_effects("foo")
            # we are still inside the transaction, so the side-effect
            # should not have fired yet.
            assert len(mail.outbox) == 0
        # now we are outside the transaction, so the side-effect should
        # have fired.
        assert len(mail.outbox) == 1

    def test_disable_side_effects(self) -> None:
        registry._registry.clear()
        registry.register_side_effect("foo", email_side_effect)
        with registry.disable_side_effects() as events:
            mail.outbox = []
            registry.run_side_effects("foo")
        assert events == ["foo"]
        assert len(mail.outbox) == 0
