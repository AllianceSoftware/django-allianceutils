import subprocess

import django.apps
import django.conf
import django.core.management.commands.flush
import django.db

import allianceutils.management.commands.mysqlquickdump


class Command(django.core.management.commands.flush.Command):
    help = 'Quickly restore database contents (data only, not structure)'

    def add_arguments(self, parser):
        # super(Command, self).add_arguments(parser)
        # # there appears to be no official way to change this after construction, and Command
        # # doesn't provide a nice hook for changing it
        # parser.conflict_handler = 'resolve'
        # for group in parser._action_groups:
        #     group.conflict_handler = 'resolve'
        #
        # # override flush command options
        # parser.add_argument('--noinput', dest='interactive', action='store_const', const=False, help=argparse.SUPPRESS)
        # parser.add_argument('--no-initial-data', dest='load_initial_data', action='store_const', const=False, help=argparse.SUPPRESS)

        parser.add_argument('--database', action='store', dest='database',
            default=django.db.DEFAULT_DB_ALIAS,
            help='Database to load into (default: %(default)s)')

        parser.add_argument('--dump', action='store', dest='dump_file',
            default='data.sql',
            help='Database dump to load (default: %(default)s)')

        # inherited flush command arguments
        parser.set_defaults(interactive=False)
        parser.set_defaults(load_initial_data=False)

    def handle(self, **options):
        import datetime
        t1 = datetime.datetime.now()
        verbosity = options.get('verbosity')
        database = options.get('database')
        connection = django.db.connections[database]

        with connection.cursor() as cursor:
            cursor.execute('SELECT DATABASE() AS db_name')
            db_name = cursor.fetchone()[0]

        sql_file = allianceutils.management.commands.mysqlquickdump.get_dump_file_path(options['dump_file'])
        cmd = [
            'mysql',
            '--batch',
            '--disable-auto-rehash',
            '--no-auto-rehash',
            db_name,
        ]

        # if verbosity >= 3:
        #     self.stdout.write('Reading %s\n' % sql_file)
        #
        # # now load the new database SQL
        # with open(sql_file, 'rb') as f:
        #     sql = unicode(f.read(), 'utf-8')

        if verbosity >= 3:
            self.stdout.write('Truncating tables\n')

        # truncate tables
        super(Command, self).handle(**options)

        # if verbosity >= 3:
        #     self.stdout.write('Loading data\n')
        #
        # # insert data
        # connection = django.db.connections[database]
        # with django.db.transaction.atomic():
        #     with connection.cursor() as cursor:
        #         # This doesn't work because args is empty; I can't find a way of running
        #         # multiple raw (no argument substitution) SQL queries
        #         r = cursor.executemany(sql, None)

        if verbosity >= 1:
            self.stdout.write('%s %s\n' % (self.style.NOTICE('Executing'), ' '.join(cmd)))

        with open(sql_file, 'rb') as f:
            returncode = subprocess.call(cmd, stdin=f, stdout=self.stdout, stderr=self.stderr)
            if returncode != 0:
                self.stdout.write(self.style.ERROR('Error executing mysql (return code %s)\n' % returncode))
        t2 = datetime.datetime.now()
        print t2-t1


    @staticmethod
    def emit_post_migrate(verbosity, interactive, database):
        # override flush command:
        # don't emit migrate signal or content types, permissions will be recreated
        pass
