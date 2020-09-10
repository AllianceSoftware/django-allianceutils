from pathlib import Path

from django.apps import apps


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
    schema_editor.execute(path.read_text())


