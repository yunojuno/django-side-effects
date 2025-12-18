from django.dispatch import Signal

# if using the disable_side_effects context manager or decorator,
# then this signal is used to communicate details of events that
# would have fired, but have been suppressed.
suppressed_side_effect = Signal()
