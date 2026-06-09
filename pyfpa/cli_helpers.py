from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _write_json(
            {
                "schema_version": SCHEMA_VERSION,
                "command": "usage",
                "ok": False,
                "error": {"type": "usage_error", "message": message},
            },
            stream=sys.stderr,
        )
        raise SystemExit(EXIT_USAGE)


def _write_json(payload: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _success(command: str, root: Path, data: dict[str, Any]) -> int:
    _write_json(
        {
            "schema_version": SCHEMA_VERSION,
            "command": command,
            "ok": True,
            "root": str(root),
            "data": data,
        }
    )
    return EXIT_OK


def _failure(
    command: str,
    root: Path,
    error_type: str,
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> int:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "ok": False,
        "root": str(root),
        "error": {"type": error_type, "message": message},
    }
    if data is not None:
        payload["data"] = data
    _write_json(payload)
    return EXIT_FAILED


def _root(path: str) -> Path:
    return Path(path).expanduser().resolve()
