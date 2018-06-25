import io
import subprocess

import django.apps
import django.conf
import django.core.management.base
import django.db
import unipath


def get_dump_file_path(dump_file):
    f = unipath.Path(dump_file)
    if f.isabsolute():
        return f
    else:
        return unipath.Path(django.conf.settings.PROJECT_DIR, 'quicksql', dump_file)


class Command(django.core.management.base.BaseCommand):
    help = 'Quickly save database contents (data only, not structure)'

    def add_arguments(self, parser):
        parser.add_argument('--database', action='store', dest='database',
            default=django.db.DEFAULT_DB_ALIAS,
            help='Database to dump from (default: %(default)s)')

        parser.add_argument('--dump', action='store', dest='dump_file',
            default='data.sql',
            help='Database dump to save to (default: %(default)s)')

        parser.add_argument('--model', action='append', dest='dump_tables',
                        default=[],
                        help='Models dump to load (default: ALL')

        parser.add_argument('--explicit', action='store', dest='explicit_mode',
                        default=False,
                        help='Make mysqldump use full INSERTs with column names, one row per line. Slower but more robust. (default: FALSE')

    def handle(self, **options):
        verbosity = options.get('verbosity')
        database = options.get('database')
        connection = django.db.connections[database]

        with connection.cursor() as cursor:
            cursor.execute('SELECT DATABASE() AS db_name')
            db_name = cursor.fetchone()[0]

        sql_file = get_dump_file_path(options['dump_file'])
        cmd = [
            'mysqldump',
            db_name,
            ] + options['dump_tables'] +[
            '--comments',
            '--dump-date',
            '--disable-keys',
            '--extended-insert',
            '--lock-tables',
            '--add-locks',
            '--single-transaction',
            '--no-autocommit',
            '--quick',
            '--set-charset',
            '--no-create-db',
            '--no-create-info',
            '--replace',

            '--complete-insert',
        ]

        if options['explicit_mode']:
            cmd += ['--skip-extended-insert',]
        else:
            cmd += ['--extended-insert',]

        if not sql_file.parent.isdir():
            if verbosity >= 1:
                self.stdout.write('%s %s\n' % (self.style.WARNING('Creating'), sql_file.parent))
            sql_file.parent.mkdir(parents=True)

        if verbosity >= 1:
            self.stdout.write('%s %s\n' % (self.style.NOTICE('Executing'), ' '.join(cmd)))

        with open(sql_file, 'wb') as f:
            # in django >=2.0 the stderr wrapper don't have a fileno() attribute
            # see https://stackoverflow.com/a/48392466/6653190
            # unwrap stderr until we find something that supports fileno()
            wrapped_stderr = self.stderr
            fileno = None
            while fileno is None and hasattr(wrapped_stderr, '_out'):
                wrapped_stderr = wrapped_stderr._out
                try:
                    fileno = wrapped_stderr.fileno()
                except io.UnsupportedOperation:
                    pass
            returncode = subprocess.call(cmd, stdout=f, stderr=wrapped_stderr)
            if returncode != 0:
                self.stdout.write(self.style.ERROR('Error executing mysqldump (return code %s)\n' % returncode))

        if verbosity >= 2:
            self.stdout.write('Wrote %s\n' % sql_file)
