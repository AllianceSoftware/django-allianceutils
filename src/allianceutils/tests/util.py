from collections.abc import Iterable
import logging
import warnings

from django.conf import settings
from django.db import connection
from django.db import connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test.utils import TestContextDecorator


# ---------------------------------------------------------------------------
class suppress_silk(TestContextDecorator):
    """
    Disable silk SQL query logging

    This is needed for anything that uses assertNumQueries() otherwise your
    query counts may also include silk's EXPLAINs

    Note that silk's impact can sometimes pop up unexpectedly:
    - silk only hooks the DB connection after Middleware is invoked for the first time
    - silk only EXPLAINs queries involving models (manual SQL will be logged but not EXPLAINed)
    """

    conn_name: str | None
    previous_flag_stack: list[bool]  # is a stack to handle nesting

    def __init__(self, connection_name: str | None = None):
        """
        Suppresses silk's EXPLAIN queries for the specified database connection
        Will use the default connection if none given
        """
        self.conn_name = connection_name
        self.previous_flag_stack = []
        super().__init__()

    def _get_conn(self) -> BaseDatabaseWrapper:
        return connection if self.conn_name is None else connections[self.conn_name]

    def enable(self):
        conn = self._get_conn()
        self.previous_flag_stack.append(conn.features.supports_explaining_query_execution)
        conn.features.supports_explaining_query_execution = False

    def disable(self):
        conn = self._get_conn()
        conn.features.supports_explaining_query_execution = self.previous_flag_stack.pop()


# ---------------------------------------------------------------------------
class logging_filter(TestContextDecorator):
    """
    Disable logging for specified log names

    override_settings(LOGGING=...) seems to change the django setting but
    seem to trigger an update to the the python logging settings
    """

    loggers: Iterable[str]

    def __init__(self, loggers=None):
        self.loggers = loggers
        super().__init__()

    modified_loggers: dict[str, bool]

    def enable(self):
        logger_names = self.loggers or settings.LOGGING["loggers"].keys()
        self.modified_loggers = dict.fromkeys(logger_names, None)
        for logger_name in self.modified_loggers.keys():
            logger = logging.getLogger(logger_name)
            self.modified_loggers[logger_name] = logger.disabled
            logger.disabled = True

    def disable(self):
        for logger_name in self.modified_loggers.keys():
            logger = logging.getLogger(logger_name)
            logger.disabled = self.modified_loggers[logger_name]


class warning_filter(TestContextDecorator):
    """
    Apply a warning.simplefilter()

    see https://docs.python.org/3/library/warnings.html#describing-warning-filters
    """

    action: str
    filters: dict

    def __init__(self, action, **filters):
        self.action = action
        self.filters = filters
        super().__init__()

    def enable(self):
        self.context_manager = warnings.catch_warnings()
        self.context_manager.__enter__()
        warnings.filterwarnings(self.action, **self.filters)

    def disable(self):
        self.context_manager.__exit__(None, None, None)
