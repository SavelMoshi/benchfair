"""Immutable schedule records and shared input validation."""

from collections.abc import Sequence
from dataclasses import dataclass
import unicodedata

DEFAULT_SEED = 42
MAX_NAME_LENGTH = 40


def validate_players(players: Sequence[str]) -> tuple[str, ...]:
    """Return trimmed names; raise ValueError for unsupported or unsafe rosters."""
    if isinstance(players, (str, bytes)) or not isinstance(players, Sequence):
        raise ValueError("players must be a list or tuple of names")
    if not 4 <= len(players) <= 32:
        raise ValueError("players must contain between 4 and 32 names")
    cleaned = []
    seen = set()
    for index, name in enumerate(players, 1):
        if not isinstance(name, str):
            raise ValueError(f"player {index}: name must be a string")
        # Check before trimming so even trailing newlines are rejected.
        if any(unicodedata.category(char) in {"Cc", "Cs", "Zl", "Zp"}
               or unicodedata.bidirectional(char) in
               {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
               for char in name):
            raise ValueError(f"player {index}: name contains a control character or line break")
        name = name.strip()
        if not name:
            raise ValueError(f"player {index}: name must not be empty")
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(f"player {index}: name must be at most {MAX_NAME_LENGTH} characters")
        if name.casefold() in seen:
            raise ValueError(f"player {index}: duplicate name (ignoring case and outer whitespace)")
        seen.add(name.casefold())
        cleaned.append(name)
    return tuple(cleaned)


def validate_config(player_count: int, courts: int, rounds: int, seed: int) -> None:
    """Validate session options, including for direct Python callers."""
    for label, value, lower, upper in (("courts", courts, 1, 8), ("rounds", rounds, 1, 100)):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f"{label} must be an integer between {lower} and {upper}")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if player_count < 4 * courts:
        raise ValueError(f"{courts} courts require at least {4 * courts} players")


@dataclass(frozen=True)
class Match:
    """Two teams on one court; court numbers come from their round order."""

    team_a: tuple[str, str]
    team_b: tuple[str, str]


@dataclass(frozen=True)
class Round:
    """All simultaneous matches and resting players for one round."""

    matches: tuple[Match, ...]
    resting: tuple[str, ...]


@dataclass(frozen=True)
class Schedule:
    """Completed session. Names retain roster order; rounds are chronological."""

    players: tuple[str, ...]
    courts: int
    seed: int
    rounds: tuple[Round, ...]
