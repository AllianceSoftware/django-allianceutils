from django.apps import apps
from unipath import Path


def migrate_run_sql_file(schema_editor, app_name, filename):
    """

    Run arbitrary SQL from the migration/sql directory as part of a mgiration

    This is designed to be convenient to include as part of a migration:

    ```
    migrations.RunPython(insert_my_table),

    def insert_my_table(_, schema_editor):
        migrate_run_sql_file(schema_editor, 'my_app', '0001_my_table_sql_file')
    ```

    The reason you would do this as an external file & function is so that squashed migrations don't become
    unwieldy (it will inline and strip whitespace the SQL even for large data files)


    :param schema_editor: schema editor passed in by migrations
    :param app_name: app name to find the SQL in
    :param filename: file to run (without .sql extension)
    """
    path = Path(apps.get_app_config(app_name).path, 'migrations/sql', filename + '.sql')
    schema_editor.execute(path.read_file())


def migrate_create_group(schema_editor, groups):
    """
    Create authentication groups
    :param schema_editor: schema editor passed in by migrations
    :param groups: sequence of tuples of (group_id, group_name)
    """
    for group in groups:
        group_id, group_name = group[0], group[1]
        schema_editor.execute('INSERT IGNORE INTO auth_group VALUES (%s, %s)', (group_id, group_name))

    # update postgres autoid
    # schema_editor.execute("SELECT pg_catalog.setval('auth_group_id_seq', (SELECT MAX(id) FROM auth_group), TRUE)")
