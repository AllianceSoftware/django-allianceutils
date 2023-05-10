import logging
import sys

import django.core.management.base


class Command(django.core.management.base.BaseCommand):
    help = 'Print python logging configuration'

    def handle(self, **options):

        try:
            import logging_tree
        except ImportError as ie:
            raise django.core.management.base.CommandError('Need to pip install logging_tree first')

        # logging_tree only prints the config for loggers that have been created
        # some may not get created just by running a management command
        logging.getLogger('debug')
        logging.getLogger('django')
        logging.getLogger('django.db')
        logging.getLogger('django.db.backends.schema')
        logging.getLogger('django.request')
        logging.getLogger('django.security.csrf')
        logging.getLogger('django.server')
        logging.getLogger('django.template')
        logging.getLogger('net')
        logging.getLogger('py.warnings')

        # only print config if these modules are present
        try:
            import rules
            logging.getLogger('rules')
        except ImportError:
            pass

        try:
            import werkzeug
            logging.getLogger('werkzeug')
        except ImportError:
            pass

        # logging_tree always goes to stdout; need to capture it and redirect to django management stdout
        orig_stdout = sys.stdout
        try:
            sys.stdout = self.stdout
            logging_tree.printout()
        finally:
            sys.stdout = orig_stdout
