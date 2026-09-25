"""IT5005 Assignment 1: student implementation file.

Implement the functions marked below. Do not modify utils.py or logic_.py.
"""

import sys
from collections import defaultdict

from utils import *
from logic_ import *


# Do not change this function; it is used to create atomic propositions.
def atom(prefix, r, c, v):
    """prefix is 'Is' or 'Not'. Returns the Expr for e.g. Is3_2_4."""
    return expr(f'{prefix}{r}_{c}_{v}')


def build_general_kb(n, box_h, box_w, givens):
    """Return a PropKB encoding this n x n Sudoku's constraints plus the given
    cells, as general clauses.

    Parameters
    ----------
    n, box_h, box_w : int
    givens : dict[(int, int), int]

    Returns
    -------
    PropKB
    """
    kb = PropKB()

    # every cell has at least one value from 1...n      -- n^2 clauses
    for i in range(1, n+1):
        for j in range(1, n+1):
            at_least_one = [atom('Is', i, j, k) for k in range(1, n+1)]
            kb.tell('|'.join([str(exp) for exp in at_least_one]))

    # every cell has at most one value from 1...n       -- n^3(n-1)/2 clauses
    # Redundant: with the clauses above, n cells per row and each value used
    # at most once per row leave no room for a cell to take two values. Stated
    # anyway, because it is a rule of the puzzle and dropping it would only
    # weaken propagation.
    for i in range(1, n+1):
        for j in range(1, n+1):
            for k in range(1, n+1):
                for l in range(k+1, n+1):
                    kb.tell(f'~{atom("Is", i, j, k)} | ~{atom("Is", i, j, l)}')

    # no two cells in the same row hold the same value  -- n^3(n-1)/2 clauses
    for i in range(1, n+1):
        for j in range(1, n+1):
            for j2 in range(j+1, n+1):
                for k in range(1, n+1):
                    kb.tell(f'~{atom("Is", i, j, k)} | ~{atom("Is", i, j2, k)}')

    # no two cells in the same column hold the same value   -- n^3(n-1)/2
    for j in range(1, n+1):
        for i in range(1, n+1):
            for i2 in range(i+1, n+1):
                for k in range(1, n+1):
                    kb.tell(f'~{atom("Is", i, j, k)} | ~{atom("Is", i2, j, k)}')

    # no two cells in the same box hold the same value  -- n^3(n+1-h-w)/2
    # Box pairs that share a row or column are skipped: the loops above have
    # already told that exact clause, so this is deduplication, not the
    # dropping of an implied clause.
    for r in range(1, n+1, box_h):
        for c in range(1, n+1, box_w):
            cells = [(r + dr, c + dc) for dr in range(box_h) for dc in range(box_w)]
            for a in range(len(cells)):
                for b in range(a+1, len(cells)):
                    (r1, c1), (r2, c2) = cells[a], cells[b]
                    if r1 == r2 or c1 == c2:
                        continue
                    for k in range(1, n+1):
                        kb.tell(f'~{atom("Is", r1, c1, k)} | ~{atom("Is", r2, c2, k)}')

    # given cells hold their stated values
    for (r, c), v in givens.items():
        kb.tell(atom('Is', r, c, v))

    return kb


