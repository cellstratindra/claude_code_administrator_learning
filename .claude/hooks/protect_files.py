#!/usr/bin/env python3
"""PreToolUse hook (SEC-06): block edits to .env, *.db, and .git/."""
import json
import os
import sys


def is_protected(path: str) -> str | None:
    """Return a block reason if path is protected, else None."""
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    if os.path.basename(normalized) == ".env":
        return "Editing .env is blocked (SEC-06): secrets must never be written by Claude Code."
    if ".git" in parts:
        return "Editing files inside .git/ is blocked (SEC-06)."
    if normalized.endswith(".db"):
        return "Editing database files (*.db) is blocked (SEC-06): use the app, not direct edits."
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        file_path = payload.get("tool_input", {}).get("file_path", "")
    except (json.JSONDecodeError, AttributeError):
        return 0

    if not file_path:
        return 0

    reason = is_protected(file_path)
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
