import os
from pkg_resources import parse_version
import re
import subprocess

# automatically detect the current version from the highest version in the changelog section of the README
with open("CHANGELOG.md", "r") as f:
    section = None
    highest_ver = parse_version("0")
    for line in f.readlines():
        if re.match("^#", line):
            section = line.strip("#").strip().upper()
        if section == "CHANGELOG" and re.match("^[ \t]*\* [0-9.]+(dev)?", line):
            cur_ver = line.replace("*", " ").strip()
            try:
                cur_ver = parse_version(cur_ver)
            except ValueError:
                pass
            else:
                if cur_ver >= highest_ver:
                    highest_ver = cur_ver

# Update version in pyproject.toml
subprocess.run(f"poetry version {highest_ver}".split(), check=True)
# Generate build for distribution
subprocess.run(f"poetry build".split(), check=True)
