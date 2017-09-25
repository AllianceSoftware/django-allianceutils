#!/usr/bin/env python
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "allianceutils.tests.settings")

#sys.path.append()

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    print(sys.argv)
    execute_from_command_line([sys.argv[0], 'test'] + sys.argv[1:])