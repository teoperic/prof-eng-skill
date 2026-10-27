#!/usr/bin/env python3
"""Generate a small synthetic subject folder for testing prof-eng.

Usage: make_fixtures.py <out_dir> [--with-samples]   -> creates <out_dir>/Demo-Subject/

Everything is synthetic plain text: no real course material. The folder holds
the sources a user would add before `/prof-eng init`: two lectures, one exam
plus its `-solution` file (which must never be selected as an exam), one
homework sheet and a small book. Point Claude Code at it to try the skill.

--with-samples also writes what the skill would have generated for lecture 2
with `output_format: pdf`: CLAUDE.md, a note, its cheatsheet, an exam
solution, the open-book index and its print version (SAMPLES). Together they
use every Markdown construct the PDF converter supports, and they pass
check_links.py and check_coverage.py. The PDF tests build them.
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfgen import write_pdf  # noqa: E402

SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "prof-eng")

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
        ["Agenda", "1. Time constant", "2. Step response"],
        ["Capacitor", "i = C du/dt"],
        ["Time constant", "tau = R C"],
        ["Units", "Ohm * F = s"],
        ["Example", "R = 1 kOhm, C = 1 uF", "tau = 1 ms"],
        ["Charging circuit", "source U0, switch, R in series with C"],
        ["Time constant from the graph", "u reaches 63 % of U0 after tau"],
        ["Step response", "u(t) = U0 (1 - exp(-t/tau))"],
        ["Current", "i(t) = U0/R exp(-t/tau)"],
        ["After 5 tau", "the capacitor is 99 % charged"],
        ["Example", "U0 = 10 V, tau = 1 ms", "u(1 ms) = 6.3 V"],
        ["Discharging", "u(t) = U0 exp(-t/tau)"],
        ["Energy", "W = C u^2 / 2"],
        ["Common mistake", "kOhm times uF gives ms, not s"],
        ["Summary", "tau = R C sets every time scale"],
        ["Exam-style problem", "R = 2 kOhm, C = 5 uF: find tau"],
        ["Solution", "tau = 10 ms"],
        ["Further reading", "Demo Circuits Book, chapter 2"],
        ["Thank you"],
    ],
}

EXAM = [
    ["Exam 2023-jan", "Duration 90 min, 20 points", "Calculator allowed"],
    ["Q1 (10 pts)", "R1 = 4 Ohm and R2 = 6 Ohm in series.", "Applied voltage u = 20 V.", "Find the current i."],
    ["Q2 (10 pts)", "R = 2 kOhm, C = 5 uF.", "Find the time constant tau."],
]

EXAM_SOLUTION = [
    ["Solution 2023-jan (student made)"],
    ["Q1: i = 2 A", "Q2: tau = 10 ms"],
]

HOMEWORK = [
    ["Homework 1"],
    ["P1: R1 = 3 Ohm, R2 = 5 Ohm in series.", "Current i = 1 A. Find the voltage u."],
]

BOOK = [
    ["Demo Circuits Book"],
    ["Contents", "1 Resistors .......... 1", "2 Capacitors ......... 3"],
    ["1 Resistors", "printed page 1"],
    ["Ohm's law derivation", "printed page 2"],
    ["2 Capacitors", "printed page 3"],
    ["RC worked example with solution", "printed page 4"],
]

# ---- generated files (--with-samples) ----

CLAUDE_FIELDS = {  # template line start -> value in the sample
    "conventions_status:": "approved",
    "runtime:": "python",
    "exam_format:": "open",
    "exam_aids:": "[calculator]",
    "print_version:": "yes",
    "book:": "book/demo-book.pdf",
    "output_format:": "pdf",
}

NOTE = """\
---
course: Demo Circuits & Systems
lecture: 2
title: RC circuits
source: ../slides/L02-rc-circuits.pdf
slides: 20
status: draft        # draft | reviewed
tags: [lecture]
prerequisites: [L01]
---
# L02 – RC circuits

