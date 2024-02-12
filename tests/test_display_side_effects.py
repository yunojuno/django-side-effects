from __future__ import annotations

from django.test import TestCase

from side_effects.management.commands.display_side_effects import sort_events


class SortEventsTests(TestCase):
    def test_sort_events(self) -> None:
        def handler_zero() -> None:
            """Docstring 0."""

        def handler_one() -> None:
            """Docstring 1."""

        def handler_two() -> None:
            """Docstring 2."""

        events = {
            "label_2": [handler_zero, handler_one, handler_two],
            "label_1": [handler_zero, handler_two],
        }

        sorted_by_function_name = list(
            sort_events(
                events,
                handler_sort_key=lambda handler: handler.__name__,
            ).items()
        )
        assert sorted_by_function_name == [
            ("label_1", [handler_two, handler_zero]),
            ("label_2", [handler_one, handler_two, handler_zero]),
        ]

        sorted_by_docstring = list(
            sort_events(
                events,
                handler_sort_key=lambda handler: handler.__doc__,
            ).items()
        )
        assert sorted_by_docstring == [
            ("label_1", [handler_zero, handler_two]),
            ("label_2", [handler_zero, handler_one, handler_two]),
        ]