def build_definite_kb(n, box_h, box_w, givens):
    """Return a PropDefiniteKB encoding this n x n Sudoku's constraints plus
    the given cells, using elimination + last-candidate reasoning.

    Parameters
    ----------
    n, box_h, box_w : int
    givens : dict[(int, int), int] -- {(row, col): value}, 1-indexed

    Returns
    -------
    PropDefiniteKB
    """
    kb = PropDefiniteKB()

    # every cell has at most one value from 1...n: holding k rules out every
    # other value in that cell                         -- n^3(n-1) clauses
    for i in range(1, n+1):
        for j in range(1, n+1):
            for k in range(1, n+1):
                for l in range(1, n+1):
                    if l == k:
                        continue
                    kb.tell(expr(f'{atom("Is", i, j, k)} ==> {atom("Not", i, j, l)}'))

    # every cell has at least one value from 1...n, so once the other n-1
    # values are ruled out, k is the last candidate    -- n^3 clauses
    # This is the Horn stand-in for the general KB's at-least-one clause: a
    # bare disjunction is not a definite clause, so it is stated as the only
    # inference it can soundly drive.
    for i in range(1, n+1):
        for j in range(1, n+1):
            for k in range(1, n+1):
                ruled_out = [atom('Not', i, j, l)
                             for l in range(1, n+1) if l != k]
                premise = ' & '.join([str(exp) for exp in ruled_out])
                kb.tell(expr(f'{premise} ==> {atom("Is", i, j, k)}'))

    # no two cells in the same row hold the same value -- n^3(n-1) clauses
    # Ordered pairs, unlike the general KB: an implication only fires one way,
    # so both directions have to be stated separately.
    for i in range(1, n+1):
        for j in range(1, n+1):
            for j2 in range(1, n+1):
                if j2 == j:
                    continue
                for k in range(1, n+1):
                    kb.tell(expr(f'{atom("Is", i, j, k)} ==> {atom("Not", i, j2, k)}'))

    # no two cells in the same column hold the same value  -- n^3(n-1)
    for j in range(1, n+1):
        for i in range(1, n+1):
            for i2 in range(1, n+1):
                if i2 == i:
                    continue
                for k in range(1, n+1):
                    kb.tell(expr(f'{atom("Is", i, j, k)} ==> {atom("Not", i2, j, k)}'))

    # no two cells in the same box hold the same value -- n^3(n+1-h-w)
    # Same deduplication as the general KB: pairs sharing a row or column
    # would repeat a clause already told above.
    for r in range(1, n+1, box_h):
        for c in range(1, n+1, box_w):
            cells = [(r + dr, c + dc) for dr in range(box_h) for dc in range(box_w)]
            for a in range(len(cells)):
                for b in range(len(cells)):
                    (r1, c1), (r2, c2) = cells[a], cells[b]
                    if r1 == r2 or c1 == c2:
                        continue
                    for k in range(1, n+1):
                        kb.tell(expr(f'{atom("Is", r1, c1, k)} ==> {atom("Not", r2, c2, k)}'))

    # given cells hold their stated values
    for (r, c), v in givens.items():
        kb.tell(atom('Is', r, c, v))

    return kb

def peers(r, c, n, box_h, box_w):
    """Return the cells sharing a row, column, or box with (r, c)."""
    cells = {(r, j) for j in range(1, n+1)} | {(i, c) for i in range(1, n+1)}
    box_r = (r - 1) // box_h * box_h + 1
    box_c = (c - 1) // box_w * box_w + 1
    cells |= {(box_r + dr, box_c + dc)
              for dr in range(box_h) for dc in range(box_w)}
    cells.discard((r, c))
    return cells


class RecordingDefiniteKB(PropDefiniteKB):
    """A PropDefiniteKB that remembers what pl_fc_entails derived.

    pl_fc_entails calls clauses_with_premise(p) exactly once for every symbol
    it newly infers, so overriding it lets us record each derived symbol --
    all of them entailed, so reusing them in later queries is sound. It also
    answers from a premise index instead of rescanning every clause, which is
    what made each forward pass quadratic in the KB size.
    """

    def __init__(self, sentence=None):
        self.derived = set()
        self._index = defaultdict(list)
        super().__init__(sentence)

    def tell(self, sentence):
        super().tell(sentence)
        if sentence.op == '==>':
            # one entry per clause, even if a premise repeats, to match the
            # list the unindexed version would return
            for p in set(conjuncts(sentence.args[0])):
                self._index[p].append(sentence)

    def clauses_with_premise(self, p):
        self.derived.add(p)
        return self._index.get(p, [])


def build_recording_kb(n, box_h, box_w, givens):
    """Same clauses as build_definite_kb, held in a RecordingDefiniteKB.

    Returns
    -------
    RecordingDefiniteKB
    """
    kb = RecordingDefiniteKB()
    for clause in build_definite_kb(n, box_h, box_w, givens).clauses:
        kb.tell(clause)
    return kb


