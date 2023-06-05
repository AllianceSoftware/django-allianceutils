from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
    ]

    run_before = [
        ("profile_auth", "0001_initial"),
    ]

    try:
        from django.contrib.postgres.operations import CreateCollation
        operations = [
            CreateCollation("case_insensitive", provider="icu", locale="und-u-ks-level2", deterministic=False),
        ]
    except ImportError:
        operations = []


