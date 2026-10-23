# BenchFair

[![Tests](https://github.com/SavelMoshi/benchfair/actions/workflows/tests.yml/badge.svg)](https://github.com/SavelMoshi/benchfair/actions/workflows/tests.yml)

BenchFair makes 2v2 schedules for casual sports and game nights. It gives the
next spots to players with fewer games, uses waiting time to break ties, and
tries to avoid repeating teammates and opponents. A **court** can also mean a
gaming station.

## Example

This is round 1 of the [generated sample schedule](examples/schedule.md), using
10 fictional players, two courts, eight rounds, and seed 42:

| Court | Team A | Team B |
| --- | --- | --- |
| 1 | Indigo + Casey | Finley + Devon |
| 2 | Gray + Ellis | Harper + Jules |

Resting: Alex, Blair

Across the complete sample, each player plays six or seven games. It has zero
repeated teammate pairings and 21 repeated opponent pairings.

## Features

- 4–32 players, 1–8 courts, and 1–100 rounds; exactly four players per court.
- Playing-time counts differ by at most one after **every round**, assuming a
  fixed roster whose players are all available for the whole session.
- Among players with equal game counts, longer current rest streaks come first.
- A bounded search prefers teammate variety, then opponent variety.
- Markdown and versioned JSON reports, with a fixed default seed of **42**.
- No runtime dependencies; callable Python functions and an optional installed
  command.

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
The package installation uses setuptools; running from the checkout does not
need an installation step.

## Roster format

Save a UTF-8 JSON file with a `players` list. For example:

```json
{
  "players": ["Alex", "Blair", "Casey", "Devon", "Ellis"]
}
```

The complete [sample roster](examples/players.json) uses **fictional names**.
Names can use Unicode and are limited to **40 code points after trimming outer
whitespace**. They cannot be blank or duplicate another name after case-folding
(`Alex` and ` alex ` collide). BenchFair rejects control characters, line breaks,
unpaired surrogates, and bidirectional formatting controls. It escapes names in
Markdown and preserves them in JSON. Unicode normalization is not performed, so
use consistent spelling. Extra top-level roster fields are ignored.

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

`generate_schedule` applies the CLI's validation to direct Python calls and
raises `ValueError` for invalid inputs. It returns immutable `Schedule`, `Round`,
and `Match` records without changing the input roster or global random state.
`calculate_report` checks the completed schedule and recounts its statistics;
the render functions use that report.

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

The same ordered roster, options, and seed reproduce a schedule with this
version of the algorithm. Reordering names or changing the algorithm can change
the result. See the [design notes](docs/design.md) for the balance argument and
complexity.

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

The `unittest` suite checks round membership, playing-time balance, selection
priorities, reproducibility, validation, CLI behavior, and both output formats.
Hand-built schedules check the statistics and pair scoring against known answers.

GitHub Actions runs the tests on Python 3.11–3.15, checks that both examples
regenerate unchanged, and tries the installed command.

## Limits and tradeoffs

The one-game maximum difference depends on a fixed roster with every player
available for every round. Pair variety is a heuristic, so repeats can happen
and the schedule may not be globally optimal. BenchFair does not account for
skill, match difficulty, game length, or court preference. It cannot handle
players joining or leaving mid-session.

Possible next steps are skill-aware scoring, per-round availability, and court
assignment balance. Each would need a clear fairness rule before implementation.

## License

BenchFair is available under the [MIT License](LICENSE).