def justifications(kb):
    """Return kb's record of how each derived symbol was first derived.

    Both pl_fc_entails_cached and pl_bc_entails write to it whenever a rule
    fires, as {conclusion: premises of the rule that derived it}. Only
    derived symbols appear -- facts told to the KB never do -- and entries
    are kept in the order they were derived, so the premises of every entry
    come before it (or are facts). That is what lets a solve be replayed step
    by step, and a single proof be traced back to the facts.

    It is kept on the KB and carries over between calls, like the rest of
    each algorithm's saved state, and is dropped if clauses are retracted,
    since a derivation may then no longer hold.

    Parameters
    ----------
    kb : PropDefiniteKB

    Returns
    -------
    dict[Expr, list[Expr]]
    """
    seen, why = getattr(kb, '_why', (0, {}))
    if seen > len(kb.clauses):
        why = {}
    kb._why = (len(kb.clauses), why)
    return why


def pl_fc_entails_cached(kb, q):
    """pl_fc_entails that keeps its work between calls on the same KB.

    The library version rebuilds its counters from scratch on every call,
    scans every clause for each symbol it infers, and throws away everything
    it derived once it returns. A definite KB only ever grows, so none of that
    work goes stale: this version stores the counters, a premise -> rule
    index, the inferred set and the unfinished agenda on the KB, and each call
    resumes where the last one stopped. Clauses told since the last call are
    folded in first.

    Parameters
    ----------
    kb : PropDefiniteKB
    q : Expr

    Returns
    -------
    bool
    """
    why = justifications(kb)
    seen, count, uses, inferred, agenda, facts = getattr(
        kb, '_fc_state', (0, [], defaultdict(list), set(), [], set()))
    if seen > len(kb.clauses):
        # clauses were retracted; anything inferred may no longer hold
        seen, count, uses, inferred, agenda, facts = (
            0, [], defaultdict(list), set(), [], set())

    for c in kb.clauses[seen:]:
        if is_prop_symbol(c.op):
            facts.add(c)
            agenda.append(c)
            continue
        # counters are per rule position, not keyed by the clause itself, so
        # duplicate clauses each get their own counter
        i = len(count)
        premises, conclusion = parse_definite_clause(c)
        waiting = set(premises) - inferred
        count.append((len(waiting), conclusion, premises))
        for p in waiting:
            uses[p].append(i)
        if not waiting:
            # every premise was already inferred before this rule arrived
            agenda.append(conclusion)
            if conclusion not in facts:
                why.setdefault(conclusion, premises)

    kb._fc_state = (len(kb.clauses), count, uses, inferred, agenda, facts)

    while q not in inferred and agenda:
        p = agenda.pop()
        if p in inferred:
            continue
        inferred.add(p)
        # p is fully propagated before we stop, so the saved state is always
        # consistent for the next call to resume from
        for i in uses.pop(p, ()):
            remaining, conclusion, premises = count[i]
            count[i] = (remaining - 1, conclusion, premises)
            if remaining == 1:
                agenda.append(conclusion)
                # the first rule to fire is the derivation kept; a fact
                # needs none, even if a rule also concludes it
                if conclusion not in facts:
                    why.setdefault(conclusion, premises)

    return q in inferred


def solve_full_grid_fc(n, box_h, box_w, givens):
    """Solve the whole puzzle using build_definite_kb + pl_fc_entails.

    For every unsolved cell, ask pl_fc_entails which value is entailed and
    take the first one it confirms, so every value in the result is one
    forward chaining derived from the KB.

    Returns
    -------
    dict[(int, int), int] -- {(row, col): value} for every cell
    """
    kb = build_definite_kb(n, box_h, box_w, givens)
    output = {}

    for k, v in givens.items():
        output[k] = v

    for r in range(1, n+1):
        for c in range(1, n+1):
            # skip values already known
            if (r,c) in output:
                continue
            # A value already held by a peer cannot be entailed here: the KB's
            # row/column/box clauses give Not{r}_{c}_{v}, so the query would cost a
            # full forward pass only to come back False. Skip it.
            # this cuts from 40min -> 10min
            taken = {output[p] for p in peers(r, c, n, box_h, box_w)
                     if p in output}
            for v in range(1, n+1):
                if v in taken:
                    continue
                result = pl_fc_entails(kb, atom('Is', r, c, v))
                if result:
                    # Re-asserting an entailed fact is sound, and it puts the
                    # symbol at the end of kb.clauses, so pl_fc_entails pops it
                    # early and later queries hit its early exit sooner.
                    kb.tell(atom("Is", r, c, v))
                    output[(r, c)] = v
                    break

    return output


