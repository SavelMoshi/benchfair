# BenchFair

[![Tests](https://github.com/SavelMoshi/benchfair/actions/workflows/tests.yml/badge.svg)](https://github.com/SavelMoshi/benchfair/actions/workflows/tests.yml)

**Reproducible 2v2 rotations for pickup sports and game nights.**

When friends organize doubles games, a few people can end up playing repeatedly
while others wait. BenchFair chooses who plays next, forms teams that discourage
repeated pairings, and shows exactly how playing time and pair variety turned out.
A **court** can mean a sports court or a gaming station.

## Example

This is round 1 of the [generated sample schedule](examples/schedule.md), using
10 fictional players, two courts, eight rounds, and seed 42:

| Court | Team A | Team B |
| --- | --- | --- |
| 1 | Indigo + Casey | Finley + Devon |
| 2 | Gray + Ellis | Harper + Jules |

Resting: Alex, Blair

Across that complete sample, each player plays six or seven games. There are
zero repeated teammate pairings and 21 repeated opponent pairings. These are
results for this particular input, not promises for every session.

## Features

- 4–32 players, 1–8 courts, and 1–100 rounds; exactly four players per court.
- Playing-time counts differ by at most one after **every round**, assuming a
  fixed roster whose players are all available for the whole session.
- Among players with equal game counts, longer current rest streaks come first.
- A bounded search prefers teammate variety, then opponent variety.
- Markdown and versioned JSON reports, with a fixed default seed of **42**.
- Standard-library runtime and tests; reusable Python functions and an optional
  installed command.

## Requirements and quick start

Use Python **3.11 or newer**. No installation or external runtime packages are
needed from a checkout. CI covers Python 3.11–3.15.

```bash
git clone https://github.com/SavelMoshi/benchfair.git
cd benchfair
python --version
python -m benchfair examples/players.json --courts 2 --rounds 8 --seed 42
python -m unittest discover -s tests -v
```

If your system names Python 3 `python3`, use `python3` in these commands. On
Windows, `py -3.11` (or a newer installed version) is another option.

For the optional installed `benchfair` command, create an environment first:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
benchfair examples/players.json --courts 2 --rounds 8 --seed 42
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
Installation uses setuptools as a build dependency and may need network access;
running the module and tests from the checkout does not.

## Roster format

Save a UTF-8 JSON file with a `players` list. For example:

```json
{
  "players": ["Alex", "Blair", "Casey", "Devon", "Ellis"]
}
```

The complete [sample roster](examples/players.json) uses **fictional names**.
Names must be nonempty strings with at most **40 Unicode code points after
trimming outer whitespace**. Duplicate names are rejected after trimming and
Unicode case-folding (`Alex` and ` alex ` collide). Unicode normalization is
not performed; use consistent spelling. Ordinary Unicode names, including
non-Latin scripts and emoji, are supported.

Control characters, line/paragraph separators, unpaired surrogates, and explicit
bidirectional formatting controls are rejected before trimming. This prevents
names from introducing new lines or misleading directional overrides in reports.
Names are escaped in Markdown and preserved as strings in JSON. Extra top-level
roster fields are ignored.

## CLI options

```bash
python -m benchfair --help
```

| Argument | Meaning | Default |
| --- | --- | --- |
| `roster` | Path to a UTF-8 JSON roster | Required |
| `--courts` | Courts used simultaneously, 1–8 | `1` |
| `--rounds` | Rounds to schedule, 1–100 | `6` |
| `--seed` | Integer random seed; negative integers are allowed | `42` |
| `--format` | `markdown` or `json` | `markdown` |

There must be at least `4 × courts` players. BenchFair rejects an insufficient
roster instead of silently reducing courts. Expected input errors go to standard
error without a traceback and exit with status 2. Success exits with status 0.

### Save reports

```bash
python -m benchfair examples/players.json --courts 2 --rounds 8 --seed 42 > schedule.md
python -m benchfair examples/players.json --courts 2 --rounds 8 --seed 42 --format json > schedule.json
python -m json.tool schedule.json
```

Standard output contains only the selected report. See the checked-in
[Markdown](examples/schedule.md) and [JSON](examples/schedule.json) samples and
the [JSON field reference](docs/json-format.md).

## Use from Python

```python
from benchfair import generate_schedule, calculate_report, render_markdown

schedule = generate_schedule(
    ["Alex", "Blair", "Casey", "Devon", "Ellis"],
    courts=1,
    rounds=6,
    seed=42,
)
report = calculate_report(schedule)
print(report.game_count_difference)
print(render_markdown(schedule))
```

`generate_schedule` accepts a sequence of names, validates the same constraints
as the CLI, and raises `ValueError` for invalid inputs. It returns immutable
`Schedule`, `Round`, and `Match` records, does not modify the roster, and does not
alter global random state. `calculate_report`, `render_markdown`, and
`render_json` work on the completed schedule; reporting also checks round
membership and court/team sizes. Manually constructed records should follow the
annotated tuple-based structure in `benchfair/models.py`.

## How scheduling works

1. **Choose players.** Shuffle a copy of the roster with a dedicated seeded RNG,
   then stably sort by games played ascending and current resting streak
   descending. Take exactly `4 × courts` players. The shuffle decides remaining
   ties; game counts always take priority over waiting time.
2. **Form teams.** Shuffle those selected players into 128 candidate arrangements.
   Each consecutive group of four becomes two teams of two.
3. **Compare candidates.** For every pair with `k` previous occurrences, a new
   occurrence costs `(k + 1)² − k² = 2k + 1`. Sum teammate costs and opponent costs
   separately. Compare `(teammate cost, opponent cost)` lexicographically, so any
   improvement in teammate cost wins even if opponent cost gets worse. Keep the
   first candidate when scores tie.
4. **Update history** and proceed to the next round. After scheduling, calculate
   the report afresh from the matches.

The same ordered roster, options, seed, and algorithm version reproduce a
schedule on the tested Python versions. Reordering the roster or changing the
algorithm/search budget can change the result. Different seeds may produce
the same schedule. See [design notes](docs/design.md) for the balance argument,
complexity, and interview discussion points.

## Fairness metrics

| Metric | Definition |
| --- | --- |
| Games played | Rounds in which the player is on a court |
| Rounds rested | Total rounds minus games played |
| Distinct teammates | Number of different people on the player's team |
| Distinct opponents | Number of different people on the opposing team |
| Longest resting streak | Longest consecutive sequence of resting rounds, including session edges; zero if never resting |
| Minimum / maximum games | Smallest / largest per-player game count, including players with zero games |
| Game-count difference | Maximum minus minimum games played |
| Repeated teammate pairings | Sum of `max(0, k − 1)` over unordered teammate pairs appearing `k` times |
| Repeated opponent pairings | Same calculation for unordered opponent pairs |

A match has two teammate pairs and four opponent pairs. Each unordered pair is
counted once per match, not once from each player's perspective. A pair appearing
three times contributes **two repeats**. The reported repeat total is different
from the squared-count cost used during search.

## Tests

```bash
python -m unittest discover -s tests -v
```

The suite uses `unittest` and subtests across roster sizes, courts, rounds, and
seeds. It checks round membership, court shape, selection priorities, per-round
balance, odd rosters, smallest and largest sessions, reproducibility across hash
seeds, state isolation, global RNG preservation, validation, CLI exits, JSON, and
Markdown escaping. Hand-built schedules verify statistics, and known pair
histories verify scoring independently of search outcomes.

GitHub Actions runs the suite, regenerates and compares both checked-in samples,
and installs the package to verify the console command. The workflow has only
`contents: read` permissions. Action major versions were checked against the
official [checkout](https://github.com/actions/checkout) and
[setup-python](https://github.com/actions/setup-python) documentation.

## Limits and tradeoffs

Playing-time balance is a specific guarantee for this fixed-roster model.
Teammate/opponent variety is heuristic: the search does not enumerate all
arrangements or guarantee a global optimum. Repeats are unavoidable in some
sessions. Equal playing time says nothing about skill, match difficulty, or game
duration. Rest streaks break game-count ties; there is no separate optimal
maximum-wait guarantee. Court assignment itself is not balanced.

Version one has no ratings, arrivals/departures, results, brackets, accounts,
database, web interface, cloud services, or AI APIs. It schedules complete
sessions before play begins.

Plausible future improvements include optional skill-aware scoring, explicit
availability per round, court-assignment balance, and a small exhaustive-search
reference solver to compare heuristic results on tiny sessions. Each would need
new tests and clear definitions of which fairness goals take priority.

## License

BenchFair is available under the [MIT License](LICENSE).
