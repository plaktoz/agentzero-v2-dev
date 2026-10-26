"""Check that the evidence in a minimalism-ladder record exists in a repository.

Usage:
    python check_evidence.py RECORD.json REPO_ROOT

Each evidence entry is a repository-relative path, or path:symbol.
Evidence is checked for rungs 1 to 4, which require it. Rungs 5 and 6 are not checked.

A symbol is checked as text: each dotted part (Class.method -> Class, method)
must appear as a whole word in the file. This is not a parser.

Exit codes:
    0  every evidence entry for rungs 1 to 4 exists
    1  an evidence entry is missing or invalid, or rungs 1 to 4 have no evidence
    2  usage or input error (bad arguments, unreadable or invalid record)

Stdlib only. Runs on Windows, Linux and macOS.
"""

import json
import re
import sys
from pathlib import Path

EVIDENCE_RUNGS = (1, 2, 3, 4)
ALL_RUNGS = (1, 2, 3, 4, 5, 6)

EXIT_OK = 0
EXIT_MISSING = 1
EXIT_INPUT = 2

# A trailing ":identifier" (or dotted identifiers) is a symbol. "C:\\x.py" is not.
PATH_SYMBOL = re.compile(r"^(?P<path>.+):(?P<symbol>[A-Za-z_][A-Za-z0-9_.]*)$")


def split_entry(entry):
    """Return (path_text, symbol or None) for one evidence entry."""
    match = PATH_SYMBOL.match(entry)
    if match:
        return match.group("path"), match.group("symbol")
    return entry, None


def resolve_inside(root, path_text):
    """Return the resolved path under root, or None if it is absolute or leaves root.

    Backslashes are read as separators, so a record written on Windows checks on Linux and macOS.
    """
    candidate = Path(path_text.replace("\\", "/"))
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def symbol_problem(file_path, symbol):
    """Return None if every dotted part of symbol is a word in the file, else a reason."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "file is not readable as UTF-8 text"
    for part in symbol.split("."):
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(part) + r"(?![A-Za-z0-9_])"
        if not re.search(pattern, text):
            return f"symbol '{part}' not found in file"
    return None


def check_entry(root, entry):
    """Return None if the evidence entry is valid, else a short reason."""
    entry = entry.strip()
    path_text, symbol = split_entry(entry)
    if not path_text.strip():
        return "empty evidence entry"
    try:
        target = resolve_inside(root, path_text)
        if target is None:
            return "path is absolute or leaves the repository root"
        if not target.exists():
            return "path not found"
        if symbol is None:
            return None
        if not target.is_file():
            return "symbol given but path is not a file"
        reason = symbol_problem(target, symbol)
    except (OSError, ValueError) as exc:
        return f"cannot check ({exc})"
    return reason


def load_record(record_path):
    """Load the JSON record. A UTF-8 byte order mark is tolerated."""
    with record_path.open(encoding="utf-8") as handle:
        text = handle.read().lstrip("\ufeff")
    return json.loads(text)


def run(record_path, repo_root):
    """Return the exit code for one record and one repository."""
    if not repo_root.is_dir():
        print(f"error: repository root is not a directory: {repo_root}", file=sys.stderr)
        return EXIT_INPUT
    root = repo_root.resolve()

    try:
        record = load_record(record_path)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"error: cannot read record {record_path}: {exc}", file=sys.stderr)
        return EXIT_INPUT

    if not isinstance(record, dict):
        print("error: record must be a JSON object", file=sys.stderr)
        return EXIT_INPUT
    rung = record.get("rung")
    if isinstance(rung, bool) or rung not in ALL_RUNGS:
        print(f"error: record 'rung' must be an integer from 1 to 6, got {rung!r}", file=sys.stderr)
        return EXIT_INPUT
    evidence = record.get("evidence", [])
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        print("error: record 'evidence' must be an array of strings", file=sys.stderr)
        return EXIT_INPUT

    if rung not in EVIDENCE_RUNGS:
        print(f"ok: rung {rung} does not require evidence")
        return EXIT_OK

    if not evidence:
        print(f"MISSING: rung {rung} requires at least one evidence entry", file=sys.stderr)
        return EXIT_MISSING

    problems = []
    for entry in evidence:
        reason = check_entry(root, entry)
        if reason is not None:
            problems.append(f"MISSING: '{entry}': {reason}")
    for line in problems:
        print(line, file=sys.stderr)
    if problems:
        return EXIT_MISSING

    print(f"ok: {len(evidence)} evidence entr{'y' if len(evidence) == 1 else 'ies'} found for rung {rung}")
    return EXIT_OK


def main(argv):
    # Evidence text can contain non-ASCII. A console that cannot print it (for example
    # a Windows code page) gets escape sequences instead of a traceback.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="backslashreplace")
    if len(argv) != 3:
        print("usage: python check_evidence.py RECORD.json REPO_ROOT", file=sys.stderr)
        return EXIT_INPUT
    return run(Path(argv[1]), Path(argv[2]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
