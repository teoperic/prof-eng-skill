#!/usr/bin/env python3
"""Generate a small synthetic subject folder for testing prof-eng.

Usage: make_fixtures.py <out_dir>   -> creates <out_dir>/Demo-Subject/

Everything is synthetic plain text: no real course material. The folder holds
the sources a user would add before `/prof-eng init`: two lectures, one exam
plus its `-solution` file (which must never be selected as an exam), one
homework sheet and a small book. Point Claude Code at it to try the skill.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfgen import write_pdf  # noqa: E402

LECTURES = {
    "L01-ohms-law.pdf": [
        ["Lecture 1", "Ohm's law"],
        ["Agenda", "1. Voltage and current", "2. Resistance"],
        ["Ohm's law", "u = R i", "u: voltage in V, i: current in A"],
        ["Series resistors", "R = R1 + R2"],
        ["Example", "R = 4 Ohm, i = 2 A", "u = 8 V"],
        ["Thank you"],
    ],
    "L02-rc-circuits.pdf": [
        ["Lecture 2", "RC circuits"],
        ["Time constant", "tau = R C"],
        ["Step response", "u(t) = U0 (1 - exp(-t/tau))"],
        ["Example", "R = 1 kOhm, C = 1 uF", "tau = 1 ms"],
    ],
}

EXAM = [
    ["Exam 2023-jan", "Duration 90 min, 20 points", "Calculator allowed"],
    ["Q1 (10 pts)", "R1 = 4 Ohm and R2 = 6 Ohm in series, u = 20 V.", "Find the current i."],
    ["Q2 (10 pts)", "R = 2 kOhm, C = 5 uF.", "Find the time constant tau."],
]

EXAM_SOLUTION = [
    ["Solution 2023-jan (student made)"],
    ["Q1: i = 2 A", "Q2: tau = 10 ms"],
]

HOMEWORK = [
    ["Homework 1"],
    ["P1: R1 = 3 Ohm, R2 = 5 Ohm in series, i = 1 A. Find u."],
]

BOOK = [
    ["Demo Circuits Book"],
    ["Contents", "1 Resistors .......... 1", "2 Capacitors ......... 3"],
    ["1 Resistors", "printed page 1"],
    ["Ohm's law derivation", "printed page 2"],
    ["2 Capacitors", "printed page 3"],
    ["RC worked example with solution", "printed page 4"],
]


def make_subject(out_dir, name="Demo-Subject"):
    root = os.path.join(out_dir, name)
    for sub in ("slides", "exams", "homework", "book"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    for filename, pages in LECTURES.items():
        write_pdf(os.path.join(root, "slides", filename), pages)
    write_pdf(os.path.join(root, "exams", "2023-jan.pdf"), EXAM)
    write_pdf(os.path.join(root, "exams", "2023-jan-solution.pdf"), EXAM_SOLUTION)
    write_pdf(os.path.join(root, "homework", "hw01.pdf"), HOMEWORK)
    write_pdf(os.path.join(root, "book", "demo-book.pdf"), BOOK)
    return root


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        sys.exit(2)
    print(make_subject(sys.argv[1]))
