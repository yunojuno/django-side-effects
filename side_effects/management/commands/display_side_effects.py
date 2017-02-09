# -*- coding: utf-8 -*-
from __future__ import absolute_import

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

    def handle(self, *args, **options):
        self.stdout.write("The following side-effects are registered:")
        if options['raw']:
            self.print_raw()
        elif options['verbose']:
            self.print_verbose()
        else:
            self.print_default()

    def print_raw(self):
        """Print out the fully-qualified named for each mapped function."""
        raw = {label: [fname(f) for f in funcs] for label, funcs in _registry.iteritems()}
        self.stdout.write(json.dumps(raw, indent=4))

    def print_verbose(self):
        """Print the entire docstring for each mapped function."""
        for label, funcs in _registry.iteritems():
            self.stdout.write('')
            self.stdout.write(label)
            self.stdout.write('')
            for func in funcs:
                docs = docstring(func)
                self.stdout.write('  - %s' % docs[0])
                for line in docs[1:]:
                    self.stdout.write('    %s' % line)
                self.stdout.write('')

    def print_default(self):
        """Print the first line of the docstring for each mapped function."""
        for label, funcs in _registry.iteritems():
            self.stdout.write('')
            self.stdout.write(label)
            for func in funcs:
                docs = docstring(func)
                self.stdout.write('  - %s' % docs[0])
