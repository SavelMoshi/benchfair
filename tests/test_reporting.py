"""Hand-counted schedules provide an independent statistics oracle."""

import json
import unittest

from benchfair import Match, Round, Schedule, calculate_report, generate_schedule
from benchfair.reporting import PlayerStats, escape_markdown, render_json, render_markdown


class ReportingTests(unittest.TestCase):
    def test_manual_schedule_and_unordered_repeats(self):
        # ABCD play three times; swapping sides/order must not create new pairs.
        schedule = Schedule(tuple("ABCDE"), 1, 42, (
            Round((Match(("A", "B"), ("C", "D")),), ("E",)),
            Round((Match(("D", "C"), ("B", "A")),), ("E",)),
            Round((Match(("A", "C"), ("B", "D")),), ("E",)),
            Round((Match(("A", "E"), ("B", "C")),), ("D",)),
        ))
        report = calculate_report(schedule)
        self.assertEqual(report.players, (
            PlayerStats("A", 4, 0, 3, 3, 0),
            PlayerStats("B", 4, 0, 3, 4, 0),
            PlayerStats("C", 4, 0, 3, 4, 0),
            PlayerStats("D", 3, 1, 2, 3, 1),
            PlayerStats("E", 1, 3, 1, 2, 3),
        ))
        self.assertEqual((report.min_games_played, report.max_games_played,
                          report.game_count_difference), (1, 4, 3))
        self.assertEqual(report.repeated_teammate_pairings, 2)
        self.assertEqual(report.repeated_opponent_pairings, 8)

    def test_longest_rest_streak_resets(self):
        resting_e = Round((Match(("A", "B"), ("C", "D")),), ("E",))
        playing_e = Round((Match(("A", "E"), ("B", "C")),), ("D",))
        schedule = Schedule(tuple("ABCDE"), 1, 0,
                            (resting_e, resting_e, playing_e, resting_e, resting_e))
        player = calculate_report(schedule).players[-1]
        self.assertEqual((player.rounds_rested, player.longest_resting_streak), (4, 2))

    def test_three_occurrences_mean_two_repeats_per_pair(self):
        round_ = Round((Match(("A", "B"), ("C", "D")),), ())
        report = calculate_report(Schedule(tuple("ABCD"), 1, 0, (round_,) * 3))
        self.assertEqual(report.repeated_teammate_pairings, 4)
        self.assertEqual(report.repeated_opponent_pairings, 8)

    def test_reject_invalid_schedule(self):
        rounds = [Round((), tuple("ABCD")),
                  Round((Match(("A", "B"), ("A", "D")),), ()),
                  Round((Match(("A", "B"), ("C", "Z")),), ()),
                  Round((Match(("A",), ("B", "C")),), ("D",))]
        for round_ in rounds:
            with self.subTest(round=round_), self.assertRaises(ValueError):
                calculate_report(Schedule(tuple("ABCD"), 1, 42, (round_,)))

    def test_json_schema_and_unicode_round_trip(self):
        roster = ["Zoë", "李", "A|B", "<C>", "D"]
        schedule = generate_schedule(roster, rounds=2)
        data = json.loads(render_json(schedule))
        self.assertEqual(set(data), {"schema_version", "session", "rounds", "fairness"})
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["session"], {"players": roster, "courts": 1, "rounds": 2, "seed": 42})
        self.assertEqual([r["round"] for r in data["rounds"]], [1, 2])
        self.assertEqual(data["rounds"][0]["matches"][0]["court"], 1)
        self.assertEqual([p["name"] for p in data["fairness"]["players"]], roster)

    def test_markdown_escaping_in_teams_resting_and_report(self):
        names = ("A|B", "<script>", "*bold*", "[link](url)", "back\\tick` &quot;")
        schedule = Schedule(names, 1, 42,
                            (Round((Match(names[:2], names[2:4]),), (names[4],)),))
        output = render_markdown(schedule)
        for expected in (r"A\|B", "&lt;script&gt;", r"\*bold\*", r"\[link\]\(url\)",
                         r"back\\tick\` &amp;quot\;"):
            self.assertGreaterEqual(output.count(expected), 2)
        self.assertNotIn("<script>", output)
        self.assertEqual(escape_markdown("Zoë 李"), "Zoë 李")


if __name__ == "__main__":
    unittest.main()