> [!abstract] Summary
> The capacitor voltage follows a step with time constant $\\tau = RC$ (see [§2](#2.%20Step%20response)).

## Learning objectives
- Derive the **step response**; compute *time constants* with µs, Ω, °C, τ ≈ 1 ms.
  - nested item with $x_1$
- Use `tau` and the #hashtag & under_score.

## Core content
### 1. Time constant
(Slides 3–8: [slide 3](../slides/L02-rc-circuits.pdf#page=3))

The time constant is defined by

$$
\\tau = R\\,C
$$

The [cheatsheet card](../cheatsheets/L02-cheatsheet.md#R2%20–%20Time%20constant%20of%20an%20RC%20circuit) and [a site](https://example.org/a_b?x=1&y=2#frag).

> [!important] Key result
> The time constant is $\\tau = RC$.

> [!example] Worked example (slide 6)
> $R = 1\\,\\text{k}\\Omega$ and $C = 1\\,\\mu\\text{F}$ give $\\tau = 1\\,\\text{ms}$.

> [!warning] Common mistake
> kΩ times µF gives ms, not s (slide 15).

> [!info] From the book (p. 4)
> A worked RC example with its solution. [Book p. 4](../book/demo-book.pdf#page=6)

> [!note]- Why "time constant"
> After one $\\tau$ the voltage has covered 63 % of the step (slide 8).

> [!question] Slide 5: the unit of the product is unreadable.

Figure (slide 7): the charging circuit, a source $U_0$ with a switch and $R$ in series with $C$. [Slide 7](../slides/L02-rc-circuits.pdf#page=7)

![Slide 7](img/L02-s07.png)

#### Check in MATLAB
```matlab
R = 1e3; C = 1e-6;
tau = R*C   % 1 ms
```

```mermaid
graph LR
  A[Input] --> B[RC]
```

---

### 2. Step response
(Slides 9–14: [slide 9](../slides/L02-rc-circuits.pdf#page=9))

The capacitor voltage and current after a step are

$$
\\begin{aligned}
u(t) &= U_0\\,(1 - e^{-t/\\tau}) \\\\
i(t) &= \\frac{U_0}{R}\\, e^{-t/\\tau}
\\end{aligned}
$$

To sketch it:
1. Mark $U_0$ and $\\tau$ on the axes.
2. Draw the tangent at $t = 0$; it reaches $U_0$ at $t = \\tau$.
   - The curve reaches 99 % after $5\\tau$ (slide 11).

## Formula box
| Formula | Meaning | Section |
|---|---|---|
| $\\tau = RC$ | time constant | [1. Time constant](#1.%20Time%20constant) |
| $u(t) = U_0\\,(1 - e^{-t/\\tau})$ | step response | [2. Step response](#2.%20Step%20response) |

## Self-test
1. What is $\\tau$ for $R = 1\\,\\text{k}\\Omega$, $C = 1\\,\\mu\\text{F}$, and $τ_1, …, τ_n$ – in µs?

> [!tip]- Answer
> $\\tau = 1\\,\\text{ms}$.

## Slide coverage
| Slides | Section |
|---|---|
| 1 | skipped (title) |
| 2 | skipped (agenda) |
""" + "".join(f"| {n} | 1. Time constant |\n" for n in range(3, 9)) \
    + "".join(f"| {n} | 2. Step response |\n" for n in range(9, 15)) \
    + "".join(f"| {n} | skipped (outlook) |\n" for n in range(15, 21))

CHEATSHEET = """\
# L02 – RC circuits – cheatsheet
> [!info] Built from: 1 exams. Note: [L02 – RC circuits](../notes/L02-rc-circuits.md)

## Recipes
### R2 – Time constant of an RC circuit
**Frequency:** 1 of 1 exams · typically 10 pts
**Recognize it:** the question gives $R$ and $C$ and asks for $\\tau$.
**Steps:**
1. Write $\\tau = RC$.
2. Convert units.

**Key formulas:** $\\tau = RC$
**Mini example:** $R = 2\\,\\text{k}\\Omega$, $C = 5\\,\\mu\\text{F}$ give $\\tau = 10\\,\\text{ms}$.
**Pitfalls:** kΩ · µF = ms.
**Go deeper:** [L02 – 1. Time constant](../notes/L02-rc-circuits.md#1.%20Time%20constant)
**Confidence:** algebra-checked

## Formulas and constants
| Formula | Meaning | Unit |
|:---|:---:|---:|
| $\\tau = RC$ | time constant | s |

## Conflicts
None so far.
"""

SOLUTION = """\
---
exam: 2023-jan
source: ../exams/2023-jan.pdf
status: reviewed
questions: 2
---
# Exam 2023-jan – solutions

> [!tip] Try each question before scrolling to its solution.

## Questions
### Q1 (10 pts) – type R1
**Statement:** $R_1 = 4\\,\\Omega$ and $R_2 = 6\\,\\Omega$ in series, applied voltage $u = 20\\,\\text{V}$. Find the current $i$. [Page 2](../exams/2023-jan.pdf#page=2)

### Q2 (10 pts) – type R2
**Statement:** $R = 2\\,\\text{k}\\Omega$, $C = 5\\,\\mu\\text{F}$. Find $\\tau$. [Page 3](../exams/2023-jan.pdf#page=3)

## Solutions
### Q1 solution
**Lectures:** [L01, slide 4](../slides/L01-ohms-law.pdf#page=4)
**Solution:**
1. $R = R_1 + R_2 = 10\\,\\Omega$.
2. $i = u / R = 2\\,\\text{A}$.

**Check:** units V/Ω = A.
**Confidence:** matches-solution

### Q2 solution
**Lectures:** [L02 – 1. Time constant](../notes/L02-rc-circuits.md#1.%20Time%20constant)
**Solution:**
1. $\\tau = RC = 10\\,\\text{ms}$.

**Check:** units Ω·F = s, [the check](checks/2023-jan-Q2.py).
**Confidence:** matches-solution
"""

CHECK = """\
tau = 2e3 * 5e-6
assert abs(tau - 10e-3) < 1e-12
print("Q2 ok: tau =", tau)
"""

EXAM_SHEET = """\
# Demo – exam sheet (open book)
> [!info] Built from: 1 notes, 1 cheatsheets, 1 exams.

## How to use
1. Find the row below whose left column matches what the question asks.
2. Open the linked card and follow its **Steps**.

## Find the right cheatsheet
| If the question asks for … | Type | Frequency | Go to |
|---|---|---|---|
| $\\tau$ from $R$ and $C$ | R2 | 1 of 1 exams | [L02 cheatsheet – R2](cheatsheets/L02-cheatsheet.md#R2%20–%20Time%20constant%20of%20an%20RC%20circuit) |

## By lecture
| Lecture | Cheatsheet | Note |
|---|---|---|
| L02 – RC circuits | [L02 cheatsheet](cheatsheets/L02-cheatsheet.md) | [L02 note](notes/L02-rc-circuits.md) |

## When stuck
- Try a limiting case to check a result.
"""

EXAM_SHEET_PRINT = """\
# Demo – exam sheet (print)

## Find the right cheatsheet
| If the question asks for … | Type | Frequency | Go to |
|---|---|---|---|
| $\\tau$ from $R$ and $C$ | R2 | 1 of 1 exams | L02 cheatsheet, R2 |

# L02 – RC circuits – cheatsheet

## Recipes
### R2 – Time constant of an RC circuit
**Frequency:** 1 of 1 exams · typically 10 pts
**Steps:**
1. Write $\\tau = RC$.
2. Convert units.

**Key formulas:** $\\tau = RC$
"""

SAMPLES = {  # the files with a PDF version
    "notes/L02-rc-circuits.md": NOTE,
    "cheatsheets/L02-cheatsheet.md": CHEATSHEET,
    "solutions/exam-2023-jan.md": SOLUTION,
    "EXAM-SHEET.md": EXAM_SHEET,
    "EXAM-SHEET-print.md": EXAM_SHEET_PRINT,
}


def write_png(path):
    """A valid 4x4 white PNG (pdflatex reads the real image format)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    raw = b"".join(b"\x00" + b"\xff" * 12 for _ in range(4))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def claude_md():
    """The skill's CLAUDE.md template with the sample's settings."""
    with open(os.path.join(SKILL, "templates", "CLAUDE.md"), encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    for start, value in CLAUDE_FIELDS.items():
        index = next(i for i, line in enumerate(lines) if line.startswith(start))
        lines[index] = f"{start} {value}"
    return "\n".join(lines)


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


def write_samples(root):
    """Add the generated files of SAMPLES (plus CLAUDE.md, image and check) to a subject."""
    write_text(os.path.join(root, "CLAUDE.md"), claude_md())
    for rel, text in SAMPLES.items():
        write_text(os.path.join(root, rel), text)
    write_png(os.path.join(root, "notes", "img", "L02-s07.png"))
    write_text(os.path.join(root, "solutions", "checks", "2023-jan-Q2.py"), CHECK)


if __name__ == "__main__":
    args = sys.argv[1:]
    samples = "--with-samples" in args
    args = [a for a in args if a != "--with-samples"]
    if len(args) != 1:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        sys.exit(2)
    subject = make_subject(args[0])
    if samples:
        write_samples(subject)
    print(subject)
