#!/usr/bin/env python3
from pathlib import Path
from pkg_resources import parse_version
import re
import subprocess

# taken from https://semver.org/
RE_VER = r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?'

# automatically detect the current version from the highest version in the changelog section of the README
with (Path(__file__).parent.parent / "CHANGELOG.md").open("r") as f:
    section = None
    highest_ver = parse_version("0")
    ver_string = "0"
    for line in f.readlines():
        if re.match("^#", line):
            section = line.strip("#").strip().upper()
        match = re.match("^[ \t]+[*] (?P<ver>" + RE_VER + ")", line)
        if section == "CHANGELOG" and match:
            cur_ver = line.replace("*", " ").strip()
            try:
                cur_ver = parse_version(cur_ver)
            except ValueError:
                pass
            else:
                if cur_ver >= highest_ver:
                    highest_ver = cur_ver
                    ver_string = match.groups('ver')[0]

# Update version in pyproject.toml
subprocess.run(["poetry", "version", ver_string], check=True)
# Generate build for distribution
subprocess.run(f"poetry build".split(), check=True)
