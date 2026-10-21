"""Balanced player selection followed by bounded team-formation search."""

from collections import Counter
from collections.abc import Mapping, Sequence
import random

from .models import DEFAULT_SEED, Match, Round, Schedule, validate_config, validate_players

SEARCH_CANDIDATES = 128
Pair = tuple[str, str]


def pair_key(first: str, second: str) -> Pair:
    """Canonical unordered pair; never rely on set iteration order."""
    return (first, second) if first < second else (second, first)


def match_pairs(match: Match) -> tuple[tuple[Pair, ...], tuple[Pair, ...]]:
    """Return two teammate pairs and four opponent pairs, each counted once."""
    teammates = (pair_key(*match.team_a), pair_key(*match.team_b))
    opponents = tuple(pair_key(a, b) for a in match.team_a for b in match.team_b)
    return teammates, opponents


def repeat_cost(matches: Sequence[Match], teammates: Mapping[Pair, int],
                opponents: Mapping[Pair, int]) -> tuple[int, int]:
    """Score valid, disjoint matches by increases in squared historical counts.

    An occurrence after k prior occurrences costs (k+1)^2-k^2 = 2k+1.
    Compare the two totals lexicographically: teammate cost always comes first.
    """
    teammate_cost = opponent_cost = 0
    for match in matches:
        team_pairs, opponent_pairs = match_pairs(match)
        teammate_cost += sum(2 * teammates.get(pair, 0) + 1 for pair in team_pairs)
        opponent_cost += sum(2 * opponents.get(pair, 0) + 1 for pair in opponent_pairs)
    return teammate_cost, opponent_cost


def _select_players(players: tuple[str, ...], count: int, games: Mapping[str, int],
                    resting_streak: Mapping[str, int], rng: random.Random) -> list[str]:
    # Stable sorting a shuffled list makes only the remaining ties random.
    candidates = list(players)
    rng.shuffle(candidates)
    candidates.sort(key=lambda name: (games[name], -resting_streak[name]))
    return candidates[:count]


def _form_teams(active: list[str], teammates: Mapping[Pair, int],
                opponents: Mapping[Pair, int], rng: random.Random) -> tuple[Match, ...]:
    best_matches: tuple[Match, ...] = ()
    best_score: tuple[int, int] | None = None
    for _ in range(SEARCH_CANDIDATES):
        candidate = active.copy()
        rng.shuffle(candidate)
        matches = tuple(Match((candidate[i], candidate[i + 1]),
                              (candidate[i + 2], candidate[i + 3]))
                        for i in range(0, len(candidate), 4))
        score = repeat_cost(matches, teammates, opponents)
        if best_score is None or score < best_score:
            best_matches, best_score = matches, score
    return best_matches


def generate_schedule(players: Sequence[str], *, courts: int = 1, rounds: int = 6,
                      seed: int = DEFAULT_SEED) -> Schedule:
    """Generate a reproducible session without mutating players or global RNG state.

    Players must be a sequence of 4–32 unique names. Courts are 1–8, rounds
    1–100, and seed is an integer. Invalid input raises ValueError.
    Games played differ by at most one after every round for this fixed roster.
    Pair variety is a heuristic objective, not an optimality guarantee.
    """
    roster = validate_players(players)
    validate_config(len(roster), courts, rounds, seed)
    rng = random.Random(seed)
    games: Counter[str] = Counter()
    resting_streak: Counter[str] = Counter()
    teammates: Counter[Pair] = Counter()
    opponents: Counter[Pair] = Counter()
    completed = []
    for _ in range(rounds):
        active = _select_players(roster, 4 * courts, games, resting_streak, rng)
        matches = _form_teams(active, teammates, opponents, rng)
        active_set = set(active)  # Membership only; roster order determines output.
        resting = tuple(name for name in roster if name not in active_set)
        completed.append(Round(matches, resting))
        for name in roster:
            if name in active_set:
                games[name] += 1
                resting_streak[name] = 0
            else:
                resting_streak[name] += 1
        for match in matches:
            team_pairs, opponent_pairs = match_pairs(match)
            teammates.update(team_pairs)
            opponents.update(opponent_pairs)
    return Schedule(roster, courts, seed, tuple(completed))
