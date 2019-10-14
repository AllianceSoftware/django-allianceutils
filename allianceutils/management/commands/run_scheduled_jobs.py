import ast
import datetime
import importlib
import os
import pathlib
import time

import django.core.management.base
from django.conf import settings


class Command(django.core.management.base.BaseCommand):
    help = 'Find ASYNC pseudo crons via checking for decorator and import & execute task. To be used by CRON-worker.'

    def handle(self, **options):
        base_dir = settings.BASE_DIR

        files = []
        for walk in os.walk(base_dir):
            for f in walk[2]:
                if f.endswith('.py'):
                    files.append((walk[0], f))

        all_tasks = []

        for path, fn in files:
            try:
                with open(pathlib.Path(path) / fn,'r') as f:
                    p = ast.parse(f.read())
            except Exception:
                continue

            class_defs = [
                node
                for node in p.body
                if type(node).__name__ == "ClassDef" and len(node.decorator_list)
            ]

            for cls in class_defs:
                decorated_with_ros = False
                for dec in cls.decorator_list:
                    try:
                        if dec.func.id == "run_on_schedule":
                            decorated_with_ros = dec
                            break
                    except Exception:
                        pass

                if not decorated_with_ros:
                    continue

                kwargs = {}

                for kw in decorated_with_ros.keywords:
                    k = kw.arg
                    v = kw.value
                    if hasattr(v, "value"):
                        v = v.value
                    elif hasattr(v, "n"):
                        v = v.n
                    else:
                        print(v, dir(v))
                        raise NotImplementedError(
                            "FIXME: Unknown type of args passed to run_on_schedule."
                        )
                    kwargs[k] = v

                # kwargs is now kwargs we passed onto run_on_schedule, with cls being the Task we're intended to run.
                # check if criteria had been met; if yes, run it.
                # note: all schedule tasks are presumed to be self-containing and takes no external params.
                rel_path = os.path.relpath(pathlib.Path(path) / fn, base_dir)[:-3]
                all_tasks.append((rel_path, cls, kwargs))

        def match(time_dict, now):
            if not time_dict:
                return False

            flag = True
            for k, v in time_dict.items():
                if getattr(now, k, None) != v:
                    flag = False

            return flag

        while True:
            time.sleep(1)
            now = datetime.now()
            for rel_path, cls, scheduled_time in all_tasks:
                if match(scheduled_time, now):
                    import_path = rel_path.replace('/', '.')
                    actual_cls = importlib.import_module(import_path, cls.name)
                    actual_cls().enqueue()

