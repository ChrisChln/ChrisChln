"""Monitor numeric changes within a range and emit a beep on change.

This module exposes a command line interface that periodically samples a
numeric value obtained either from a shell command or from the contents of a
file. When the value changes while remaining within a user-defined range, a
notification sound is emitted.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for the monitor."""

    parser = argparse.ArgumentParser(
        description=(
            "Periodically check a numeric value within a given range and emit "
            "an audible alert when the value changes."
        )
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--command",
        help=(
            "Shell command to execute. The first floating-point number found "
            "in its stdout will be used as the sampled value."
        ),
    )
    source_group.add_argument(
        "--file",
        type=Path,
        help=(
            "Path to a file containing the numeric value to monitor. The file "
            "is read on each sampling iteration."
        ),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Sampling interval in seconds (default: 1.0).",
    )
    parser.add_argument(
        "--min",
        dest="min_value",
        type=float,
        default=None,
        help="Lower bound of the range to monitor (inclusive).",
    )
    parser.add_argument(
        "--max",
        dest="max_value",
        type=float,
        default=None,
        help="Upper bound of the range to monitor (inclusive).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help=(
            "Minimum absolute difference required to treat two samples as "
            "different (default: 0.0)."
        ),
    )

    return parser.parse_args()


def fetch_value_from_command(command: str) -> Optional[float]:
    """Execute *command* and extract the first float found in its stdout."""

    process = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )

    if process.returncode != 0:
        sys.stderr.write(
            f"Command '{command}' exited with code {process.returncode}: {process.stderr}\n"
        )
        return None

    for token in process.stdout.replace(",", " ").split():
        try:
            return float(token)
        except ValueError:
            continue

    sys.stderr.write(
        f"Unable to find a numeric value in the output of '{command}'.\n"
    )
    return None


def fetch_value_from_file(path: Path) -> Optional[float]:
    """Read *path* and parse the first floating-point number it contains."""

    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.stderr.write(f"File '{path}' not found.\n")
        return None
    except OSError as exc:
        sys.stderr.write(f"Failed to read '{path}': {exc}\n")
        return None

    for token in content.replace(",", " ").split():
        try:
            return float(token)
        except ValueError:
            continue

    sys.stderr.write(f"No numeric value found in '{path}'.\n")
    return None


def beep() -> None:
    """Emit an audible beep if supported by the current platform."""

    try:  # Windows
        import winsound

        winsound.Beep(1000, 500)
        return
    except (ImportError, RuntimeError):
        pass

    # Fallback for POSIX terminals
    sys.stdout.write("\a")
    sys.stdout.flush()


def value_in_range(value: float, min_value: Optional[float], max_value: Optional[float]) -> bool:
    """Return True if *value* lies within the [min_value, max_value] range."""

    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def monitor(args: argparse.Namespace) -> None:
    """Monitor the configured numeric source and emit a beep on changes."""

    last_value: Optional[float] = None

    while True:
        if args.command:
            value = fetch_value_from_command(args.command)
        else:
            value = fetch_value_from_file(args.file)

        if value is None:
            time.sleep(args.interval)
            continue

        if not value_in_range(value, args.min_value, args.max_value):
            last_value = None
        elif last_value is None:
            last_value = value
        elif abs(value - last_value) > args.threshold:
            beep()
            print(
                time.strftime("[%Y-%m-%d %H:%M:%S] ")
                + f"Value changed: {last_value} -> {value}",
                flush=True,
            )
            last_value = value

        time.sleep(args.interval)


def main() -> None:
    monitor(parse_arguments())


if __name__ == "__main__":
    main()
