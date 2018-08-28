import json
from os import sys

from django.core.management.base import BaseCommand

from side_effects.registry import fname, docstring, _registry


class Command(BaseCommand):

    help = "Displays project side_effects."

    def __init__(self, *args, **kwargs):
        self.missing_docstrings = []
        super().__init__(*args, **kwargs)

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
            '--strict',
            action='store_true',
            default=False,
            dest='strict',
            help="Exit with a non-zero exit code if any registered functions have no docstrings."
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
        elif options['verbose']:
            self.print_verbose(events)
        else:
            self.print_default(events)

        self.print_missing()

        if options['strict']:
            self.exit()

    def print_raw(self, events: dict) -> None:
        """Print out the fully-qualified named for each mapped function."""
        raw = {label: [fname(f) for f in funcs] for label, funcs in events}
        self.stdout.write(json.dumps(raw, indent=4))

    def print_verbose(self, events: dict) -> None:
        """Print the entire docstring for each mapped function."""
        for label, funcs in events:
            self.stdout.write('')
            self.stdout.write(label)
            self.stdout.write('')
            for func in funcs:
                docs = docstring(func)
                if docs is None:
                    self.missing_docstrings.append(fname(func))
                    self.stderr.write(f'  x {fname(func)} (no docstring)')
                    self.stdout.write('')
                else:
                    self.stdout.write(f'  - {fname(func)}:')
                    self.stdout.write(f'    {docs[0]}')
                    for line in docs[1:]:
                        self.stdout.write(f'    {line}')
                    self.stdout.write('')

    def print_default(self, events: dict) -> None:
        """Print the first line of the docstring for each mapped function."""
        for label, funcs in events:
            self.stdout.write('')
            self.stdout.write(label)
            for func in funcs:
                docs = docstring(func)
                if docs is None:
                    self.missing_docstrings.append(fname(func))
                    self.stderr.write(f'  x {fname(func)} (no docstring)')
                else:
                    self.stdout.write(f'  - {docs[0]}')

    def print_missing(self):
        """Print out the contents of self.missing_docstrings."""
        if self.missing_docstrings:
            self.stderr.write('\nThe following functions have no docstrings:')
            for md in self.missing_docstrings:
                self.stderr.write(f'  {md}')
        else:
            self.stdout.write('\nAll registered functions have docstrings')

    def exit(self):
        """Exit based on whether there are any missing docstrings.

        This is used in CI scenarios to fail a build in which there are missing
        docstrings.

        """
        sys.exit(len(self.missing_docstrings))
