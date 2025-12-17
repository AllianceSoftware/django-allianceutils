from __future__ import annotations

from pathlib import Path

from django.db import connection
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase

from allianceutils.migrations import RunSQLFromFile


class RunSQLFromFileTests(TransactionTestCase):
    def test_absolute_filename_rejected(self):
        with self.assertRaisesMessage(ValueError, "relative"):
            RunSQLFromFile(app_name="myapp", filename=Path("/abs/path.sql"))

    def test_runs_sql_from_file(self):
        project_state = ProjectState()
        new_state = project_state.clone()
        op = RunSQLFromFile(app_name="test_allianceutils", filename="001-test.sql")
        with connection.schema_editor() as editor:
            op.database_forwards(
                "test_runsql", editor, project_state, new_state
            )
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM test_run_sql_from_file")
            results = list(cursor.fetchall())
            self.assertEqual(len(results), 2)
            self.assertEqual(results, [(1, "entry one"), (2, "entry two")])

