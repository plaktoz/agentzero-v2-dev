#!/usr/bin/env python3
"""Deterministic pre-filter for the test-policy pack.

Reads a unified diff (a file path, or standard input when the path is "-" or
omitted) and prints exactly one word on standard output:

    trivial       no model call is needed; the change needs no tests
    needs_model   a model must classify the change

It never decides risk. "trivial" is printed only when one of these holds:

1. Every changed file matches an exempt glob or a trivial extension (docs,
   lockfiles, configuration), or is a pure rename or mode change.
2. Every changed hunk in the remaining files changes only whitespace or
   whole-line comments.
3. Every other changed hunk belongs to one consistent identifier rename
   (switched by "rename_detection" in config.yaml): each old name maps to one
   new name, the old name no longer appears in unchanged lines, the new name
   did not exist before, neither is a language keyword, and each old name is
   replaced at least "rename_min_occurrences" times.

Anything else, and any input it cannot parse, prints "needs_model".

With --candidates the script also writes lines such as "pricing.py:12:money"
to standard error. They are the added lines that match a pattern from
risky-patterns.yaml. Candidates are hints for the model to confirm, never a
verdict. They are written only when the answer is "needs_model".

Exit status: 0 after printing an answer, 2 for a usage or configuration error
(nothing is printed on standard output).

Standard library only. Input is decoded as UTF-8; CRLF and LF are both read.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml_subset  # noqa: E402  (sibling module, stdlib only)

TRIVIAL = "trivial"
NEEDS_MODEL = "needs_model"

PACK_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACK_DIR / "config.yaml"

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_TOKEN_RE = re.compile(
    r"""\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`[^`]*`"""  # string literal
    r"|\d[\w.]*"  # number
    r"|[A-Za-z_]\w*"  # identifier
    r"|\s+"  # whitespace
    r"|."  # any other character
)
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")


@dataclass
class Line:
    kind: str  # " " context, "-" removed, "+" added
    text: str
    new_lineno: int | None = None


@dataclass
class Hunk:
    lines: list[Line] = field(default_factory=list)


@dataclass
class FileDiff:
    old_path: str | None = None
    new_path: str | None = None
    binary: bool = False
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def path(self) -> str:
        return self.new_path or self.old_path or ""


@dataclass
class Result:
    verdict: str
    candidates: list[tuple[str, int, str]] = field(default_factory=list)


# --------------------------------------------------------------------------
# Diff parsing
# --------------------------------------------------------------------------


def _clean_path(raw: str) -> str | None:
    raw = raw.split("\t", 1)[0].strip()
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        raw = raw[1:-1]
    if raw == "/dev/null":
        return None
    raw = raw.replace("\\", "/")
    if raw.startswith(("a/", "b/")):
        raw = raw[2:]
    while raw.startswith("./"):
        raw = raw[2:]
    return raw


def _paths_from_git_header(rest: str) -> tuple[str | None, str | None]:
    """Split the tail of a "diff --git" line into old and new path."""
    if rest.startswith('"') or " b/" not in rest:
        parts = rest.split(" ")
        if len(parts) == 2:
            return _clean_path(parts[0]), _clean_path(parts[1])
        return _clean_path(rest), _clean_path(rest)
    # Prefer a split where both halves name the same path.
    index = rest.find(" b/")
    while index != -1:
        left, right = rest[:index], rest[index + 1 :]
        if left[2:] == right[2:]:
            return _clean_path(left), _clean_path(right)
        index = rest.find(" b/", index + 1)
    left, right = rest.rsplit(" b/", 1)
    return _clean_path(left), _clean_path("b/" + right)


def parse_diff(text: str) -> list[FileDiff] | None:
    """Parse a unified diff. Returns None when the text is not a usable diff."""
    lines = [line.rstrip("\r") for line in text.split("\n")]
    files: list[FileDiff] = []
    current: FileDiff | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git "):
            old_path, new_path = _paths_from_git_header(line[len("diff --git ") :])
            current = FileDiff(old_path=old_path, new_path=new_path)
            files.append(current)
            index += 1
        elif line.startswith("--- ") and index + 1 < len(lines) and lines[index + 1].startswith("+++ "):
            old_path = _clean_path(line[4:])
            new_path = _clean_path(lines[index + 1][4:])
            if current is None or current.hunks:
                current = FileDiff()
                files.append(current)
            current.old_path, current.new_path = old_path, new_path
            index += 2
        elif line.startswith("rename from ") and current is not None:
            current.old_path = _clean_path(line[len("rename from ") :])
            index += 1
        elif line.startswith("rename to ") and current is not None:
            current.new_path = _clean_path(line[len("rename to ") :])
            index += 1
        elif (line.startswith("Binary files ") or line.startswith("GIT binary patch")) and current is not None:
            current.binary = True
            index += 1
        elif line.startswith("@@") and current is not None:
            match = _HUNK_RE.match(line)
            if match is None:
                return None
            old_left = int(match.group(2)) if match.group(2) is not None else 1
            new_left = int(match.group(4)) if match.group(4) is not None else 1
            new_no = int(match.group(3))
            hunk = Hunk()
            index += 1
            while (old_left > 0 or new_left > 0) and index < len(lines):
                body = lines[index]
                if body.startswith("\\"):  # "\ No newline at end of file"
                    index += 1
                    continue
                marker = body[:1] if body else " "
                content = body[1:]
                if marker == " ":
                    hunk.lines.append(Line(" ", content, new_no))
                    old_left -= 1
                    new_left -= 1
                    new_no += 1
                elif marker == "-":
                    hunk.lines.append(Line("-", content))
                    old_left -= 1
                elif marker == "+":
                    hunk.lines.append(Line("+", content, new_no))
                    new_left -= 1
                    new_no += 1
                else:
                    return None
                index += 1
            if old_left > 0 or new_left > 0:
                return None
            current.hunks.append(hunk)
        else:
            index += 1  # index lines, mode lines, similarity, commit text
    return files


# --------------------------------------------------------------------------
# Globs and configuration
# --------------------------------------------------------------------------


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a path glob. "**" crosses directories; "*" and "?" do not.

    A pattern without "/" matches the file name at any depth. A pattern with
    "/" is anchored at the root of the repository.
    """
    pattern = pattern.replace("\\", "/")
    while pattern.startswith("./"):
        pattern = pattern[2:]
    anchored = "/" in pattern
    out: list[str] = [] if anchored else [r"(?:.*/)?"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if pattern[index : index + 3] == "**/":
                out.append(r"(?:.*/)?")
                index += 3
                continue
            if pattern[index : index + 2] == "**":
                out.append(r".*")
                index += 2
                continue
            out.append(r"[^/]*")
        elif char == "?":
            out.append(r"[^/]")
        elif char == "[":
            end = pattern.find("]", index + 2)
            if end == -1:
                out.append(re.escape(char))
            else:
                body = pattern[index + 1 : end]
                if body.startswith("!"):
                    body = "^" + body[1:]
                out.append("[" + body.replace("\\", "\\\\") + "]")
                index = end
        else:
            out.append(re.escape(char))
        index += 1
    return re.compile("".join(out))


@dataclass
class Settings:
    exempt: list[re.Pattern[str]]
    trivial_extensions: set[str]
    rename_detection: bool
    reserved: set[str]
    languages: dict
    rename_min_occurrences: int = 2


def load_settings(config_path: Path, patterns_path: Path | None = None) -> Settings:
    config = yaml_subset.load_path(config_path) or {}
    if not isinstance(config, dict):
        raise ValueError(f"{config_path}: top level must be a mapping")
    patterns_name = config.get("risky_patterns_file", "risky-patterns.yaml")
    if patterns_path is None:
        patterns_path = Path(config_path).resolve().parent / str(patterns_name)
    patterns = yaml_subset.load_path(patterns_path) or {}
    languages = patterns.get("languages")
    if not isinstance(languages, dict) or "default" not in languages:
        raise ValueError(f"{patterns_path}: 'languages' with a 'default' entry is required")
    compiled: dict = {}
    for name, entry in languages.items():
        rules = []
        for rule in entry.get("patterns") or []:
            try:
                rules.append((str(rule["kind"]), re.compile(str(rule["regex"]), re.IGNORECASE)))
            except (KeyError, re.error) as error:
                raise ValueError(f"{patterns_path}: bad pattern in {name!r}: {error}") from error
        compiled[name] = {
            "extensions": {str(ext).lower() for ext in entry.get("extensions") or []},
            "line_comments": [str(token) for token in entry.get("line_comments") or []],
            "block_comments": bool(entry.get("block_comments")),
            "indent_significant": bool(entry.get("indent_significant")),
            "rules": rules,
        }
    return Settings(
        exempt=[glob_to_regex(str(glob)) for glob in config.get("exempt_globs") or []],
        trivial_extensions={str(ext).lower() for ext in config.get("trivial_extensions") or []},
        rename_detection=bool(config.get("rename_detection", True)),
        rename_min_occurrences=int(config.get("rename_min_occurrences", 2)),
        reserved={str(word) for word in patterns.get("reserved_words") or []},
        languages=compiled,
    )


def _language_for(settings: Settings, path: str) -> dict:
    suffix = PurePosixPath(path).suffix.lower()
    for name, entry in settings.languages.items():
        if suffix and suffix in entry["extensions"]:
            return entry
    return settings.languages["default"]


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------


def _path_is_trivial(settings: Settings, path: str | None) -> bool:
    if path is None:
        return True  # /dev/null side of an add or delete
    if any(regex.fullmatch(path) for regex in settings.exempt):
        return True
    return PurePosixPath(path).suffix.lower() in settings.trivial_extensions


def _is_comment_line(language: dict, text: str, state: dict) -> bool:
    """Whole-line comment test. state["block"] tracks an open /* ... */."""
    stripped = text.strip()
    if language["block_comments"]:
        if state["block"]:
            if "*/" in stripped:
                state["block"] = False
                return stripped.endswith("*/")
            return True
        if stripped.startswith("/*"):
            state["block"] = "*/" not in stripped
            return stripped.endswith("*/") or state["block"]
    return any(stripped.startswith(token) for token in language["line_comments"])


def _tokens(text: str) -> list[str]:
    return [" " if token.isspace() else token for token in _TOKEN_RE.findall(text.strip())]


_SPACE_FREE_NEXT = set("()[]{},;")


def _norm(text: str, indent_significant: bool) -> str:
    """Canonical form for whitespace comparison.

    A space is dropped only where it cannot change the tokens: next to a
    bracket, a comma or a semicolon. Every other run of spacing is kept as one
    space, so "a - -b" and "a--b" stay different. Leading indentation is kept
    where the language makes it significant.
    """
    prefix = text[: len(text) - len(text.lstrip())] if indent_significant else ""
    out: list[str] = []
    pending_space = False
    for token in _TOKEN_RE.findall(text.strip()):
        if token.isspace():
            pending_space = True
            continue
        if out and pending_space:
            previous = out[-1]
            free = previous in _SPACE_FREE_NEXT or token in _SPACE_FREE_NEXT
            if not free:
                out.append(" ")
        out.append(token)
        pending_space = False
    return prefix + "".join(out)


def _code_lines(language: dict, hunk: Hunk) -> tuple[list[Line], list[Line], list[Line]]:
    """Return removed, added and context lines that are neither blank nor comments."""
    state = {"block": False}
    removed: list[Line] = []
    added: list[Line] = []
    context: list[Line] = []
    for line in hunk.lines:
        if _is_comment_line(language, line.text, state) or not line.text.strip():
            continue
        {"-": removed, "+": added, " ": context}[line.kind].append(line)
    return removed, added, context


def _hunk_is_whitespace_or_comment_only(language: dict, hunk: Hunk) -> bool:
    removed, added, _ = _code_lines(language, hunk)
    indent = language["indent_significant"]
    return [_norm(line.text, indent) for line in removed] == [_norm(line.text, indent) for line in added]


def _rename_pairs(language: dict, hunk: Hunk, mapping: dict, kept: set, counts: dict) -> bool:
    """Check one hunk as an identifier rename. Updates mapping, kept and counts."""
    removed, added, context = _code_lines(language, hunk)
    if len(removed) != len(added) or not removed:
        return False
    indent = language["indent_significant"]
    for old_line, new_line in zip(removed, added):
        if indent and old_line.text[: len(old_line.text) - len(old_line.text.lstrip())] != new_line.text[
            : len(new_line.text) - len(new_line.text.lstrip())
        ]:
            return False
        old_tokens, new_tokens = _tokens(old_line.text), _tokens(new_line.text)
        if len(old_tokens) != len(new_tokens):
            return False
        for old, new in zip(old_tokens, new_tokens):
            if old == new:
                if _IDENT_RE.fullmatch(old):
                    kept.add(old)
                continue
            if not (_IDENT_RE.fullmatch(old) and _IDENT_RE.fullmatch(new)):
                return False
            if mapping.setdefault(old, new) != new:
                return False
            counts[old] = counts.get(old, 0) + 1
    return True


def _collect_names(language: dict, hunk: Hunk, kept: set, seen: set) -> None:
    """Record identifiers that remain in unchanged code and identifiers in old code.

    A name that still appears in context lines was not renamed everywhere in
    the hunk, so it cannot be the old side of a complete rename.
    """
    removed, _, context = _code_lines(language, hunk)
    for line in context:
        names = {token for token in _tokens(line.text) if _IDENT_RE.fullmatch(token)}
        kept.update(names)
        seen.update(names)
    for line in removed:
        seen.update(token for token in _tokens(line.text) if _IDENT_RE.fullmatch(token))


def _rename_is_safe(settings: Settings, mapping: dict, counts: dict, kept: set, seen: set) -> bool:
    if not mapping:
        return False
    olds, news = set(mapping), set(mapping.values())
    if len(news) != len(mapping):
        return False  # two names merged into one
    if (olds | news) & settings.reserved:
        return False
    if any(counts.get(old, 0) < settings.rename_min_occurrences for old in olds):
        return False  # one swapped name may point at a different variable
    if olds & kept:
        return False  # the old name still appears, so this is not a full rename
    if news & seen:
        return False  # the new name already exists in the old code: possible collision
    return True


def _candidates(settings: Settings, files: list[FileDiff]) -> list[tuple[str, int, str]]:
    found: list[tuple[str, int, str]] = []
    for file in files:
        if _path_is_trivial(settings, file.new_path) and _path_is_trivial(settings, file.old_path):
            continue
        language = _language_for(settings, file.path)
        for hunk in file.hunks:
            state = {"block": False}
            for line in hunk.lines:
                if _is_comment_line(language, line.text, state) or line.kind != "+" or not line.text.strip():
                    continue
                for kind, regex in language["rules"]:
                    if regex.search(line.text):
                        found.append((file.path, line.new_lineno or 0, kind))
    return found


def classify(text: str, settings: Settings) -> Result:
    """Return the pre-filter verdict for a unified diff."""
    text = text.lstrip("\ufeff")
    if not text.strip():
        return Result(TRIVIAL)  # nothing changed
    files = parse_diff(text)
    if not files:
        return Result(NEEDS_MODEL)

    remaining: list[FileDiff] = []
    for file in files:
        if file.binary and not (
            _path_is_trivial(settings, file.new_path) and _path_is_trivial(settings, file.old_path)
        ):
            return Result(NEEDS_MODEL, _candidates(settings, files))
        if _path_is_trivial(settings, file.new_path) and _path_is_trivial(settings, file.old_path):
            continue
        if not file.hunks and not file.binary:
            continue  # pure rename or mode change, content unchanged
        remaining.append(file)

    mapping: dict = {}
    counts: dict = {}
    kept: set = set()
    seen: set = set()
    for file in remaining:
        language = _language_for(settings, file.path)
        for hunk in file.hunks:
            _collect_names(language, hunk, kept, seen)
            if _hunk_is_whitespace_or_comment_only(language, hunk):
                continue
            if settings.rename_detection and _rename_pairs(language, hunk, mapping, kept, counts):
                continue
            return Result(NEEDS_MODEL, _candidates(settings, files))
    if mapping and not _rename_is_safe(settings, mapping, counts, kept, seen):
        return Result(NEEDS_MODEL, _candidates(settings, files))
    return Result(TRIVIAL)


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------


def _read_input(source: str | None) -> str:
    if source in (None, "-"):
        data = sys.stdin.buffer.read()
        return data.decode("utf-8", errors="replace")
    with Path(source).open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return handle.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print 'trivial' or 'needs_model' for a unified diff.")
    parser.add_argument("diff", nargs="?", help="diff file; '-' or omitted reads standard input")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="config.yaml path")
    parser.add_argument("--patterns", type=Path, default=None, help="risky-patterns.yaml path (default: from config)")
    parser.add_argument("--candidates", action="store_true", help="write candidate flags to standard error")
    args = parser.parse_args(argv)
    try:
        settings = load_settings(args.config, args.patterns)
        text = _read_input(args.diff)
    except (OSError, ValueError) as error:
        sys.stderr.buffer.write(f"prefilter: {error}\n".encode("utf-8"))
        sys.stderr.buffer.flush()
        return 2
    result = classify(text, settings)
    if args.candidates and result.verdict == NEEDS_MODEL:
        for path, line, kind in result.candidates:
            sys.stderr.buffer.write(f"{path}:{line}:{kind}\n".encode("utf-8"))
        sys.stderr.buffer.flush()
    sys.stdout.buffer.write((result.verdict + "\n").encode("ascii"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
