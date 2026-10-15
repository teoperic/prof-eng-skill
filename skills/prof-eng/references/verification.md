# Verification rules

A wrong answer that a student then studies from is the worst outcome of this skill. These rules decide how a solution is checked and which confidence label it may carry. A label must describe what was actually checked, and nothing more. When in doubt, use the lower label and say why.

## 1. Read the statement first

Read the statement and every figure carefully before solving. Write the given values exactly as read from the PDF next to the page link, in the `Given` line:

```markdown
**Given (as read from page 2):** $R_1 = 4\,\Omega$, $R_2 = 6\,\Omega$, $C = 10\,\mu\text{F}$, $u(0^-) = 0$, switch closes at $t = 0$.
```

Copy values with their units and signs exactly as printed, including the ones you think are irrelevant. Most wrong answers come from a misread statement or figure, which no code check can catch. If a digit, sign or label is unclear, say so in the `Given` line ("$R_2 = 6\,\Omega$ (could be 8; scan unclear)") and apply rule 7.

## 2. Solve with the course's methods

Use only methods taught in the lectures, or the book where the lectures point to it. Cite the lecture section for each step (`[L07 §2](../notes/L07-laplace-transform.md#2.%20Partial%20fractions)`). Follow `Preferred methods` in `CLAUDE.md`. If the lectures do not cover the method needed, say so:

```markdown
> [!warning] Method not covered in the lectures: this solution uses the Z-transform, which no lecture note teaches yet.
```

and set the confidence to `uncertain`.

## 3. Check computations with code

For computational problems, check the algebra and the numbers with code, using only the tools `runtime` in `CLAUDE.md` allows:

| `runtime` | Check with | File |
|---|---|---|
| `python` | Python 3 (sympy if installed, otherwise numeric with the standard library) | `.py` |
| `python+matlab` | Python, or MATLAB via `matlab -batch "run('file.m')"` | `.py` or `.m` |
| `other: <tools>` | the tools the user named | that tool's extension |

Save every check to `solutions/checks/<source>-Q<n>.<ext>` (exams) or `solutions/checks/hw-Lxx-P<n>.<ext>` (homework). Start the file with the given values as comments, so it can be audited and rerun:

```python
# Check for exam 2023-jan Q1 (solutions/exam-2023-jan.md#Q1%20solution)
# Given (page 2): R = 4 Ohm, C = 10 uF, V0 = 5 V
R, C, V0 = 4.0, 10e-6, 5.0
tau = R * C
print("tau =", tau)          # solution says 4e-05 s
assert abs(tau - 4e-5) < 1e-12
```

Run it and record in the solution's **Check** line what was run and whether it agreed. If the chosen tool is not installed or fails to run, check by hand, say so in the **Check** line, and cap the confidence at `consistent-with-lectures`.

## 4. Units and sanity

Always check units through the final result, and do a sanity check: limiting cases ($t \to 0$, $t \to \infty$, $R \to 0$), signs and directions, orders of magnitude. Write one line about each in the **Check** line.

## 5. Confidence labels

| Label | Use it only when | It does not mean |
|---|---|---|
| `algebra-checked` | saved code actually ran and agrees with the solution | that the statement or figure was read correctly |
| `matches-solution` | the independent solve agrees with a provided solution file (`exams/<exam>-solution.*`) or the book's solution | that the solution file is correct (it may be student-made) |
| `consistent-with-lectures` | the method and result match the lectures, without a code check | that the numbers were verified |
| `uncertain` | attempts disagree; the solve disagrees with the lectures, a solution file or the book; the statement is unclear; or the verifier reported a problem that was not fixed | that the solution is wrong: it needs a spot-check |

If two labels apply (code ran and agrees, and a solution file agrees), use `matches-solution` and mention the code check in the **Check** line. Any reason for `uncertain` overrides every other label.

A solution file is read only after solving, and only to compare. Never copy it into the solve.

## 6. Disagreement

When two attempts disagree (two solves, the solve and a solution file, the generator and the verifier), keep the better-supported one, mark `uncertain`, and note the alternative and why it was not chosen:

```markdown
**Confidence:** uncertain. The solution file gives $\tau = 0.4$ ms; this solve gives $0.04$ ms. The difference is a factor of 10 in $C$: the scan shows "10 µF", which matches $0.04$ ms.
```

## 7. Ambiguity

If a statement is ambiguous or a figure is unreadable, do not solve a guessed version silently. State the assumption at the top of the solution, solve under it, and flag `uncertain`:

```markdown
> [!question] Assumption: the switch in figure 2 is read as opening at $t = 0$ (the arrow is unclear in the scan).
```

## 8. Verifier sub-agent

The verifier (SKILL.md rule 15) works only from the source PDF pages, the extractions in `.prof-eng-work/<target>/`, and the written files. For a solution file it must:

1. compare every `Given` line with the source page, value by value;
2. recompute each final result independently, without reading or reusing the generator's code in `solutions/checks/`;
3. check that each confidence label matches what was actually run (for `algebra-checked`, the check file exists and its recorded result agrees);
4. check that every cited lecture section exists and teaches the step it is cited for.

A disagreement the verifier finds counts as "two attempts disagree" (item 6).
