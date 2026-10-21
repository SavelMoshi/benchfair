"""Recompute statistics from completed matches, then render Markdown or JSON."""

from collections import Counter
from dataclasses import asdict, dataclass
import html
import json
import string

from .models import Schedule, validate_config, validate_players


@dataclass(frozen=True)
class PlayerStats:
    name: str
    games_played: int
    rounds_rested: int
    distinct_teammates: int
    distinct_opponents: int
    longest_resting_streak: int


@dataclass(frozen=True)
class FairnessReport:
    players: tuple[PlayerStats, ...]
    min_games_played: int
    max_games_played: int
    game_count_difference: int
    repeated_teammate_pairings: int
    repeated_opponent_pairings: int


def calculate_report(schedule: Schedule) -> FairnessReport:
    """Recount a completed schedule; reject invalid round membership with ValueError.

    Uses its own pair enumeration, independent of scheduler history and scoring.
    A pair occurring k times contributes max(0, k-1) repeats.
    """
    roster = validate_players(schedule.players)
    if roster != schedule.players:
        raise ValueError("schedule players must be a tuple of trimmed names")
    validate_config(len(roster), schedule.courts, len(schedule.rounds), schedule.seed)
    games: Counter[str] = Counter()
    streak: Counter[str] = Counter()
    longest: Counter[str] = Counter()
    teammate_pairs: Counter[frozenset[str]] = Counter()
    opponent_pairs: Counter[frozenset[str]] = Counter()
    teammates: dict[str, set[str]] = {name: set() for name in roster}
    opponents: dict[str, set[str]] = {name: set() for name in roster}
    for number, round_ in enumerate(schedule.rounds, 1):
        if len(round_.matches) != schedule.courts:
            raise ValueError(f"round {number}: incorrect number of courts")
        present = list(round_.resting)
        for match in round_.matches:
            if len(match.team_a) != 2 or len(match.team_b) != 2:
                raise ValueError(f"round {number}: each team must have two players")
            present.extend((*match.team_a, *match.team_b))
        if Counter(present) != Counter(roster):
            raise ValueError(f"round {number}: each roster player must appear exactly once")
        resting_set = set(round_.resting)
        for name in roster:
            if name in resting_set:
                streak[name] += 1
                longest[name] = max(longest[name], streak[name])
            else:
                games[name] += 1
                streak[name] = 0
        for match in round_.matches:
            for first, second in (match.team_a, match.team_b):
                teammate_pairs[frozenset((first, second))] += 1
                teammates[first].add(second)
                teammates[second].add(first)
            for first in match.team_a:
                for second in match.team_b:
                    opponent_pairs[frozenset((first, second))] += 1
                    opponents[first].add(second)
                    opponents[second].add(first)
    minimum, maximum = min(games[name] for name in roster), max(games[name] for name in roster)
    return FairnessReport(
        tuple(PlayerStats(name, games[name], len(schedule.rounds) - games[name],
                          len(teammates[name]), len(opponents[name]), longest[name])
              for name in roster),
        minimum, maximum, maximum - minimum,
        sum(count - 1 for count in teammate_pairs.values()),
        sum(count - 1 for count in opponent_pairs.values()),
    )


def render_json(schedule: Schedule) -> str:
    """Return schema-version 1 JSON; see docs/json-format.md for field definitions."""
    report = asdict(calculate_report(schedule))
    data = {
        "schema_version": 1,
        "session": {"players": schedule.players, "courts": schedule.courts,
                    "rounds": len(schedule.rounds), "seed": schedule.seed},
        "rounds": [
            {"round": number, "matches": [
                {"court": court, "team_a": match.team_a, "team_b": match.team_b}
                for court, match in enumerate(round_.matches, 1)], "resting": round_.resting}
            for number, round_ in enumerate(schedule.rounds, 1)],
        "fairness": report,
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def escape_markdown(name: str) -> str:
    """Escape inline HTML and ASCII punctuation, including table delimiters."""
    return "".join(html.escape(char, quote=True) if char in "&<>\"'" else
                   "\\" + char if char in string.punctuation else char for char in name)


def render_markdown(schedule: Schedule) -> str:
    """Return a GitHub-readable schedule and independently calculated report."""
    report = calculate_report(schedule)
    lines = ["# BenchFair schedule", "",
             f"Players: {len(schedule.players)} · Courts: {schedule.courts} · "
             f"Rounds: {len(schedule.rounds)} · Seed: {schedule.seed}", ""]
    for number, round_ in enumerate(schedule.rounds, 1):
        lines.extend([f"## Round {number}", "", "| Court | Team A | Team B |",
                      "| --- | --- | --- |"])
        for court, match in enumerate(round_.matches, 1):
            team_a = " + ".join(map(escape_markdown, match.team_a))
            team_b = " + ".join(map(escape_markdown, match.team_b))
            lines.append(f"| {court} | {team_a} | {team_b} |")
        resting = ", ".join(map(escape_markdown, round_.resting)) or "None"
        lines.extend(["", f"Resting: {resting}", ""])
    lines.extend(["## Fairness report", "",
                  "| Player | Games | Rounds rested | Distinct teammates | Distinct opponents | Longest rest streak |",
                  "| --- | --- | --- | --- | --- | --- |"])
    for player in report.players:
        lines.append(f"| {escape_markdown(player.name)} | {player.games_played} | "
                     f"{player.rounds_rested} | {player.distinct_teammates} | "
                     f"{player.distinct_opponents} | {player.longest_resting_streak} |")
    lines.extend(["", f"Games played: min {report.min_games_played}, max {report.max_games_played}, "
                  f"difference {report.game_count_difference}.", "",
                  f"Repeated teammate pairings: {report.repeated_teammate_pairings}.", "",
                  f"Repeated opponent pairings: {report.repeated_opponent_pairings}.", "",
                  "Each unordered pair occurring k times contributes k − 1 repeats. "
                  "Rest streaks are measured in consecutive rounds.", ""])
    return "\n".join(lines)
