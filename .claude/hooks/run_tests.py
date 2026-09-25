#!/usr/bin/env python3
"""PostToolUse hook (SEC-06): run the test suite after every file edit."""
import subprocess
import sys

# Hooks inherit the shell environment claude was started in, so pytest is
# only importable if claude was launched from an activated venv.
NO_TESTS_COLLECTED = 5


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x"],
        capture_output=True,
        text=True,
    )

    if result.returncode in (0, NO_TESTS_COLLECTED):
        return 0

    output = (result.stdout + result.stderr).splitlines()
    print("\n".join(output[-30:]), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
