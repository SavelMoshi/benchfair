# Design notes

## Separate participation from pairing

Player selection determines **who gets to play**. Team formation determines
**with whom and against whom**. Keeping these steps separate prevents a good
pairing score from buying extra playing time for a favored player. It also lets
tests check the participation guarantee without relying on the heuristic.

Selection orders by `(games played, -current rest streak)`. A stable sort after
a seeded shuffle randomizes only exact ties. A dedicated `random.Random(seed)`
belongs to each scheduling call; no global state is read or modified. Sets are
used only for membership, never to determine scheduling order.

### Why the game-count spread stays at most one

Initially all counts are zero. Assume before a round the counts are either `m`
or `m + 1`. Let `L` players have count `m`, and let `K = 4 × courts` be the number
of available playing slots.

- If `K <= L`, select only players with count `m`; afterwards all counts remain
  in `{m, m + 1}`.
- If `K > L`, select every player with count `m`, then `K − L` players with count
  `m + 1`; afterwards all counts are in `{m + 1, m + 2}`.

Either way the spread is at most one. This induction depends on every player
being eligible every round, each selected player playing once, and always
selecting the lowest game counts first. It does not prove optimal waiting times
or pair variety. The tests verify the property over many concrete sessions.

## Pair histories and scoring

The scheduler uses two `Counter` objects: one for teammate pairs and one for
opponent pairs. A pair is the lexicographically ordered tuple of two names, so
`("Alex", "Blair")` and the reverse address the same history entry. One 2v2
match contributes two teammate occurrences and four opponent occurrences.

For each new occurrence of a pair previously used `k` times, the cost is:

```text
delta(k) = (k + 1)^2 - k^2 = 2k + 1
score = (sum of teammate deltas, sum of opponent deltas)
```

Scores compare lexicographically. This makes teammate cost the absolute first
priority; opponent cost breaks ties. Because every candidate has the same
number of pairs, the `+1` terms are constant within a round. The historical
counts still matter: another use of a heavily repeated pair costs more than a
second use of a pair seen once. Pairs occur at most once in a valid candidate
because selected players are disjoint across courts.

The report's repeat count, `max(0, k − 1)`, is deliberately a more interpretable
measure than the search cost. A lower squared-count cost is an objective for
this round, not a guarantee of the fewest reported repeats over the session.

## Bounded search

For each round, generate exactly **128** shuffled arrangements of the chosen
players. Partition each into groups of four and split each group in half. Keep
the lowest score, retaining the first candidate on ties. Duplicate candidates
are allowed; there is no unbounded retry or rejection loop.

Exhaustive search grows quickly even though court order and team order produce
equivalent arrangements. A fixed candidate budget keeps the implementation
small and work predictable across the supported limits. More candidates may
improve a round's score but also take more time and can change future history.
The constant is an explicit design choice, not a benchmark-derived optimum.

## Rough complexity

Let `N` be roster size, `C` courts, `R` rounds, and `B` candidate arrangements per
round (128). At most `4C <= N` players are active. Treat validated, bounded-length
names as constant-sized keys and hash lookups as average constant time.

- Selection: `O(N log N)` per round for sorting.
- Team formation and scoring: `O(BC)` per round.
- Whole scheduler: `O(R(N log N + BC))` time.
- Pair history: `O(N²)` space in the worst case. Counters/streaks require `O(N)`.
- Saved schedule: `O(RN)` space, including resting lists. Candidate storage is
  `O(C)` because only the current candidate and best arrangement are retained.
- Reporting: `O(RN + N²)` time, including per-round validation and the final
  pair-history scan. Report history is `O(N²)` space. Resting names are converted
  to a set for constant-time membership checks; roster order controls display.

No performance numbers or real-world adoption claims are implied by these bounds.

## Independent reporting and tests

The report sees only a finished schedule. It does not read the scheduler's
counters or call its pair-enumeration function. Its own `frozenset` pair keys
count unordered pairs, and its own scans collect games, rest streaks, teammates,
and opponents. Sets never affect displayed order; reports follow roster order.
Invalid membership, team sizes, and court counts are rejected. A valid manually
constructed schedule may be unbalanced; the report shows that honestly.

Tests check structural invariants and selection priorities across subtests,
including one and eight courts, odd rosters, and 100-round sessions. Separate
tests cover exact known pair costs, manually counted statistics, input failures,
Unicode, Markdown/JSON output, process exit codes, reproducibility, and isolation.
CI also checks generated samples and package installation on Python 3.11–3.15.

These tests establish the checked cases, not global optimality of the heuristic.
They do not assume every seed gives a unique result or that the heuristic beats
every random schedule. The balance argument above explains the wider property.

## Possible extensions

Skill ratings would belong in team scoring after defining how skill imbalance
trades off against pairing variety. Player selection could retain its current
participation priorities. Availability changes would instead alter selection
and require redefining fairness against eligible rounds or waiting time; the
current count-spread proof would no longer apply unchanged. Neither feature
needs a database or account system to explore locally.
