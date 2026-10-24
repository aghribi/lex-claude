#!/usr/bin/env python3
"""manifest: per-file sha256 manifest of a data tree, and comparison of two manifests.

The manifest is a JSON object {relative posix path: sha256}, keys sorted, one entry
per line. Built the same way on both sides of a copy, two manifests prove the copy.
Finder metadata (.DS_Store, ._*) is skipped: it is not data, and rsync excludes it.
Symlinks are not followed; they are counted and listed on stderr.

Standard library only (Python 3.6+), so it runs on a cluster without installing
anything, also streamed: ssh host python3 - build /path < manifest.py > out.json

Usage:
  manifest.py build ROOT [-o OUT.json]    write the manifest (stdout by default)
  manifest.py compare A.json B.json       exit 0 when identical, 1 otherwise
"""
import argparse
import hashlib
import json
import os
import sys

SKIP = {".DS_Store"}
CHUNK = 8 * 1024 * 1024


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def build(root, out):
    root = os.path.abspath(root)
    digests, links, size = {}, [], 0
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            if name in SKIP or name.startswith("._"):
                continue
            path = os.path.join(d, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.islink(path):
                links.append(rel)
                continue
            digests[rel] = sha256(path)
            size += os.stat(path).st_size
    text = json.dumps(digests, sort_keys=True, indent=1) + "\n"
    if out:
        with open(out, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    print("%s: %d files, %d bytes, %d symlinks skipped" % (root, len(digests), size, len(links)),
          file=sys.stderr)
    for rel in links:
        print("symlink: " + rel, file=sys.stderr)


def compare(a, b):
    with open(a) as f:
        da = json.load(f)
    with open(b) as f:
        db = json.load(f)
    only_a = sorted(set(da) - set(db))
    only_b = sorted(set(db) - set(da))
    differ = sorted(k for k in set(da) & set(db) if da[k] != db[k])
    for k in only_a:
        print("only in %s: %s" % (a, k))
    for k in only_b:
        print("only in %s: %s" % (b, k))
    for k in differ:
        print("differs: " + k)
    print("%d files compared, %d only in A, %d only in B, %d differ"
          % (len(set(da) | set(db)), len(only_a), len(only_b), len(differ)), file=sys.stderr)
    return 1 if (only_a or only_b or differ) else 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd")
    pb = sub.add_parser("build")
    pb.add_argument("root")
    pb.add_argument("-o", "--out")
    pc = sub.add_parser("compare")
    pc.add_argument("a")
    pc.add_argument("b")
    args = p.parse_args()
    if args.cmd == "build":
        build(args.root, args.out)
    elif args.cmd == "compare":
        sys.exit(compare(args.a, args.b))
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
