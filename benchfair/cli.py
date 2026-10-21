"""Command-line parsing and roster file handling."""

import argparse
import json
from pathlib import Path
from collections.abc import Sequence
import sys

from .models import DEFAULT_SEED, validate_players
from .reporting import render_json, render_markdown
from .scheduler import generate_schedule


def load_roster(path: Path) -> tuple[str, ...]:
    """Read UTF-8 JSON and validate players; expected failures raise ValueError."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read roster {str(path)!r}: {error}") from None
    try:
        data = json.loads(content)
    except (ValueError, RecursionError):
        raise ValueError("roster must contain valid JSON") from None
    if not isinstance(data, dict) or not isinstance(data.get("players"), list):
        raise ValueError("roster must be an object with a 'players' list")
    return validate_players(data["players"])


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI. Return 0 on success, 2 for expected input/output errors."""
    parser = argparse.ArgumentParser(
        description="Fair 2v2 rotations. A court can also represent a gaming station.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python -m benchfair examples/players.json --courts 2 --rounds 8 --seed 42\n"
               "  python -m benchfair examples/players.json --format json > schedule.json",
    )
    parser.add_argument("roster", type=Path, help="UTF-8 JSON file containing a players list (4–32 names)")
    parser.add_argument("--courts", type=int, default=1, help="number of courts, 1–8 (default: 1)")
    parser.add_argument("--rounds", type=int, default=6, help="number of rounds, 1–100 (default: 6)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"integer random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown",
                        help="output format (default: markdown)")
    args = parser.parse_args(argv)
    try:
        schedule = generate_schedule(load_roster(args.roster), courts=args.courts,
                                     rounds=args.rounds, seed=args.seed)
        output = render_json(schedule) if args.format == "json" else render_markdown(schedule)
        sys.stdout.write(output)
        sys.stdout.flush()
    except (ValueError, OSError) as error:
        print(f"benchfair: error: {error}", file=sys.stderr)
        return 2
    return 0
