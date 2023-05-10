from pathlib import Path
from typing import Union

from django.apps import apps
from django.db.migrations import RunSQL


class RunSQLFromFile(RunSQL):
    """
    Modification of RunSQL that runs SQL from a file instead of a string

    SQL file is expected to be at {app_dir}/migration/sql/{filename}

    The reason you would do this as an external file & function is so that squashed migrations don't become
    unwieldy (it will inline and strip whitespace the SQL even for large data files)

    """
    def __init__(self, app_name: str, filename: Union[str, Path], *args, **kwargs):
        # RunSQL isn't really made to be modified; we store the app_name & filename
        # in self.sql to avoid having to cut & paste large chunks of RunSQL
        super().__init__(sql=(app_name, filename), *args, **kwargs)

    def _run_sql(self, schema_editor, sqls):
        app_name, filename = sqls
        path = Path(apps.get_app_config(app_name).path) / 'migrations' / filename
        schema_editor.execute(path.read_text())
