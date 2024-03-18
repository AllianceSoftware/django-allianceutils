from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Dict
from typing import Sequence
from typing import Tuple
from typing import Union

from django.apps import apps
from django.db.migrations import RunSQL


class RunSQLFromFile(RunSQL):
    """
    Modification of RunSQL that runs SQL from a file instead of a string

    SQL file is expected to be at {app_dir}/migration/sql/{filename}

    The reason you would do this as an external file & function is so that squashed migrations don't become
    unreadable (the squash process will inline and strip whitespace in the SQL even for large data files)
    """

    app_name: str
    filename: Path

    def __init__(self, *, app_name: str, filename: Union[str, Path], **kwargs):
        self.app_name = app_name
        self.filename = Path(filename)
        if self.filename.is_absolute():
            raise ValueError("filename should be relative to app's migrations directory")

        super().__init__(
            sql="",
            reverse_sql=None,
            **kwargs)

    def deconstruct(self) -> Tuple[str, Sequence[Any], Dict[str, Any]]:
        path, args, kwargs = super().deconstruct()
        del kwargs["sql"]
        del kwargs["reverse_sql"]
        kwargs["app_name"] = self.app_name
        kwargs["filename"] = str(self.filename)
        return path, args, kwargs

    def describe(self):
        return "Raw SQL operation from file"

    def _run_sql(self, schema_editor, sqls):
        path = Path(apps.get_app_config(self.app_name).path, 'migrations', self.filename)
        sql = path.read_text()
        super()._run_sql(schema_editor, sqls)  # type:ignore[misc] # underscore methods are hidden


# TODO: add test cases for this
