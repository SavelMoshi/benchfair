"""Scheduling guarantees, selection priorities, scoring, and API validation."""

from collections import Counter
import os
import random
import subprocess
import sys
import unittest

from benchfair import Match, calculate_report, generate_schedule
from benchfair.scheduler import _select_players, pair_key, repeat_cost


class SchedulerTests(unittest.TestCase):
    def assert_invariants(self, size, courts, rounds, seed):
        players = [f"Player {i}" for i in range(size)]
        original = players.copy()
        schedule = generate_schedule(players, courts=courts, rounds=rounds, seed=seed)
        games = Counter({name: 0 for name in players})
        streak = Counter({name: 0 for name in players})
        for round_ in schedule.rounds:
            self.assertEqual(len(round_.matches), courts)
            active = []
            for match in round_.matches:
                self.assertEqual(len(match.team_a), 2)
                self.assertEqual(len(match.team_b), 2)
                self.assertEqual(len(set((*match.team_a, *match.team_b))), 4)
                active.extend((*match.team_a, *match.team_b))
            self.assertEqual(Counter(active + list(round_.resting)), Counter(players))
            for chosen in active:
                for resting in round_.resting:
                    self.assertLessEqual((games[chosen], -streak[chosen]),
                                         (games[resting], -streak[resting]))
            games.update(active)
            for name in players:
                streak[name] = streak[name] + 1 if name in round_.resting else 0
            self.assertLessEqual(max(games.values()) - min(games.values()), 1)
        report = calculate_report(schedule)
        self.assertEqual({p.name: p.games_played for p in report.players}, dict(games))
        self.assertEqual(players, original)
        return schedule

    def test_invariants_across_rosters_courts_rounds_and_seeds(self):
        for size in (4, 5, 7, 8, 10, 13, 17, 31, 32):
            for courts in sorted({1, size // 4}):
                for rounds in (1, 7):
                    for seed in (0, 42, -7):
                        with self.subTest(size=size, courts=courts, rounds=rounds, seed=seed):
                            self.assert_invariants(size, courts, rounds, seed)

    def test_supported_size_limits(self):
        self.assert_invariants(32, 8, 100, 42)
        self.assert_invariants(32, 1, 100, 42)

    def test_everyone_plays(self):
        schedule = self.assert_invariants(8, 2, 6, 42)
        self.assertTrue(all(round_.resting == () for round_ in schedule.rounds))
        for player in calculate_report(schedule).players:
            self.assertEqual((player.games_played, player.rounds_rested,
                              player.longest_resting_streak), (6, 0, 0))

    def test_reproducibility_state_isolation_and_global_rng(self):
        players = list("ABCDEFGHI")
        before = random.getstate()
        first = generate_schedule(players, courts=2, rounds=9)
        generate_schedule(list("JKLMN"), seed=100)
        self.assertEqual(first, generate_schedule(players, courts=2, rounds=9))
        self.assertEqual(random.getstate(), before)

    def test_hash_seed_independence(self):
        code = "from benchfair import *; print(render_json(generate_schedule(list('ABCDEFGHI'))))"
        results = [subprocess.check_output([sys.executable, "-c", code],
                   env={**os.environ, "PYTHONHASHSEED": seed}) for seed in ("1", "99")]
        self.assertEqual(results[0], results[1])

    def test_selection_priorities(self):
        players = tuple("ABCDEF")
        games = dict(zip(players, (0, 0, 0, 0, 0, 1)))
        streak = dict(zip(players, (0, 3, 2, 1, 4, 99)))
        selected = _select_players(players, 4, games, streak, random.Random(42))
        self.assertEqual(selected, list("EBCD"))

    def test_pair_cost_with_known_histories(self):
        arrangement = (Match(("A", "B"), ("C", "D")),)
        self.assertEqual(pair_key("B", "A"), ("A", "B"))
        self.assertEqual(repeat_cost(arrangement, {}, {}), (2, 4))
        self.assertEqual(repeat_cost(arrangement, {("A", "B"): 3},
                                     {("A", "C"): 2, ("B", "D"): 1}), (8, 10))
        alternative = (Match(("A", "C"), ("B", "D")),)
        teams = {("A", "B"): 1}
        opponents = {("A", "B"): 100}
        self.assertLess(repeat_cost(alternative, teams, opponents),
                        repeat_cost(arrangement, teams, opponents))
        # With equal teammate cost, opponent cost breaks the tie.
        self.assertLess(repeat_cost(arrangement, {}, opponents),
                        repeat_cost(alternative, {}, opponents))

    def test_invalid_options(self):
        for option, values in {"courts": (0, 9, -1, 1.5, True, "1", None),
                               "rounds": (0, 101, -1, 1.5, True, "6", None),
                               "seed": (None, True, 1.5, "42")}.items():
            for value in values:
                with self.subTest(option=option, value=value), self.assertRaises(ValueError):
                    generate_schedule(list("ABCDEFGH"), **{option: value})
        with self.assertRaisesRegex(ValueError, "require at least 8"):
            generate_schedule(list("ABCDEFG"), courts=2)

    def test_invalid_rosters(self):
        invalid = [None, "ABCD", set("ABCD"), [], list("ABC"),
                   [str(i) for i in range(33)], ["A", "B", "C", 4],
                   ["A", "B", "C", ""], ["A", "B", "C", "  "],
                   ["A", "B", "C", " a "], ["A", "B", "Straße", "STRASSE"],
                   ["A", "B", "C", "x" * 41]]
        invalid += [["A", "B", "C", "X" + char] for char in
                    ("\n", "\r", "\t", "\0", "\x7f", "\x85", "\u2028", "\u2029", "\u202e", "\ud800")]
        for roster in invalid:
            with self.subTest(roster=repr(roster)), self.assertRaises(ValueError):
                generate_schedule(roster)

    def test_unicode_trim_and_name_length_boundary(self):
        roster = ["  Zoë  ", "李", "أمل", "x" * 40]
        self.assertEqual(generate_schedule(roster, rounds=1).players,
                         ("Zoë", "李", "أمل", "x" * 40))


if __name__ == "__main__":
    unittest.main()
