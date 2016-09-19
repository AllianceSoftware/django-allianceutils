function resolve_path() {
    # OS readlink does not contain the canonicalize functionality that gnu readlink does
    # so we do this in python
    python -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$1"
}