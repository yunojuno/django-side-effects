import json

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
            '--label',
            action='store',
            dest='label',
            help="Filter side-effects on a single event label"
        )
        parser.add_argument(
            '--label-contains',
            action='store',
            dest='label-contains',
            help="Filter side-effects on event labels containing the supplied value"
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

    def print_raw(self, events):
        """Print out the fully-qualified named for each mapped function."""
        raw = {label: [fname(f) for f in funcs] for label, funcs in events.items()}
        self.stdout.write(json.dumps(raw, indent=4))

    def print_verbose(self, events):
        """Print the entire docstring for each mapped function."""
        for label, funcs in events.items():
            self.stdout.write('')
            self.stdout.write(label)
            self.stdout.write('')
            for func in funcs:
                docs = docstring(func)
                self.stdout.write('  - %s' % docs[0])
                for line in docs[1:]:
                    self.stdout.write('    %s' % line)
                self.stdout.write('')

    def print_default(self, events):
        """Print the first line of the docstring for each mapped function."""
        for label, funcs in events.items():
            self.stdout.write('')
            self.stdout.write(label)
            for func in funcs:
                docs = docstring(func)
                if docs is None:
                    self.stdout.write('*** DOCSTRING MISSING: %s ***' % func.__name__)
                else:
                    self.stdout.write('  - %s' % docs[0])
