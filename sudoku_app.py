import json
import time
import streamlit as st
from utils import *
from logic_ import *
from sudoku_solver import (
    atom,
    build_definite_kb,
    build_general_kb,
    solve_full_grid_fc,
    solve_full_grid_bc,
    pl_bc_entails,
)

st.title('Sudoku Solver')

with open('puzzles.json') as f:
    pool = json.load(f)

# --- 1. Puzzle selection & visual board display ---
n, box_h, box_w = pool['n'], pool['box_h'], pool['box_w']

st.sidebar.header('Settings')
option = st.sidebar.selectbox(
    "Puzzle selection",
    (i for i in range(1, len(pool['puzzles']) + 1))
)

# givens keyed as (row, col), 1-indexed, to match the solver's expected input
givens = {
    tuple(int(x) for x in k.split('_')): v
    for k, v in pool['puzzles'][option - 1]['givens'].items()
}


def render_grid(values, givens, target=st):
    """Render an n x n grid as an HTML table with thick box borders.

    values : dict[(int, int), int] -- cells to display
    givens : dict[(int, int), int] -- cells to show in bold
    target : where to draw it; pass an st.empty() to replace what's there
    """
    rows = []
    for r in range(1, n + 1):
        cells = []
        for c in range(1, n + 1):
            style = [
                'width:2.2em', 'height:2.2em', 'text-align:center',
                'font-size:1.2em', 'border:1px solid #999',
            ]
            if r % box_h == 1 or box_h == 1:
                style.append('border-top:3px solid currentColor')
            if r == n:
                style.append('border-bottom:3px solid currentColor')
            if c % box_w == 1 or box_w == 1:
                style.append('border-left:3px solid currentColor')
            if c == n:
                style.append('border-right:3px solid currentColor')

            v = values.get((r, c), '')
            if (r, c) in givens:
                text = f'<b>{v}</b>'
            else:
                text = f'<span style="color:#1f77b4">{v}</span>'
            cells.append(f'<td style="{";".join(style)}">{text}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    target.markdown(
        f'<table style="border-collapse:collapse">{"".join(rows)}</table>',
        unsafe_allow_html=True,
    )


st.header(f'Puzzle {option}')
# one board: shows the givens now, redrawn with the solution once solved
board = st.empty()
render_grid(givens, givens, board)

# --- 2. Full-grid auto-solver, with algorithm selection ---
# TODO: a radio/selectbox letting the user choose forward chaining
# (solve_full_grid_fc) or backward chaining (solve_full_grid_bc).
# TODO: a button that times and calls the chosen solver on
# (n, box_h, box_w, givens), then displays the solved grid and the elapsed
# time.

# --- 3. Targeted cell entailment query ---
# TODO: number inputs for row (r), column (c), value (v).
# TODO: a button that builds the definite KB, calls
# pl_bc_entails(kb, atom('Is', r, c, v)), and displays True/False.

# --- 4. Reasoning trace ("tutor mode") ---
# TODO: instrument your forward- or backward-chaining approach to record each
# reasoning step (which rule fired, on what premises, producing what
# conclusion) as it answers the query above.
# TODO: render that trace as human-readable output -- e.g. a sequence of
# st.expander(...) blocks, one per step, each with a plain-English sentence
# -- not a raw list/dict dump.
#
# Keep the core solver functions in sudoku_solver.py; do not duplicate them here.
