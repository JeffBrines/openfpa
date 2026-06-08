from __future__ import annotations

import re

_SEGMENT = re.compile(r"^(\w+)(?:\[(\*|\d+)\])?$")


def _parse_path(path: str) -> list[tuple[str, str | int | None]]:
    parsed: list[tuple[str, str | int | None]] = []
    for segment in path.split("."):
        match = _SEGMENT.match(segment)
        if not match:
            raise ValueError(f"malformed override path segment: {segment!r}")
        key, index = match.group(1), match.group(2)
        if index is None:
            parsed.append((key, None))
        elif index == "*":
            parsed.append((key, "*"))
        else:
            parsed.append((key, int(index)))
    return parsed


def _set_segments(node, segments, value) -> None:
    (key, index), rest = segments[0], segments[1:]
    if not isinstance(node, dict) or key not in node:
        raise ValueError(f"override path key not found: {key!r}")
    if index is None:
        if rest:
            _set_segments(node[key], rest, value)
        else:
            node[key] = value
        return
    target = node[key]
    if not isinstance(target, list):
        raise ValueError(f"override path expects a list at {key!r}, got {type(target).__name__}")
    items = range(len(target)) if index == "*" else [int(index)]
    for i in items:
        if rest:
            _set_segments(target[i], rest, value)
        else:
            target[i] = value


def _set_by_path(data: dict, path: str, value: float) -> None:
    """Set ``value`` at ``path`` in ``data`` (in place).

    Supports:
    - Dotted key navigation:  ``"working_capital.dio_days"``
    - Numeric list index:     ``"channels[0].seasonality[11]"``
    - Wildcard list spread:   ``"channels[*].cogs_pct"``

    Raises ``ValueError`` on any malformed or unresolvable path segment.
    """
    try:
        _set_segments(data, _parse_path(path), value)
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"cannot apply override path {path!r}: {exc}") from exc


def apply_override(data: dict, path: str, value: float) -> None:
    """Set ``value`` at dotted ``path`` (supports ``name``, ``name[n]``, ``name[*]``)
    in ``data``, in place. Public wrapper over the internal path setter."""
    _set_by_path(data, path, value)