def solve_full_grid_fc_recording(n, box_h, box_w, givens):
    """solve_full_grid_fc, backed by build_recording_kb.

    Same per-cell strategy, but a value some earlier pl_fc_entails call
    already derived is taken from kb.derived instead of asking again: one
    forward pass solves most of the grid on its way to the first query.

    Returns
    -------
    dict[(int, int), int] -- {(row, col): value} for every cell
    """
    kb = build_recording_kb(n, box_h, box_w, givens)
    output = dict(givens)

    for r in range(1, n+1):
        for c in range(1, n+1):
            if (r, c) in output:
                continue
            taken = {output[p] for p in peers(r, c, n, box_h, box_w)
                     if p in output}
            for v in range(1, n+1):
                if v in taken:
                    continue
                query = atom('Is', r, c, v)
                if query in kb.derived or pl_fc_entails(kb, query):
                    kb.tell(query)
                    output[(r, c)] = v
                    break

    return output


def solve_full_grid_fc_cached(n, box_h, box_w, givens, kb=None):
    """solve_full_grid_fc, backed by pl_fc_entails_cached.

    Same per-cell strategy and the same KB; the only change is that forward
    chaining keeps what it derived between queries, so the whole grid costs
    about one forward pass instead of one per query.

    Parameters
    ----------
    kb : PropDefiniteKB, optional -- a KB from build_definite_kb for these
        givens, to solve on instead of building one; pass it to read the
        reasoning back afterwards with justifications(kb)

    Returns
    -------
    dict[(int, int), int] -- {(row, col): value} for every cell
    """
    if kb is None:
        kb = build_definite_kb(n, box_h, box_w, givens)
    output = dict(givens)

    for r in range(1, n+1):
        for c in range(1, n+1):
            if (r, c) in output:
                continue
            taken = {output[p] for p in peers(r, c, n, box_h, box_w)
                     if p in output}
            for v in range(1, n+1):
                if v in taken:
                    continue
                if pl_fc_entails_cached(kb, atom('Is', r, c, v)):
                    output[(r, c)] = v
                    break

    return output


def bc_index(kb):
    """Return (facts, rules, proven) for kb, where rules maps a consequent to
    the list of premise lists that conclude it, and proven collects symbols
    already derived from it.

    pl_fc_entails walks facts forwards, so PropDefiniteKB only indexes clauses
    by premise. Backward chaining needs the opposite direction, and rebuilding
    it per query would dominate the run, so it is cached on the KB and extended
    in place as solve_full_grid_bc tells newly entailed facts. proven rides
    along because entailment is monotone -- telling more clauses can only add
    consequences -- so a symbol derived for one query stays derived for the
    next, which is what makes the per-cell queries share their work.
    """
    seen, facts, rules, proven = getattr(
        kb, '_bc_index', (0, set(), defaultdict(list), set()))
    if seen > len(kb.clauses):
        # clauses were retracted; entailment is no longer monotone, so neither
        # the index nor the derived symbols can be trusted
        seen, facts, rules, proven = 0, set(), defaultdict(list), set()

    for c in kb.clauses[seen:]:
        if is_prop_symbol(c.op):
            facts.add(c)
        elif c.op == '==>':
            premises, conclusion = parse_definite_clause(c)
            rules[conclusion].append(premises)

    kb._bc_index = (len(kb.clauses), facts, rules, proven)
    return facts, rules, proven


