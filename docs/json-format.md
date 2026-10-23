# JSON output, schema version 1

`--format json` writes one UTF-8 JSON object and a final newline to standard
output. Errors go to standard error. See the complete generated
[sample](../examples/schedule.json). JSON uses original trimmed names, not
Markdown-escaped names. Arrays are ordered; consumers should not rely on object
key order or whitespace.

| Top-level field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | `1`; incremented for incompatible structure changes |
| `session` | object | Configuration below |
| `rounds` | array of objects | Schedule in chronological order |
| `fairness` | object | Statistics recomputed from the entire schedule |

## Session

| Field | Type | Meaning |
| --- | --- | --- |
| `players` | array of strings | Trimmed, validated names in original roster order |
| `courts` | integer | Courts per round, 1–8 |
| `rounds` | integer | Number of rounds, 1–100 |
| `seed` | integer | Random seed, default 42 |

## Round and match

Each round has `round` (one-based integer), `matches` (array of exactly
`session.courts` objects), and `resting` (array of names in roster order; empty
when everyone plays). Each match has:

```json
{
  "court": 1,
  "team_a": ["Indigo", "Casey"],
  "team_b": ["Finley", "Devon"]
}
```

Court numbers are one-based within each round. Teams contain exactly two
different names; the four names on a court are distinct. Each roster player
appears exactly once in each round, either in a match or in `resting`.

## Fairness

`fairness.players` is an array in roster order. Each object contains `name`
(string) and these nonnegative integer fields:

- `games_played`: count of rounds played.
- `rounds_rested`: session rounds minus games played.
- `distinct_teammates`: number of different teammates.
- `distinct_opponents`: number of different opponents.
- `longest_resting_streak`: maximum consecutive resting rounds, including at
  the start or end; zero for players who never rest.

The remaining fields of `fairness` are nonnegative integers:

- `min_games_played`, `max_games_played`: extremes across all roster players,
  including anyone with zero games.
- `game_count_difference`: maximum minus minimum.
- `repeated_teammate_pairings`, `repeated_opponent_pairings`: for each unordered
  pair appearing `k` times, add `max(0, k − 1)`. Each match has two teammate pairs
  and four opponent pairs; do not count a pair twice from both perspectives.

Seeds are Python integers; the CLI does not impose a smaller numeric range.
