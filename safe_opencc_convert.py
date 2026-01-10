#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def iter_json_files(paths, include_hidden):
    for path in paths:
        if os.path.isfile(path):
            if path.lower().endswith(".json"):
                yield path
            continue
        if not os.path.isdir(path):
            continue
        for root, dirs, files in os.walk(path):
            if not include_hidden:
                dirs[:] = [
                    d for d in dirs if not d.startswith(".") and d != "__pycache__"
                ]
            for name in files:
                if not name.lower().endswith(".json"):
                    continue
                if not include_hidden and name.startswith("."):
                    continue
                yield os.path.join(root, name)


def iter_top_dirs(base, include_hidden):
    for name in sorted(os.listdir(base)):
        if not include_hidden and name.startswith("."):
            continue
        path = os.path.join(base, name)
        if os.path.isdir(path):
            yield path


def run_opencc(config, src, dst):
    result = subprocess.run(
        ["opencc", "-c", config, "-i", src, "-o", dst],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(stderr or "opencc failed")


def count_crlf(data):
    return data.count(b"\r\n")


def safe_convert(path, config, dry_run):
    dir_name = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile(delete=False, dir=dir_name) as tmp:
        tmp_path = tmp.name
    try:
        run_opencc(config, path, tmp_path)
        with open(path, "rb") as f:
            original = f.read()
        with open(tmp_path, "rb") as f:
            converted = f.read()

        if count_crlf(original) != count_crlf(converted):
            return "SKIP", "CRLF changed"
        if original == converted:
            return "OK", None
        if dry_run:
            return "WOULD-UPDATE", None

        os.replace(tmp_path, path)
        return "UPDATED", None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def main():
    parser = argparse.ArgumentParser(
        description="Safely convert Traditional Chinese to Simplified with OpenCC."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to process. Defaults to top-level folders.",
    )
    parser.add_argument(
        "--config",
        default="t2s.json",
        help="OpenCC config name (default: t2s.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files, only report changes.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files/directories.",
    )
    args = parser.parse_args()

    if not shutil.which("opencc"):
        print("opencc not found. Please install it first.", file=sys.stderr)
        return 2

    base = os.getcwd()
    targets = args.paths if args.paths else list(
        iter_top_dirs(base, args.include_hidden)
    )
    files = sorted(set(iter_json_files(targets, args.include_hidden)))

    if not files:
        print("No JSON files found.")
        return 0

    for path in files:
        status, reason = safe_convert(path, args.config, args.dry_run)
        rel = os.path.relpath(path, base)
        if reason:
            print(f"{status} {rel} ({reason})")
        else:
            print(f"{status} {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