def pl_bc_entails(kb, query):
    """Your own backward-chaining implementation.

    Parameters
    ----------
    kb : PropDefiniteKB
    query : Expr

    Returns
    -------
    bool
    """
    facts, rules, proven = bc_index(kb)
    why = justifications(kb)

    # chains run Is -> Not -> Is -> ..., so a proof can stack up one frame per
    # symbol in the KB -- deeper than the interpreter's default allowance
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))

    active = set()   # goals on the current branch; reaching one again is a loop
    failed = set()   # goals that came up short during this pass only

    def prove(goal):
        if goal in facts or goal in proven:
            return True
        if goal in active or goal in failed:
            # either the goal is its own sub-goal, so this branch is circular
            # and offers no support, or this pass already came up short on it
            return False

        active.add(goal)
        for premises in rules.get(goal, ()):
            if all(prove(p) for p in premises):
                # a derivation only ever consumes true answers, which bottom
                # out in facts, so this holds no matter how we reached it
                proven.add(goal)
                # the rule that fired, kept for replaying the reasoning
                why[goal] = premises
                active.discard(goal)
                return True
        active.discard(goal)

        failed.add(goal)
        return False

    # A failure is only as good as the branch it was found on: a goal can come
    # up short while one of its ancestors is still open, yet be provable once
    # that ancestor is settled. Caching failures anyway keeps each pass linear
    # in the rules it touches; re-running the pass with those failures dropped
    # is what recovers the ones that were only conditionally false. Every pass
    # keeps whatever it proved, so a pass that proves nothing new is a fixed
    # point and the remaining failures are genuine.
    while True:
        settled = len(proven)
        failed.clear()
        if prove(query):
            return True
        if len(proven) == settled:
            return False


def proof_steps(kb, query):
    """Return the rule firings that derived query, in the order they apply.

    Call after pl_bc_entails or pl_fc_entails_cached has returned True for
    query on the same KB. Only the firings the proof of query depends on are
    returned, not everything the algorithm derived on the way. Every entry in
    justifications(kb) was derived after its premises, so following them back
    from query always ends at facts and never loops.

    Parameters
    ----------
    kb : PropDefiniteKB
    query : Expr

    Returns
    -------
    list[(list[Expr], Expr)] -- (premises, conclusion) pairs, premises
        proven before the conclusion that uses them; empty if query is a
        fact or has not been proven
    """
    why = justifications(kb)
    steps, done = [], set()

    def walk(goal):
        # facts have no entry, so the walk stops at them
        if goal in done or goal not in why:
            return
        done.add(goal)
        for p in why[goal]:
            walk(p)
        steps.append((why[goal], goal))

    walk(query)
    return steps


def bc_unproven_premises(kb, query):
    """For each rule concluding query, return its premises that the KB does
    not entail -- what is missing for query to be proven.

    pl_bc_entails stops at the first premise that fails, so the rest are
    asked about one by one here rather than read off its search.

    Parameters
    ----------
    kb : PropDefiniteKB
    query : Expr

    Returns
    -------
    list[list[Expr]] -- one list per rule concluding query
    """
    _, rules, _ = bc_index(kb)
    return [[p for p in premises if not pl_bc_entails(kb, p)]
            for premises in rules.get(query, ())]


def solve_full_grid_bc(n, box_h, box_w, givens, kb=None):
    """Solve the whole puzzle using build_definite_kb + your own pl_bc_entails.

    For each cell, try each candidate value until pl_bc_entails confirms one
    -- the same per-cell strategy as solve_full_grid_fc, but backed by
    backward chaining instead of a single shared forward-chaining pass.

    Parameters
    ----------
    kb : PropDefiniteKB, optional -- a KB from build_definite_kb for these
        givens, to solve on instead of building one; pass it to read the
        reasoning back afterwards with justifications(kb)

    Returns
    -------
    dict[(int, int), int] -- {(row, col): value} for every cell
    """
    if kb is None:
        kb = build_definite_kb(n, box_h, box_w, givens)
    output = {}

    for k, v in givens.items():
        output[k] = v

    for r in range(1, n+1):
        for c in range(1, n+1):
            # skip values already known
            if (r, c) in output:
                continue
            # same pruning as the forward chaining solver: a value held by a
            # peer cannot be entailed here, so asking would only walk the
            # whole rule graph to come back False
            taken = {output[p] for p in peers(r, c, n, box_h, box_w)
                     if p in output}
            for v in range(1, n+1):
                if v in taken:
                    continue
                if pl_bc_entails(kb, atom('Is', r, c, v)):
                    # asserting an entailed fact is sound, and it lets later
                    # queries stop at a fact instead of re-deriving the chain
                    kb.tell(atom('Is', r, c, v))
                    output[(r, c)] = v
                    break

    return output
