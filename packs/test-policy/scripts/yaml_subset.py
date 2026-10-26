"""Stdlib reader for the YAML subset used by the test-policy pack.

Every data file in this pack (config.yaml, risky-patterns.yaml, fixtures/*.yaml)
stays inside this subset, so each file is valid YAML 1.2 and a full YAML
library reads it too. Supported:

- block mappings and block sequences, indented with spaces only
- flow sequences of scalars on one line, for example ["docs/**", "*.md"]
- plain, single-quoted and double-quoted scalars
- literal block scalars: "key: |" (keeps the final newline) and "key: |-"
- comments: whole-line "#" comments and trailing " #" comments

Plain scalars become null, true/false, int or float when they look like one.
Everything else is a string. Input outside the subset raises ValueError with
a line number.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+(\.\d*)?[eE][+-]?\d+)$")
_DOUBLE_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def load(text: str) -> Any:
    """Parse a document in the subset. Returns None for an empty document."""
    return _Reader(text).parse()


def load_path(path: Path) -> Any:
    """Read a UTF-8 file and parse it in the subset."""
    text = Path(path).read_text(encoding="utf-8")
    return load(text.lstrip("\ufeff"))


class _Reader:
    def __init__(self, text: str) -> None:
        self.lines = text.replace("\r\n", "\n").split("\n")
        self.pos = 0

    def _error(self, message: str, index: int | None = None) -> ValueError:
        number = (self.pos if index is None else index) + 1
        return ValueError(f"line {number}: {message}")

    @staticmethod
    def _indent_of(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def _peek(self) -> tuple[int, int, str] | None:
        """Index, indent and stripped text of the next significant line."""
        index = self.pos
        while index < len(self.lines):
            raw = self.lines[index]
            stripped = raw.strip()
            if stripped and not stripped.startswith("#"):
                indent = self._indent_of(raw)
                if raw[indent : indent + 1] == "\t":
                    raise self._error("tab used for indentation", index)
                return index, indent, stripped
            index += 1
        return None

    def parse(self) -> Any:
        head = self._peek()
        if head is None:
            return None
        value = self._block(head[1])
        leftover = self._peek()
        if leftover is not None:
            raise self._error("unexpected content", leftover[0])
        return value

    def _block(self, indent: int) -> Any:
        head = self._peek()
        assert head is not None
        if _is_seq(head[2]):
            return self._seq(indent)
        return self._map(indent, None)

    def _map(self, indent: int, first: str | None) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while True:
            if first is not None:
                content = first
                first = None
            else:
                head = self._peek()
                if head is None:
                    break
                index, found_indent, content = head
                if found_indent != indent or _is_seq(content):
                    break
                self.pos = index + 1
            split = _split_key(content)
            if split is None:
                raise self._error(f"expected 'key: value', got {content!r}")
            key, rest = split
            if key in result:
                raise self._error(f"duplicate key {key!r}")
            result[key] = self._value(indent, rest)
        return result

    def _value(self, indent: int, rest: str) -> Any:
        if rest == "":
            head = self._peek()
            if head is None:
                return None
            _, found_indent, content = head
            if found_indent > indent or (found_indent == indent and _is_seq(content)):
                return self._block(found_indent)
            return None
        if rest.startswith("["):
            return _flow(rest)
        token = _strip_trailing_comment(rest) if rest[:1] not in ('"', "'") else rest
        if token in ("|", "|-"):
            return self._literal(indent, keep_final=token == "|")
        return _scalar(rest)

    def _seq(self, indent: int) -> list[Any]:
        items: list[Any] = []
        while True:
            head = self._peek()
            if head is None:
                break
            index, found_indent, content = head
            if found_indent != indent or not _is_seq(content):
                break
            self.pos = index + 1
            tail = content[1:]
            item = tail.lstrip(" ")
            if item == "":
                nxt = self._peek()
                if nxt is not None and nxt[1] > indent:
                    items.append(self._block(nxt[1]))
                else:
                    items.append(None)
            elif _split_key(item) is not None:
                item_indent = indent + len(content) - len(item)
                items.append(self._map(item_indent, first=item))
            else:
                items.append(self._value(indent, item))
        return items

    def _literal(self, parent_indent: int, keep_final: bool) -> str:
        index = self.pos
        block_indent: int | None = None
        raw_lines: list[str] = []
        while index < len(self.lines):
            raw = self.lines[index]
            if raw.strip() == "":
                raw_lines.append(raw)
                index += 1
                continue
            indent = self._indent_of(raw)
            if indent <= parent_indent:
                break
            if block_indent is None:
                block_indent = indent
            if indent < block_indent:
                raise self._error("bad indentation in block scalar", index)
            raw_lines.append(raw)
            index += 1
        while raw_lines and raw_lines[-1].strip() == "":
            raw_lines.pop()
            index -= 1
        self.pos = index
        if block_indent is None:
            return ""
        body = "\n".join(raw[block_indent:] for raw in raw_lines)
        return body + "\n" if keep_final else body


def _is_seq(content: str) -> bool:
    return content == "-" or content.startswith("- ")


def _split_key(content: str) -> tuple[str, str] | None:
    if content[:1] in ('"', "'", "[", "{"):
        return None
    index = content.find(":")
    while index != -1:
        if index + 1 == len(content) or content[index + 1] == " ":
            key = content[:index].strip()
            if not key:
                return None
            return key, content[index + 1 :].strip()
        index = content.find(":", index + 1)
    return None


def _strip_trailing_comment(text: str) -> str:
    text = text.strip()
    if text.startswith("#"):
        return ""
    match = re.search(r"\s#", text)
    if match:
        text = text[: match.start()]
    return text.strip()


def _scalar(text: str) -> Any:
    text = text.strip()
    if text[:1] in ('"', "'"):
        value, rest = _quoted(text)
        rest = rest.strip()
        if rest and not rest.startswith("#"):
            raise ValueError(f"unexpected text after quoted scalar: {rest!r}")
        return value
    return _plain(_strip_trailing_comment(text))


def _plain(token: str) -> Any:
    if token in ("", "~", "null", "Null", "NULL"):
        return None
    if token in ("true", "True", "TRUE"):
        return True
    if token in ("false", "False", "FALSE"):
        return False
    if _INT_RE.match(token):
        return int(token)
    if _FLOAT_RE.match(token):
        return float(token)
    return token


def _quoted(text: str) -> tuple[str, str]:
    """Parse a quoted scalar at the start of text. Returns (value, rest)."""
    quote = text[0]
    out: list[str] = []
    index = 1
    while index < len(text):
        char = text[index]
        if quote == "'":
            if char == "'":
                if text[index + 1 : index + 2] == "'":
                    out.append("'")
                    index += 2
                    continue
                return "".join(out), text[index + 1 :]
            out.append(char)
        else:
            if char == "\\":
                escape = text[index + 1 : index + 2]
                if escape not in _DOUBLE_ESCAPES:
                    raise ValueError(f"unsupported escape \\{escape}")
                out.append(_DOUBLE_ESCAPES[escape])
                index += 2
                continue
            if char == '"':
                return "".join(out), text[index + 1 :]
            out.append(char)
        index += 1
    raise ValueError("unterminated quoted scalar")


def _flow(text: str) -> list[Any]:
    """Parse a one-line flow sequence of scalars, for example ["a", b]."""
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    index = 1
    end: int | None = None
    while index < len(text):
        char = text[index]
        if quote is not None:
            buf.append(char)
            if quote == '"' and char == "\\":
                buf.append(text[index + 1 : index + 2])
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in ('"', "'") and "".join(buf).strip() == "":
            quote = char
            buf.append(char)
        elif char == ",":
            parts.append("".join(buf))
            buf = []
        elif char == "]":
            end = index
            break
        elif char == "[":
            raise ValueError("nested flow sequences are not supported")
        else:
            buf.append(char)
        index += 1
    if end is None:
        raise ValueError("unterminated flow sequence")
    tail = text[end + 1 :].strip()
    if tail and not tail.startswith("#"):
        raise ValueError(f"unexpected text after flow sequence: {tail!r}")
    last = "".join(buf)
    if last.strip():
        parts.append(last)
    return [_scalar(part) for part in parts]
