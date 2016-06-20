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
            help='Database to load into (default: %(default)s)')

        parser.add_argument('--dump', action='store', dest='dump_file',
            default='data.sql',
            help='Database dump to load (default: %(default)s)')

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

            # These make things more resilient to schema changes but are significantly slower:
            # '--skip-extended-insert',
            # '--skip-compact',
            # '--complete-insert',
        ]
        if not sql_file.parent.isdir():
            if verbosity >= 1:
                self.stdout.write('%s %s\n' % (self.style.WARNING('Creating'), sql_file.parent))
            sql_file.parent.mkdir(parents=True)

        if verbosity >= 1:
            self.stdout.write('%s %s\n' % (self.style.NOTICE('Executing'), ' '.join(cmd)))

        with open(sql_file, 'wb') as f:
            returncode = subprocess.call(cmd, stdout=f, stderr=self.stderr)
            if returncode != 0:
                self.stdout.write(self.style.ERROR('Error executing mysqldump (return code %s)\n' % returncode))

        if verbosity >= 2:
            self.stdout.write('Wrote %s\n' % sql_file)
