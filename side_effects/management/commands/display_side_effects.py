import json
from os import sys

from django.core.management.base import BaseCommand

from side_effects.registry import fname, docstring, _registry


class Command(BaseCommand):

    help = "Displays project side_effects."

    def add_arguments(self, parser):
        parser.add_argument(
            '--raw',
            action='store_true',
            help="Display raw mapping of labels to functions."
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help="Display full docstring for all side-effect functions."
        )
        parser.add_argument(
            '--check-docstrings',
            action='store_true',
            default=False,
            dest='docstrings',
            help="Check for valid docstrings on all registered functions (& fail if any missing)."
        )
        parser.add_argument(
            '--label',
            action='store',
            dest='label',
            help="Filter side-effects on a single event label."
        )
        parser.add_argument(
            '--label-contains',
            action='store',
            dest='label-contains',
            help="Filter side-effects on event labels containing the supplied value."
        )

    def handle(self, *args, **options):
        if options['label']:
            events = _registry.by_label(options['label'])
            self.stdout.write(
                f"\nSide-effects for event matching \'{options['label']}\':"
            )
        elif options['label-contains']:
            self.stdout.write(
                f"\nSide-effects for events matching \'*{options['label-contains']}*\':"
            )
            events = _registry.by_label_contains(options['label-contains'])
        else:
            events = _registry.items()
            self.stdout.write("\nRegistered side-effects:")

        if options['raw']:
            self.print_raw(events)
        elif options['docstrings']:
            self.check_docstrings(events)
        elif options['verbose']:
            self.print_verbose(events)
        else:
            self.print_default(events)

    def print_raw(self, events: dict) -> None:
        """Print out the fully-qualified named for each mapped function."""
        raw = {label: [fname(f) for f in funcs] for label, funcs in events}
        self.stdout.write(json.dumps(raw, indent=4))

    def check_docstrings(self, events: dict) -> None:
        """
        Check for docstrings on all functions, and exit non-0 if any are missing.

        This method is useful for CI style checks - as it will exit with a failure
        exit code (1). Can be used to ensure that all functions have docstrings.

        """
        exit_code = 0
        for _, funcs in events:
            for func in funcs:
                if docstring(func) is None:
                    self.stdout.write(f'{fname(func)} is missing docstring')
                    exit_code = 1
        sys.exit(exit_code)

    def print_verbose(self, events: dict) -> None:
        """Print the entire docstring for each mapped function."""
        for label, funcs in events:
            self.stdout.write('')
            self.stdout.write(label)
            self.stdout.write('')
            for func in funcs:
                docs = docstring(func)
                self.stdout.write('  - %s' % docs[0])
                for line in docs[1:]:
                    self.stdout.write('    %s' % line)
                self.stdout.write('')

    def print_default(self, events: dict) -> None:
        """Print the first line of the docstring for each mapped function."""
        for label, funcs in events:
            self.stdout.write('')
            self.stdout.write(label)
            for func in funcs:
                docs = docstring(func)
                if docs is None:
                    self.stdout.write('*** DOCSTRING MISSING: %s ***' % func.__name__)
                else:
                    self.stdout.write('  - %s' % docs[0])
